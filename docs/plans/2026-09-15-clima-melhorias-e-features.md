# Plano: Melhorias de Qualidade + Busca de Não-Capitais + Alertas Climáticos

**Goal:** Corrigir os 4 problemas de qualidade (CORS inseguro, dependência morta/version drift, race condition no storage) e adicionar 2 features (fallback de geocoding para cidades não-capitais e painel de alertas climáticos), sem quebrar os 146 testes existentes.

**Approach:** Fase 1 (Tasks 1–3): correções de qualidade, cada uma independente e testável. Fase 2 (Tasks 4–8): features novas — `resolve_place` como camada de resolução acima do matcher puro (que continua sem HTTP), e `src/alerts.py` como módulo puro de regras, consumido por CLI e Web API.

**Spec:** Conversa com usuário (avaliação do projeto em 2026-09-15). Governança: `GEMINI.md`.

## Global Constraints

- Sem novas dependências (`aiofiles` será REMOVIDA; nada adicionado).
- `src/match.py` permanece puro (sem HTTP) — regra crítica do `GEMINI.md`.
- Toda chamada HTTP com timeout explícito (já existente, mantido).
- Suíte completa deve passar ao final de cada task (`pytest --cov=src -q`, ≥146 testes, cobertura ≥70%).
- Mensagens de UI em português, estilo dos módulos existentes.

---

# Fase 1 — Correções de Qualidade

### Task 1: Housekeeping — remover `aiofiles` morta + unificar versão em 1.1.0

**Files:**
- Modify: `pyproject.toml` (linha 7: `version = "1.0.0"`; linha 17: `"aiofiles>=23.2.0",`)
- Modify: `requirements.txt` (linha 6: `aiofiles>=23.2.0`)

**Interfaces:**
- Consumes: nada
- Produces: pacote `clima-paises` versão `1.1.0`, sem `aiofiles`

- [ ] Step 1: Remover `"aiofiles>=23.2.0",` do array `dependencies` em `pyproject.toml` e mudar `version = "1.0.0"` para `version = "1.1.0"`
- [ ] Step 2: Remover a linha `aiofiles>=23.2.0` de `requirements.txt`
- [ ] Step 3: Verificar: `grep -rn aiofiles pyproject.toml requirements.txt src/` → vazio; `pip install -e .` → sucesso
- [ ] Step 4: `pytest --cov=src -q` → 146 passed
- [ ] Step 5: Commit: `git add pyproject.toml requirements.txt && git commit -m "chore: remove aiofiles nao utilizada e unifica versao em 1.1.0"`

### Task 2: CORS seguro (`allow_credentials=False`)

**Files:**
- Modify: `src/web/app.py:46-52`
- Test: `tests/test_web_api.py` (adicionar teste ao final)

**Interfaces:**
- Consumes: nada
- Produces: middleware CORS conforme spec (wildcard só é válido sem credentials)

- [ ] Step 1: Escrever o teste falho em `tests/test_web_api.py`:
```python
def test_cors_preflight_sem_credentials(client):
    response = client.options(
        "/api/weather/Brasilia",
        headers={"Origin": "http://exemplo.com", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "*"
    assert "access-control-allow-credentials" not in response.headers
```
- [ ] Step 2: `pytest tests/test_web_api.py::test_cors_preflight_sem_credentials -q` → FAIL (header `access-control-allow-credentials` presente, pois `allow_credentials=True`)
- [ ] Step 3: Em `src/web/app.py:46-52`, mudar `allow_credentials=True` para `allow_credentials=False` e ajustar o comentário acima para `# CORS conforme spec: wildcard de origens só é válido sem credenciais`
- [ ] Step 4: `pytest tests/test_web_api.py -q` → PASS (novo teste + 11 existentes)
- [ ] Step 5: `pytest --cov=src -q` → 147 passed; Commit: `git add src/web/app.py tests/test_web_api.py && git commit -m "fix: CORS wildcard sem credentials conforme spec CORS"`

### Task 3: Lock no `StorageManager` contra escrita concorrente

**Files:**
- Modify: `src/storage.py` (`StorageManager.__init__`, `_read_data`, `add_history_entry`, `clear_history`, `toggle_favorite`, `get_history`, `get_favorites`, `is_favorite`)
- Test: `tests/test_storage.py` (adicionar teste ao final)

