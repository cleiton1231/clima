"""Cliente e integração com a API REST Countries.

Responsabilidade:
- Buscar dados de países e capitais (nome oficial, nomes comuns, traduções, coordenadas de latitude/longitude).
- Sem autenticação necessária (API pública sem token).
- Requisições com timeout explícito e tratamento gracioso de 404 e erros de rede.
"""
