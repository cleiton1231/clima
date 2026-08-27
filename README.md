# Clima Países 🌤️🌍

Dashboard meteorológico profissional, Web API REST e CLI para consultar e comparar o clima atual, previsões estendidas e qualidade do ar de qualquer capital do mundo, cruzando dados geográficos de países com as APIs abertas da **Open-Meteo**.

[![CI Clima Países](https://github.com/cleiton1231/clima/actions/workflows/ci.yml/badge.svg)](https://github.com/cleiton1231/clima/actions/workflows/ci.yml)

---

## 🚀 Funcionalidades Principais

- **Zero Autenticação**: 100% aberto e público, sem tokens ou chaves (Open-Meteo e REST Countries).
- **Matching Crítico e Resiliente (`src/match.py`)**:
  - Resolução por capital (ex: `Brasília`, `Tóquio`, `Paris`, `Rome`, `Washington`).
  - Resolução por país (ex: `Brasil` -> Brasília, `Alemanha` -> Berlin, `Japan` -> Tokyo).
  - Resolução por código ISO Alpha-2 / Alpha-3 (ex: `BR`, `USA`, `DE`, `JP`, `FR`).
  - Normalização completa de acentos, maiúsculas/minúsculas e pontuação (`São Tomé` -> `sao tome`, `Washington, D.C.` -> `washington dc`).
  - Mapeamento multilíngue (ex: `Viena` / `Vienna`, `Pequim` / `Beijing`, `Moscou` / `Moscow`).
  - *Fuzzy matching* determinístico para pequenos erros de digitação.
- **Previsão Estendida & Qualidade do Ar**:
  - **Previsão Diária (5 Dias)**: Temperaturas mín/máx, probabilidade de chuva, precipitação total, índice UV, horários de nascer e pôr do sol.
  - **Previsão Horária (24 Horas)**: Evolução térmica e risco de chuva hora a hora.
  - **Qualidade do Ar (AQI)**: Índice Europeu de Qualidade do Ar, PM2.5, PM10, $NO_2$ e $O_3$.
- **Web API REST & Dashboard SPA (`src/web/`)**:
  - Servidor FastAPI com documentação Swagger OpenAPI interativa em `/docs`.
  - Dashboard web moderno e responsivo em tema escuro acessível em `/`.
- **Comparador Multi-Capitais (`--compare`)**:
  - Comparação lado a lado de 2 ou mais cidades com cálculo de delta térmico ($\Delta T$) e extremos.
- **Histórico & Favoritos**:
  - Armazenamento local e exportação para **JSON** e **CSV**.
- **Containerização Docker & Entrypoint CLI**:
  - Imagem Docker otimizada baseada em `python:3.12-slim` com usuário não-root.
  - Executável de console instalado como comando global `clima`.

---

## 📁 Estrutura do Projeto

```text
clima/
├── .github/
│   └── workflows/
│       └── ci.yml             # Pipeline de CI (Python 3.10 a 3.13)
├── .venv/                     # Ambiente virtual Python
├── Dockerfile                 # Imagem containerizada otimizada
├── .dockerignore              # Exclusões do contexto Docker
├── GEMINI.md                  # Governança e diretrizes do projeto
├── README.md                  # Documentação completa
├── requirements.txt           # Dependências do projeto
├── pyproject.toml             # Manifesto do pacote e scripts de console
├── pytest.ini                 # Configurações do pytest
├── src/
│   ├── api/
│   │   ├── open_meteo.py         # Integração Open-Meteo (tempo real, 5d, 24h, AQI)
│   │   └── rest_countries.py     # Cliente de países e capitais
│   ├── data/
│   │   └── countries.json        # Base de dados local com 250 países
│   ├── match.py                  # Algoritmo de normalização e matching difuso
│   ├── storage.py                # Histórico, favoritos e exportadores JSON/CSV
│   ├── comparator.py             # Comparação e análise térmica multi-cidades
│   ├── ui/
│   │   └── views.py              # Visualização rica no terminal (Rich)
│   ├── web/
│   │   ├── app.py                # Servidor Web API FastAPI
│   │   └── static/
│   │       └── index.html        # Dashboard Web SPA
│   └── main.py                   # Ponto de entrada CLI e menu interativo
└── tests/
    ├── test_match.py             # Testes de matching e normalização
    ├── test_api.py               # Testes de integração de APIs
    ├── test_extended_weather.py    # Testes de previsão 5d, 24h e qualidade do ar
    ├── test_storage.py           # Testes de storage e variáveis de ambiente
    ├── test_comparator.py        # Testes de comparação de cidades
    ├── test_views.py             # Testes de renderização Rich
    ├── test_cli_entrypoint.py    # Testes do executável de console 'clima'
    ├── test_web_api.py           # Testes da API Web FastAPI com mocks
    └── test_main.py              # Testes do fluxo CLI
```

---

## 🛠️ Instalação e Execução

### 1. Ambiente Virtual Local (`venv`)

```bash
# Criação e ativação do ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalação das dependências e do comando 'clima'
pip install -r requirements.txt
pip install -e .
```

---

### 2. Executando a Web API e o Dashboard Web

Inicie o servidor local com Uvicorn:

```bash
uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000
```

- **Dashboard Web**: Acesse [`http://localhost:8000`](http://localhost:8000) no seu navegador.
- **Documentação OpenAPI / Swagger**: Acesse [`http://localhost:8000/docs`](http://localhost:8000/docs).

---

### 3. Executando via Linha de Comando (CLI)

Após instalar com `pip install -e .`, o comando `clima` fica disponível:

```bash
# Menu interativo
clima

# Consulta direta de clima atual
clima "Brasília"
clima "Tóquio"
clima "Alemanha"

# Dashboard completo (clima atual + previsão 5 dias + horária 24h + qualidade do ar)
clima "Brasília" --all

# Previsão diária (5 dias) ou horária (24h)
clima "Paris" --forecast
clima "Paris" --hourly

# Qualidade do ar
clima "Pequim" --air-quality

# Comparar múltiplas capitais
clima --compare "Brasília" "Tóquio" "Londres" "Roma"

# Exportar para JSON ou CSV
clima "Brasília" --all --export json --output relatorio_brasilia.json
```

---

### 4. Executando com Docker

```bash
# Construir a imagem Docker
docker build -t clima:latest .

# Executar comando CLI dentro do container
docker run --rm clima:latest "Brasília" --all

# Executar servidor Web no container
docker run --rm -p 8000:8000 --entrypoint uvicorn clima:latest src.web.app:app --host 0.0.0.0 --port 8000
```

---

## 🧪 Suíte de Testes Automatizados

Execute a suíte de testes com cobertura de código:

```bash
pytest --cov=src -v
```
