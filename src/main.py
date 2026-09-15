"""Ponto de entrada principal e Interface de Linha de Comando (CLI) para o Clima Países.

Responsabilidade:
- Analisar argumentos de linha de comando (flags, subcomandos e queries).
- Prover menu interativo navegável via terminal.
- Orquestrar CityMatcher, OpenMeteoClient, HistoricalWeatherClient e StorageManager.
- Formatar saídas ricas via módulo views.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.api.historical import HistoricalWeatherClient
from src.api.open_meteo import OpenMeteoClient
from src.api.rest_countries import RestCountriesClient
from src.comparator import compare_cities
from src.match import CityMatcher
from src.resolver import resolve_place
from src.storage import StorageManager, export_report_csv, export_report_json
from src.ui.views import (
    render_24h_hourly,
    render_5day_forecast,
    render_air_quality,
    render_comparison,
    render_current_weather,
    render_extended_dashboard,
    render_favorites,
    render_historical_analysis,
    render_history,
)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None


def execute_city_query(
    query: str,
    matcher: CityMatcher,
    meteo_client: OpenMeteoClient,
    storage: StorageManager,
    show_forecast: bool = False,
    show_hourly: bool = False,
    show_air_quality: bool = False,
    show_historical: bool = False,
    show_all: bool = False,
    export_format: str | None = None,
    export_output: str | None = None,
) -> bool:
    """Executa a busca para uma cidade e renderiza a saída solicitada."""
    query = query.strip()
    if not query:
        return False

    if HAS_RICH and console:
        console.print(f"\n[dim]🔍 Buscando:[/dim] [bold]{query}[/bold]...")
    else:
        print(f"\nBuscando: {query}...")

    match_res = resolve_place(query, matcher, meteo_client)
    if not match_res:
        msg = f"❌ Nenhuma capital ou país encontrado para '{query}'. Verifique o nome e tente novamente."
        if HAS_RICH and console:
            console.print(f"[bold red]{msg}[/bold red]\n")
        else:
            print(f"{msg}\n")
        return False

    capital = match_res.capital
    country = match_res.country

    # Obtém coordenadas da capital
    coords = meteo_client.get_coordinates(capital, country.cca2)
    if coords:
        lat, lon, resolved_name, tz = coords
    elif country.latlng and len(country.latlng) >= 2:
        lat, lon = float(country.latlng[0]), float(country.latlng[1])
        tz = "auto"
    else:
        lat, lon, tz = 0.0, 0.0, "auto"

    # Se requisitado apenas clima simples
    need_extended = show_forecast or show_hourly or show_air_quality or show_all or export_format is not None

    if need_extended:
        extended = meteo_client.get_extended_forecast(lat, lon, timezone=tz, forecast_days=5, include_air_quality=True)
        if not extended:
            msg = f"⚠️ Não foi possível obter os dados meteorológicos completos para {capital}."
            if HAS_RICH and console:
                console.print(f"[bold yellow]{msg}[/bold yellow]\n")
            else:
                print(f"{msg}\n")
            return False

        # Salva no histórico
        storage.add_history_entry(query, match_res, extended.current)

        # Exibição
        if show_all:
            render_extended_dashboard(match_res, extended)
            if extended.hourly:
                render_24h_hourly(extended.hourly)
        else:
            render_current_weather(match_res, extended.current)
            if show_air_quality and extended.air_quality:
                render_air_quality(extended.air_quality)
            if show_forecast and extended.daily:
                render_5day_forecast(extended.daily)
            if show_hourly and extended.hourly:
                render_24h_hourly(extended.hourly)

        # Se solicitado histórico climático
        if show_historical:
            hist_client = HistoricalWeatherClient()
            hist_analysis = hist_client.get_historical_analysis(
                capital=capital,
                country_name=country.name_pt,
                latitude=lat,
                longitude=lon,
                current_temp=extended.current.temperature,
                timezone=tz,
            )
            if hist_analysis:
                render_historical_analysis(hist_analysis)

        # Exportação se requisitada
        if export_format:
            out_file = export_output or f"{capital.lower().replace(' ', '_')}_clima.{export_format}"
            if export_format == "json":
                out_path = export_report_json(extended, out_file)
            else:
                rows = [
                    {
                        "capital": capital,
                        "country": country.name_pt,
                        "cca2": country.cca2,
                        "temperature": extended.current.temperature,
                        "apparent_temperature": extended.current.apparent_temperature,
                        "condition": extended.current.weather_description,
                        "humidity": extended.current.relative_humidity,
                        "wind_speed": extended.current.wind_speed,
                        "aqi": extended.air_quality.european_aqi if extended.air_quality else None,
                    }
                ]
                out_path = export_report_csv(rows, out_file)

            if HAS_RICH and console:
                console.print(f"[bold green] Relatório exportado com sucesso para:[/] [underline]{out_path}[/]")
            else:
                print(f" Relatório exportado para: {out_path}")

    else:
        weather = meteo_client.get_current_weather(lat, lon, timezone=tz)
        if not weather:
            msg = f"⚠️ Não foi possível obter os dados meteorológicos para {capital} no momento."
            if HAS_RICH and console:
                console.print(f"[bold yellow]{msg}[/bold yellow]\n")
            else:
                print(f"{msg}\n")
            return False

        # Salva no histórico
        storage.add_history_entry(query, match_res, weather)
        render_current_weather(match_res, weather)

        if show_historical:
            hist_client = HistoricalWeatherClient()
            hist_analysis = hist_client.get_historical_analysis(
                capital=capital,
                country_name=country.name_pt,
                latitude=lat,
                longitude=lon,
                current_temp=weather.temperature,
                timezone=tz,
            )
            if hist_analysis:
                render_historical_analysis(hist_analysis)

    return True


def interactive_menu(matcher: CityMatcher, meteo_client: OpenMeteoClient, storage: StorageManager) -> None:
    """Menu interativo rico com múltiplas opções."""
    while True:
        if HAS_RICH and console:
            console.print("\n")
            console.print(
                Panel.fit(
                    "[bold cyan]🌍 DASHBOARD METEOROLÓGICO DE CAPITAIS MUNDIAIS[/bold cyan]\n\n"
                    "[bold green]1.[/] Consultar Clima Atual de uma Capital/País\n"
                    "[bold green]2.[/] Consultar Previsão Completa (Atual + 5 Dias + Qualidade do Ar)\n"
                    "[bold green]3.[/] Previsão Horária (Próximas 24 Horas)\n"
                    "[bold green]4.[/] Análise Histórica e Anomalia Climática (10 Anos) 📊\n"
                    "[bold green]5.[/] Comparar Clima entre Múltiplas Capitais ⚖️\n"
                    "[bold green]6.[/] Minhas Capitais Favoritas ⭐\n"
                    "[bold green]7.[/] Adicionar / Remover Capital dos Favoritos\n"
                    "[bold green]8.[/] Histórico de Consultas Recentes 📜\n"
                    "[bold red]0.[/] Sair",
                    border_style="cyan",
                    title="Menu Principal",
                )
            )
            opt = Prompt.ask("[bold yellow]Escolha uma opção[/bold yellow]", choices=["0", "1", "2", "3", "4", "5", "6", "7", "8"], default="1")
        else:
            print("\n=== DASHBOARD DE CLIMA DE CAPITAIS MUNDIAIS ===")
            print("1. Consultar Clima Atual")
            print("2. Consultar Previsão Completa (5 Dias + Qualidade do Ar)")
            print("3. Previsão Horária (24h)")
            print("4. Análise Histórica e Anomalias Climáticas")
            print("5. Comparar Capitais")
            print("6. Minhas Capitais Favoritas")
            print("7. Adicionar/Remover Favorito")
            print("8. Histórico de Consultas")
            print("0. Sair")
            opt = input("Escolha uma opção [1]: ").strip() or "1"

        if opt == "0":
            if HAS_RICH and console:
                console.print("[cyan]Obrigado por usar o Clima Países. Até logo![/cyan]\n")
            else:
                print("Até logo!")
            break

        elif opt == "1":
            q = input("\nDigite o nome da capital, país ou código ISO: ").strip()
            if q:
                execute_city_query(q, matcher, meteo_client, storage)

        elif opt == "2":
            q = input("\nDigite o nome da capital, país ou código ISO: ").strip()
            if q:
                execute_city_query(q, matcher, meteo_client, storage, show_all=True)

        elif opt == "3":
            q = input("\nDigite o nome da capital, país ou código ISO: ").strip()
            if q:
                execute_city_query(q, matcher, meteo_client, storage, show_hourly=True)

        elif opt == "4":
            q = input("\nDigite o nome da capital, país ou código ISO para análise histórica: ").strip()
            if q:
                execute_city_query(q, matcher, meteo_client, storage, show_historical=True)

        elif opt == "5":
            c_input = input("\nDigite as capitais separadas por espaço (ex: Brasília Tóquio Paris): ").strip()
            if c_input:
                cities = c_input.split()
                if len(cities) < 2:
                    print("Informe ao menos duas capitais para comparar.")
                else:
                    comp_res = compare_cities(cities, matcher, meteo_client)
                    render_comparison(comp_res)

        elif opt == "6":
            favs = storage.get_favorites()
            render_favorites(favs)

        elif opt == "7":
            q = input("\nDigite o nome da capital para alternar favorito: ").strip()
            if q:
                match_res = resolve_place(q, matcher, meteo_client)
                if match_res:
                    added = storage.toggle_favorite(
                        capital=match_res.capital,
                        cca2=match_res.country.cca2,
                        country_name=match_res.country.name_pt,
                        flag=match_res.country.flag_emoji,
                    )
                    status_str = "adicionada aos favoritos ⭐" if added else "removida dos favoritos ❌"
                    print(f"\n{match_res.country.flag_emoji} {match_res.capital} ({match_res.country.name_pt}) foi {status_str}!")
                else:
                    print(f"Capital '{q}' não encontrada.")

        elif opt == "8":
            hist = storage.get_history(limit=15)
            render_history(hist)


def main() -> None:
    """Função principal da CLI."""
    parser = argparse.ArgumentParser(
        prog="clima",
        description="Dashboard e CLI de Clima para Capitais Mundiais com previsões estendidas e comparador.",
    )
    parser.add_argument(
        "query",
        nargs="?",
        default=None,
        help="Nome da capital, país ou código ISO (ex: 'Brasília', 'Tóquio', 'Brasil', 'JP')",
    )
    parser.add_argument(
        "-f", "--forecast",
        action="store_true",
        help="Exibe previsão diária para os próximos 5 dias",
    )
    parser.add_argument(
        "-H", "--hourly",
        action="store_true",
        help="Exibe previsão horária detalhada para as próximas 24 horas",
    )
    parser.add_argument(
        "-a", "--air-quality",
        action="store_true",
        help="Exibe dados detalhados de qualidade do ar (AQI, PM2.5, PM10)",
    )
    parser.add_argument(
        "--historical",
        action="store_true",
        help="Exibe análise histórica comparativa de 10 anos e anomalia climática",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Exibe dashboard meteorológico completo",
    )
    parser.add_argument(
        "-c", "--compare",
        nargs="+",
        help="Compara duas ou mais capitais simultaneamente (ex: --compare Brasília Tóquio Paris)",
    )
    parser.add_argument(
        "--export",
        choices=["json", "csv"],
        default=None,
        help="Exporta os dados obtidos para arquivo JSON ou CSV",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Caminho do arquivo de exportação (ex: relatorio.json)",
    )
    parser.add_argument(
        "--favorites",
        action="store_true",
        help="Lista todas as capitais favoritas salvas",
    )
    parser.add_argument(
        "--add-fav",
        type=str,
        default=None,
        help="Adiciona/remove uma capital dos favoritos",
    )
    parser.add_argument(
        "--history",
        action="store_true",
        help="Exibe o histórico de consultas recentes",
    )

    args = parser.parse_args()

    # Inicialização dos clientes e serviços
    countries_client = RestCountriesClient()
    countries = countries_client.load_countries()
    matcher = CityMatcher(countries)
    meteo_client = OpenMeteoClient()
    storage = StorageManager()

    # Processamento de flags específicas
    if args.favorites:
        render_favorites(storage.get_favorites())
        return

    if args.history:
        render_history(storage.get_history())
        return

    if args.add_fav:
        match_res = resolve_place(args.add_fav, matcher, meteo_client)
        if match_res:
            added = storage.toggle_favorite(
                match_res.capital,
                match_res.country.cca2,
                match_res.country.name_pt,
                match_res.country.flag_emoji,
            )
            status_str = "adicionada aos favoritos ⭐" if added else "removida dos favoritos ❌"
            print(f"{match_res.capital} foi {status_str}!")
        else:
            print(f"Capital '{args.add_fav}' não encontrada.")
        return

    if args.compare:
        comparison_res = compare_cities(args.compare, matcher, meteo_client)
        render_comparison(comparison_res)
        if args.export:
            out_file = args.output or f"comparacao_clima.{args.export}"
            if args.export == "json":
                out_path = export_report_json(comparison_res.to_summary_dict(), out_file)
            else:
                rows = [
                    {
                        "capital": item.capital,
                        "country": item.country_name,
                        "cca2": item.cca2,
                        "temperature": item.temperature,
                        "apparent_temperature": item.apparent_temperature,
                        "condition": item.condition,
                        "humidity": item.humidity,
                        "wind_speed": item.wind_speed,
                        "precipitation": item.precipitation,
                    }
                    for item in comparison_res.items
                ]
                out_path = export_report_csv(rows, out_file)
            print(f"Comparação exportada para: {out_path}")
        return

    # Consulta direta por query
    if args.query:
        execute_city_query(
            query=args.query,
            matcher=matcher,
            meteo_client=meteo_client,
            storage=storage,
            show_forecast=args.forecast,
            show_hourly=args.hourly,
            show_air_quality=args.air_quality,
            show_historical=args.historical,
            show_all=args.all,
            export_format=args.export,
            export_output=args.output,
        )
    else:
        interactive_menu(matcher, meteo_client, storage)


if __name__ == "__main__":
    main()
