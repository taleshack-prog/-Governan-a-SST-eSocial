#!/usr/bin/env python3
"""Teste de aceitacao da SECAO 8 do Adendo 05 — PELA APLICACAO, nao por SQL.

A Carolina: "dois escritorios, cada um com uma empresa, e a confirmacao de que um usuario do
primeiro nao alcanca o dado do segundo — nem pela tela, nem por chamada direta, nem por
EXPORTACAO, nem alterando identificadores na barra de endereco."

O teste por SQL (feito em 16/10) provou a policy do banco. Este prova a aplicacao inteira: a
API real, com autenticacao real, conectando como radar_app (sem superuser, sem bypassrls),
contra o esquema construido pelas migrations de verdade.

A "tela" nao e exercida com navegador de proposito: toda tela consome estes mesmos endpoints,
entao o que fecha aqui fecha la. O que o navegador acrescentaria seria so a camada visual.
"""
import asyncio, os, sys, uuid
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Banco DESCARTAVEL, nunca producao. Parametros por ambiente:
#   PGHOST_TESTE, PGPORT_TESTE, PGDB_TESTE, RADAR_APP_SENHA
HOST = os.environ.get("PGHOST_TESTE", "127.0.0.1")
PORT = int(os.environ.get("PGPORT_TESTE", "5448"))
DB = os.environ.get("PGDB_TESTE", "s8")
SENHA = os.environ.get("RADAR_APP_SENHA")
if not SENHA:
    sys.exit("defina RADAR_APP_SENHA com a senha do papel radar_app no banco de teste")
os.environ.update({
    "APP_ENV": "development", "SECRET_KEY": "k" * 64,
    "POSTGRES_HOST": HOST, "POSTGRES_PORT": str(PORT), "POSTGRES_DB": DB,
    "POSTGRES_USER": "postgres", "POSTGRES_PASSWORD": "",
    "APP_DB_USER": "radar_app", "APP_DB_PASSWORD": SENHA,
})

import httpx
from sqlalchemy import text
from api.main import app
from api.database import engine
from api.auth import hash_password

VERDE, VERMELHO, FIM = "\033[32m", "\033[31m", "\033[0m"
falhas = []


def ok(cond, titulo, detalhe=""):
    marca = f"{VERDE}ok  {FIM}" if cond else f"{VERMELHO}FALHOU{FIM}"
    print(f"  {marca} {titulo}" + (f"  [{detalhe}]" if detalhe else ""))
    if not cond:
        falhas.append(titulo)


async def semear():
    """Dois escritorios completos. Semeado como SUPERUSER (curadoria), nao pela app."""
    import asyncpg
    c = await asyncpg.connect(host=HOST, port=PORT, user="postgres", database=DB)
    await c.execute("TRUNCATE escritorios, usuarios, empresas, estabelecimentos CASCADE")
    ids = {}
    for rotulo, esc_nome, email, emp_nome, cnpj in [
        ("A", "Burnett Advocacia", "a@teste.local", "KRETA LTDA", "11222333000181"),
        ("B", "Escritorio Rival",  "b@teste.local", "OUTRA EMPRESA LTDA", "44555666000172"),
    ]:
        esc = await c.fetchval(
            "INSERT INTO escritorios (razao_social, modalidade) VALUES ($1,'saas') RETURNING id", esc_nome)
        emp = await c.fetchval(
            "INSERT INTO empresas (razao_social, cnpj, escritorio_id, periodo_apuracao_inicio,"
            " periodo_apuracao_fim, cnae_principal) VALUES ($1,$2,$3,$4,$5,'4321500') RETURNING id",
            emp_nome, cnpj, esc, date(2024, 1, 1), date(2024, 12, 1))
        est = await c.fetchval(
            "INSERT INTO estabelecimentos (empresa_id, codigo, nome, cnpj, posicao, escritorio_id,"
            " data_abertura, tipo_estabelecimento, status)"
            " VALUES ($1,'001',$2,$3,'matriz',$4,$5,'CNPJ','ativa') RETURNING id",
            emp, f"Matriz {rotulo}", cnpj, esc, date(2020, 1, 1))
        await c.execute(
            "INSERT INTO estabelecimento_atividade (estabelecimento_id, cnae, quantitativo,"
            " vigencia_inicio, escritorio_id) VALUES ($1,'4321500',10,$2,$3)", est, date(2024,1,1), esc)
        await c.execute(
            "INSERT INTO usuarios (email, senha_hash, nome, perfil, empresa_id, escritorio_id, papel,"
            " ativo) VALUES ($1,$2,$3,'admin',$4,$5,'titular',true)",
            email, hash_password("senha-de-teste"), f"Usuario {rotulo}", emp, esc)
        ids[rotulo] = {"escritorio": esc, "empresa": emp, "estab": est, "email": email}
    await c.close()
    return ids