**Interfaces:**
- Consumes: nada
- Produces: `StorageManager` thread-safe em processo via `threading.RLock()` (RLock porque `_read_data`/`_write_data` são chamados dentro dos métodos públicos travados)

- [ ] Step 1: Escrever o teste falho em `tests/test_storage.py`:
```python
def test_history_escrita_concorrente_sem_perda(tmp_path, sample_match_and_weather):
    from concurrent.futures import ThreadPoolExecutor

    match_res, weather = sample_match_and_weather
    storage = StorageManager(tmp_path / "concurrent.json")

    with ThreadPoolExecutor(max_workers=10) as pool:
        list(
            pool.map(
                lambda i: storage.add_history_entry(f"query{i}", match_res, weather),
                range(10),
            )
        )

    history = storage.get_history(limit=50)
    assert len(history) == 10
    assert {h["query"] for h in history} == {f"query{i}" for i in range(10)}
```
- [ ] Step 2: `pytest tests/test_storage.py::test_history_escrita_concorrente_sem_perda -q` → pode passar por sorte no momento, mas falha de forma intermitente sem lock (lost updates no read-modify-write); o objetivo do lock é garantir determinismo
- [ ] Step 3: Implementar em `src/storage.py`: adicionar `import threading` no topo; em `StorageManager.__init__` (antes de `self._ensure_storage_file()`), adicionar `self._lock = threading.RLock()`. Envolver o corpo de `add_history_entry`, `clear_history`, `toggle_favorite`, `get_history`, `get_favorites` e `is_favorite` com `with self._lock:`
- [ ] Step 4: `pytest tests/test_storage.py -q` → PASS; `pytest --cov=src -q` → 148 passed
- [ ] Step 5: Commit: `git add src/storage.py tests/test_storage.py && git commit -m "fix: RLock no StorageManager para evitar perda de dados sob concorrencia"`

---

# Fase 2 — Features

### Task 4: `search_place` no cliente Open-Meteo + módulo `resolver`

**Files:**
- Modify: `src/api/open_meteo.py` (adicionar `PlaceHit` dataclass e `OpenMeteoClient.search_place`)
- Create: `src/resolver.py`
- Test: `tests/test_resolver.py` (novo)

**Interfaces:**
- Consumes: `CityMatcher.match(query: str) -> MatchResult | None` (existente), `Country` e `country_code_to_flag_emoji` de `src.api.rest_countries` (existentes)
- Produces:
  - `PlaceHit` dataclass com campos `name: str, latitude: float, longitude: float, timezone: str, country: str, country_code: str` (em `src.api.open_meteo`)
  - `OpenMeteoClient.search_place(city: str) -> PlaceHit | None`
  - `src.resolver.resolve_place(query: str, matcher: CityMatcher, meteo_client: OpenMeteoClient) -> MatchResult | None`

