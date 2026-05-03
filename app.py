import tkinter as tk
import numpy as np
import pygame

# Audio setup

SAMPLE_RATE = 44100

try:
    pygame.mixer.quit()
except Exception:
    pass

pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=512)
pygame.mixer.set_num_channels(16)

_state = pygame.mixer.get_init()
if _state is None:
    raise RuntimeError("Audio mixer failed to initialize")
MIXER_FREQ, MIXER_SIZE, MIXER_CHANNELS = _state


# Music theory

NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

CHORD_TYPES = [
    ('',     [0, 4, 7],     'major'),
    ('m',    [0, 3, 7],     'minor'),
    ('7',    [0, 4, 7, 10], 'major'),
    ('maj7', [0, 4, 7, 11], 'major'),
    ('m7',   [0, 3, 7, 10], 'minor'),
    ('dim',  [0, 3, 6],     'dim'),
    ('sus4', [0, 5, 7],     'major'),
    ('aug',  [0, 4, 8],     'aug'),
]


def note_freq(semitones_from_c0):
    return 440.0 * (2 ** ((semitones_from_c0 - 57) / 12))


def chord_freqs(root_name, intervals, base_octave=3):
    root_idx = NOTES.index(root_name)
    base = base_octave * 12 + root_idx
    return [note_freq(base + i) for i in intervals]


# Synthesis

def piano_note(freq, duration):
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    wave = np.zeros(n, dtype=np.float64)

    harmonics = [
        (1, 1.00, 0.4),
        (2, 0.55, 0.7),
        (3, 0.30, 1.2),
        (4, 0.18, 1.8),
        (5, 0.10, 2.5),
        (6, 0.05, 3.2),
    ]

    for mult, amp, decay in harmonics:
        wave += amp * np.sin(2 * np.pi * freq * mult * t) * np.exp(-decay * t)

    attack = max(1, int(0.005 * SAMPLE_RATE))
    wave[:attack] *= np.linspace(0, 1, attack)

    fade = max(1, int(0.05 * SAMPLE_RATE))
    wave[-fade:] *= np.linspace(1, 0, fade)

    return wave


def chord_sound(freqs, duration, volume):
    audio = np.zeros(int(SAMPLE_RATE * duration), dtype=np.float64)
    for f in freqs:
        audio += piano_note(f, duration)

    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio * (0.85 * volume / peak)

    audio_i16 = (audio * 32767).astype(np.int16)

    if MIXER_CHANNELS == 1:
        arr = audio_i16
    else:
        arr = np.column_stack([audio_i16] * MIXER_CHANNELS)

    return pygame.sndarray.make_sound(np.ascontiguousarray(arr))


# UI

BG      = "#0f1115"
SURFACE = "#1a1d23"
ACCENT  = "#5b9ee0"
TEXT    = "#e8e8ea"
MUTED   = "#8a8e96"

CAT_BG = {
    'major': "#252a31",
    'minor': "#2b2536",
    'dim':   "#312727",
    'aug':   "#273127",
}

CAT_HOVER = {
    'major': "#2f353d",
    'minor': "#382f44",
    'dim':   "#3d3232",
    'aug':   "#323d32",
}


