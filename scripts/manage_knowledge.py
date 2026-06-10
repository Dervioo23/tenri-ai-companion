import argparse
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.prompt import Prompt, Confirm

console = Console()


ROOT_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = ROOT_DIR / "app" / "knowledge"
SOURCES_PATH = KNOWLEDGE_DIR / "sources.json"

TYPE_DIRS = {
    "book": "books",
    "archive": "archives",
    "paper": "papers",
    "project_note": "project_notes",
    "presentation": "presentation",
}


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    return slug.strip("-") or "untitled-source"


def ensure_knowledge_tree() -> None:
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    for directory in TYPE_DIRS.values():
        (KNOWLEDGE_DIR / directory).mkdir(parents=True, exist_ok=True)
    (KNOWLEDGE_DIR / "inbox").mkdir(parents=True, exist_ok=True)
    (KNOWLEDGE_DIR / "indexes").mkdir(parents=True, exist_ok=True)
    if not SOURCES_PATH.exists():
        save_sources([])


def load_sources() -> list:
    ensure_knowledge_tree()
    with open(SOURCES_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def save_sources(sources: list) -> None:
    SOURCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SOURCES_PATH, "w", encoding="utf-8") as file:
        json.dump(sources, file, indent=2, ensure_ascii=False)
        file.write("\n")


def find_source(sources: list, source_id: str) -> dict | None:
    for source in sources:
        if source.get("id") == source_id:
            return source
    return None


def unique_source_id(sources: list, title: str) -> str:
    base_id = slugify(title)
    existing_ids = {source.get("id") for source in sources}
    if base_id not in existing_ids:
        return base_id

    suffix = 2
    while f"{base_id}-{suffix}" in existing_ids:
        suffix += 1
    return f"{base_id}-{suffix}"


def next_version(source: dict) -> str:
    versions = source.get("versions", [])
    if not versions:
        return "v1"

    highest = 0
    for version in versions:
        label = version.get("version", "")
        match = re.fullmatch(r"v(\d+)", label)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"v{highest + 1}"


def copy_into_knowledge(file_path: Path, source_type: str, source_id: str, version: str) -> str:
    if source_type not in TYPE_DIRS:
        raise ValueError(f"Unknown source type: {source_type}")
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"Source file not found: {file_path}")

    target_dir = KNOWLEDGE_DIR / TYPE_DIRS[source_type]
    target_dir.mkdir(parents=True, exist_ok=True)
    extension = file_path.suffix.lower()
    target_name = f"{source_id}_{version}{extension}"
    target_path = target_dir / target_name

    counter = 2
    while target_path.exists():
        target_name = f"{source_id}_{version}_{counter}{extension}"
        target_path = target_dir / target_name
        counter += 1

    shutil.copy2(file_path, target_path)
    return str(target_path.relative_to(KNOWLEDGE_DIR)).replace("\\", "/")


def add_source(source_type: str, title: str, file_path: Path, notes: str = "") -> dict:
    sources = load_sources()
    source_id = unique_source_id(sources, title)
    version = "v1"
    relative_path = copy_into_knowledge(file_path, source_type, source_id, version)

    source = {
        "id": source_id,
        "title": title,
        "type": source_type,
        "active_version": version,
        "status": "active",
        "versions": [
            {
                "version": version,
                "path": relative_path,
                "status": "active",
                "created_at": date.today().isoformat(),
            }
        ],
        "notes": notes,
    }
    sources.append(source)
    save_sources(sources)
    return source


def replace_source(source_id: str, file_path: Path) -> dict:
    sources = load_sources()
    source = find_source(sources, source_id)
    if source is None:
        raise ValueError(f"Source id not found: {source_id}")

    for version in source.get("versions", []):
        if version.get("status") == "active":
            version["status"] = "archived"

    version_label = next_version(source)
    relative_path = copy_into_knowledge(
        file_path,
        source["type"],
        source["id"],
        version_label,
    )
    source.setdefault("versions", []).append(
        {
            "version": version_label,
            "path": relative_path,
            "status": "active",
            "created_at": date.today().isoformat(),
        }
    )
    source["active_version"] = version_label
    source["status"] = "active"
    save_sources(sources)
    return source