- [ ] Step 1: Escrever `tests/test_resolver.py` (teste falho):
```python
"""Testes do resolver: matcher local com fallback de geocoding."""

from unittest.mock import MagicMock

from src.api.open_meteo import PlaceHit
from src.match import MatchResult
from src.resolver import resolve_place


def test_matcher_tem_prioridade_sobre_geocoding():
    match_res = MatchResult(
        capital="Paris",
        country=MagicMock(),
        matched_term="paris",
        match_type="exact_capital",
        confidence=1.0,
    )
    matcher = MagicMock()
    matcher.match.return_value = match_res
    meteo = MagicMock()

    result = resolve_place("Paris", matcher, meteo)

    assert result is match_res
    meteo.search_place.assert_not_called()


def test_fallback_geocoding_para_cidade_nao_capital():
    matcher = MagicMock()
    matcher.match.return_value = None
    meteo = MagicMock()
    meteo.search_place.return_value = PlaceHit(
        name="São Paulo",
        latitude=-23.5505,
        longitude=-46.6333,
        timezone="America/Sao_Paulo",
        country="Brazil",
        country_code="BR",
    )

    result = resolve_place("sao paulo", matcher, meteo)

    assert result is not None
    assert result.capital == "São Paulo"
    assert result.match_type == "geocoding_fallback"
    assert result.country.cca2 == "BR"
    assert result.country.flag_emoji == "🇧🇷"


def test_retorna_none_quando_ambos_falham():
    matcher = MagicMock()
    matcher.match.return_value = None
    meteo = MagicMock()
    meteo.search_place.return_value = None

    assert resolve_place("cidade inexistente", matcher, meteo) is None
```
- [ ] Step 2: `pytest tests/test_resolver.py -q` → FAIL com `ImportError: cannot import name 'PlaceHit'`
- [ ] Step 3: Implementar. Em `src/api/open_meteo.py`, após a dataclass `WeatherData`:
```python
@dataclass
class PlaceHit:
    """Resultado do fallback de geocoding para cidades não-capitais."""

    name: str
    latitude: float
    longitude: float
    timezone: str
    country: str
    country_code: str
```
E na classe `OpenMeteoClient` (após `get_coordinates`):
```python
def search_place(self, city: str) -> PlaceHit | None:
    """Busca qualquer cidade (não apenas capitais) via Geocoding API."""
    if not city:
        return None
    params: dict[str, Any] = {"name": city, "count": 1, "language": "pt", "format": "json"}
    try:
        response = requests.get(OPEN_METEO_GEOCODING_URL, params=params, timeout=self.timeout)
        if response.status_code == 200:
            results = response.json().get("results") or []
            if results:
                best = results[0]
                return PlaceHit(
                    name=str(best.get("name", city)),
                    latitude=float(best.get("latitude", 0.0)),
                    longitude=float(best.get("longitude", 0.0)),
                    timezone=str(best.get("timezone", "UTC")),
                    country=str(best.get("country", "")),
                    country_code=str(best.get("country_code", "")).upper(),
                )
    except requests.RequestException as e:
        logger.warning(f"Erro no fallback de geocoding para '{city}': {e}")
    return None
```
Criar `src/resolver.py`:
```python
"""Resolver de consultas: matcher local de capitais + fallback de geocoding Open-Meteo."""

from __future__ import annotations

from src.api.open_meteo import OpenMeteoClient, PlaceHit
from src.api.rest_countries import Country, country_code_to_flag_emoji
from src.match import CityMatcher, MatchResult


def _country_from_place(hit: PlaceHit) -> Country:
    cca2 = hit.country_code.upper()
    return Country(
        name_common=hit.country or hit.name,
        name_official=hit.country or hit.name,
        name_pt=hit.country or hit.name,
        capitals=[hit.name],
        cca2=cca2,
        cca3="",
        region="",
        subregion="",
        flag_emoji=country_code_to_flag_emoji(cca2),
        latlng=[hit.latitude, hit.longitude],
    )


def resolve_place(
    query: str, matcher: CityMatcher, meteo_client: OpenMeteoClient
) -> MatchResult | None:
    """Resolve a query pelo matcher de capitais; se falhar, usa o geocoding Open-Meteo."""
    if not query or not query.strip():
        return None

    match_res = matcher.match(query.strip())
    if match_res:
        return match_res

    hit = meteo_client.search_place(query.strip())
    if not hit or not hit.country_code:
        return None

    return MatchResult(
        capital=hit.name,
        country=_country_from_place(hit),
        matched_term=hit.name.lower(),
        match_type="geocoding_fallback",
        confidence=1.0,
    )
```
- [ ] Step 4: `pytest tests/test_resolver.py -q` → PASS (3 testes)
- [ ] Step 5: `pytest --cov=src -q` → 151 passed; Commit: `git add src/api/open_meteo.py src/resolver.py tests/test_resolver.py && git commit -m "feat: resolver com fallback de geocoding para cidades nao-capitais"`

### Task 5: Usar `resolve_place` na CLI (query, menu e favoritos)

**Files:**
- Modify: `src/main.py:16-32` (import), `src/main.py:68` (`execute_city_query`), `src/main.py:269` (menu opção 7), `src/main.py:376` (`--add-fav`)
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `src.resolver.resolve_place(query, matcher, meteo_client) -> MatchResult | None` (Task 4, verbatim)
- Produces: CLI que aceita qualquer cidade, com `match_type="geocoding_fallback"` visível no card

