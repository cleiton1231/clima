"""Módulo de integração com a Open-Meteo Historical Archive API e análise de anomalias climáticas.

Responsabilidade:
- Consultar registros meteorológicos históricos dos últimos 10 a 20 anos para capitais mundiais.
- Calcular normais climatológicas da mesma data (média, máxima histórica, mínima histórica e precipitação média).
- Calcular e classificar anomalias térmicas e pluviométricas em tempo real.
- Garantir segurança contra SSRF e injeção de parâmetros com validações de limites.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

OPEN_METEO_HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"


def classify_temperature_anomaly(anomaly: float) -> tuple[str, str]:
    """Classifica a anomalia térmica em relação à normal histórica da data.
    
    Retorna (status_descritivo, emoji).
    """
    if anomaly >= 3.0:
        return "Muito acima da média histórica", "🔥"
    elif anomaly >= 1.0:
        return "Acima da média histórica", "🔺"
    elif anomaly > -1.0:
        return "Dentro da normalidade histórica", "🟢"
    elif anomaly > -3.0:
        return "Abaixo da média histórica", "🔻"
    else:
        return "Muito abaixo da média histórica", "❄️"


@dataclass
class HistoricalAnalysis:
    """Estrutura com os resultados da análise histórica e anomalia climática."""
    capital: str
    country_name: str
    target_date: str  # YYYY-MM-DD
    years_analyzed: int
    current_temp: float
    historical_mean_temp: float
    historical_max_temp: float
    historical_min_temp: float
    temp_anomaly: float
    anomaly_status: str
    anomaly_emoji: str
    historical_avg_precip: float


class HistoricalWeatherClient:
    """Cliente para a API de Arquivo Histórico da Open-Meteo."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def _validate_coordinates(self, latitude: float, longitude: float) -> None:
        """Valida se as coordenadas estão dentro dos limites geográficos válidos."""
        try:
            lat = float(latitude)
            lon = float(longitude)
        except (ValueError, TypeError):
            raise ValueError(f"Coordenadas inválidas: lat={latitude}, lon={longitude}")

        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"Latitude inválida ({lat}). Deve estar entre -90 e 90.")
        if not (-180.0 <= lon <= 180.0):
            raise ValueError(f"Longitude inválida ({lon}). Deve estar entre -180 e 180.")

    def get_historical_analysis(
        self,
        capital: str,
        country_name: str,
        latitude: float,
        longitude: float,
        current_temp: float,
        target_date: Optional[str] = None,
        years_back: int = 10,
        timezone: str = "auto",
    ) -> Optional[HistoricalAnalysis]:
        """Obtém a análise comparativa histórica para a mesma data nos anos anteriores."""
        self._validate_coordinates(latitude, longitude)

        if not target_date:
            target_date = datetime.now().strftime("%Y-%m-%d")

        try:
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            target_dt = datetime.now()
            target_date = target_dt.strftime("%Y-%m-%d")

        # Define o intervalo dos anos históricos anteriores (ex: 2016 a 2025 para consulta em 2026)
        end_year = target_dt.year - 1
        start_year = max(1940, end_year - years_back + 1)
        actual_years_count = end_year - start_year + 1

        start_date = f"{start_year}-{target_dt.month:02d}-{target_dt.day:02d}"
        end_date = f"{end_year}-{target_dt.month:02d}-{target_dt.day:02d}"

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": [
                "temperature_2m_mean",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
            ],
            "timezone": timezone or "auto",
        }

        try:
            response = requests.get(
                OPEN_METEO_HISTORICAL_URL,
                params=params,
                timeout=self.timeout,
            )
            if response.status_code != 200:
                logger.warning(
                    f"Erro na API Histórica ({response.status_code}): {response.text[:200]}"
                )
                return None

            data = response.json()
            daily = data.get("daily", {})
            times = daily.get("time", [])

            t_means: list[float] = []
            t_maxs: list[float] = []
            t_mins: list[float] = []
            precips: list[float] = []

            # Filtra apenas os dias correspondentes ao mesmo mês e dia
            target_month_day = f"{target_dt.month:02d}-{target_dt.day:02d}"

            for i, t_str in enumerate(times):
                # Se for a mesma data do ano ou amostra
                if t_str.endswith(target_month_day) or len(times) <= actual_years_count:
                    m = daily.get("temperature_2m_mean", [None])[i] if i < len(daily.get("temperature_2m_mean", [])) else None
                    mx = daily.get("temperature_2m_max", [None])[i] if i < len(daily.get("temperature_2m_max", [])) else None
                    mn = daily.get("temperature_2m_min", [None])[i] if i < len(daily.get("temperature_2m_min", [])) else None
                    p = daily.get("precipitation_sum", [None])[i] if i < len(daily.get("precipitation_sum", [])) else None

                    if m is not None:
                        t_means.append(float(m))
                    if mx is not None:
                        t_maxs.append(float(mx))
                    if mn is not None:
                        t_mins.append(float(mn))
                    if p is not None:
                        precips.append(float(p))

            # Se não encontrou amostra exata por data, usa todas as disponíveis no payload
            if not t_means and daily.get("temperature_2m_mean"):
                t_means = [float(v) for v in daily["temperature_2m_mean"] if v is not None]
            if not t_maxs and daily.get("temperature_2m_max"):
                t_maxs = [float(v) for v in daily["temperature_2m_max"] if v is not None]
            if not t_mins and daily.get("temperature_2m_min"):
                t_mins = [float(v) for v in daily["temperature_2m_min"] if v is not None]
            if not precips and daily.get("precipitation_sum"):
                precips = [float(v) for v in daily["precipitation_sum"] if v is not None]

            if not t_means:
                logger.warning(f"Nenhum dado histórico de temperatura encontrado para {capital}")
                return None

            hist_mean = sum(t_means) / len(t_means)
            hist_max = max(t_maxs) if t_maxs else hist_mean
            hist_min = min(t_mins) if t_mins else hist_mean
            hist_precip = sum(precips) / len(precips) if precips else 0.0

            anomaly = current_temp - hist_mean
            status_desc, emoji = classify_temperature_anomaly(anomaly)

            return HistoricalAnalysis(
                capital=capital,
                country_name=country_name,
                target_date=target_date,
                years_analyzed=len(t_means),
                current_temp=current_temp,
                historical_mean_temp=round(hist_mean, 1),
                historical_max_temp=round(hist_max, 1),
                historical_min_temp=round(hist_min, 1),
                temp_anomaly=round(anomaly, 1),
                anomaly_status=status_desc,
                anomaly_emoji=emoji,
                historical_avg_precip=round(hist_precip, 1),
            )

        except requests.RequestException as e:
            logger.warning(f"Erro de conexão na API Histórica: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado no cálculo histórico: {e}", exc_info=True)
            return None
