# Clima Países 🌤️🌍

Dashboard meteorológico profissional, rápido e resiliente para consultar e comparar o clima atual e previsões de qualquer capital do mundo, cruzando dados geográficos de países com as APIs abertas da **Open-Meteo**.

---

## 🚀 Funcionalidades Principais

- **Zero Autenticação & Zero Chaves**: 100% público e gratuito, sem necessidade de tokens (Open-Meteo Forecast, Geocoding e Air Quality APIs).
- **Matching Crítico e Resiliente (`src/match.py`)**:
  - Resolução por capital (ex: `Brasília`, `Tóquio`, `Paris`, `Rome`, `Washington`).
  - Resolução por país (ex: `Brasil` -> Brasília, `Alemanha` -> Berlin, `Japan` -> Tokyo).
  - Resolução por código ISO Alpha-2 / Alpha-3 (ex: `BR`, `USA`, `DE`, `JP`, `FR`).
  - Normalização completa de acentos, maiúsculas/minúsculas e pontuação (`São Tomé` -> `sao tome`, `Washington, D.C.` -> `washington dc`).
  - Mapeamento multilíngue (ex: `Viena` / `Vienna`, `Pequim` / `Beijing`, `Moscou` / `Moscow`).
  - Tolerância a pequenos erros de digitação via *fuzzy matching*.
- **Previsão Estendida & Qualidade do Ar**:
  - **Previsão Diária (5 Dias)**: Temperaturas mín/máx, probabilidade de chuva, precipitação total, índice UV, horários de nascer e pôr do sol.
  - **Previsão Horária (24 Horas)**: Evolução térmica e risco de chuva a cada hora.
  - **Qualidade do Ar (AQI)**: Índice Europeu de Qualidade do Ar, PM2.5, PM10, $NO_2$ e $O_3$.
- **Comparador entre Múltiplas Capitais**:
  - Comparação lado a lado de 2 ou mais cidades (`--compare`), destacando a capital mais quente, mais fria e o delta térmico ($\Delta T$).
- **Histórico & Favoritos**:
  - Armazenamento de histórico de consultas recentes e gerenciamento de capitais favoritas.
- **Exportação de Relatórios**:
  - Exportação direta de dados meteorológicos para **JSON** ou **CSV**.
- **Interface Visual Rica no Terminal**:
  - Tabelas, cards e painéis formatados com cores temáticas e gradientes via `rich`.

---

## 📁 Estrutura do Projeto

```text
clima/
├── .venv/                   # Ambiente virtual Python
├── GEMINI.md               # Governança e diretrizes do projeto
├── README.md               # Documentação e instruções de uso
├── requirements.txt        # Dependências do projeto
├── pyproject.toml          # Configurações do pacote e ferramentas
├── pytest.ini              # Configurações do pytest
├── src/
│   ├── api/
│   │   ├── open_meteo.py      # Integração com APIs Open-Meteo (Previsão, Horária, AQI e Geocoding)
│   │   └── rest_countries.py  # Modelo e cliente de países e capitais
│   ├── data/
│   │   └── countries.json     # Base de dados local com 250 países e capitais
│   ├── match.py               # Algoritmo de normalização e matching crítico
│   ├── storage.py             # Histórico, favoritos e exportação JSON/CSV
│   ├── comparator.py          # Comparação e análise térmica multi-cidades
│   ├── ui/
│   │   └── views.py           # Componentes visuais Rich
│   └── main.py                # Ponto de entrada CLI e menu interativo
└── tests/
    ├── test_match.py          # Testes de matching, acentos, idiomas e fallbacks
    ├── test_api.py            # Testes de integração de APIs
    ├── test_extended_weather.py # Testes de previsão 5d, 24h e qualidade do ar
    ├── test_storage.py        # Testes de persistência e exportadores
    ├── test_comparator.py     # Testes do comparador de capitais
    ├── test_views.py          # Testes dos componentes de visualização
    └── test_main.py           # Testes do fluxo CLI
```

---

## 🛠️ Instalação e Configuração

### 1. Criar e Ativar o Ambiente Virtual (`venv`)

```bash
# Criação do ambiente virtual
python3 -m venv .venv

# Ativação (Linux/macOS)
source .venv/bin/activate

# Instalação das dependências
pip install -r requirements.txt
```

---

## 💻 Como Usar

### 1. Menu Interativo Completo
Basta executar o script sem argumentos para abrir o menu interativo com todas as opções:

```bash
python src/main.py
```

---

### 2. Consultas Diretas via Linha de Comando (CLI)

#### Clima Atual
```bash
python src/main.py "Brasília"
python src/main.py "Tóquio"
python src/main.py "Alemanha"
python src/main.py "US"
```

#### Dashboard Completo (Atual + Previsão 5 Dias + Horária 24h + Qualidade do Ar)
```bash
python src/main.py "Brasília" --all
```

#### Previsão Diária (5 Dias) ou Horária (24h)
```bash
python src/main.py "Paris" --forecast
python src/main.py "Paris" --hourly
```

#### Qualidade do Ar
```bash
python src/main.py "Pequim" --air-quality
```

#### Comparar Múltiplas Capitais
```bash
python src/main.py --compare "Brasília" "Tóquio" "Londres" "Roma"
```

#### Favoritos e Histórico
```bash
# Adicionar ou remover dos favoritos
python src/main.py --add-fav "Tóquio"
python src/main.py --add-fav "Brasília"

# Listar favoritos
python src/main.py --favorites

# Ver histórico de consultas recentes
python src/main.py --history
```

#### Exportar Relatório Climático
```bash
# Exportar dados em JSON
python src/main.py "Brasília" --all --export json --output relatorio_brasilia.json

# Exportar dados em CSV
python src/main.py "Brasília" --export csv --output relatorio_brasilia.csv
```

---

## 🧪 Suíte de Testes Unitários

Execute os testes automatizados com cobertura:

```bash
pytest -v
```