class ChordApp:
    def __init__(self, root):
        self.root = root
        root.title("Chord Player")
        root.configure(bg=BG)
        root.resizable(False, False)

        # Header
        header = tk.Frame(root, bg=BG)
        header.pack(fill="x", padx=24, pady=(20, 12))

        tk.Label(
            header, text="Chord Player",
            font=("Segoe UI Light", 24),
            bg=BG, fg=TEXT,
        ).pack(anchor="w")

        tk.Label(
            header, text="Tap any chord. Adjust sustain to taste.",
            font=("Segoe UI", 10),
            bg=BG, fg=MUTED,
        ).pack(anchor="w", pady=(2, 0))

        # Controls
        controls_outer = tk.Frame(root, bg=BG)
        controls_outer.pack(fill="x", padx=24, pady=(0, 16))

        controls = tk.Frame(controls_outer, bg=SURFACE)
        controls.pack(fill="x", ipady=12, ipadx=18)

        self._build_slider(controls, "Sustain", 1, 10, 5.0, "sustain_var", "s")
        self._build_slider(controls, "Volume", 0, 1, 0.7, "volume_var", "")

        # Chord grid
        grid_frame = tk.Frame(root, bg=BG)
        grid_frame.pack(padx=24, pady=(0, 16))

        # Column headers
        header_row = tk.Frame(grid_frame, bg=BG)
        header_row.pack(fill="x", pady=(0, 4))
        tk.Frame(header_row, width=36, bg=BG).pack(side="left")
        for suffix, _, _ in CHORD_TYPES:
            label = suffix if suffix else "maj"
            tk.Label(
                header_row, text=label,
                width=8, bg=BG, fg=MUTED,
                font=("Segoe UI", 9),
            ).pack(side="left", padx=2)

        # Note rows
        for note in NOTES:
            row = tk.Frame(grid_frame, bg=BG)
            row.pack(fill="x", pady=1)

            tk.Label(
                row, text=note,
                width=4, bg=BG, fg=MUTED,
                font=("Segoe UI Semibold", 11),
                anchor="e",
            ).pack(side="left", padx=(0, 6))

            for suffix, intervals, cat in CHORD_TYPES:
                self._build_chord_button(row, note, suffix, intervals, cat)

        # Status bar
        self.status = tk.Label(
            root,
            text=f"Ready  \u2022  audio at {MIXER_FREQ} Hz, {MIXER_CHANNELS} ch",
            bg=BG, fg=MUTED, font=("Segoe UI", 9), anchor="w",
        )
        self.status.pack(fill="x", padx=24, pady=(0, 14))

    def _build_slider(self, parent, label, lo, hi, default, var_name, unit):
        wrap = tk.Frame(parent, bg=SURFACE)
        wrap.pack(side="left", padx=14)

        tk.Label(wrap, text=label, bg=SURFACE, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")

        var = tk.DoubleVar(value=default)
        setattr(self, var_name, var)

        row = tk.Frame(wrap, bg=SURFACE)
        row.pack()

        slider = tk.Scale(
            row, from_=lo, to=hi, resolution=0.1,
            orient="horizontal",
            variable=var,
            bg=SURFACE, fg=TEXT,
            troughcolor=BG,
            activebackground=ACCENT,
            highlightthickness=0,
            bd=0,
            sliderrelief="flat",
            showvalue=False,
            length=180,
        )
        slider.pack(side="left")

        val_label = tk.Label(
            row, text=f"{default:.1f}{unit}",
            bg=SURFACE, fg=TEXT, width=5,
            font=("Segoe UI", 10),
        )
        val_label.pack(side="left", padx=(8, 0))

        var.trace_add(
            "write",
            lambda *a: val_label.config(text=f"{var.get():.1f}{unit}"),
        )

    def _build_chord_button(self, parent, note, suffix, intervals, cat):
        base_color = CAT_BG[cat]
        hover_color = CAT_HOVER[cat]
        label = note + suffix

        btn = tk.Button(
            parent,
            text=label,
            bg=base_color, fg=TEXT,
            font=("Segoe UI", 10),
            width=8, height=2,
            bd=0, highlightthickness=0,
            relief="flat",
            activebackground=ACCENT,
            activeforeground="#ffffff",
            cursor="hand2",
        )
        btn.pack(side="left", padx=2)

        btn.is_hovering = False

        def on_enter(e):
            btn.is_hovering = True
            btn.config(bg=hover_color)

        def on_leave(e):
            btn.is_hovering = False
            btn.config(bg=base_color)

        def on_click():
            self._play(note, suffix, intervals)
            btn.config(bg=ACCENT)
            btn.after(
                140,
                lambda: btn.config(bg=hover_color if btn.is_hovering else base_color),
            )

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        btn.config(command=on_click)

    def _play(self, note, suffix, intervals):
        try:
            duration = float(self.sustain_var.get())
            volume = float(self.volume_var.get())
            freqs = chord_freqs(note, intervals)
            sound = chord_sound(freqs, duration, volume)
            sound.play()
            self.status.config(
                text=f"Playing {note}{suffix}  \u2022  {len(freqs)} notes  \u2022  {duration:.1f}s"
            )
        except Exception as e:
            self.status.config(text=f"Error: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ChordApp(root)
    root.mainloop()