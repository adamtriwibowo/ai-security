import asyncio
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.markdown import Markdown
from rich import print as rprint

from src.wazuh_client import WazuhClient
from src.llm_agent import LLMAgent
from src.config import settings

app = typer.Typer(help="AI Security Agent - Wazuh + Ollama")
console = Console()


async def _run_analysis(min_level: int, limit: int) -> None:
    wazuh = WazuhClient()
    llm = LLMAgent()

    try:
        # Cek Ollama
        console.print("[yellow]Mengecek koneksi Ollama...[/yellow]")
        if not await llm.check_ollama():
            console.print(
                f"[red]Model '{settings.ollama_model}' tidak ditemukan di Ollama.[/red]\n"
                f"Jalankan: [bold]ollama pull {settings.ollama_model}[/bold]"
            )
            return

        # Ambil data Wazuh
        console.print("[yellow]Mengambil alert dari Wazuh...[/yellow]")
        try:
            stats = await wazuh.get_stats_summary()
            alerts = await wazuh.get_alerts(limit=limit, min_level=min_level)
        except Exception as e:
            console.print(f"[red]Gagal terhubung ke Wazuh: {e}[/red]")
            console.print("[dim]Pastikan Wazuh Docker sudah berjalan.[/dim]")
            return

        # Tampilkan stats
        table = Table(title="Status Wazuh", show_header=True)
        table.add_column("Metrik", style="cyan")
        table.add_column("Nilai", style="green")
        table.add_row("Total Alert", str(stats["total_alerts"]))
        table.add_row("Agent Aktif", str(stats["active_agents"]))
        table.add_row("Agent Disconnect", str(stats["disconnected_agents"]))
        table.add_row("Alert Dianalisis", str(len(alerts)))
        console.print(table)

        if not alerts:
            console.print(Panel(
                f"[green]Tidak ada alert dengan level >= {min_level}.[/green]",
                title="Hasil"
            ))
            return

        # Analisis LLM
        console.print(f"\n[bold blue]Menganalisis {len(alerts)} alert dengan {settings.ollama_model}...[/bold blue]\n")

        result = []
        with Live(console=console, refresh_per_second=10) as live:
            async for chunk in llm.analyze_alerts(alerts, context=stats):
                result.append(chunk)
                live.update(Markdown("".join(result)))

    finally:
        await wazuh.close()
        await llm.close()


async def _run_chat() -> None:
    llm = LLMAgent()
    wazuh = WazuhClient()

    console.print(Panel(
        "[bold]AI Security Analyst[/bold]\nKetik pertanyaan keamanan. 'exit' untuk keluar.",
        style="blue"
    ))

    try:
        stats = await wazuh.get_stats_summary()
        recent_alerts = await wazuh.get_alerts(limit=10, min_level=7)
        context = f"Stats Wazuh: {stats}\nAlert terbaru (level 7+): {len(recent_alerts)} alert"
    except Exception:
        context = "Wazuh tidak tersedia. Jawab pertanyaan umum keamanan."

    history_context = context

    while True:
        try:
            question = console.input("\n[bold cyan]Kamu>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if question.lower() in ("exit", "quit", "keluar"):
            break
        if not question:
            continue

        console.print("\n[dim]AI Security Analyst sedang menganalisis...[/dim]\n")
        result = []
        try:
            async for chunk in llm.ask(question, context=history_context):
                result.append(chunk)
                print(chunk, end="", flush=True)
            print()
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    await llm.close()
    await wazuh.close()


@app.command()
def analyze(
    min_level: int = typer.Option(7, "--level", "-l", help="Minimum alert level (1-15)"),
    limit: int = typer.Option(50, "--limit", "-n", help="Jumlah alert yang dianalisis"),
):
    """Analisis alert keamanan terbaru dari Wazuh menggunakan AI."""
    asyncio.run(_run_analysis(min_level=min_level, limit=limit))


@app.command()
def chat():
    """Mode chat interaktif dengan AI Security Analyst."""
    asyncio.run(_run_chat())


@app.command()
def status():
    """Cek status koneksi Wazuh dan Ollama."""

    async def _check():
        console.print("[yellow]Mengecek koneksi...[/yellow]")

        # Cek Ollama
        llm = LLMAgent()
        ollama_ok = await llm.check_ollama()
        await llm.close()

        # Cek Wazuh
        wazuh = WazuhClient()
        try:
            info = await wazuh.get_manager_info()
            wazuh_ok = True
            wazuh_version = info.get("version", "unknown")
        except Exception:
            wazuh_ok = False
            wazuh_version = "N/A"
        await wazuh.close()

        table = Table(title="Status Koneksi")
        table.add_column("Service", style="cyan")
        table.add_column("Status")
        table.add_column("Info")

        table.add_row(
            "Ollama",
            "[green]OK[/green]" if ollama_ok else "[red]GAGAL[/red]",
            settings.ollama_model if ollama_ok else "Model tidak ditemukan"
        )
        table.add_row(
            "Wazuh Manager",
            "[green]OK[/green]" if wazuh_ok else "[red]GAGAL[/red]",
            f"v{wazuh_version}" if wazuh_ok else "Tidak dapat terhubung"
        )
        console.print(table)

    asyncio.run(_check())


if __name__ == "__main__":
    app()
