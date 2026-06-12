from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.status import Status
from rich import box
from app.state import AppState
from app.config import Config

console = Console(emoji=False)

class TerminalUI:
    @staticmethod
    def print_welcome_banner():
        """Prints a premium, neon-themed ASCII welcome banner for Tenri."""
        console.clear()
        banner_text = """
    T E N R I
 Voice Companion Terminal
        """
        styled_banner = Text(banner_text, style="bold cyan")
        
        info_text = Text()
        info_text.append("\n  Tenri Voice Companion Prototype - v1.0.0\n", style="bold white")
        info_text.append("  Archive, Memory, and Presentation Companion\n", style="italic gray")
        info_text.append("  ------------------------------------------\n", style="dim cyan")
        info_text.append(f"  Language: {Config.APP_LANGUAGE.upper()} | ")
        display_model = Config.ACTIVE_LLM_MODEL
        if Config.LLM_PROVIDER == "groq" and Config.GROQ_LIVE_MODEL:
            display_model = f"{Config.GROQ_LIVE_MODEL} (live)"
        info_text.append(f"  LLM: {Config.LLM_PROVIDER.upper()} / {display_model} | ")
        
        vision_status = "ENABLED" if Config.VISION_ENABLED else "DISABLED"
        info_text.append(f"  Vision: {vision_status}\n")

        panel = Panel(
            Columns([styled_banner, info_text], align="center", expand=True),
            title="[bold cyan]SYSTEM INITIATED[/bold cyan]",
            border_style="cyan",
            box=box.ASCII,
            safe_box=True,
            padding=(1, 2)
        )
        console.print(panel)
        console.print()

    @staticmethod
    def print_setup_status(errors: list, warnings: list):
        """Prints warnings and errors about configuration."""
        if errors:
            err_text = Text()
            for err in errors:
                err_text.append(f"[X] {err}\n", style="bold red")
            console.print(Panel(err_text, title="CRITICAL ERRORS", border_style="red", box=box.ASCII, safe_box=True))
            console.print()
            
        if warnings:
            warn_text = Text()
            for warn in warnings:
                warn_text.append(f"[!] {warn}\n", style="yellow")
            console.print(Panel(warn_text, title="SYSTEM WARNINGS (RUNNING WITH FALLBACKS)", border_style="yellow", box=box.ASCII, safe_box=True))
            console.print()

    @staticmethod
    def get_state_badge(state: AppState, error_msg: str = None) -> Text:
        """Returns a stylized Text badge for the given state."""
        badge = Text()
        if state == AppState.IDLE:
            badge.append("* IDLE ", style="bold green")
            badge.append("Waiting for trigger...", style="dim white")
        elif state == AppState.LISTENING:
            badge.append("* LISTENING ", style="bold red blinking")
            badge.append("Speak now...", style="bold white")
        elif state == AppState.THINKING:
            badge.append("* THINKING ", style="bold yellow")
            badge.append("Tenri is formulating a response...", style="italic yellow")
        elif state == AppState.SPEAKING:
            badge.append("* SPEAKING ", style="bold cyan")
            badge.append("Tenri is speaking...", style="cyan")
        elif state == AppState.ERROR:
            badge.append("X ERROR ", style="bold red")
            badge.append(f"{error_msg or 'Unknown error occurred.'}", style="red")
        return badge

    @staticmethod
    def update_state_display(state: AppState, error_msg: str = None):
        """Prints state transition in terminal."""
        badge = TerminalUI.get_state_badge(state, error_msg)
        console.print(badge)

    @staticmethod
    def print_user_message(text: str):
        """Displays user message transcribed text."""
        console.print(f"\n[bold magenta]You:[/bold magenta] {text}")

    @staticmethod
    def print_assistant_response(name: str, text: str):
        """Displays assistant response inside a premium custom frame."""
        # Cyan frame for Tenri responses
        panel = Panel(
            Text(text, style="bold white"),
            title=f"[bold cyan]Tenri ({name})[/bold cyan]",
            border_style="cyan",
            subtitle="TTS Output",
            subtitle_align="right",
            box=box.ASCII,
            safe_box=True
        )
        console.print(panel)
        console.print()

    @staticmethod
    def print_sensory_update(vision_context: dict):
        """Displays brief info about vision tracking."""
        if not Config.VISION_ENABLED:
            return
            
        vis_text = Text("Sensory: ", style="dim gray")
        
        if vision_context.get("face_detected"):
            vis_text.append(f"{vision_context.get('face_count')} Face(s) Detected ", style="green")
        else:
            vis_text.append("No Presence ", style="dim gray")
            
        if vision_context.get("motion_detected"):
            vis_text.append(" | Motion Active", style="yellow")
            
        console.print(vis_text)

    @staticmethod
    def print_slide_startup(slide: dict, current: int, total: int) -> None:
        """Compact slide indicator shown once at startup."""
        title = slide.get("title", "—")
        topics = slide.get("topics", [])
        line = Text()
        line.append(f"[{current}/{total}] ", style="dim cyan")
        line.append(title, style="cyan")
        if topics:
            line.append(f"  ·  {', '.join(topics)}", style="dim")
        console.print(Panel(line, title="[dim cyan]Slide Aktif[/dim cyan]",
                            border_style="dim cyan", box=box.SIMPLE, expand=False))
        console.print()

    @staticmethod
    def print_slide_status(slide: dict, current: int, total: int) -> None:
        """Detailed slide info shown on 'status' command."""
        title = slide.get("title", "—")
        topics = slide.get("topics", [])
        notes = slide.get("presenter_notes", "")
        lines: list[str] = [f"[bold]{title}[/bold]"]
        if topics:
            lines.append(f"[dim]Topik: {', '.join(topics)}[/dim]")
        if notes:
            lines.append(f"[italic dim]{notes}[/italic dim]")
        console.print(Panel(
            "\n".join(lines),
            title=f"[cyan]Posisi: Slide {current}/{total}[/cyan]",
            border_style="cyan",
            box=box.ASCII,
            safe_box=True,
            expand=False,
        ))

    @staticmethod
    def print_slide_list(slides: list, current_1based: int) -> None:
        """Table of all slides with the active one highlighted."""
        table = Table(box=box.SIMPLE_HEAD, show_lines=False,
                      title="[bold]Daftar Slide[/bold]")
        table.add_column("No.", justify="center", style="cyan", no_wrap=True)
        table.add_column("Judul")
        table.add_column("Topik", style="dim")
        table.add_column("", justify="center", width=1)
        for i, slide in enumerate(slides):
            marker = "[green]●[/green]" if (i + 1) == current_1based else ""
            table.add_row(
                str(i + 1),
                slide.get("title", "—"),
                ", ".join(slide.get("topics", [])),
                marker,
            )
        console.print(table)

    @staticmethod
    def print_slide_change(slide: dict | None, current: int, total: int) -> None:
        """Displays active slide change notification."""
        if not slide:
            return
        title = slide.get("title", "—")
        text = Text()
        text.append(f"→ Slide {current}/{total}: ", style="bold cyan")
        text.append(title, style="cyan")
        console.print(text)

    @staticmethod
    def print_interruption(mode: str, text: str) -> None:
        """Displays Tenri's proactive interjection with a yellow border."""
        _labels = {
            "comment":    "komentar",
            "question":   "pertanyaan",
            "correction": "koreksi",
            "memory":     "ingatan",
        }
        label = _labels.get(mode, mode)
        panel = Panel(
            Text(text, style="bold white"),
            title=f"[bold yellow]Tenri — {label}[/bold yellow]",
            border_style="yellow",
            subtitle="[dim italic]proaktif[/dim italic]",
            subtitle_align="right",
            box=box.ASCII,
            safe_box=True,
        )
        console.print(panel)
        console.print()

    @staticmethod
    def print_retrieval_sources(chunks: list):
        """Displays which knowledge sources were retrieved for the current query."""
        if not chunks:
            return
        labels = []
        for chunk in chunks:
            sid = chunk.get("source_id", "?")
            heading = chunk.get("heading", "")
            labels.append(f"{sid} › {heading}" if heading else sid)

        text = Text("Sumber: ", style="dim cyan")
        text.append(" | ".join(labels), style="dim")
        console.print(text)

    @staticmethod
    def print_auto_listen_hint(user_input: str) -> None:
        """Shown in auto-listen mode when captured speech is not addressed to Tenri."""
        preview = user_input[:60] + ("..." if len(user_input) > 60 else "")
        console.print(
            f"[dim]→ terdengar: \"{preview}\" "
            "— awali dengan [bold]Tenri[/bold] untuk memanggil langsung[/dim]"
        )

    @staticmethod
    def print_timing_summary(
        llm_s: float,
        tts_s: float,
        cycle_s: float,
        wait_s: float = 0.0,
        record_s: float = 0.0,
        stt_s: float = 0.0,
        retrieval_s: float = 0.0,
        first_voice_s: float = 0.0,
        audio_playback_s: float = 0.0,
    ) -> None:
        """Compact latency breakdown after each response."""
        parts = []
        if wait_s > 0:
            parts.append(f"Wait {wait_s:.1f}s")
        if record_s > 0:
            parts.append(f"Record {record_s:.1f}s")
        if stt_s > 0:
            parts.append(f"STT {stt_s:.1f}s")
        if retrieval_s > 0:
            parts.append(f"Retrieval {retrieval_s:.1f}s")
        if first_voice_s > 0:
            parts.append(f"FirstVoice {first_voice_s:.1f}s")
        if llm_s > 0:
            parts.append(f"LLM {llm_s:.1f}s")
        if tts_s > 0:
            parts.append(f"TTS {tts_s:.1f}s")
        if audio_playback_s > 0:
            parts.append(f"Audio {audio_playback_s:.1f}s")
        parts.append(f"Cycle {cycle_s:.1f}s")
        console.print(Text("timing  " + "  |  ".join(parts), style="dim yellow"))

    @staticmethod
    def get_spinner(status_text: str) -> Status:
        """Returns a spinner with standardized style."""
        return console.status(f"[bold yellow]{status_text}[/bold yellow]", spinner="arc")
