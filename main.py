import sys
from app.utils.logger import setup_logger
from app.core.interaction_loop import InteractionLoop

from rich.console import Console
from rich.panel import Panel
from rich import box
from rich.prompt import Prompt

console = Console()


def _print_main_header() -> None:
    console.print(Panel(
        "[bold cyan]Tenri AI Companion[/bold cyan]\n"
        "[dim]Sistem AI berbasis suara untuk presentasi[/dim]",
        box=box.DOUBLE_EDGE,
        expand=False,
    ))


def _run_tenri() -> None:
    setup_logger()
    jarvis_ui = None
    try:
        from app.ui.jarvis_display import JarvisDisplay
        jarvis_ui = JarvisDisplay()
        jarvis_ui.start()

        loop = InteractionLoop(jarvis_ui=jarvis_ui)
        loop.run()
    except KeyboardInterrupt:
        console.print("\n[dim]Aplikasi dihentikan oleh pengguna.[/dim]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Kritikal:[/red] Gagal menjalankan aplikasi: {e}")
        sys.exit(1)
    finally:
        if jarvis_ui:
            jarvis_ui.stop()


def _run_knowledge_manager() -> None:
    from scripts.manage_knowledge import run_interactive
    run_interactive()


def _run_rehearsal() -> None:
    console.print("\n[bold]Menjalankan rehearsal simulasi...[/bold]")
    console.print("[dim]Tenri akan mensimulasikan semua slide dan mencatat hasilnya.[/dim]\n")
    try:
        from scripts.run_rehearsal import run_rehearsal
        rehearsal_path, priority_path = run_rehearsal()
        console.print(f"\n[green]Rehearsal selesai.[/green]")
        console.print(f"  Catatan  : [cyan]{rehearsal_path}[/cyan]")
        console.print(f"  Prioritas: [cyan]{priority_path}[/cyan]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


def _import_document() -> None:
    from pathlib import Path
    from rich.prompt import Confirm
    from rich.table import Table
    from rich import box as rbox

    SUPPORTED = {".pptx", ".docx", ".pdf"}
    INBOX_DIR = Path(__file__).resolve().parent / "app" / "knowledge" / "inbox"
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    # Cari semua file yang didukung di folder inbox
    files = sorted(
        f for f in INBOX_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED
    )

    console.print()
    if not files:
        console.print(Panel(
            f"[yellow]Belum ada file di folder inbox.[/yellow]\n\n"
            f"Salin file materi ke folder berikut, lalu jalankan Import Materi lagi:\n\n"
            f"[bold cyan]{INBOX_DIR}[/bold cyan]\n\n"
            f"[dim]Format yang didukung: .pptx  .docx  .pdf[/dim]",
            title="[bold]Import Materi[/bold]",
            border_style="yellow",
            box=rbox.ASCII,
            safe_box=True,
        ))
        return

    # Tampilkan file yang tersedia
    table = Table(box=rbox.SIMPLE_HEAD, show_lines=False,
                  title="[bold]File di Folder Inbox[/bold]")
    table.add_column("No.", justify="center", style="cyan", width=4)
    table.add_column("Nama File")
    table.add_column("Format", justify="center", width=8)
    table.add_column("Ukuran", justify="right", style="dim", width=10)
    for i, f in enumerate(files, 1):
        size_kb = f.stat().st_size // 1024
        size_str = f"{size_kb} KB" if size_kb < 1024 else f"{size_kb // 1024} MB"
        table.add_row(str(i), f.name, f.suffix.upper()[1:], size_str)
    console.print(table)

    # Pilih file
    while True:
        raw = Prompt.ask(
            f"[bold]Pilih nomor file[/bold] [dim](1–{len(files)})[/dim]"
        )
        if raw.isdigit() and 1 <= int(raw) <= len(files):
            break
        console.print("[red]Pilihan tidak valid.[/red]")

    doc_path = files[int(raw) - 1]

    presenter_name = Prompt.ask(
        "[bold]Nama presenter[/bold] (opsional, Enter untuk skip)",
        default=""
    )

    fresh = Confirm.ask(
        "Nonaktifkan materi lama? "
        "[dim](Tidak = Tenri tetap ingat semua, Ya = hanya materi ini)[/dim]",
        default=False,
    )

    console.print()
    try:
        from scripts.import_document import run as import_run
        import_run(doc_path, presenter_name, fresh)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


MENU_OPTIONS = [
    ("Jalankan Tenri",        _run_tenri),
    ("Import Materi",         _import_document),
    ("Rehearsal Simulasi",    _run_rehearsal),
    ("Kelola Knowledge Base", _run_knowledge_manager),
    ("Keluar",                None),
]


def main() -> None:
    _print_main_header()

    console.print("\n[bold]Menu:[/bold]")
    for i, (label, _) in enumerate(MENU_OPTIONS, 1):
        console.print(f"  [cyan]{i}.[/cyan] {label}")

    while True:
        raw = Prompt.ask("\nPilihan")
        if raw.isdigit() and 1 <= int(raw) <= len(MENU_OPTIONS):
            break
        console.print("[red]Pilihan tidak valid.[/red]")

    label, action = MENU_OPTIONS[int(raw) - 1]
    if action is None:
        console.print("[dim]Sampai jumpa.[/dim]")
        sys.exit(0)

    action()


if __name__ == "__main__":
    main()
