"""Testes para persistência de histórico, favoritos e exportação."""

import json
from pathlib import Path
import pytest
from src.api.open_meteo import WeatherData
from src.api.rest_countries import Country
from src.match import MatchResult
from src.storage import StorageManager, export_report_csv, export_report_json


@pytest.fixture
def temp_storage(tmp_path):
    storage_file = tmp_path / "test_history.json"
    return StorageManager(file_path=storage_file)


@pytest.fixture
def sample_match_and_weather():
    country = Country(
        name_common="Japan",
        name_official="Japan",
        name_pt="Japão",
        capitals=["Tokyo"],
        cca2="JP",
        cca3="JPN",
        region="Asia",
        subregion="Eastern Asia",
        flag_emoji="🇯🇵",
    )
    match_res = MatchResult(
        capital="Tokyo",
        country=country,
        matched_term="toquio",
        match_type="capital_alias",
        confidence=1.0,
    )
    weather = WeatherData(
        temperature=22.0,
        apparent_temperature=21.5,
        relative_humidity=60,
        wind_speed=5.0,
        precipitation=0.0,
        weather_code=0,
        weather_description="Céu limpo",
        weather_emoji="☀️",
        is_day=True,
        time="2026-08-27T16:00",
        latitude=35.68,
        longitude=139.69,
        elevation=40.0,
        timezone="Asia/Tokyo",
    )
    return match_res, weather


def test_history_recording(temp_storage, sample_match_and_weather):
    match_res, weather = sample_match_and_weather
    temp_storage.add_history_entry("Tóquio", match_res, weather)

    history = temp_storage.get_history()
    assert len(history) == 1
    assert history[0]["capital"] == "Tokyo"
    assert history[0]["cca2"] == "JP"
    assert history[0]["temperature"] == 22.0

    temp_storage.clear_history()
    assert len(temp_storage.get_history()) == 0


def test_favorites_toggle(temp_storage):
    # Adicionar aos favoritos
    added = temp_storage.toggle_favorite("Tokyo", "JP", "Japão", "🇯🇵")
    assert added is True
    assert temp_storage.is_favorite("Tokyo", "JP") is True
    assert len(temp_storage.get_favorites()) == 1

    # Remover dos favoritos
    removed = temp_storage.toggle_favorite("Tokyo", "JP", "Japão", "🇯🇵")
    assert removed is False
    assert temp_storage.is_favorite("Tokyo", "JP") is False
    assert len(temp_storage.get_favorites()) == 0


def test_export_json(tmp_path):
    out_file = tmp_path / "report.json"
    data = {"city": "Tokyo", "temp": 22.0}
    result_path = export_report_json(data, out_file)
    assert result_path.exists()
    with open(result_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["city"] == "Tokyo"


def test_export_csv(tmp_path):
    out_file = tmp_path / "report.csv"
    rows = [
        {"city": "Tokyo", "temp": 22.0},
        {"city": "Paris", "temp": 25.0},
    ]
    result_path = export_report_csv(rows, out_file)
    assert result_path.exists()
    content = result_path.read_text(encoding="utf-8")
    assert "city,temp" in content
    assert "Tokyo,22.0" in content
    assert "Paris,25.0" in content


def test_storage_custom_env_var(tmp_path, monkeypatch):
    custom_file = tmp_path / "custom_env_storage.json"
    monkeypatch.setenv("CLIMA_STORAGE_PATH", str(custom_file))

    storage = StorageManager()
    assert storage.file_path == custom_file
    assert custom_file.exists()


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
