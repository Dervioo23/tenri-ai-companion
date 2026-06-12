"""Tenri JARVIS-style visual display.

Pygame display and event handling run on the process main thread. Interaction
updates arrive through a thread-safe queue from the companion worker thread.
"""
import array
import logging
import math
import queue
import threading
import time
import pygame

logger = logging.getLogger("AICompanion.JarvisUI")

# ── Colour palette ────────────────────────────────────────────────────────────
BG        = (4,   8,  14)
TEAL      = (0,  210, 190)
TEAL_MID  = (0,  140, 130)
TEAL_DIM  = (0,   55,  55)
TEAL_GLOW = (0,  255, 220)
CYAN      = (0,  180, 255)
GREEN     = (0,  220, 130)
RED       = (220,  55,  55)
WHITE     = (200, 235, 235)

_STATE_COLOR = {
    "IDLE":      TEAL_MID,
    "LISTENING": GREEN,
    "THINKING":  CYAN,
    "SPEAKING":  TEAL,
    "ERROR":     RED,
}

_STATE_SPEED = {          # degrees/frame for outer arc rotation
    "IDLE":      0.25,
    "LISTENING": 1.80,
    "THINKING":  3.60,
    "SPEAKING":  1.20,
    "ERROR":     5.00,
}


class _UISounds:
    """JARVIS-style UI sound effects for each state transition.

    All waveforms are synthesised at runtime using array.array — no audio files
    needed. Uses Sound.play() which auto-assigns a free mixer channel, keeping
    it completely separate from ElevenLabs TTS (pygame.mixer.music).

    Sound design:
      LISTENING → ascending 3-note arpeggio  (ears opening)
      THINKING  → rapid rising triple blip   (processing)
      SPEAKING  → descending smooth glide    (voice opening)
      IDLE      → soft low fade-out click    (powering down)
      ERROR     → sawtooth warning buzz      (alert)

    NOTE: Must be instantiated AFTER pygame.mixer is initialised (i.e. after
    AudioPlayer has called pygame.mixer.init). Use the lazy factory below.
    """

    def __init__(self, rate: int, channels: int):
        self._rate     = rate
        self._channels = channels
        self._sounds: dict[str, "pygame.mixer.Sound | None"] = {}
        self._active: "pygame.mixer.Channel | None" = None

        self._sounds = {
            # Ascending triple ping — "Tenri is listening"
            "LISTENING": self._arpeggio([
                (360, 0.07), (540, 0.07), (800, 0.10),
            ], vol=0.30),

            # Rapid rising blips — "processing"
            "THINKING": self._arpeggio([
                (440, 0.045), (580, 0.045), (740, 0.05),
            ], vol=0.22),

            # Descending glide — "opening voice"
            "SPEAKING":  self._tone(660, 330, 0.16, vol=0.28),

            # Soft low fade-out — "standing by"
            "IDLE":      self._tone(280, 170, 0.14, vol=0.20),

            # Sawtooth buzz — "error / alert"
            "ERROR":     self._tone(160, 160, 0.30, vol=0.25, wave="saw"),
        }
        loaded = sum(1 for s in self._sounds.values() if s)
        logger.info(f"UISounds ready — {loaded}/{len(self._sounds)} sounds at {rate}Hz.")

    @classmethod
    def build(cls) -> "tuple[_UISounds, bool]":
        """Factory: returns (instance, ok).  Returns (None, False) if mixer not ready."""
        info = pygame.mixer.get_init()
        if not info:
            return None, False
        rate, _size, channels = info
        try:
            return cls(rate, channels), True
        except Exception as e:
            logger.warning(f"UISounds build failed: {e}")
            return None, False

    def play(self, state: str) -> None:
        snd = self._sounds.get(state)
        if not snd:
            return
        try:
            # Stop previous UI sound so transitions don't overlap
            if self._active and self._active.get_busy():
                self._active.stop()
            self._active = snd.play()
        except Exception as e:
            logger.debug(f"UISounds play error ({state}): {e}")

    # ── Waveform builders ────────────────────────────────────────────────────

    def _tone(
        self, f1: float, f2: float, dur: float,
        vol: float = 0.28, wave: str = "sine",
    ) -> "pygame.mixer.Sound | None":
        try:
            snd = pygame.mixer.Sound(buffer=self._gen(f1, f2, dur, wave))
            snd.set_volume(vol)
            return snd
        except Exception as e:
            logger.debug(f"UISounds tone({f1}→{f2}Hz) error: {e}")
            return None

    def _arpeggio(
        self, notes: list[tuple[float, float]], vol: float = 0.28
    ) -> "pygame.mixer.Sound | None":
        """Sequence of (freq, dur) notes joined into one Sound object."""
        try:
            combined: array.array = array.array("h")
            for f, d in notes:
                combined.extend(self._gen(f, f, d, "sine"))
            snd = pygame.mixer.Sound(buffer=combined)
            snd.set_volume(vol)
            return snd
        except Exception as e:
            logger.debug(f"UISounds arpeggio error: {e}")
            return None

    def _gen(self, f1: float, f2: float, dur: float, shape: str) -> array.array:
        """Generate a 16-bit PCM waveform as array.array('h') matching mixer format."""
        n    = max(1, int(self._rate * dur))
        fade = max(1, int(n * 0.12))               # 12 % trapezoid envelope
        out  = array.array("h", [0] * (n * self._channels))
        for i in range(n):
            t    = i / self._rate
            freq = f1 + (f2 - f1) * i / max(n - 1, 1)
            if shape == "sine":
                v = math.sin(2 * math.pi * freq * t)
            else:                                   # sawtooth
                v = 2.0 * (freq * t - math.floor(freq * t + 0.5))
            env = min(i / fade, 1.0, (n - i) / fade)
            amp = max(-32768, min(32767, int(v * env * 17000)))
            for ch in range(self._channels):
                out[i * self._channels + ch] = amp
        return out


