import os
import sys
import threading


def _configure_windows_utf8_console() -> None:
    """Keep Rich box drawing and arrows readable in Windows PowerShell."""
    if sys.platform != "win32":
        return
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        os.system("chcp 65001 > nul")
    except Exception:
        pass
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_configure_windows_utf8_console()

from app.utils.logger import setup_logger
from app.core.interaction_loop import InteractionLoop
from app.config import Config

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
    errors, _warnings = Config.validate_critical_configs()
    if errors:
        console.print("\n[bold red]Konfigurasi Tenri tidak valid.[/bold red]")
        for error in errors:
            console.print(f"  [red]- {error}[/red]")
        console.print("[dim]Tidak ada UI, microphone, kamera, atau TTS yang diinisialisasi.[/dim]")
        return

    jarvis_ui = None
    loop = None
    interaction_thread = None
    worker_errors: list[Exception] = []
    try:
        from app.ui.jarvis_display import JarvisDisplay
        jarvis_ui = JarvisDisplay()
        loop = InteractionLoop(jarvis_ui=jarvis_ui)

        def _run_interaction() -> None:
            try:
                loop.run()
            except Exception as error:
                worker_errors.append(error)
            finally:
                jarvis_ui.stop()

        interaction_thread = threading.Thread(
            target=_run_interaction,
            daemon=True,
            name="TenriInteractionLoop",
        )
        interaction_thread.start()

        # Pygame display/event pump must stay on the process main thread.
        jarvis_ui.start(on_quit=loop.request_stop)
        loop.request_stop()
        interaction_thread.join(timeout=15.0)
        if interaction_thread.is_alive():
            console.print(
                "[yellow]Tenri masih menunggu operasi input selesai; "
                "worker akan dihentikan saat proses keluar.[/yellow]"
            )
        if worker_errors:
            raise worker_errors[0]
    except KeyboardInterrupt:
        if loop:
            loop.request_stop()
        if jarvis_ui:
            jarvis_ui.stop()
        console.print("\n[dim]Aplikasi dihentikan oleh pengguna.[/dim]")
    except Exception as e:
        console.print(f"[red]Kritikal:[/red] Gagal menjalankan aplikasi: {e}")
    finally:
        if loop:
            loop.request_stop()
        if jarvis_ui:
            jarvis_ui.stop()
        if interaction_thread and interaction_thread.is_alive():
            interaction_thread.join(timeout=15.0)


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


def _print_menu() -> None:
    console.print("\n[bold]Menu:[/bold]")
    for i, (label, _) in enumerate(MENU_OPTIONS, 1):
        console.print(f"  [cyan]{i}.[/cyan] {label}")


def _prompt_menu_choice() -> int:
    """Prompt until a valid menu index is chosen. Returns a 0-based index."""
    while True:
        try:
            raw = Prompt.ask("\nPilihan")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Sampai jumpa.[/dim]")
            sys.exit(0)
        if raw.isdigit() and 1 <= int(raw) <= len(MENU_OPTIONS):
            return int(raw) - 1
        console.print("[red]Pilihan tidak valid.[/red]")


def main() -> None:
    _print_main_header()

    # Loop kembali ke menu setelah setiap aksi selesai; hanya keluar saat
    # pengguna memilih "Keluar". Sebelumnya menu hanya berjalan sekali sehingga
    # mengimpor materi lalu menjalankan Tenri butuh restart aplikasi.
    while True:
        _print_menu()
        label, action = MENU_OPTIONS[_prompt_menu_choice()]

        if action is None:
            console.print("[dim]Sampai jumpa.[/dim]")
            return

        try:
            action()
        except KeyboardInterrupt:
            # _run_tenri menangani Ctrl+C-nya sendiri (sys.exit); aksi lain yang
            # dibatalkan dengan Ctrl+C cukup kembali ke menu.
            console.print("\n[dim]Dibatalkan. Kembali ke menu.[/dim]")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


if __name__ == "__main__":
    main()
