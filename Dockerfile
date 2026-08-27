FROM python:3.12-slim

# Metadados
LABEL maintainer="Cleiton <cleiton1231>"
LABEL description="Dashboard e API de Clima para Capitais Mundiais"

RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copia requisitos e código completo
COPY requirements.txt pyproject.toml README.md ./
COPY src/ ./src/

# Instala dependências e o pacote clima-paises
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir .

# Configura diretório de dados com permissões para appuser
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

ENV CLIMA_STORAGE_PATH=/app/data/.history.json
ENV PORT=8000
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

ENTRYPOINT ["clima"]
CMD []