def disable_source(source_id: str) -> dict:
    sources = load_sources()
    source = find_source(sources, source_id)
    if source is None:
        raise ValueError(f"Source id not found: {source_id}")
    source["status"] = "disabled"
    save_sources(sources)
    return source


def enable_source(source_id: str) -> dict:
    sources = load_sources()
    source = find_source(sources, source_id)
    if source is None:
        raise ValueError(f"Source id not found: {source_id}")
    source["status"] = "active"
    save_sources(sources)
    return source


def list_sources() -> str:
    sources = load_sources()
    if not sources:
        return "No sources registered."

    grouped = {}
    for source in sources:
        grouped.setdefault(source.get("status", "unknown"), []).append(source)

    lines = []
    for status in sorted(grouped):
        lines.append(status.upper())
        for source in sorted(grouped[status], key=lambda item: item.get("title", "")):
            lines.append(
                f"- {source['id']} {source.get('active_version', '-')}: "
                f"{source.get('title', '(untitled)')} [{source.get('type', '-')}]"
            )
        lines.append("")
    return "\n".join(lines).strip()


def ingest_inbox(source_type: str) -> list:
    inbox_dir = KNOWLEDGE_DIR / "inbox"
    ensure_knowledge_tree()
    ingested = []
    for file_path in sorted(inbox_dir.iterdir()):
        if file_path.name == ".gitkeep" or not file_path.is_file():
            continue
        title = file_path.stem.replace("_", " ").replace("-", " ").strip().title()
        ingested.append(add_source(source_type, title, file_path))
        file_path.unlink()
    return ingested


def reindex_all() -> int:
    sys.path.insert(0, str(ROOT_DIR))
    from app.services.document_loader import DocumentLoader
    loader = DocumentLoader()
    chunks = loader.load_all_documents(force_rechunk=True)
    return len(chunks)


# ------------------------------------------------------------------ interactive menu

def _print_header() -> None:
    console.print(Panel(
        "[bold cyan]Tenri Knowledge Manager[/bold cyan]\n"
        "[dim]Kelola sumber pengetahuan Tenri[/dim]",
        box=box.DOUBLE_EDGE,
        expand=False,
    ))


def _print_sources_table() -> None:
    sources = load_sources()
    if not sources:
        console.print("[yellow]Belum ada sumber terdaftar.[/yellow]")
        return

    table = Table(box=box.SIMPLE_HEAD, show_lines=False)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Versi", justify="center")
    table.add_column("Judul")
    table.add_column("Tipe")
    table.add_column("Status", justify="center")

    status_color = {"active": "green", "disabled": "red", "draft": "yellow"}
    for s in sorted(sources, key=lambda x: x.get("id", "")):
        color = status_color.get(s.get("status", ""), "white")
        table.add_row(
            s.get("id", "-"),
            s.get("active_version", "-"),
            s.get("title", "-"),
            s.get("type", "-"),
            f"[{color}]{s.get('status', '-')}[/{color}]",
        )
    console.print(table)


def _ask_type() -> str:
    choices = sorted(TYPE_DIRS.keys())
    console.print("\n[bold]Tipe sumber:[/bold]")
    for i, t in enumerate(choices, 1):
        console.print(f"  [cyan]{i}.[/cyan] {t}")
    while True:
        raw = Prompt.ask("Pilih nomor tipe")
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            return choices[int(raw) - 1]
        console.print("[red]Pilihan tidak valid, coba lagi.[/red]")


def _ask_existing_id(label: str = "ID sumber") -> str:
    _print_sources_table()
    return Prompt.ask(f"\n[bold]{label}[/bold]")


