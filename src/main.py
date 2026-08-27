"""Ponto de entrada do dashboard/CLI de clima para capitais do mundo.

Responsabilidade:
- Orquestrar o fluxo principal: receber entrada do usuário (argumentos ou interativo),
  resolver o matching da capital/país com normalização/fallback difuso,
  consultar REST Countries e Open-Meteo, e exibir as informações de clima
  de forma visual, clara e amigável.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Garante que a raiz do projeto esteja no sys.path para execução direta ou como módulo
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from src.api.open_meteo import OpenMeteoClient, WeatherData
from src.api.rest_countries import Country, RestCountriesClient
from src.match import CityMatcher, MatchResult


console = Console() if HAS_RICH else None


def format_weather_display(match_res: MatchResult, weather: WeatherData) -> None:
    """Renderiza os dados do clima e país de forma rica no terminal."""
    country = match_res.country
    capital = match_res.capital

    if HAS_RICH and console:
        # Cabeçalho do País e Capital
        title_text = f"{country.flag_emoji} {capital} — {country.name_pt} ({country.cca2})"
        if country.name_pt != country.name_common:
            title_text += f" / {country.name_common}"

        # Tabela de Clima
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Chave", style="cyan bold")
        table.add_column("Valor", style="white")

        temp_style = "bold yellow"
        if weather.temperature <= 10:
            temp_style = "bold cyan"
        elif weather.temperature >= 30:
            temp_style = "bold red"

        table.add_row("Condição:", f"{weather.weather_emoji}  {weather.weather_description}")
        table.add_row("Temperatura:", f"[{temp_style}]{weather.temperature:.1f} °C[/]")
        table.add_row("Sensação Térmica:", f"{weather.apparent_temperature:.1f} °C")
        table.add_row("Umidade do Ar:", f"{weather.relative_humidity}%")
        table.add_row("Vento:", f"{weather.wind_speed:.1f} km/h")
        table.add_row("Precipitação:", f"{weather.precipitation:.1f} mm")
        table.add_row("Coordenadas:", f"Lat {weather.latitude:.4f}, Lon {weather.longitude:.4f}")
        table.add_row("Fuso Horário:", f"{weather.timezone} ({weather.time})")
        table.add_row("Região:", f"{country.region} ({country.subregion})")

        panel = Panel(
            table,
            title=f"[bold green]🌤️  Dashboard de Clima — {title_text}[/]",
            subtitle=f"[dim]Match: {match_res.match_type} (confiança: {int(match_res.confidence * 100)}%)[/dim]",
            expand=False,
            border_style="blue",
        )
        console.print(panel)
    else:
        # Fallback para texto plano se rich não estiver disponível
        print(f"\n==================================================")
        print(f" {country.flag_emoji} {capital} — {country.name_pt} ({country.cca2})")
        print(f"==================================================")
        print(f" Condição:         {weather.weather_emoji} {weather.weather_description}")
        print(f" Temperatura:      {weather.temperature:.1f} °C (Sensação: {weather.apparent_temperature:.1f} °C)")
        print(f" Umidade:          {weather.relative_humidity}%")
        print(f" Vento:            {weather.wind_speed:.1f} km/h")
        print(f" Precipitação:     {weather.precipitation:.1f} mm")
        print(f" Coordenadas:      Lat {weather.latitude:.4f}, Lon {weather.longitude:.4f}")
        print(f" Fuso Horário:     {weather.timezone} ({weather.time})")
        print(f" Região:           {country.region} ({country.subregion})")
        print(f" Confiança Match:  {int(match_res.confidence * 100)}% ({match_res.match_type})")
        print(f"==================================================\n")


def search_and_display(query: str, matcher: CityMatcher, meteo_client: OpenMeteoClient) -> bool:
    """Realiza a busca de uma cidade/país e exibe o clima."""
    query = query.strip()
    if not query:
        return False

    if HAS_RICH and console:
        console.print(f"\n[dim]🔍 Buscando:[/dim] [bold]{query}[/bold]...")
    else:
        print(f"\nBuscando: {query}...")

    match_res = matcher.match(query)
    if not match_res:
        msg = f"❌ Nenhuma capital ou país encontrado para '{query}'. Verifique o nome e tente novamente."
        if HAS_RICH and console:
            console.print(f"[bold red]{msg}[/bold red]\n")
        else:
            print(f"{msg}\n")
        return False

    capital = match_res.capital
    country = match_res.country

    # Obtém coordenadas da capital via Geocoding ou fallback para latlng do país
    coords = meteo_client.get_coordinates(capital, country.cca2)
    if coords:
        lat, lon, resolved_name, tz = coords
    elif country.latlng and len(country.latlng) >= 2:
        lat, lon = float(country.latlng[0]), float(country.latlng[1])
        tz = "auto"
    else:
        lat, lon, tz = 0.0, 0.0, "auto"

    weather = meteo_client.get_current_weather(lat, lon, timezone=tz)
    if not weather:
        msg = f"⚠️ Não foi possível obter os dados meteorológicos para {capital} no momento (erro de conexão ou API indisponível)."
        if HAS_RICH and console:
            console.print(f"[bold yellow]{msg}[/bold yellow]\n")
        else:
            print(f"{msg}\n")
        return False

    format_weather_display(match_res, weather)
    return True


def interactive_loop(matcher: CityMatcher, meteo_client: OpenMeteoClient) -> None:
    """Modo interativo de consulta."""
    if HAS_RICH and console:
        console.print(
            Panel.fit(
                "[bold cyan]🌍 Bem-vindo ao Dashboard de Clima de Capitais Mundiais![/bold cyan]\n"
                "[dim]Digite o nome de uma capital, país ou código ISO (ex: Brasília, Tóquio, Paris, Alemanha, US).\n"
                "Digite 'sair', 'exit' ou Ctrl+C para encerrar.[/dim]",
                border_style="green",
            )
        )
    else:
        print("=== Dashboard de Clima de Capitais Mundiais ===")
        print("Digite o nome de uma capital, país ou código ISO. Digite 'sair' para encerrar.\n")

    while True:
        try:
            if HAS_RICH and console:
                query = console.input("[bold green]Digite uma capital/país > [/bold green]")
            else:
                query = input("Digite uma capital/país > ")

            query = query.strip()
            if query.lower() in ("sair", "exit", "quit", "q"):
                if HAS_RICH and console:
                    console.print("[cyan]Até logo![/cyan]")
                else:
                    print("Até logo!")
                break

            if not query:
                continue

            search_and_display(query, matcher, meteo_client)
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando...")
            break


def main() -> None:
    """Função principal de inicialização da CLI."""
    parser = argparse.ArgumentParser(
        description="Consulta o clima atual de qualquer capital do mundo cruzando Open-Meteo e REST Countries."
    )
    parser.add_argument(
        "query",
        nargs="?",
        default=None,
        help="Nome da capital, país ou código ISO (ex: 'Brasília', 'Tóquio', 'Brasil', 'JP')",
    )
    args = parser.parse_args()

    # Inicialização dos clientes
    countries_client = RestCountriesClient()
    countries = countries_client.load_countries()
    matcher = CityMatcher(countries)
    meteo_client = OpenMeteoClient()

    if args.query:
        search_and_display(args.query, matcher, meteo_client)
    else:
        interactive_loop(matcher, meteo_client)


if __name__ == "__main__":
    main()