- [ ] Step 1: Escrever o teste falho em `tests/test_main.py`:
```python
def test_execute_city_query_fallback_geocoding(tmp_path):
    storage = StorageManager(tmp_path / "hist.json")
    mock_matcher = MagicMock()
    mock_matcher.match.return_value = None
    mock_meteo = MagicMock()
    from src.api.open_meteo import PlaceHit, WeatherData

    mock_meteo.search_place.return_value = PlaceHit(
        name="São Paulo",
        latitude=-23.5505,
        longitude=-46.6333,
        timezone="America/Sao_Paulo",
        country="Brazil",
        country_code="BR",
    )
    weather = WeatherData(
        temperature=21.0,
        apparent_temperature=20.5,
        relative_humidity=70,
        wind_speed=6.0,
        precipitation=0.0,
        weather_code=0,
        weather_description="Céu limpo",
        weather_emoji="☀️",
        is_day=True,
        time="2026-08-27T16:00",
        latitude=-23.5505,
        longitude=-46.6333,
        elevation=760.0,
        timezone="America/Sao_Paulo",
    )
    mock_meteo.get_current_weather.return_value = weather

    assert execute_city_query("sao paulo", mock_matcher, mock_meteo, storage) is True
    history = storage.get_history()
    assert len(history) == 1
    assert history[0]["capital"] == "São Paulo"
    assert history[0]["cca2"] == "BR"
```
- [ ] Step 2: `pytest tests/test_main.py::test_execute_city_query_fallback_geocoding -q` → FAIL ( retorna False: ainda só usa `matcher.match` )
- [ ] Step 3: Implementar em `src/main.py`:
  - Import: `from src.resolver import resolve_place`
  - `execute_city_query` linha 68: trocar `match_res = matcher.match(query)` por `match_res = resolve_place(query, matcher, meteo_client)`
  - Menu opção 7 (linha 269): trocar `match_res = matcher.match(q)` por `match_res = resolve_place(q, matcher, meteo_client)`
  - Flag `--add-fav` (linha 376): trocar `match_res = matcher.match(args.add_fav)` por `match_res = resolve_place(args.add_fav, matcher, meteo_client)`
  - Atualizar o teste existente `test_execute_city_query_not_found`: adicionar `mock_meteo.search_place.return_value = None` (sem isso o MagicMock retorna truthy e o teste quebra)
- [ ] Step 4: `pytest tests/test_main.py -q` → PASS; `pytest --cov=src -q` → 152 passed
- [ ] Step 5: Commit: `git add src/main.py tests/test_main.py && git commit -m "feat: CLI aceita qualquer cidade via fallback de geocoding"`

### Task 6: Módulo de alertas climáticos (`src/alerts.py`)

**Files:**
- Create: `src/alerts.py`
- Test: `tests/test_alerts.py` (novo)

**Interfaces:**
- Consumes: `ExtendedWeatherData` de `src.api.open_meteo` (existente)
- Produces:
  - `@dataclass Alert` com campos `level: str` (`critico` | `alto` | `atencao`), `emoji: str`, `title: str`, `detail: str`
  - `src.alerts.build_alerts(extended: ExtendedWeatherData) -> list[Alert]`

**Regras exatas (na ordem, todas testadas):**
1. `critico ⛈️ "Tempestade prevista"` — `extended.current.weather_code >= 95` ou qualquer `d.weather_code >= 95` em `extended.daily`; `detail` = datas dos dias (`", ".join(d.date ...)`)
2. `alto 🌧️ "Risco alto de chuva"` — qualquer `d.precipitation_sum >= 10.0` ou `d.precipitation_probability_max >= 80`
3. `atencao ☀️ "Índice UV muito alto"` — qualquer `d.uv_index_max >= 8.0`
4. `alto 🔥 "Calor extremo"` — qualquer `d.temp_max >= 35.0` ou `extended.current.apparent_temperature >= 35.0`
5. `atencao ❄️ "Temperatura negativa"` — qualquer `d.temp_min <= 0.0`
6. `alto 🌫️ "Qualidade do ar ruim"` — `extended.air_quality` não nulo e `european_aqi > 80`