class JarvisDisplay:
    """Pygame JARVIS-style companion window for Tenri."""

    WIDTH  = 960
    HEIGHT = 700
    FPS    = 60

    def __init__(self):
        self._q           = queue.Queue()
        self._stop        = threading.Event()

        # Shared display state (written by public API, read by render thread)
        self.state      = "IDLE"
        self.response   = ""
        self.user_input = ""
        self.slide_info = ""

    # ── Public thread-safe API ────────────────────────────────────────────────

    def start(self, on_quit=None) -> None:
        """Run the blocking display loop on the process main thread."""
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError("JarvisDisplay must run on the main thread.")
        self._render_loop(on_quit=on_quit)

    def stop(self) -> None:
        self._stop.set()

    def update_state(self, state_name: str) -> None:
        self._q.put(("state", state_name))

    def update_response(self, text: str) -> None:
        self._q.put(("response", text))

    def update_user_input(self, text: str) -> None:
        self._q.put(("user_input", text))

    def update_slide(self, text: str) -> None:
        self._q.put(("slide", text))

    # ── Render loop (main thread) ────────────────────────────────────────────

    def _render_loop(self, on_quit=None) -> None:
        # Only init display subsystem — mixer is already initialised by AudioPlayer
        pygame.display.init()
        pygame.font.init()

        screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("TENRI — AI Companion")

        # Window icon: small teal circle
        icon = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(icon, TEAL, (16, 16), 13, 2)
        pygame.display.set_icon(icon)

        # Fonts — consolas for the clean monospace JARVIS feel
        def _font(size: int, bold: bool = False) -> pygame.font.Font:
            try:
                return pygame.font.SysFont("consolas", size, bold=bold)
            except Exception:
                return pygame.font.SysFont(None, size, bold=bold)

        f_title  = _font(54, bold=True)
        f_sub    = _font(15)
        f_status = _font(16)
        f_small  = _font(14)

        clock    = pygame.time.Clock()
        angle    = 0.0          # outer arc rotation (degrees)
        t0       = time.time()

        # Sound engine — lazy: built only after pygame.mixer is ready.
        # JarvisDisplay.start() is called BEFORE AudioPlayer creates the mixer,
        # so we cannot build _UISounds at thread start — we poll each frame.
        sfx: _UISounds | None = None
        _prev_state = ""

        while not self._stop.is_set():
            # ── Pygame window events
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self._stop.set()
                    if on_quit:
                        on_quit()
                    pygame.display.quit()
                    return

            # ── Drain update queue
            while True:
                try:
                    kind, data = self._q.get_nowait()
                    if kind == "state":
                        self.state = data
                    elif kind == "response":
                        self.response = data
                    elif kind == "user_input":
                        self.user_input = data
                    elif kind == "slide":
                        self.slide_info = data
                except queue.Empty:
                    break

            # ── Lazy-init sound engine once mixer is available
            if sfx is None:
                sfx, _ = _UISounds.build()

            # ── Play sound on state transition
            if self.state != _prev_state:
                if sfx:
                    sfx.play(self.state)
                _prev_state = self.state

            # ── Animation values
            speed  = _STATE_SPEED.get(self.state, 1.0)
            angle  = (angle + speed) % 360
            t      = time.time() - t0
            pulse  = (math.sin(t * 2.8) + 1) / 2          # 0–1 slow
            fpulse = (math.sin(t * 5.5) + 1) / 2          # 0–1 fast
            color  = _STATE_COLOR.get(self.state, TEAL_MID)

            # ── Clear
            screen.fill(BG)

            cx = self.WIDTH  // 2
            cy = self.HEIGHT // 2 - 30      # visual centre, shifted up

            # ── Outer atmosphere rings (very dim)
            for r in [250, 235, 220]:
                c = tuple(min(255, int(v * 0.18)) for v in color)
                pygame.draw.circle(screen, c, (cx, cy), r, 1)

            # ── Outer rotating arcs (4 segments, large)
            self._draw_arcs(screen, cx, cy, 205, angle, color, 3, 4)

            # ── Static decorative ring
            pygame.draw.circle(screen, TEAL_DIM, (cx, cy), 176, 1)

            # ── Inner counter-rotating arcs (6 segments, smaller)
            self._draw_arcs(screen, cx, cy, 155, -angle * 0.65, color, 2, 6)

            # ── Dynamic inner ring (pulses outward)
            ir = 120 + int(pulse * 10)
            pygame.draw.circle(screen, color, (cx, cy), ir, 2)

            # ── Core glow (soft, layered)
            for g in range(7, 0, -1):
                alpha = int(100 * (1 - g / 8) * (0.55 + fpulse * 0.45))
                gc = tuple(min(255, int(v * alpha // 100)) for v in color)
                r_core = ir - g * 5
                if r_core > 0:
                    pygame.draw.circle(screen, gc, (cx, cy), r_core, g + 1)

            # ── TENRI text (centre)
            t_surf = f_title.render("TENRI", True, color)
            screen.blit(t_surf, t_surf.get_rect(center=(cx, cy - 6)))

            # ── Sub-label
            sub_c = tuple(min(255, int(v * 0.55)) for v in color)
            s_surf = f_sub.render("AI  COMPANION", True, sub_c)
            screen.blit(s_surf, s_surf.get_rect(center=(cx, cy + 34)))

            # ── Horizontal accent lines (flanking subtitles)
            line_hw = 55 + int(pulse * 18)
            lc = tuple(min(255, int(v * 0.45)) for v in color)
            for sign in (-1, 1):
                px = cx + sign * (line_hw + 8)
                pygame.draw.line(screen, lc, (cx + sign * 6, cy + 34), (px, cy + 34), 1)

            # ── Tick marks around outer ring
            self._draw_tick_marks(screen, cx, cy, 222, color, 36)

            # ── State indicator (top-left)
            dot = "● " if self.state != "IDLE" else "○ "
            st_surf = f_status.render(dot + self.state, True, color)
            screen.blit(st_surf, (22, 20))

            # ── Corner accents
            self._draw_corner_accent(screen, 0, 0, color, 40)
            self._draw_corner_accent(screen, self.WIDTH, 0, color, 40, flip_x=True)

            # ── Bottom info panel ─────────────────────────────────────────────
            py = cy + 185
            lh = 20

            if self.slide_info:
                line = self._trunc("SLIDE  " + self.slide_info, 100)
                screen.blit(f_small.render(line, True, TEAL_DIM), (22, py))
                py += lh

            if self.user_input:
                line = self._trunc("YOU    " + self.user_input, 100)
                screen.blit(f_small.render(line, True, (100, 170, 160)), (22, py))
                py += lh

            if self.response:
                for ln in self._wrap("TENRI  " + self.response, f_small, self.WIDTH - 44)[:3]:
                    screen.blit(f_small.render(ln, True, color), (22, py))
                    py += lh

            pygame.display.flip()
            clock.tick(self.FPS)

        pygame.display.quit()

    # ── Drawing helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _draw_arcs(
        surface: pygame.Surface,
        cx: int, cy: int,
        radius: int,
        angle_deg: float,
        color: tuple,
        width: int,
        n: int,
    ) -> None:
        """Draw *n* equally-spaced rotating arc segments."""
        gap   = 360 / n
        span  = gap * 0.52          # fraction of gap that is filled
        for i in range(n):
            pts = []
            base = angle_deg + i * gap
            for d in range(int(span)):
                a = math.radians(base + d)
                pts.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
            if len(pts) >= 2:
                pygame.draw.lines(surface, color, False, pts, width)

    @staticmethod
    def _draw_tick_marks(
        surface: pygame.Surface,
        cx: int, cy: int,
        radius: int,
        color: tuple,
        count: int,
    ) -> None:
        """Small radial tick marks around a ring."""
        for i in range(count):
            a    = math.radians(i * 360 / count)
            cos_a, sin_a = math.cos(a), math.sin(a)
            tick = 5 if i % 3 == 0 else 3
            x0   = cx + (radius - tick) * cos_a
            y0   = cy + (radius - tick) * sin_a
            x1   = cx + radius * cos_a
            y1   = cy + radius * sin_a
            c    = tuple(min(255, int(v * (0.7 if i % 3 == 0 else 0.35))) for v in color)
            pygame.draw.line(surface, c, (int(x0), int(y0)), (int(x1), int(y1)), 1)

    @staticmethod
    def _draw_corner_accent(
        surface: pygame.Surface,
        x: int, y: int,
        color: tuple,
        size: int,
        flip_x: bool = False,
    ) -> None:
        """L-shaped corner accent bracket."""
        c = tuple(min(255, int(v * 0.5)) for v in color)
        if flip_x:
            pygame.draw.line(surface, c, (x - size, y + 3), (x - 3, y + 3), 1)
            pygame.draw.line(surface, c, (x - 3, y + 3), (x - 3, y + size), 1)
        else:
            pygame.draw.line(surface, c, (x + 3, y + 3), (x + size, y + 3), 1)
            pygame.draw.line(surface, c, (x + 3, y + 3), (x + 3, y + size), 1)

    @staticmethod
    def _trunc(text: str, n: int) -> str:
        return text if len(text) <= n else text[:n - 1] + "…"

    @staticmethod
    def _wrap(text: str, font: pygame.font.Font, max_w: int) -> list[str]:
        words, lines, cur = text.split(), [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if font.size(test)[0] <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines
