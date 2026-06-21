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


REFRESH_KEYWORDS = {
    "alert", "ancaman", "serangan", "status", "agent", "terbaru",
    "sekarang", "saat ini", "laporan", "deteksi", "insiden",
}


async def _run_chat() -> None:
    llm = LLMAgent()
    wazuh = WazuhClient()

    console.print(Panel(
        "[bold]AI Security Analyst[/bold]\n"
        "Tanya apa saja: analisis alert, konsep keamanan, rekomendasi.\n"
        "'refresh' untuk update data Wazuh | 'exit' untuk keluar.",
        style="blue"
    ))

    # Load konteks Wazuh awal
    wazuh_context = ""
    try:
        console.print("[dim]Memuat data Wazuh...[/dim]")
        stats = await wazuh.get_stats_summary()
        alerts = await wazuh.get_alerts(limit=20, min_level=1)
        wazuh_context = llm.format_wazuh_context(stats, alerts)
        console.print(
            f"[green]Data Wazuh dimuat:[/green] {stats['total_alerts']} alert, "
            f"{stats['active_agents']} agent aktif\n"
        )
    except Exception:
        wazuh_context = ""
        console.print("[yellow]Wazuh tidak tersedia. Mode tanya jawab umum aktif.[/yellow]\n")

    # History percakapan — seed dengan data Wazuh
    history: list[dict] = []
    if wazuh_context:
        history.append({
            "role": "user",
            "content": f"Ini adalah data Wazuh SIEM saya saat ini:\n\n{wazuh_context}\n\nSaya siap menerima pertanyaan."
        })
        history.append({
            "role": "assistant",
            "content": "Saya sudah membaca data Wazuh Anda. Silakan ajukan pertanyaan — bisa tentang alert yang ada, ancaman yang terdeteksi, atau topik keamanan lainnya."
        })

    while True:
        try:
            question = console.input("\n[bold cyan]Kamu>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if question.lower() in ("exit", "quit", "keluar"):
            break
        if not question:
            continue

        # Refresh data Wazuh jika diminta atau pertanyaan relevan
        if question.lower() == "refresh" or any(kw in question.lower() for kw in REFRESH_KEYWORDS):
            try:
                stats = await wazuh.get_stats_summary()
                alerts = await wazuh.get_alerts(limit=20, min_level=1)
                wazuh_context = llm.format_wazuh_context(stats, alerts)
                user_msg = f"[Data Wazuh diperbarui]\n\n{wazuh_context}\n\nPertanyaan: {question}"
            except Exception:
                user_msg = question
            if question.lower() == "refresh":
                console.print("[green]Data Wazuh diperbarui.[/green]")
                continue
        else:
            user_msg = question

        history.append({"role": "user", "content": user_msg})

        # Batasi history agar tidak meledak (max 10 turn = 20 pesan)
        context_messages = history[-20:] if len(history) > 20 else history

        console.print("\n[dim]AI Security Analyst sedang menjawab...[/dim]\n")
        response_parts: list[str] = []
        try:
            async for chunk in llm.ask(context_messages):
                response_parts.append(chunk)
                print(chunk, end="", flush=True)
            print()
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            history.pop()
            continue

        # Simpan jawaban ke history
        history.append({"role": "assistant", "content": "".join(response_parts)})

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