async def main():
    ids = await semear()
    A, B = ids["A"], ids["B"]

    async with engine.connect() as conn:
        r = (await conn.execute(text(
            "SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user"))).fetchone()
    print(f"\nA aplicacao conecta como '{r[0]}' (superuser={r[1]}, bypassrls={r[2]})")
    ok(not r[1] and not r[2], "a aplicacao NAO tem privilegio que ignore o RLS")

    transporte = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transporte, base_url="http://teste") as cli:
        print("\n— Login (com RLS ligado na tabela usuarios, como a 032c deixaria) —")
        # Cada login num task proprio: e assim que um servidor ASGI real atende requisicoes, e
        # sem isso o ContextVar de uma chamada vazaria para a seguinte dentro do ASGITransport,
        # produzindo uma falha que nao existe em producao.
        tokens = {}
        for rot, d in (("A", A), ("B", B)):
            resp = await asyncio.create_task(cli.post(
                "/api/auth/token", data={"username": d["email"], "password": "senha-de-teste"}))
            ok(resp.status_code == 200, f"usuario {rot} consegue entrar", f"HTTP {resp.status_code}")
            if resp.status_code == 200:
                tokens[rot] = resp.json()["access_token"]
        if "A" not in tokens:
            print("\nSem token de A, o resto nao faz sentido."); return
        hA = {"Authorization": f"Bearer {tokens['A']}"}

        print("\n— O usuario A so enxerga o proprio escritorio —")
        resp = await cli.get("/api/estabelecimentos/", headers=hA)
        nomes = [e["nome"] for e in resp.json()] if resp.status_code == 200 else []
        ok(resp.status_code == 200 and nomes == ["Matriz A"],
           "listagem de estabelecimentos traz só os de A", f"{nomes}")

        print("\n— Chamada direta com o identificador de B na URL —")
        casos = [
            ("GET", f"/api/empresas/{B['empresa']}", None, "ler a empresa de B"),
            ("GET", f"/api/empresas/{B['empresa']}/regime", None, "ler o regime de B"),
            ("GET", f"/api/empresas/{B['empresa']}/cprb", None, "ler a CPRB de B"),
            ("GET", f"/api/empresas/{B['empresa']}/matriz-enquadramento", None, "ler o espelho de B"),
            ("GET", f"/api/estabelecimentos/{B['estab']}/atividades", None, "ler as atividades de B"),
            ("GET", f"/api/estabelecimentos/{B['estab']}/enquadramento", None, "ler o enquadramento de B"),
            ("GET", f"/api/estabelecimentos/{B['estab']}/fap", None, "ler o FAP de B"),
            ("GET", f"/api/estabelecimentos/{B['estab']}/rat-aplicado", None, "ler o RAT aplicado de B"),
            ("GET", f"/api/estabelecimentos/{B['estab']}/fpas", None, "ler o FPAS de B"),
        ]
        for metodo, url, corpo, titulo in casos:
            resp = await cli.request(metodo, url, headers=hA, json=corpo)
            ok(resp.status_code in (403, 404), f"A NÃO consegue {titulo}", f"HTTP {resp.status_code}")

        print("\n— EXPORTAÇÃO (o vetor que o teste por SQL não cobria) —")
        resp = await cli.get(f"/api/estabelecimentos/{B['estab']}/memoria", headers=hA)
        ok(resp.status_code in (403, 404),
           "A NÃO consegue exportar a memória em PDF de B", f"HTTP {resp.status_code}")
        if resp.status_code == 200:
            ok(False, "   ⚠ o PDF de B foi entregue a A", f"{len(resp.content)} bytes")

        print("\n— Escrita no dado de B —")
        escritas = [
            ("PUT", f"/api/estabelecimentos/{B['estab']}/fap", [{"ano": 2024, "fap": 2.0}], "alterar o FAP de B"),
            ("PUT", f"/api/estabelecimentos/{B['estab']}/rat-aplicado",
             [{"aliquota_rat": 3, "fap_aplicado": 2.0, "inicio": "2024-01-01"}], "alterar o RAT aplicado de B"),
            ("POST", f"/api/estabelecimentos/{B['estab']}/apurar", None, "reapurar o enquadramento de B"),
            ("PUT", f"/api/empresas/{B['empresa']}", {"razao_social": "INVADIDA"}, "renomear a empresa de B"),
        ]
        for metodo, url, corpo, titulo in escritas:
            resp = await cli.request(metodo, url, headers=hA, json=corpo)
            ok(resp.status_code in (403, 404), f"A NÃO consegue {titulo}", f"HTTP {resp.status_code}")

        print("\n— Exclusão: dado de B, e a trava da razão social —")
        resp = await cli.request("DELETE", f"/api/empresas/{B['empresa']}", headers=hA,
                                 json={"razao_social": "OUTRA EMPRESA LTDA"})
        ok(resp.status_code in (403, 404),
           "A NÃO consegue excluir a empresa de B mesmo sabendo a razão social", f"HTTP {resp.status_code}")
        resp = await cli.request("DELETE", f"/api/empresas/{A['empresa']}", headers=hA,
                                 json={"razao_social": "nome errado"})
        ok(resp.status_code == 422,
           "a própria empresa não é excluída com a razão social errada", f"HTTP {resp.status_code}")

        print("\n— O dado de B continua intacto depois de tudo —")
        import asyncpg
        c = await asyncpg.connect(host=HOST, port=PORT, user="postgres", database=DB)
        nome_b = await c.fetchval("SELECT razao_social FROM empresas WHERE id=$1", B["empresa"])
        existe_b = await c.fetchval("SELECT count(*) FROM estabelecimentos WHERE id=$1", B["estab"])
        await c.close()
        ok(nome_b == "OUTRA EMPRESA LTDA", "a empresa de B não foi renomeada", nome_b)
        ok(existe_b == 1, "o estabelecimento de B não foi apagado")

        print("\n— A enxerga e opera o PRÓPRIO dado (o isolamento não pode travar o trabalho) —")
        resp = await cli.get(f"/api/empresas/{A['empresa']}", headers=hA)
        ok(resp.status_code == 200, "A lê a própria empresa", f"HTTP {resp.status_code}")
        resp = await cli.post(f"/api/estabelecimentos/{A['estab']}/apurar", headers=hA)
        ok(resp.status_code == 200, "A reapura o próprio enquadramento", f"HTTP {resp.status_code}")
        resp = await cli.get(f"/api/estabelecimentos/{A['estab']}/memoria", headers=hA)
        ok(resp.status_code == 200 and resp.content[:4] == b"%PDF",
           "A exporta a própria memória em PDF", f"HTTP {resp.status_code}")

    await engine.dispose()
    print("\n" + "=" * 70)
    if falhas:
        print(f"{VERMELHO}SECAO 8: REPROVADO — {len(falhas)} verificacao(oes) falharam{FIM}")
        for f in falhas:
            print(f"  - {f}")
        sys.exit(1)
    print(f"{VERDE}SECAO 8: APROVADO — nenhum vazamento entre escritorios pela aplicacao{FIM}")


if __name__ == "__main__":
    asyncio.run(main())
