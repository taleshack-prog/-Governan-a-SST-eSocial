# SST eSocial Gov 🛡️

**Sistema de Governança SST/eSocial com Inteligência Artificial**

> Plataforma SaaS multi-tenant para automação e validação inteligente de documentos de Saúde e Segurança do Trabalho — conformidade com NR-01, NR-07, NR-15, eSocial S-2240 e S-2220.

[![CI](https://github.com/taleshack-prog/-Governan-a-SST-eSocial/actions/workflows/ci.yml/badge.svg)](https://github.com/taleshack-prog/-Governan-a-SST-eSocial/actions)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+pgvector-blue.svg)](https://github.com/pgvector/pgvector)

---

## 🗺️ Visão Geral

```
[Usuário Navegador]
        │
        ▼
[React 18 + Vite — porta 3001]
        │
        ▼
[Nginx Proxy Reverso]
        │
    ┌───┴───┐
    │       │
    ▼       ▼
[FastAPI  ] [Celery Worker]
[porta 8001]    │
    │           │ (tarefas IA assíncronas)
    ▼           ▼
[PostgreSQL 16 + pgvector]
[Redis 7]
[MinIO (documentos)]
```

---

## 🚀 Como Executar (Desenvolvimento)

### Pré-requisitos
- Docker Desktop 4.x
- Docker Compose v2
- Git

### 1. Clonar e configurar

```bash
git clone https://github.com/taleshack-prog/-Governan-a-SST-eSocial.git
cd -Governan-a-SST-eSocial

# Copiar e editar variáveis de ambiente
cp .env.example .env
# Editar .env: preencher SECRET_KEY, OPENROUTER_API_KEY, senhas
```

### 2. Subir os containers

```bash
make up
# ou: docker compose up -d
```

### 3. Verificar saúde da API

```bash
make health
# Retorna: {"status": "ok", "app": "SST eSocial Gov", "env": "development"}
```

### 4. Acessar

| Serviço | URL |
|---|---|
| Frontend | http://localhost:3001 |
| API Docs (Swagger) | http://localhost:8001/api/docs |
| API ReDoc | http://localhost:8001/api/redoc |
| MinIO Console | http://localhost:9002 |

---

## 🗃️ Portas (sem conflito com outros projetos)

| Serviço | Host | Container |
|---|---|---|
| Backend API | **8001** | 8000 |
| Frontend | **3001** | 3000 |
| PostgreSQL | **5433** | 5432 |
| Redis | **6380** | 6379 |
| MinIO API | **9001** | 9000 |
| MinIO Console | **9002** | 9001 |

---

## 🏗️ Arquitetura

### Stack Tecnológico

| Camada | Tecnologia |
|---|---|
| Backend | FastAPI 0.115 + Python 3.12 |
| ORM | SQLAlchemy 2.0 async + asyncpg |
| Banco | PostgreSQL 16 + pgvector 0.7 |
| Cache / Filas | Redis 7 + Celery 5 |
| IA | OpenRouter (Claude Haiku / GPT-4o-mini) + RAG |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| Frontend | React 18 + TypeScript + Tailwind CSS + Vite |
| Estado | Zustand + React Query |
| Storage | MinIO (S3-compatível) |
| Infra | Docker Compose + Nginx |
| CI/CD | GitHub Actions |

### Estrutura de Arquivos

```
sst-esocial-gov/
├── api/                        ← Backend FastAPI
│   ├── main.py                 ← Entrypoint + routers
│   ├── config.py               ← Settings (pydantic-settings)
│   ├── database.py             ← Engine async + session
│   ├── auth.py                 ← JWT HS256 + RBAC
│   ├── models/                 ← 11 modelos ORM
│   ├── routers/                ← 9 routers REST
│   └── services/               ← Lógica de negócio
├── ai-layer/                   ← Módulo de IA independente
│   ├── pipeline.py             ← Pipeline 9 etapas
│   ├── confidence.py           ← Score GRADE (A-F)
│   ├── extractors/             ← LTCAT, PGR extrators
│   ├── matchers/               ← Tabela 24 matcher (23 códigos)
│   └── validators/             ← Cross-doc validator
├── database/
│   ├── migrations/             ← Schema SQL (15 tabelas)
│   ├── triggers/               ← Auditoria SHA-256 encadeada
│   ├── rls/                    ← Row Level Security (multi-tenant)
│   └── seeds/                  ← NRs, Tabela 24, perfis
├── frontend/                   ← React 18 + TypeScript
│   └── src/
│       ├── pages/              ← 8 páginas (Dashboard, Docs, etc.)
│       ├── components/         ← UI reutilizável
│       ├── hooks/              ← React Query hooks
│       ├── api/                ← Axios client + interceptors
│       └── store/              ← Zustand (auth)
├── nginx/nginx.conf            ← Proxy reverso + rate limit
├── docker-compose.yml          ← 6 serviços
├── Dockerfile.api              ← Multi-stage Python 3.12
├── requirements.txt
├── Makefile
└── .env.example
```

---

## 🤖 AI Layer — Pipeline de 9 Etapas

```
Documento (PDF/DOCX)
    │
    ▼ Etapa 1: Extração de texto (PyMuPDF / python-docx)
    ▼ Etapa 2: Chunking semântico (512 tokens)
    ▼ Etapa 3: Embedding (all-MiniLM-L6-v2 → 384 dims)
    ▼ Etapa 4: Busca RAG na base normativa (PGVector cosine)
    ▼ Etapa 5: Prompt assembly (contexto NR + documento)
    ▼ Etapa 6: Inferência LLM (OpenRouter → JSON estruturado)
    ▼ Etapa 7: 6 Barreiras anti-alucinação (HAL-001 a HAL-006)
    ▼ Etapa 8: Score GRADE (A/B/C/D/F) com threshold de revisão
    ▼ Etapa 9: Log + feedback loop (RLHF)
    │
    ▼
Resultado: agentes_identificados + codigos_tabela24 + alertas + grade
```

### 6 Barreiras Anti-Alucinação

| Código | Barreira |
|---|---|
| HAL-001 | Código Tabela 24 deve existir na whitelist (23 códigos) |
| HAL-002 | Fundamentação normativa deve ser citada (NR/eSocial) |
| HAL-003 | Cross-check com dados reais do banco |
| HAL-004 | Coerência temporal (datas de vigência) |
| HAL-005 | Limites quantitativos verificados (NR-15: 85 dB) |
| HAL-006 | Não contradizer dados inseridos manualmente |

### Score GRADE

| Grade | Score | Ação |
|---|---|---|
| A | ≥ 90% | Aprovado automaticamente |
| B | ≥ 75% | Aprovado automaticamente |
| C | ≥ 60% | **Revisão humana recomendada** |
| D | ≥ 40% | **Revisão humana obrigatória** |
| F | < 40% | **Rejeitado — reprocessar** |

---

## 📋 Documentos SST Suportados

| Documento | Módulo | NR/eSocial |
|---|---|---|
| LTCAT | Laudo Técnico Condições Ambientais | NR-15, S-2240 |
| PGR | Programa de Gerenciamento de Riscos | NR-01 |
| PCMSO | Programa de Controle Médico | NR-07, S-2220 |
| ASO | Atestado de Saúde Ocupacional | NR-07 |
| CAT | Comunicação de Acidente | CLT Art.169, S-2210 |
| AET | Análise Ergonômica do Trabalho | NR-17 |

---

## 🔒 Segurança

- **Multi-tenant** com RLS (Row Level Security) no PostgreSQL
- **JWT HS256** com expiração configurável
- **RBAC** com 6 perfis: admin, sst, saude_ocupacional, rh, juridico, leitura
- **Auditoria imutável** com hash SHA-256 encadeado (blockchain-like)
- **Rate limiting** no Nginx (30 req/min API, 10 req/min auth)
- **Senhas** com bcrypt (passlib)

---

## 🧪 Testes

```bash
# Rodar testes unitários
make test

# Lint
make lint

# Type check frontend
cd frontend && npm run type-check
```

---

## 🛠️ Comandos Make

```bash
make up           # Sobe todos os containers
make down         # Para containers
make build        # Rebuild das imagens
make db-migrate   # Roda migrations Alembic
make db-seed      # Popula dados iniciais
make logs         # Logs API + Worker
make test         # Testes pytest
make lint         # Lint ruff
make health       # Verifica API
make clean        # Remove volumes
```

---

## 📊 Tabela 24 eSocial — Agentes Implementados

23 agentes mapeados:
- **Físicos (8):** Ruído, Calor, Frio, Umidade, Radiações, Vibração localizada, Vibração corpo inteiro, Pressão hiperbárica
- **Químicos (8):** Arsênio, Chumbo, Cromo, Benzeno, Mercúrio, Sílica, Amianto, Poeiras minerais
- **Biológicos (7):** Vírus, Bactérias, Fungos, Parasitas, Coleta de lixo, Cemitérios, Hospitais/Lab

---

## 📄 Licença

MIT — Ver [LICENSE](LICENSE)

---

*Documentação técnica completa disponível nos PDFs do projeto. Desenvolvido com base nas NRs vigentes e eSocial leiaute 3.1.x (2025).*
