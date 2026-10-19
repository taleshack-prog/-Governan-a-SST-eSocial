#!/usr/bin/env python3
"""Carga da tabela de aliquotas por codigo FPAS, por ATO NORMATIVO (Carolina, 18/10, item 3).

A curadoria entrega Anexo II, Anexo III e a tabela da IN RFB 2.321/2026 em CSV, com a coluna de
vigencia preenchida. Este script carrega cada arquivo SUBSTITUINDO o bloco daquele ato: apaga as
linhas cuja 'fonte' e o ato informado e insere as do arquivo. Rodar duas vezes nao duplica, e
corrigir o CSV e recarregar nao deixa resto da carga anterior.

PROTECAO CONTRA O ESTRAGO DO EXCEL
----------------------------------
A curadoria avisou: os CSV NAO devem ser abertos e salvos no Excel em hipotese nenhuma. O
programa remove os zeros a esquerda em silencio, e tanto os codigos de Terceiros quanto as
subclasses da CNAE dependem deles — o codigo 0079 vira 79 e a subclasse 0111301 vira 111301.
Como o estrago e silencioso no Excel, ele tem de ser RUIDOSO aqui: o script le tudo como TEXTO
(nunca converte codigo para int) e ABORTA quando encontra codigo mais curto do que a largura
esperada, dizendo qual linha e o que provavelmente aconteceu.

FORMATO ESPERADO (cabecalho na primeira linha, separador virgula ou ponto-e-virgula):
    codigo_fpas,descricao,aliquota_terceiros,codigo_terceiros,vigencia_inicio,vigencia_fim
    0507,Comercio e industria (regra geral),5.80,0079,2022-10-17,2026-03-31
- codigo_fpas: 3 ou 4 digitos, COM zeros a esquerda
- aliquota_terceiros: ponto ou virgula decimal
- codigo_terceiros: opcional, 4 digitos com zeros a esquerda
- vigencia_fim: vazio = em vigor

USO
    python3 scripts/carregar_tabela_fpas.py anexo_iii_2110.csv --ato "IN RFB 2.110/2022 Anexo III"
    python3 scripts/carregar_tabela_fpas.py in_2321.csv --ato "IN RFB 2.321/2026" --conferir
Opcoes:
    --ato TEXTO      obrigatorio: identifica o bloco a substituir (vai para a coluna 'fonte')
    --conferir       so analisa e mostra o que faria, sem gravar
    --a-confirmar    marca as linhas como confirmado=false (vao a fila de conferencia)
"""
import argparse
import csv
import os
import re
import sys
from datetime import date

LARGURA_MIN_FPAS = 3          # codigos FPAS tem 3 ou 4 digitos
LARGURA_FPAS = 4
LARGURA_TERCEIROS = 4
LARGURA_CNAE = 7           # subclasse da CNAE: 0111301


def _erro(msg: str) -> None:
    print(f"ERRO: {msg}", file=sys.stderr)
    sys.exit(1)


def _ler_csv(caminho: str) -> list[dict]:
    """Le o CSV inteiro como TEXTO. Nenhum campo e convertido para numero aqui."""
    if not os.path.exists(caminho):
        _erro(f"arquivo nao encontrado: {caminho}")
    with open(caminho, newline="", encoding="utf-8-sig") as f:
        amostra = f.read(4096)
        f.seek(0)
        try:
            dialeto = csv.Sniffer().sniff(amostra, delimiters=",;\t")
        except csv.Error:
            dialeto = csv.excel
        linhas = [{(k or "").strip().lower(): (v or "").strip() for k, v in linha.items()}
                  for linha in csv.DictReader(f, dialect=dialeto)]
    if not linhas:
        _erro("o arquivo nao tem nenhuma linha de dados")
    obrigatorias = {"codigo_fpas", "aliquota_terceiros", "vigencia_inicio"}
    faltando = obrigatorias - set(linhas[0].keys())
    if faltando:
        _erro(f"colunas obrigatorias ausentes no cabecalho: {', '.join(sorted(faltando))}")
    return linhas


