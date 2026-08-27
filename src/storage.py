"""Módulo de persistência para histórico de buscas, favoritos e exportação de relatórios.

Responsabilidade:
- Armazenar histórico local de consultas recentes em formato JSON.
- Gerenciar capitais favoritas do usuário.
- Exportar relatórios climáticos em JSON e planilhas CSV.
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.api.open_meteo import WeatherData, ExtendedWeatherData
    from src.match import MatchResult

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_FILE = Path(__file__).resolve().parent.parent / ".history.json"


class CustomJSONEncoder(json.JSONEncoder):
    """Encoder JSON customizado com suporte a Dataclasses e datetime."""

    def default(self, o: Any) -> Any:
        if is_dataclass(o):
            return asdict(o)
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, Path):
            return str(o)
        return super().default(o)


class StorageManager:
    """Gerenciador de armazenamento local para histórico e favoritos."""

    def __init__(self, file_path: Path = DEFAULT_STORAGE_FILE):
        self.file_path = file_path
        self._ensure_storage_file()

    def _ensure_storage_file(self) -> None:
        """Garante que o arquivo de armazenamento existe com estrutura básica."""
        if not self.file_path.exists():
            try:
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                initial_data = {"history": [], "favorites": []}
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(initial_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Não foi possível criar arquivo de storage: {e}")

    def _read_data(self) -> dict[str, Any]:
        """Lê todos os dados persistidos."""
        if not self.file_path.exists():
            return {"history": [], "favorites": []}
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            logger.warning(f"Erro ao ler storage: {e}")
        return {"history": [], "favorites": []}

    def _write_data(self, data: dict[str, Any]) -> None:
        """Grava dados no arquivo com segurança."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, cls=CustomJSONEncoder)
        except Exception as e:
            logger.warning(f"Erro ao salvar storage: {e}")

    def add_history_entry(
        self, query: str, match_res: MatchResult, weather: WeatherData
    ) -> None:
        """Adiciona uma entrada ao histórico de consultas recentes (máximo 50 itens)."""
        data = self._read_data()
        history: list[dict[str, Any]] = data.get("history", [])

        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "query": query,
            "capital": match_res.capital,
            "country_name": match_res.country.name_pt,
            "cca2": match_res.country.cca2,
            "flag": match_res.country.flag_emoji,
            "temperature": weather.temperature,
            "apparent_temperature": weather.apparent_temperature,
            "condition": weather.weather_description,
            "emoji": weather.weather_emoji,
            "humidity": weather.relative_humidity,
            "wind_speed": weather.wind_speed,
        }

        # Insere no início da lista
        history.insert(0, entry)
        # Mantém até 50 registros
        data["history"] = history[:50]
        self._write_data(data)

    def get_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Retorna o histórico de consultas recentes ordenado pelo mais recente."""
        data = self._read_data()
        return data.get("history", [])[:limit]

    def clear_history(self) -> None:
        """Limpa o histórico de consultas."""
        data = self._read_data()
        data["history"] = []
        self._write_data(data)

    def toggle_favorite(self, capital: str, cca2: str, country_name: str, flag: str) -> bool:
        """Adiciona ou remove uma capital dos favoritos. Retorna True se foi adicionada, False se removida."""
        data = self._read_data()
        favorites: list[dict[str, Any]] = data.get("favorites", [])

        cca2 = cca2.upper().strip()
        capital_clean = capital.strip()

        existing_index = -1
        for i, fav in enumerate(favorites):
            if fav.get("cca2") == cca2 and fav.get("capital", "").lower() == capital_clean.lower():
                existing_index = i
                break

        if existing_index >= 0:
            # Remove
            favorites.pop(existing_index)
            is_added = False
        else:
            # Adiciona
            favorites.append(
                {
                    "capital": capital_clean,
                    "cca2": cca2,
                    "country_name": country_name,
                    "flag": flag,
                    "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
            is_added = True

        data["favorites"] = favorites
        self._write_data(data)
        return is_added

    def get_favorites(self) -> list[dict[str, Any]]:
        """Retorna a lista de capitais favoritas."""
        data = self._read_data()
        return data.get("favorites", [])

    def is_favorite(self, capital: str, cca2: str) -> bool:
        """Verifica se uma capital já está salva nos favoritos."""
        favorites = self.get_favorites()
        cca2 = cca2.upper().strip()
        capital_clean = capital.strip().lower()
        return any(
            f.get("cca2") == cca2 and f.get("capital", "").lower() == capital_clean
            for f in favorites
        )


def export_report_json(data: Any, filepath: str | Path) -> Path:
    """Exporta qualquer estrutura de dados ou relatório em arquivo JSON formatado."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, cls=CustomJSONEncoder)
    return path


def export_report_csv(rows: list[dict[str, Any]], filepath: str | Path) -> Path:
    """Exporta uma lista de dicionários para planilha CSV."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        with open(path, "w", encoding="utf-8", newline="") as f:
            pass
        return path

    fieldnames = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path