- [ ] Step 1: Escrever `tests/test_alerts.py` (teste falho):
```python
"""Testes das regras de alertas climáticos."""

from src.alerts import build_alerts
from src.api.open_meteo import (
    AirQualityData,
    DailyForecast,
    ExtendedWeatherData,
    HourlyForecast,
    WeatherData,
)


def _extended(
    daily: list[DailyForecast] | None = None,
    air_quality: AirQualityData | None = None,
    current_temp: float = 22.0,
    current_code: int = 0,
) -> ExtendedWeatherData:
    weather = WeatherData(
        temperature=current_temp,
        apparent_temperature=current_temp,
        relative_humidity=50,
        wind_speed=5.0,
        precipitation=0.0,
        weather_code=current_code,
        weather_description="Céu limpo",
        weather_emoji="☀️",
        is_day=True,
        time="2026-08-27T16:00",
        latitude=0.0,
        longitude=0.0,
        elevation=0.0,
        timezone="UTC",
    )
    return ExtendedWeatherData(
        current=weather,
        daily=daily or [],
        hourly=[],
        air_quality=air_quality,
    )


def _day(
    code: int = 0,
    precip_sum: float = 0.0,
    precip_prob: int = 0,
    uv: float = 0.0,
    t_max: float = 25.0,
    t_min: float = 15.0,
    date: str = "2026-08-28",
) -> DailyForecast:
    return DailyForecast(
        date=date,
        weather_code=code,
        weather_description="x",
        weather_emoji="☀️",
        temp_min=t_min,
        temp_max=t_max,
        precipitation_sum=precip_sum,
        precipitation_probability_max=precip_prob,
        uv_index_max=uv,
        sunrise="06:00",
        sunset="18:00",
    )


def test_clima_limpo_gera_zero_alertas():
    assert build_alerts(_extended(daily=[_day()])) == []


def test_tempestade_alerta_critico():
    alerts = build_alerts(_extended(daily=[_day(code=95, date="2026-08-28")]))
    assert len(alerts) == 1
    assert alerts[0].level == "critico"
    assert "Tempestade" in alerts[0].title
    assert "2026-08-28" in alerts[0].detail


def test_chuva_intensa_por_mm_e_por_probabilidade():
    alerts_mm = build_alerts(_extended(daily=[_day(precip_sum=12.0)]))
    alerts_prob = build_alerts(_extended(daily=[_day(precip_prob=85)]))
    assert alerts_mm[0].title == "🌧️ Risco alto de chuva"
    assert alerts_prob[0].title == "🌧️ Risco alto de chuva"


def test_uv_muito_alto():
    alerts = build_alerts(_extended(daily=[_day(uv=8.5)]))
    assert len(alerts) == 1
    assert alerts[0].level == "atencao"
    assert "UV" in alerts[0].title


def test_calor_extremo_por_diario_e_por_sensacao():
    assert build_alerts(_extended(daily=[_day(t_max=36.0)]))[0].title == "🔥 Calor extremo"
    assert build_alerts(_extended(current_temp=35.5))[0].title == "🔥 Calor extremo"


def test_frio_extremo():
    alerts = build_alerts(_extended(daily=[_day(t_min=-2.0)]))
    assert alerts[0].title == "❄️ Temperatura negativa"


def test_qualidade_do_ar_ruim():
    aqi_ruim = AirQualityData(
        european_aqi=95, aqi_level="Muito Ruim", aqi_emoji="🔴",
        pm2_5=40.0, pm10=50.0, nitrogen_dioxide=5.0, ozone=80.0,
    )
    alerts = build_alerts(_extended(air_quality=aqi_ruim))
    assert alerts[0].title == "🌫️ Qualidade do ar ruim"
    assert alerts[0].level == "alto"
```
(Nota: `uv` no `_day` é parâmetro passado a `uv_index_max`; renomear a variável do parâmetro para `uv` e usá-la diretamente.)
- [ ] Step 2: `pytest tests/test_alerts.py -q` → FAIL com `ModuleNotFoundError: No module named 'src.alerts'`
- [ ] Step 3: Implementar `src/alerts.py`:
```python
"""Regras de alertas climáticos derivados de previsão estendida e qualidade do ar."""

from __future__ import annotations

from dataclasses import dataclass

from src.api.open_meteo import ExtendedWeatherData


@dataclass
class Alert:
    """Alerta climático para exibição no CLI e na Web API."""

    level: str  # 'critico' | 'alto' | 'atencao'
    emoji: str
    title: str
    detail: str


def build_alerts(extended: ExtendedWeatherData) -> list[Alert]:
    """Deriva alertas a partir dos dados já presentes em ExtendedWeatherData."""
    alerts: list[Alert] = []
    daily = extended.daily
    current = extended.current

    storm_days = [
        d.date for d in daily if d.weather_code >= 95
    ] + ([current.time.split("T")[0]] if current.weather_code >= 95 else [])
    if storm_days:
        alerts.append(
            Alert(
                level="critico",
                emoji="⛈️",
                title="Tempestade prevista",
                detail=", ".join(sorted(set(storm_days))),
            )
        )

    rain_days = [
        d.date for d in daily if d.precipitation_sum >= 10.0 or d.precipitation_probability_max >= 80
    ]
    if rain_days:
        alerts.append(
            Alert(
                level="alto",
                emoji="🌧️",
                title="🌧️ Risco alto de chuva",
                detail=", ".join(rain_days),
            )
        )

    uv_days = [d.date for d in daily if d.uv_index_max >= 8.0]
    if uv_days:
        alerts.append(
            Alert(
                level="atencao",
                emoji="☀️",
                title="☀️ Índice UV muito alto",
                detail=", ".join(uv_days),
            )
        )

    heat_days = [d.date for d in daily if d.temp_max >= 35.0]
    if heat_days or current.apparent_temperature >= 35.0:
        alerts.append(
            Alert(
                level="alto",
                emoji="🔥",
                title="🔥 Calor extremo",
                detail=", ".join(heat_days) if heat_days else "agora",
            )
        )

    cold_days = [d.date for d in daily if d.temp_min <= 0.0]
    if cold_days:
        alerts.append(
            Alert(
                level="atencao",
                emoji="❄️",
                title="❄️ Temperatura negativa",
                detail=", ".join(cold_days),
            )
        )

    if extended.air_quality and extended.air_quality.european_aqi > 80:
        alerts.append(
            Alert(
                level="alto",
                emoji="🌫️",
                title="🌫️ Qualidade do ar ruim",
                detail=f"AQI {extended.air_quality.european_aqi}",
            )
        )

    return alerts
```
- [ ] Step 4: `pytest tests/test_alerts.py -q` → PASS (7 testes)
- [ ] Step 5: `pytest --cov=src -q` → 159 passed; Commit: `git add src/alerts.py tests/test_alerts.py && git commit -m "feat: modulo puro de alertas climaticos com 6 regras testadas"`

