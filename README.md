# Kanji Sonifier

A stroke-by-stroke sonification system for Japanese calligraphy that transforms writing gestures into recognizable audio.

## Vision

While writing a kanji, the system generates audio that reflects stroke order and motion so the user can learn and recall the character "by its sound." Each stroke becomes a recognizable sonic gesture; the complete kanji "plays" like a short motif.

## Architecture

```
[Input] → [Stroke Capture] → [Feature Extraction] → [Sonifier API] → [Audio I/O]
                                  ↑                                ↑
                             Mapping presets                 Engines (Additive, MIDI, OSC)
```

### Modular Components

- **Input**: PencilKit JSON exports with per-point stroke data
- **Feature Extraction**: Velocity, direction, curvature, stroke segmentation
- **Sonifier API**: Pluggable interface for different synthesis engines
- **Audio Engines**:
  - Additive synthesis (pyo)
  - MIDI output (mido)
  - OSC routing (python-osc)

## Installation

```bash
pip install -r requirements.txt
```

**Note**: `pyo` requires PortAudio. On Linux:

```bash
sudo apt-get update && sudo apt-get install -y \
    portaudio19-dev \
    libsndfile1-dev \
    liblo-dev \
    libportmidi-dev \
    python3-dev \
    build-essential \
    libjack-dev
sudo apt-get install portaudio19-dev python3-dev
```

On macOS:

```bash
brew install portaudio
```

## Quick Start

```python
from sonify.pipeline.render_offline import render_kanji
from sonify.engines.additive_pyo import AdditiveSonifier

# Render a kanji to audio
render_kanji(
    input_json="examples/水.json",
    output_wav="output/水.wav",
    preset="presets/default.yaml"
)
```

## Project Structure

```
sonify/
  io/              # PencilKit JSON loading
  features/        # Kinematics and feature extraction
  mapping/         # Feature-to-audio mappings
  engines/         # Synthesis engines (pyo, MIDI, OSC)
  pipeline/        # Offline rendering and live streaming
  tests/           # Unit tests
examples/          # Example kanji JSON files
presets/           # Mapping configuration files
```

## Data Format

### Input JSON (PencilKit Export)

```json
{
  "canvas": { "width": 2048, "height": 1536, "ppi": 264 },
  "strokes": [
    {
      "id": 1,
      "points": [
        {
          "x": 1023.2,
          "y": 410.7,
          "force": 0.55,
          "azimuth": 0.61,
          "altitude": 1.05,
          "t": 0.0
        }
      ]
    }
  ]
}
```

## Mapping Presets (v1)

- **Pitch** ← Y position (higher on screen → higher pitch)
- **Amplitude** ← pressure (heavier pressure → louder)
- **Vibrato** ← instantaneous speed (faster → more modulation)
- **Pan** ← X position (left/right spatial cue)
- **Stroke boundaries** → note boundaries with audible onsets
- **Stroke index** → timbral shifts for stroke order recognition

## Development Roadmap

- [x] Phase 0: Groundwork (schema, loader, features)
- [x] Phase 1: Minimum audible demo (additive synthesis)
- [ ] Phase 2: Stroke order encoding
- [ ] Phase 3: A/B mapping presets
- [ ] Phase 4: Live streaming scaffold
- [ ] Phase 5: Evaluation hooks

## References

- Hoff, "Sonification of Japanese Calligraphy" (DAFx-18, 2018)
- Apple PencilKit documentation
- pyo: Python DSP module for audio synthesis
