# Clima Países

Dashboard simples e rápido para consultar o clima atual de qualquer capital do mundo, cruzando dados geográficos da **REST Countries** com dados meteorológicos da **Open-Meteo**.

## Estrutura do Projeto

```
clima-paises/
├── GEMINI.md
├── src/
│   ├── api/
│   │   ├── open_meteo.py
│   │   └── rest_countries.py
│   ├── match.py
│   └── main.py
├── tests/
│   └── test_match.py
├── .env.example
└── README.md
```

## Características
- **Open-Meteo**: Previsão e clima atual por coordenadas (sem autenticação).
- **REST Countries**: Informações de países e capitais (sem autenticação).
- **Matching Inteligente**: Normalização de nomes de cidades com fallback resiliente para variações de acento, idioma e abreviações.
