# Governança e Diretrizes do Projeto: Clima Países

## 1. Contexto do Projeto
Dashboard que mostra o clima atual de qualquer capital do mundo, cruzando:
- **REST Countries API** (`https://restcountries.com`): Dados de países, capitais, códigos e coordenadas geográficas (sem auth).
- **Open-Meteo API** (`https://open-meteo.com`): Dados meteorológicos em tempo real por latitude/longitude (sem auth, sem rate limit restritivo).

## 2. Regra Específica Crítica: Matching de Cidades/Capitais
- O nome de cidade digitado pelo usuário quase nunca bate exato com o retornado pela REST Countries (problemas comuns: acentuação, abreviações, nome em inglês vs. local vs. português, ex: *Rome* / *Roma*, *Vienna* / *Viena*, *Washington, D.C.* / *Washington*).
- O algoritmo e fallback de matching em `src/match.py` é a **parte mais crítica do projeto**.
- Deve ser determinístico, robusto e **obrigatoriamente coberto por testes unitários** em `tests/test_match.py` — não fazer na base de tentativa e erro.

## 3. Diretrizes de Integração e APIs
- **Sem Autenticação**: Nenhuma das duas APIs exige token ou chave de autenticação. Não implementar lógica de token ou headers de autorização desnecessários.
- **Timeouts e Resiliência**:
  - Toda chamada HTTP deve ter timeout explícito definido.
  - Tratar status 404 (país/cidade não encontrada) e erros de rede de forma graciosa, sem estourar exceções cruas na tela.

## 4. Filosofia de Desenvolvimento e Processo
- Projeto pequeno, direto ao ponto e sem burocracia excessiva.
- Sem necessidade de planos formais complexos, sem revisão adversarial e sem subagentes.
- Foco em simplicidade, velocidade e código funcional bem testado no matching.