def _checar_zeros_removidos(linhas: list[dict]) -> tuple[list[str], list[str]]:
    """Detecta o estrago do Excel. Devolve (erros que abortam, avisos que so aparecem).

    QUAIS LARGURAS SAO CONFIAVEIS. O codigo FPAS tem tres OU quatro digitos de verdade (507,
    515, 582 existem com tres), entao largura curta ali NAO prova estrago e nao pode abortar a
    carga — seria alarme falso bloqueando arquivo correto. Ja o codigo de TERCEIROS e sempre de
    quatro (0079) e a subclasse da CNAE sempre de sete (0111301): nesses, largura menor e prova.
    """
    erros: list[str] = []
    avisos: list[str] = []

    for i, l in enumerate(linhas, start=2):   # 2 = primeira linha de dado (1 e o cabecalho)
        cod = l.get("codigo_fpas", "")
        if not cod:
            erros.append(f"linha {i}: codigo_fpas vazio")
            continue
        if not cod.isdigit():
            erros.append(f"linha {i}: codigo_fpas '{cod}' nao e numerico")
            continue
        if len(cod) < LARGURA_MIN_FPAS:
            erros.append(
                f"linha {i}: codigo_fpas '{cod}' tem {len(cod)} digito(s), menos que o minimo "
                f"de {LARGURA_MIN_FPAS}. Zeros a esquerda removidos — o arquivo passou pelo Excel?")

        # Terceiros: sempre quatro digitos. Largura menor e prova de estrago.
        ter = l.get("codigo_terceiros", "")
        if ter and ter.isdigit() and len(ter) < LARGURA_TERCEIROS:
            erros.append(
                f"linha {i}: codigo_terceiros '{ter}' tem {len(ter)} digito(s), esperado "
                f"{LARGURA_TERCEIROS}. Zeros a esquerda removidos (ex.: 0079 virou {ter}).")

        # CNAE/subclasse, se o arquivo trouxer: sempre sete digitos.
        for chave in ("cnae", "subclasse", "cnae_subclasse"):
            v = l.get(chave, "")
            if v and v.isdigit() and len(v) < LARGURA_CNAE:
                erros.append(
                    f"linha {i}: {chave} '{v}' tem {len(v)} digito(s), esperado {LARGURA_CNAE}. "
                    f"Zeros a esquerda removidos (ex.: 0111301 virou {v}).")

    # Mistura de larguras no FPAS: suspeito, nao conclusivo. Vira AVISO, nao erro.
    larguras = {len(l["codigo_fpas"]) for l in linhas if l.get("codigo_fpas", "").isdigit()}
    if len(larguras) > 1:
        avisos.append(
            f"o arquivo mistura codigos FPAS de larguras {sorted(larguras)}. Isso pode ser "
            f"legitimo (ha codigos de tres e de quatro digitos), mas confira se os mais curtos "
            f"nao perderam zero a esquerda.")
    return erros, avisos


def _num(v: str) -> float:
    """Aliquota com ponto OU virgula decimal."""
    s = (v or "").strip().replace(".", "").replace(",", ".") if (v or "").count(",") else (v or "").strip()
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"aliquota invalida: '{v}'")


def _data(v: str, campo: str, linha: int):
    s = (v or "").strip()
    if not s:
        return None
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", s)      # aceita dd/mm/aaaa
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    _erro(f"linha {linha}: {campo} '{v}' nao esta em AAAA-MM-DD nem dd/mm/aaaa")


