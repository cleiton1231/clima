# Clima Países 🌤️🌍

Dashboard simples, rápido e resiliente para consultar o clima atual de qualquer capital do mundo, cruzando dados geográficos de países e capitais com previsões meteorológicas em tempo real da **Open-Meteo**.

---

## 🚀 Funcionalidades

- **Zero Autenticação**: Integração com APIs abertas e públicas (Open-Meteo e REST Countries), sem necessidade de API keys ou tokens.
- **Matching Inteligente e Difuso (`src/match.py`)**:
  - Resolução por capital (ex: `Brasília`, `Tóquio`, `Paris`, `Rome`, `Washington`).
  - Resolução por país (ex: `Brasil` -> Brasília, `Alemanha` -> Berlin, `Japan` -> Tokyo).
  - Resolução por código ISO (ex: `BR`, `USA`, `DE`, `JP`, `FR`).
  - Normalização completa de acentos, maiúsculas/minúsculas e pontuação (`São Tomé` -> `sao tome`, `Washington, D.C.` -> `washington dc`).
  - Tradução multilíngue (ex: `Viena` / `Vienna`, `Pequim` / `Beijing`, `Moscou` / `Moscow`).
  - Tolerância a pequenos erros de digitação via *fuzzy matching*.
- **Dashboard Visual**: Apresentação com formatação colorida via `rich`, exibindo temperatura, sensação térmica, umidade, vento, precipitação, fuso horário e coordenadas.
- **Cache Local com Fallback**: Dataset de países pré-carregado em `src/data/countries.json` para respostas instantâneas e resiliência offline.

---

## 📁 Estrutura do Projeto

```text
clima/
├── GEMINI.md              # Governança e diretrizes do projeto
├── README.md              # Documentação e instruções de uso
├── .env.example           # Exemplo de variáveis de ambiente
├── pytest.ini             # Configurações do pytest
├── src/
│   ├── api/
│   │   ├── open_meteo.py     # Integração com API Open-Meteo (tempo real e geocoding)
│   │   └── rest_countries.py # Modelo e cliente de dados de países e capitais
│   ├── data/
│   │   └── countries.json    # Base de dados local com 250 países e capitais
│   ├── match.py              # Algoritmo de normalização e matching crítico
│   └── main.py               # Ponto de entrada CLI e dashboard interativo
└── tests/
    ├── test_match.py         # Testes de matching, acentos, idiomas e fallbacks
    ├── test_api.py           # Testes unitários de APIs e conversão de dados
    └── test_main.py          # Testes do fluxo CLI
```

---

## 💻 Como Usar

### 1. Consulta Direta via Linha de Comando

```bash
# Consultar por capital (com ou sem acento, em português ou inglês)
python src/main.py "Brasília"
python src/main.py "Tóquio"
python src/main.py "Rome"
python src/main.py "Washington, D.C."

# Consultar por país
python src/main.py "Alemanha"
python src/main.py "Japão"
python src/main.py "Estados Unidos"

# Consultar por código ISO
python src/main.py "BR"
python src/main.py "JP"
```

### 2. Modo Interativo

Basta executar o script sem argumentos:

```bash
python src/main.py
```

Digite o nome de uma capital ou país no prompt. Para sair, digite `sair` ou pressione `Ctrl+C`.

---

## 🧪 Como Rodar os Testes

A suíte de testes unitários cobre cenários exatos, acentuações, traduções, códigos ISO, tolerância a typos e erros de rede:

```bash
pytest -v
```