def _menu_add() -> None:
    console.rule("[bold]Tambah Sumber Baru[/bold]")
    source_type = _ask_type()
    title = Prompt.ask("\n[bold]Judul sumber[/bold]")
    raw_path = Prompt.ask("[bold]Path file[/bold] (contoh: C:/Downloads/paper.pdf)")
    file_path = Path(raw_path.strip('"').strip("'"))
    notes = Prompt.ask("[bold]Catatan[/bold] (opsional, tekan Enter untuk skip)", default="")

    try:
        source = add_source(source_type, title, file_path, notes)
        console.print(f"\n[green]Berhasil ditambahkan:[/green] {source['id']} {source['active_version']}")
    except (FileNotFoundError, ValueError) as e:
        console.print(f"\n[red]Error:[/red] {e}")


def _menu_replace() -> None:
    console.rule("[bold]Ganti Sumber (Replace)[/bold]")
    source_id = _ask_existing_id("ID sumber yang ingin diganti")
    if not source_id:
        return

    sources = load_sources()
    source = find_source(sources, source_id)
    if not source:
        console.print(f"\n[red]Error:[/red] Source tidak ditemukan: {source_id}")
        return

    # Tampilkan path file aktif saat ini
    active_ver = source.get("active_version", "")
    current_rel = next(
        (v["path"] for v in source.get("versions", []) if v.get("version") == active_ver),
        "",
    )
    current_abs = str(KNOWLEDGE_DIR / current_rel) if current_rel else ""
    if current_abs:
        console.print(f"\n[dim]File aktif saat ini:[/dim] [cyan]{current_abs}[/cyan]")

    raw_path = Prompt.ask(
        "[bold]Path file baru[/bold] (Enter = pakai file yang sama)",
        default=current_abs,
    )
    file_path = Path(raw_path.strip('"').strip("'"))

    try:
        source = replace_source(source_id, file_path)
        console.print(f"\n[green]Berhasil diganti:[/green] {source['id']} → {source['active_version']}")
    except (FileNotFoundError, ValueError) as e:
        console.print(f"\n[red]Error:[/red] {e}")


def _menu_disable() -> None:
    console.rule("[bold]Nonaktifkan Sumber[/bold]")
    source_id = _ask_existing_id("ID sumber yang ingin dinonaktifkan")
    if Confirm.ask(f"Yakin nonaktifkan [cyan]{source_id}[/cyan]?"):
        try:
            disable_source(source_id)
            console.print(f"\n[yellow]Dinonaktifkan:[/yellow] {source_id}")
        except ValueError as e:
            console.print(f"\n[red]Error:[/red] {e}")


def _menu_enable() -> None:
    console.rule("[bold]Aktifkan Sumber[/bold]")
    source_id = _ask_existing_id("ID sumber yang ingin diaktifkan")
    try:
        enable_source(source_id)
        console.print(f"\n[green]Diaktifkan:[/green] {source_id}")
    except ValueError as e:
        console.print(f"\n[red]Error:[/red] {e}")


def _menu_ingest() -> None:
    console.rule("[bold]Tambah dari Inbox[/bold]")
    inbox_dir = KNOWLEDGE_DIR / "inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(
        f for f in inbox_dir.iterdir()
        if f.is_file() and f.name != ".gitkeep"
    )
    if not files:
        console.print(f"[yellow]Inbox kosong.[/yellow]")
        console.print(f"[dim]Taruh file di: {inbox_dir}[/dim]")
        console.print("[dim]Format yang didukung: .md .txt .pdf .docx .pptx[/dim]")
        return

    console.print(f"\n[bold]File di inbox ({len(files)}):[/bold]")
    for i, f in enumerate(files, 1):
        console.print(f"  [cyan]{i}.[/cyan] {f.name}  [dim]({f.stat().st_size // 1024} KB)[/dim]")

    source_type = _ask_type()

    try:
        ingested = ingest_inbox(source_type)
        if ingested:
            console.print(f"\n[green]Berhasil diingest:[/green] {len(ingested)} sumber")
            for s in ingested:
                console.print(f"  [dim]→[/dim] {s['id']} {s['active_version']}: {s['title']}")
        else:
            console.print("[yellow]Tidak ada file yang berhasil diingest.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")


