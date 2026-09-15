"""Componentes de visualização e renderização no terminal via Rich.

Responsabilidade:
- Renderizar cards, painéis, tabelas e previsões meteorológicas estendidas.
- Formatação de qualidade do ar, matrizes de comparação e histórico/favoritos.
- Suporte a fallback gracioso caso Rich não esteja disponível.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.columns import Columns
    from rich.progress import BarColumn, Progress
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

if TYPE_CHECKING:
    from src.alerts import Alert
    from src.api.open_meteo import (
        AirQualityData,
        DailyForecast,
        ExtendedWeatherData,
        HourlyForecast,
        WeatherData,
    )
    from src.comparator import ComparisonResult
    from src.match import MatchResult

console = Console() if HAS_RICH else None


def _get_temp_color(temp: float) -> str:
    """Retorna cor representativa para uma dada temperatura."""
    if temp <= 0:
        return "bold blue"
    elif temp <= 15:
        return "bold cyan"
    elif temp <= 25:
        return "bold green"
    elif temp <= 32:
        return "bold yellow"
    else:
        return "bold red"


def render_current_weather(match_res: MatchResult, weather: WeatherData) -> None:
    """Exibe o card de clima atual no terminal."""
    country = match_res.country
    capital = match_res.capital

    if HAS_RICH and console:
        title_text = f"{country.flag_emoji} {capital} — {country.name_pt} ({country.cca2})"
        if country.name_pt != country.name_common:
            title_text += f" / {country.name_common}"

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Chave", style="cyan bold")
        table.add_column("Valor", style="white")

        t_color = _get_temp_color(weather.temperature)
        table.add_row("Condição:", f"{weather.weather_emoji}  {weather.weather_description}")
        table.add_row("Temperatura:", f"[{t_color}]{weather.temperature:.1f} °C[/]")
        table.add_row("Sensação Térmica:", f"{weather.apparent_temperature:.1f} °C")
        table.add_row("Umidade do Ar:", f"{weather.relative_humidity}%")
        table.add_row("Vento:", f"{weather.wind_speed:.1f} km/h")
        table.add_row("Precipitação:", f"{weather.precipitation:.1f} mm")
        table.add_row("Coordenadas:", f"Lat {weather.latitude:.4f}, Lon {weather.longitude:.4f}")
        table.add_row("Fuso Horário:", f"{weather.timezone} ({weather.time})")
        table.add_row("Região:", f"{country.region} ({country.subregion})")

        panel = Panel(
            table,
            title=f"[bold green]🌤️  Clima Atual — {title_text}[/]",
            subtitle=f"[dim]Match: {match_res.match_type} (confiança: {int(match_res.confidence * 100)}%)[/dim]",
            expand=False,
            border_style="blue",
        )
        console.print(panel)
    else:
        print(f"\n=== Clima Atual: {country.flag_emoji} {capital} — {country.name_pt} ===")
        print(f"Condição:         {weather.weather_emoji} {weather.weather_description}")
        print(f"Temperatura:      {weather.temperature:.1f} °C (Sensação: {weather.apparent_temperature:.1f} °C)")
        print(f"Umidade:          {weather.relative_humidity}% | Vento: {weather.wind_speed:.1f} km/h")
        print(f"Fuso Horário:     {weather.timezone} ({weather.time})")


def render_5day_forecast(daily: list[DailyForecast]) -> None:
    """Exibe tabela da previsão diária para os próximos dias."""
    if not daily:
        return

    if HAS_RICH and console:
        table = Table(title="📅 Previsão Estendida para os Próximos Dias", border_style="cyan", header_style="bold magenta")
        table.add_column("Data", style="cyan")
        table.add_column("Condição", style="white")
        table.add_column("Mín / Máx", style="yellow")
        table.add_column("Chuva", style="blue")
        table.add_column("Índice UV", style="green")
        table.add_column("Nascer / Pôr do Sol", style="dim")

        for d in daily:
            min_col = _get_temp_color(d.temp_min)
            max_col = _get_temp_color(d.temp_max)
            temp_str = f"[{min_col}]{d.temp_min:.1f}°C[/] / [{max_col}]{d.temp_max:.1f}°C[/]"
            rain_str = f"{d.precipitation_probability_max}% ({d.precipitation_sum:.1f}mm)"
            sun_str = f"{d.sunrise.split('T')[-1]} / {d.sunset.split('T')[-1]}" if d.sunrise else "-"

            table.add_row(
                d.date,
                f"{d.weather_emoji} {d.weather_description}",
                temp_str,
                rain_str,
                f"{d.uv_index_max:.1f}",
                sun_str,
            )
        console.print(table)
    else:
        print("\n--- Previsão Diária ---")
        for d in daily:
            print(f"{d.date}: {d.weather_emoji} {d.weather_description} | {d.temp_min:.1f}°C - {d.temp_max:.1f}°C | Chuva: {d.precipitation_probability_max}%")


def render_24h_hourly(hourly: list[HourlyForecast]) -> None:
    """Exibe evolução horária das próximas 24 horas."""
    if not hourly:
        return

    if HAS_RICH and console:
        table = Table(title="⏰ Previsão Horária (Próximas 24h)", border_style="blue", header_style="bold blue")
        table.add_column("Hora", style="cyan")
        table.add_column("Condição", style="white")
        table.add_column("Temperatura", style="yellow")
        table.add_column("Prob. Chuva", style="blue")

        # Exibe de 3 em 3 horas para visualização limpa
        for h in hourly[::2]:
            hour_clean = h.time.split("T")[-1] if "T" in h.time else h.time
            t_col = _get_temp_color(h.temperature)
            table.add_row(
                hour_clean,
                f"{h.weather_emoji} {h.weather_description}",
                f"[{t_col}]{h.temperature:.1f} °C[/]",
                f"{h.precipitation_probability}%",
            )
        console.print(table)
    else:
        print("\n--- Previsão Horária ---")
        for h in hourly[::2]:
            print(f"{h.time}: {h.weather_emoji} {h.temperature:.1f}°C ({h.precipitation_probability}% chuva)")


def render_air_quality(air: AirQualityData) -> None:
    """Exibe painel com os dados de qualidade do ar."""
    if not air:
        return

    if HAS_RICH and console:
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Poluente", style="cyan bold")
        table.add_column("Valor", style="white")

        table.add_row("Índice AQI (Europeu):", f"{air.aqi_emoji} [bold]{air.european_aqi}[/bold] — {air.aqi_level}")
        table.add_row("Partículas PM2.5:", f"{air.pm2_5:.1f} µg/m³")
        table.add_row("Partículas PM10:", f"{air.pm10:.1f} µg/m³")
        table.add_row("Dióxido de Nitrogênio (NO₂):", f"{air.nitrogen_dioxide:.1f} µg/m³")
        table.add_row("Ozônio (O₃):", f"{air.ozone:.1f} µg/m³")

        panel = Panel(
            table,
            title="🍃 [bold green]Qualidade do Ar[/bold green]",
            border_style="green",
            expand=False,
        )
        console.print(panel)
    else:
        print(f"\n--- Qualidade do Ar: AQI {air.european_aqi} ({air.aqi_level}) ---")
        print(f"PM2.5: {air.pm2_5:.1f} µg/m³ | PM10: {air.pm10:.1f} µg/m³ | NO2: {air.nitrogen_dioxide:.1f} µg/m³")


def render_extended_dashboard(match_res: MatchResult, extended: ExtendedWeatherData) -> None:
    """Exibe o dashboard completo com clima atual, previsão 5d e qualidade do ar."""
    render_current_weather(match_res, extended.current)
    if extended.air_quality:
        render_air_quality(extended.air_quality)
    if extended.daily:
        render_5day_forecast(extended.daily)


def render_comparison_matrix(comp: ComparisonResult) -> None:
    """Exibe matriz comparativa entre múltiplas cidades."""
    if not comp.items:
        if HAS_RICH and console:
            console.print("[yellow]Nenhuma cidade válida para comparar.[/yellow]")
        else:
            print("Nenhuma cidade válida para comparar.")
        return

    if HAS_RICH and console:
        table = Table(
            title=f"⚖️  Comparação de Clima entre Capitais (Delta Térmico: {comp.temp_delta} °C)",
            border_style="green",
            header_style="bold green",
        )
        table.add_column("Capital / País", style="white bold")
        table.add_column("Condição", style="white")
        table.add_column("Temperatura", style="yellow")
        table.add_column("Sensação", style="yellow")
        table.add_column("Umidade", style="cyan")
        table.add_column("Vento", style="blue")
        table.add_column("Chuva", style="blue")

        for item in comp.items:
            m = item.match_result
            w = item.weather
            t_col = _get_temp_color(w.temperature)
            city_str = f"{m.country.flag_emoji} {m.capital} ({m.country.cca2})"
            
            # Destaques
            highlights = []
            if comp.warmest and comp.warmest.match_result.capital == m.capital:
                highlights.append("🔥 Mais Quente")
            if comp.coldest and comp.coldest.match_result.capital == m.capital and len(comp.items) > 1:
                highlights.append("❄️ Mais Fria")
            
            if highlights:
                city_str += f" [dim]({', '.join(highlights)})[/dim]"

            table.add_row(
                city_str,
                f"{w.weather_emoji} {w.weather_description}",
                f"[{t_col}]{w.temperature:.1f} °C[/]",
                f"{w.apparent_temperature:.1f} °C",
                f"{w.relative_humidity}%",
                f"{w.wind_speed:.1f} km/h",
                f"{w.precipitation:.1f} mm",
            )
        console.print(table)
    else:
        print(f"\n=== Comparação entre Cidades (Delta Térmico: {comp.temp_delta}°C) ===")
        for item in comp.items:
            m = item.match_result
            w = item.weather
            print(f"{m.country.flag_emoji} {m.capital} ({m.country.cca2}): {w.temperature:.1f}°C | {w.weather_emoji} {w.weather_description} | Umidade: {w.relative_humidity}%")


def render_favorites(favorites: list[dict]) -> None:
    """Exibe a lista de capitais favoritas salvas."""
    if not favorites:
        msg = "⭐ Nenhuma capital salva nos favoritos ainda. Use a opção para adicionar!"
        if HAS_RICH and console:
            console.print(f"[yellow]{msg}[/yellow]")
        else:
            print(msg)
        return

    if HAS_RICH and console:
        table = Table(title="⭐ Capitais Favoritas", border_style="yellow", header_style="bold yellow")
        table.add_column("#", style="dim")
        table.add_column("Capital", style="bold white")
        table.add_column("País", style="white")
        table.add_column("Código ISO", style="cyan")
        table.add_column("Adicionado em", style="dim")

        for idx, fav in enumerate(favorites, 1):
            table.add_row(
                str(idx),
                f"{fav.get('flag', '')} {fav.get('capital')}",
                fav.get("country_name", ""),
                fav.get("cca2", ""),
                fav.get("added_at", ""),
            )
        console.print(table)
    else:
        print("\n--- Capitais Favoritas ---")
        for idx, fav in enumerate(favorites, 1):
            print(f"{idx}. {fav.get('flag', '')} {fav.get('capital')} - {fav.get('country_name')} ({fav.get('cca2')})")


def render_history(history: list[dict]) -> None:
    """Exibe o histórico de buscas recentes."""
    if not history:
        msg = "📜 Histórico de buscas está vazio."
        if HAS_RICH and console:
            console.print(f"[dim]{msg}[/dim]")
        else:
            print(msg)
        return

    if HAS_RICH and console:
        table = Table(title="📜 Consultas Recentes", border_style="cyan", header_style="bold cyan")
        table.add_column("Data/Hora", style="dim")
        table.add_column("Termo Buscado", style="white")
        table.add_column("Capital Resolvida", style="bold green")
        table.add_column("País", style="white")
        table.add_column("Temperatura", style="yellow")
        table.add_column("Condição", style="white")

        for h in history:
            table.add_row(
                h.get("timestamp", ""),
                h.get("query", ""),
                f"{h.get('flag', '')} {h.get('capital')}",
                h.get("country_name", ""),
                f"{h.get('temperature', 0):.1f} °C",
                f"{h.get('emoji', '')} {h.get('condition', '')}",
            )
        console.print(table)
    else:
        print("\n--- Histórico de Consultas ---")
        for h in history:
            print(f"{h.get('timestamp')}: {h.get('capital')} ({h.get('country_name')}) - {h.get('temperature')}°C {h.get('condition')}")


def render_historical_analysis(analysis: Any) -> None:
    """Exibe o card de análise histórica e anomalia climática."""
    if HAS_RICH and console:
        table = Table.grid(padding=(0, 2))
        table.add_column("Chave", style="bold cyan")
        table.add_column("Valor", style="white")

        anomaly_color = (
            "red" if analysis.temp_anomaly >= 3.0
            else "yellow" if analysis.temp_anomaly >= 1.0
            else "green" if analysis.temp_anomaly > -1.0
            else "cyan" if analysis.temp_anomaly > -3.0
            else "blue"
        )

        table.add_row("Data de Referência:", f"{analysis.target_date}")
        table.add_row("Período Analisado:", f"Últimos {analysis.years_analyzed} anos (mesmo dia/mês)")
        table.add_row("Temperatura Atual:", f"{analysis.current_temp:.1f} °C")
        table.add_row("Média Histórica:", f"{analysis.historical_mean_temp:.1f} °C")
        table.add_row("Recorde Histórico (Máx):", f"{analysis.historical_max_temp:.1f} °C")
        table.add_row("Recorde Histórico (Mín):", f"{analysis.historical_min_temp:.1f} °C")
        table.add_row(
            "Anomalia Térmica:",
            f"[{anomaly_color}]{analysis.anomaly_emoji} {analysis.temp_anomaly:+.1f} °C — {analysis.anomaly_status}[/{anomaly_color}]",
        )
        table.add_row("Precipitação Média Histórica:", f"{analysis.historical_avg_precip:.1f} mm")

        panel = Panel(
            table,
            title=f"📊 Análise Histórica & Anomalia Climática — {analysis.capital} ({analysis.country_name})",
            border_style=anomaly_color,
            expand=False,
        )
        console.print(panel)
    else:
        print(f"\n--- Análise Histórica: {analysis.capital} ({analysis.country_name}) ---")
        print(f"Data: {analysis.target_date} (base: {analysis.years_analyzed} anos)")
        print(f"Temperatura Atual: {analysis.current_temp:.1f} °C | Média Histórica: {analysis.historical_mean_temp:.1f} °C")
        print(f"Anomalia: {analysis.anomaly_emoji} {analysis.temp_anomaly:+.1f} °C ({analysis.anomaly_status})")
        print(f"Extremos: Mín {analysis.historical_min_temp:.1f} °C / Máx {analysis.historical_max_temp:.1f} °C")
        print(f"Chuva Média Histórica: {analysis.historical_avg_precip:.1f} mm\n")

# Alias de compatibilidade
render_comparison = render_comparison_matrix


def render_alerts(alerts: "list[Alert]") -> None:
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
            Panel(
                table,
                title="⚠️ [bold yellow]Alertas Climáticos[/bold yellow]",
                border_style="yellow",
                expand=False,
            )
        )
    else:
        print("\n--- Alertas Climáticos ---")
        for a in alerts:
            print(f"{a.emoji} {a.title} ({a.level}): {a.detail}")