### Task 7: Renderizar alertas no CLI (`render_alerts` + wiring)

**Files:**
- Modify: `src/ui/views.py` (nova função `render_alerts` no fim do arquivo)
- Modify: `src/main.py` (imports e chamada em `execute_city_query`, após os blocos de renderização estendidos — linha ~118)
- Test: `tests/test_views.py`

**Interfaces:**
- Consumes: `list[Alert]` de `src.alerts` (Task 6, verbatim)
- Produces: `render_alerts(alerts: list[Alert]) -> None` (no-op se lista vazia); alertas aparecem no CLI sempre que há dados estendidos (paths `show_all` e flags — um único ponto de chamada após o `if/else` de exibição). Caminho simples (`get_current_weather` sem daily) NÃO gera alertas — decisão documentada: dados insuficientes.

- [ ] Step 1: Escrever o teste falho em `tests/test_views.py`:
```python
def test_render_alerts_imprime_e_ignora_vazio(capsys):
    from src.alerts import Alert
    from src.ui.views import render_alerts

    render_alerts([])  # vazio: no-op
    assert capsys.readouterr().out.strip() == ""

    alerts = [Alert(level="alto", emoji="🌧️", title="🌧️ Risco alto de chuva", detail="2026-08-28")]
    render_alerts(alerts)
    out = capsys.readouterr().out
    assert "⚠️" in out
    assert "Risco alto de chuva" in out
```
- [ ] Step 2: `pytest tests/test_views.py::test_render_alerts_imprime_e_ignora_vazio -q` → FAIL com `ImportError`
- [ ] Step 3: Implementar. Em `src/ui/views.py` (fim do arquivo):
```python
def render_alerts(alerts: list[Alert]) -> None:
    """Exibe painel de alertas climáticos; no-op se não houver alertas."""
    if not alerts:
        return

    if HAS_RICH and console:
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Nível", style="bold")
        table.add_column("Alerta", style="white")

        level_emoji = {"critico": "🔴", "alto": "🟠", "atencao": "🟡"}
        for a in alerts:
            table.add_row(level_emoji.get(a.level, "•"), f"{a.emoji} {a.title} — {a.detail}")

        console.print(
            Panel(table, title="⚠️ [bold yellow]Alertas Climáticos[/bold yellow]", border_style="yellow", expand=False)
        )
    else:
        print("\n--- Alertas Climáticos ---")
        for a in alerts:
            print(f"{a.emoji} {a.title} ({a.level}): {a.detail}")
```
Com `Alert` adicionado ao bloco `TYPE_CHECKING` de `views.py` e anotação com aspas (`list["Alert"]`), seguindo o padrão do arquivo. Em `src/main.py`: import `from src.alerts import build_alerts` e `from src.ui.views import render_alerts`; em `execute_city_query`, após o bloco `if show_all: ... else: ...` (antes de `if show_historical:`):
```python
alerts = build_alerts(extended)
if alerts:
    render_alerts(alerts)
```
- [ ] Step 4: `pytest tests/test_views.py -q` → PASS; `pytest --cov=src -q` → 160 passed
- [ ] Step 5: Commit: `git add src/ui/views.py src/main.py tests/test_views.py && git commit -m "feat: painel de alertas climaticos no CLI"`