def main() -> None:
    ap = argparse.ArgumentParser(description="Carga versionada da tabela de FPAS/Terceiros.")
    ap.add_argument("csv", help="caminho do CSV entregue pela curadoria")
    ap.add_argument("--ato", required=True,
                    help="ato normativo; identifica o bloco a substituir (coluna 'fonte')")
    ap.add_argument("--conferir", action="store_true", help="so analisa, nao grava")
    ap.add_argument("--a-confirmar", action="store_true",
                    help="marca as linhas como pendentes de confirmacao")
    args = ap.parse_args()

    linhas = _ler_csv(args.csv)
    print(f"Arquivo: {args.csv}")
    print(f"Ato normativo (bloco a substituir): {args.ato}")
    print(f"Linhas de dado: {len(linhas)}")

    erros, avisos = _checar_zeros_removidos(linhas)
    for a in avisos:
        print(f"AVISO: {a}")
    if erros:
        print("\nO ARQUIVO NAO PASSOU NA CONFERENCIA DE INTEGRIDADE:\n", file=sys.stderr)
        for e in erros:
            print(f"  - {e}", file=sys.stderr)
        print("\nNada foi gravado. Codigos de Terceiros e subclasses da CNAE dependem dos zeros\n"
              "a esquerda; carregar o arquivo estragado produziria enquadramento errado sem\n"
              "emitir erro nenhum depois.", file=sys.stderr)
        sys.exit(2)
    print("Integridade: ok (nenhum zero a esquerda perdido).")

    registros = []
    for i, l in enumerate(linhas, start=2):
        try:
            aliq = _num(l["aliquota_terceiros"])
        except ValueError as e:
            _erro(f"linha {i}: {e}")
        ini = _data(l["vigencia_inicio"], "vigencia_inicio", i)
        if ini is None:
            _erro(f"linha {i}: vigencia_inicio e obrigatoria")
        fim = _data(l.get("vigencia_fim", ""), "vigencia_fim", i)
        if fim and fim < ini:
            _erro(f"linha {i}: vigencia_fim anterior a vigencia_inicio")
        registros.append({
            "codigo_fpas": l["codigo_fpas"],
            "descricao": l.get("descricao") or f"FPAS {l['codigo_fpas']}",
            "aliquota_terceiros": aliq,
            "codigo_terceiros": l.get("codigo_terceiros") or None,
            "fonte": args.ato,
            "confirmado": not args.a_confirmar,
            "vigencia_inicio": ini,
            "vigencia_fim": fim,
        })

    faixas = sorted({(r["vigencia_inicio"], r["vigencia_fim"]) for r in registros})
    print("Vigencias no arquivo:")
    for ini, fim in faixas:
        qtd = sum(1 for r in registros if (r["vigencia_inicio"], r["vigencia_fim"]) == (ini, fim))
        print(f"  {ini.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y') if fim else 'em vigor'}"
              f"  —  {qtd} codigo(s)")

    if args.conferir:
        print("\n--conferir: nada gravado. Rode sem a opcao para carregar.")
        return

    # Importa aqui para que --conferir funcione sem banco configurado.
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from sqlalchemy import delete, select            # noqa: E402
    from api.database import get_sync_session         # noqa: E402
    from api.models.tabela_fpas import TabelaFPAS     # noqa: E402

    with get_sync_session() as s:
        antigas = s.execute(
            select(TabelaFPAS).where(TabelaFPAS.fonte == args.ato)
        ).scalars().all()
        if antigas:
            print(f"\nSubstituindo o bloco existente deste ato: {len(antigas)} linha(s) saem.")
            s.execute(delete(TabelaFPAS).where(TabelaFPAS.fonte == args.ato))
        for r in registros:
            s.add(TabelaFPAS(ativo=True, **r))
        s.commit()
    print(f"Carregado: {len(registros)} linha(s) para '{args.ato}'.")
    print("\nConferencia sugerida:")
    print("  SELECT fonte, vigencia_inicio, vigencia_fim, count(*)")
    print("    FROM tabela_fpas GROUP BY 1,2,3 ORDER BY 2;")


if __name__ == "__main__":
    main()
