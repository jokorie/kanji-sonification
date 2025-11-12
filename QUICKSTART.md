# Quick Start Guide

## Installation

1. **Install dependencies:**

```bash
pip install -r requirements.txt
```

**Note for Linux users**: `pyo` requires PortAudio:

```bash
sudo apt-get install portaudio19-dev python3-dev
pip install pyo
```

**Note for macOS users**:

```bash
brew install portaudio
pip install pyo
```

## Basic Usage

### 1. Run the Demo

The easiest way to get started is to run the demo script:

```bash
python demo.py
```

This will render the kanji 水 (water) with the default preset and play it back.

### 2. Try Different Kanji

Render specific kanji from the examples:

```bash
# Render 川 (river)
python demo.py --kanji 川

# Render 一 (one)
python demo.py --kanji 一
```

### 3. Try Different Presets

Experiment with different audio mappings:

```bash
# Wide pitch range (more dramatic)
python demo.py --preset wide_range

# Subtle/gentle (narrower range, less vibrato)
python demo.py --preset subtle
```

### 4. Generate MIDI

Create MIDI files for use in your DAW:

```bash
python demo.py --midi
# or
python demo.py --preset midi_default
```

The MIDI file will be saved to `output/水.mid` (or whatever kanji you specify).

### 5. Batch Rendering

Render all example kanji at once:

```bash
python demo.py --batch
```

This will create audio files for all examples in the `output/` directory.

### 6. Save Without Playback

If you just want to save the audio without real-time playback:

```bash
python demo.py --no-playback
```

## Python API Usage

You can also use the API directly in your own scripts:

```python
from sonify.pipeline.render_offline import render_kanji

# Render with default settings
render_kanji(
    input_json="examples/水.json",
    output_path="output/water.wav",
    config_path="presets/default.yaml"
)

# Or with custom config
render_kanji(
    input_json="examples/川.json",
    output_path="output/river.wav",
    config={
        'engine': 'additive',
        'min_freq': 200,
        'max_freq': 1000,
        'gain': 0.4
    }
)
```

## Creating Your Own Kanji Data

To sonify your own calligraphy:

1. Create a JSON file following the PencilKit format (see `examples/水.json` for reference)
2. Each stroke should have an array of points with:
   - `x`, `y`: coordinates
   - `force`: pressure (0-1)
   - `azimuth`, `altitude`: pen angles (radians)
   - `t`: timestamp (seconds)

Example:

```json
{
  "canvas": { "width": 1024, "height": 1024, "ppi": 264 },
  "metadata": { "id": "火", "meaning": "fire" },
  "strokes": [
    {
      "id": 1,
      "points": [
        {
          "x": 512,
          "y": 200,
          "force": 0.5,
          "azimuth": 0,
          "altitude": 1.2,
          "t": 0.0
        },
        {
          "x": 512,
          "y": 400,
          "force": 0.6,
          "azimuth": 0,
          "altitude": 1.2,
          "t": 0.2
        }
      ]
    }
  ]
}
```

Then render it:

```bash
python demo.py --kanji 火
```

## Understanding the Mappings

The default preset uses these mappings:

- **Pitch** ← Y position (up = high, down = low)
- **Amplitude** ← Force/pressure (harder = louder)
- **Pan** ← X position (left-right)
- **Vibrato** ← Speed (faster strokes = more vibrato)

Each stroke is a separate note with attack/release envelopes, making stroke order audible.

## Troubleshooting

**"pyo not available"**: Install PortAudio and pyo (see installation instructions above)

**"mido not available"**: `pip install mido`

**No audio output**: Check your system audio settings and volume

**Audio glitches**: Try increasing buffer size in the config:

```yaml
buffer_size: 1024 # or 2048
```

## Next Steps

- Create custom presets (copy and modify files in `presets/`)
- Implement your own mapping functions in `sonify/mapping/`
- Try the MIDI output with different synths in your DAW
- Experiment with different kanji and drawing styles

For more details, see the main README.md and the source code documentation.