### Task 8: Wire na Web API — `resolve_place` nos endpoints + `alerts` em `/api/forecast`

**Files:**
- Modify: `src/web/app.py` (imports; endpoints `get_weather`, `get_forecast`, `get_historical`, `get_air_quality`, `toggle_favorite`)
- Test: `tests/test_web_api.py`

**Interfaces:**
- Consumes: `resolve_place` (Task 4), `build_alerts` (Task 6) — verbatim
- Produces: endpoints resolvem qualquer cidade; `/api/forecast` retorna campo `alerts: list[dict]`

- [ ] Step 1: Escrever os testes falhos em `tests/test_web_api.py`:
```python
def test_api_weather_fallback_geocoding(client, mock_country_and_weather):
    _, weather, _ = mock_country_and_weather
    from src.api.open_meteo import PlaceHit

    hit = PlaceHit(
        name="São Paulo",
        latitude=-23.5505,
        longitude=-46.6333,
        timezone="America/Sao_Paulo",
        country="Brazil",
        country_code="BR",
    )

    with patch("src.web.app.matcher.match", return_value=None), \
         patch("src.web.app.meteo_client.search_place", return_value=hit), \
         patch("src.web.app.meteo_client.get_current_weather", return_value=weather):

        response = client.get("/api/weather/sao%20paulo")
        assert response.status_code == 200
        data = response.json()
        assert data["capital"] == "São Paulo"
        assert data["match"]["type"] == "geocoding_fallback"


def test_api_forecast_inclui_alertas(client, mock_country_and_weather):
    match_res, _, extended = mock_country_and_weather

    with patch("src.web.app.resolve_place", return_value=match_res), \
         patch("src.web.app.meteo_client.get_extended_forecast", return_value=extended):

        response = client.get("/api/forecast/Brasilia")
        assert response.status_code == 200
        alerts = response.json()["alerts"]
        assert isinstance(alerts, list) and len(alerts) >= 1
        assert "UV" in alerts[0]["title"]
```
(E o fixture `mock_country_and_weather` tem `uv_index_max=8.0` → dispara alerta de UV.)
- [ ] Step 2: `pytest tests/test_web_api.py -q` → FAIL (fallback: 404; alerts: KeyError `"alerts"`)
- [ ] Step 3: Implementar em `src/web/app.py`:
  - Imports: `from src.alerts import build_alerts` e `from src.resolver import resolve_place`
  - Trocar `match_res = matcher.match(query)` por `match_res = resolve_place(query, matcher, meteo_client)` nos 5 endpoints (`get_weather`, `get_forecast`, `get_historical`, `get_air_quality`, `toggle_favorite`)
  - Em `get_forecast`, adicionar ao retorno: `"alerts": [asdict(a) for a in build_alerts(extended)]`
  - Atualizar os testes 404 existentes (`test_api_weather_not_found`, `test_api_historical_not_found`) para também patchear `src.web.app.meteo_client.search_place` com `return_value=None` (evita chamada de rede real quando matcher falha)
- [ ] Step 4: `pytest tests/test_web_api.py -q` → PASS; `pytest --cov=src -q` → 162 passed
- [ ] Step 5: Commit: `git add src/web/app.py tests/test_web_api.py && git commit -m "feat: web api resolve qualquer cidade e expoe alertas no forecast"`

---

## Decisões de escopo (documentadas)

- **Comparador (`src/comparator.py`) continua somente capitais**: usar `resolve_place` lá exigiria reestruturar a resolução de coordenadas dele; fica para depois se o usuário quiser.
- **29/02 no histórico**: comportamento atual (fallback silencioso para "hoje") mantido — caso de borda raro, sem quebra.
- **Payload pesado da API histórica** (10 anos baixados p/ usar ~10 dias): NÃO incluído neste plano (otimização de performance independente).
- **Cobertura de `main.py` (menu interativo)**: não incluída — grande esforço, baixo valor para este ciclo.
