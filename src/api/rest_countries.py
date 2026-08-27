"""Cliente e integração com a API REST Countries / Dataset de Países.

Responsabilidade:
- Carregar dados de países e capitais (nome oficial, nomes comuns, traduções, coordenadas e metadados).
- Sem necessidade de autenticação/token.
- Suporte a cache local (src/data/countries.json) com fallback resiliente para rede.
- Tratamento explícito de timeouts e erros HTTP sem estourar exceções cruas.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "countries.json"
REMOTE_DATASET_URL = "https://raw.githubusercontent.com/mledoze/countries/master/countries.json"


def country_code_to_flag_emoji(code: str) -> str:
    """Converte um código ISO 3166-1 alpha-2 (ex: 'BR') para o emoji da bandeira correspondente (🇧🇷)."""
    if not code or len(code) != 2:
        return "🌐"
    code = code.upper()
    try:
        return "".join(chr(127397 + ord(char)) for char in code)
    except Exception:
        return "🌐"


@dataclass
class Country:
    """Representação estruturada de um país."""

    name_common: str
    name_official: str
    name_pt: str
    capitals: list[str]
    cca2: str
    cca3: str
    region: str
    subregion: str
    flag_emoji: str
    latlng: list[float] = field(default_factory=list)
    translations: dict[str, str] = field(default_factory=dict)
    native_names: list[str] = field(default_factory=list)

    @property
    def primary_capital(self) -> str:
        """Retorna a capital principal ou string vazia se não houver."""
        return self.capitals[0] if self.capitals else ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Country:
        """Cria uma instância de Country a partir de um dicionário do dataset."""
        name_data = data.get("name", {})
        if isinstance(name_data, dict):
            name_common = name_data.get("common", "")
            name_official = name_data.get("official", "")
            native_dict = name_data.get("native", {})
            native_names: list[str] = []
            if isinstance(native_dict, dict):
                for _, nval in native_dict.items():
                    if isinstance(nval, dict):
                        if "common" in nval and nval["common"]:
                            native_names.append(nval["common"])
                        if "official" in nval and nval["official"]:
                            native_names.append(nval["official"])
        else:
            name_common = str(name_data)
            name_official = name_common
            native_names = []

        # Tratamento de capitais
        raw_capital = data.get("capital", [])
        if isinstance(raw_capital, list):
            capitals = [str(c).strip() for c in raw_capital if str(c).strip()]
        elif isinstance(raw_capital, str) and raw_capital.strip():
            capitals = [raw_capital.strip()]
        else:
            capitals = []

        # Traduções
        trans_dict = data.get("translations", {})
        translations: dict[str, str] = {}
        name_pt = name_common
        if isinstance(trans_dict, dict):
            for lang, val in trans_dict.items():
                if isinstance(val, dict):
                    c_name = val.get("common") or val.get("official")
                    if c_name:
                        translations[lang] = c_name
                        if lang == "por":
                            name_pt = c_name
                elif isinstance(val, str):
                    translations[lang] = val
                    if lang == "por":
                        name_pt = val

        cca2 = str(data.get("cca2", "")).upper()
        cca3 = str(data.get("cca3", "")).upper()
        region = str(data.get("region", ""))
        subregion = str(data.get("subregion", ""))
        flag_emoji = country_code_to_flag_emoji(cca2)
        latlng = data.get("latlng", [])

        return cls(
            name_common=name_common,
            name_official=name_official,
            name_pt=name_pt,
            capitals=capitals,
            cca2=cca2,
            cca3=cca3,
            region=region,
            subregion=subregion,
            flag_emoji=flag_emoji,
            latlng=latlng if isinstance(latlng, list) else [],
            translations=translations,
            native_names=list(set(native_names)),
        )


class RestCountriesClient:
    """Cliente para carregar e consultar informações de países e capitais."""

    def __init__(self, data_path: Path = DATA_FILE, timeout: int = 10):
        self.data_path = data_path
        self.timeout = timeout
        self._countries: list[Country] | None = None

    def load_countries(self, force_remote: bool = False) -> list[Country]:
        """Carrega a lista de países do cache local ou remotamente."""
        if self._countries is not None and not force_remote:
            return self._countries

        raw_data: list[dict[str, Any]] | None = None

        if not force_remote and self.data_path.exists():
            try:
                with open(self.data_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
            except Exception as e:
                logger.warning(f"Erro ao ler arquivo local de países: {e}")

        if raw_data is None:
            raw_data = self._fetch_remote()

        if not raw_data:
            logger.error("Não foi possível obter a lista de países.")
            self._countries = []
            return []

        self._countries = [Country.from_dict(item) for item in raw_data if isinstance(item, dict)]
        return self._countries

    def _fetch_remote(self) -> list[dict[str, Any]] | None:
        """Busca o dataset remoto com timeout e tratamento de erros."""
        try:
            response = requests.get(REMOTE_DATASET_URL, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    # Salva cache local se possível
                    try:
                        self.data_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(self.data_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        logger.debug(f"Não foi possível salvar cache local: {e}")
                    return data
            logger.warning(f"Requisição remota retornou status {response.status_code}")
        except requests.RequestException as e:
            logger.warning(f"Erro de conexão ao buscar dataset remoto de países: {e}")
        return None

    def get_by_cca2(self, code: str) -> Country | None:
        """Busca país pelo código ISO alpha-2."""
        code = code.strip().upper()
        for country in self.load_countries():
            if country.cca2 == code:
                return country
        return None

    def get_by_cca3(self, code: str) -> Country | None:
        """Busca país pelo código ISO alpha-3."""
        code = code.strip().upper()
        for country in self.load_countries():
            if country.cca3 == code:
                return country
        return None
