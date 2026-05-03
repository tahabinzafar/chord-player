# chord-player

App for playing chords on a laptop.

## Run it

```
pip install pygame numpy
python app.py
```

## What it does

96 chords laid out as a grid: 12 root notes (C through B, sharps included) across 8 chord types (major, minor, 7, maj7, m7, dim, sus4, aug). Click to play.

Two sliders at the top: sustain (1 to 10 seconds) and volume. Chords overlap when you click a new one before the last has faded, so you can hear a progression ring into each other.

## Sound

Each note is synthesized in Python from six stacked harmonics, each decaying at its own rate. Higher harmonics fade faster than the fundamental, which is roughly what real piano strings do.