def _menu_reindex() -> None:
    console.rule("[bold]Reindex Semua Dokumen[/bold]")
    if Confirm.ask("Rebuild semua index dari file aktif?"):
        with console.status("[cyan]Sedang mengindex...[/cyan]"):
            try:
                total = reindex_all()
                console.print(f"\n[green]Selesai.[/green] {total} chunk diindex.")
            except Exception as e:
                console.print(f"\n[red]Error:[/red] {e}")


MENU_OPTIONS = [
    ("Tambah dari inbox (taruh file dulu di knowledge/inbox/)", _menu_ingest),
    ("Tambah sumber manual (masukkan path file)",               _menu_add),
    ("Ganti sumber (replace)",                                  _menu_replace),
    ("Nonaktifkan sumber",                                      _menu_disable),
    ("Aktifkan sumber",                                         _menu_enable),
    ("Lihat semua sumber",                                      lambda: _print_sources_table()),
    ("Reindex semua dokumen",                                   _menu_reindex),
    ("Keluar",                                                  None),
]


def run_interactive() -> None:
    _print_header()
    while True:
        console.print("\n[bold]Menu:[/bold]")
        for i, (label, _) in enumerate(MENU_OPTIONS, 1):
            console.print(f"  [cyan]{i}.[/cyan] {label}")

        raw = Prompt.ask("\nPilihan")
        if not raw.isdigit() or not (1 <= int(raw) <= len(MENU_OPTIONS)):
            console.print("[red]Pilihan tidak valid.[/red]")
            continue

        label, action = MENU_OPTIONS[int(raw) - 1]
        if action is None:
            console.print("[dim]Sampai jumpa.[/dim]")
            break
        action()
        console.print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Tenri knowledge sources.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a new source as v1.")
    add_parser.add_argument("--type", required=True, choices=sorted(TYPE_DIRS))
    add_parser.add_argument("--title", required=True)
    add_parser.add_argument("--file", required=True, type=Path)
    add_parser.add_argument("--notes", default="")

    replace_parser = subparsers.add_parser("replace", help="Replace a source with a new active version.")
    replace_parser.add_argument("--id", required=True)
    replace_parser.add_argument("--file", required=True, type=Path)

    disable_parser = subparsers.add_parser("disable", help="Disable a source without deleting files.")
    disable_parser.add_argument("--id", required=True)

    enable_parser = subparsers.add_parser("enable", help="Enable a disabled source.")
    enable_parser.add_argument("--id", required=True)

    subparsers.add_parser("list", help="List registered sources by status.")

    ingest_parser = subparsers.add_parser("ingest", help="Import all files from app/knowledge/inbox.")
    ingest_parser.add_argument("--type", default="project_note", choices=sorted(TYPE_DIRS))

    subparsers.add_parser("reindex", help="Rebuild all indexes from active source files.")

    return parser


def main() -> None:
    if len(sys.argv) == 1:
        run_interactive()
        return

    args = build_parser().parse_args()

    if args.command == "add":
        source = add_source(args.type, args.title, args.file, args.notes)
        print(f"Added {source['id']} {source['active_version']}")
    elif args.command == "replace":
        source = replace_source(args.id, args.file)
        print(f"Replaced {source['id']} with {source['active_version']}")
    elif args.command == "disable":
        source = disable_source(args.id)
        print(f"Disabled {source['id']}")
    elif args.command == "enable":
        source = enable_source(args.id)
        print(f"Enabled {source['id']}")
    elif args.command == "list":
        print(list_sources())
    elif args.command == "ingest":
        sources = ingest_inbox(args.type)
        print(f"Ingested {len(sources)} source(s).")
    elif args.command == "reindex":
        total = reindex_all()
        print(f"Reindexed {total} chunk(s).")


if __name__ == "__main__":
    main()
