# Architecture Documentation

## System Overview

The Kanji Sonifier transforms Japanese calligraphy strokes into audio through a modular pipeline:

```
PencilKit JSON → Feature Extraction → Sonifier Engine → Audio/MIDI Output
```

## Module Structure

### 1. I/O Module (`sonify/io/`)

**Purpose**: Load and save stroke data

**Key Components**:

- `load_pencilkit.py`: Parses PencilKit JSON exports
  - `StrokePoint`: Individual point with x, y, force, azimuth, altitude, timestamp
  - `Stroke`: Sequence of points (pen-down to pen-up)
  - `Drawing`: Complete kanji with canvas metadata and strokes
  - `load_pencilkit_json()`: Main loader function

**Data Flow**:

```
JSON file → Drawing object → Features → Audio
```

### 2. Features Module (`sonify/features/`)

**Purpose**: Extract kinematic features from stroke data

**Components**:

#### `normalize.py`

- `normalize_coordinates()`: Convert absolute coordinates to [0, 1]
- `center_normalize()`: Center content in canvas with margin
- `get_bounding_box()`: Compute content bounds

#### `kinematics.py`

- **Point Features**: Computed per point
  - Speed (smoothed with EMA)
  - Direction (radians)
  - Curvature (change in direction per unit length)
- **Stroke Features**: Computed per stroke

  - Duration
  - Mean/max speed
  - Mean force
  - Dominant direction (8-way: up, down, left, right, diagonals)
  - Curvature statistics

- `extract_stroke_features()`: Process single stroke
- `extract_drawing_features()`: Process entire drawing

**Algorithms**:

- **Speed**: `v = hypot(dx, dy) / dt` with EMA smoothing
- **Direction**: `θ = atan2(dy, dx)`
- **Curvature**: `κ = |dθ| / ds` (change in angle per arc length)
- **EMA Smoothing**: `y[i] = α·x[i] + (1-α)·y[i-1]`

### 3. Mapping Module (`sonify/mapping/`)

**Purpose**: Map features to audio parameters

#### `pitch_maps.py`

- `y_to_pitch()`: Y position → frequency (Hz)
- `xy_to_pitch()`: Weighted combination of X and Y
- `speed_to_vibrato_depth()`: Speed → vibrato depth
- `speed_to_vibrato_rate()`: Speed → vibrato rate
- MIDI conversion utilities

#### `dynamics_maps.py`

- `force_to_amplitude()`: Pressure → amplitude
- `x_to_pan()`: X position → stereo pan [-1, 1]
- `speed_to_brightness()`: Speed → timbral brightness
- `curvature_to_roughness()`: Curvature → roughness/noise
- `adsr_envelope()`: Attack-Decay-Sustain-Release function
- `soft_clip()`: Soft saturation/limiting

**Default Mappings (v1 - Objective)**:

```
Pitch      ← Y position (inverted: up = high)
Amplitude  ← Force/pressure (exponential scaling)
Pan        ← X position (left-right)
Vibrato    ← Speed (depth and rate)
```

### 4. Engines Module (`sonify/engines/`)

**Purpose**: Synthesis and audio output

#### Base Interface (`base.py`)

All engines implement the `Sonifier` abstract class:

```python
class Sonifier(ABC):
    def initialize()          # Boot audio system
    def shutdown()            # Clean shutdown
    def begin_kanji(metadata) # Start new kanji
    def start_stroke(features)# Begin stroke
    def update(point_features)# Update per point
    def end_stroke()          # End stroke
    def end_kanji()           # Finish kanji
```

**Lifecycle**:

```
initialize()
  ↓
begin_kanji()
  ↓
for each stroke:
    start_stroke()
    for each point:
        update()
    end_stroke()
  ↓
end_kanji()
  ↓
shutdown()
```

#### Additive Synthesis (`additive_pyo.py`)

**Technology**: `pyo` (Python DSP library)

**Signal Chain**:

```
Sine oscillator → Vibrato (LFO) → Amplitude envelope → Pan → Limiter → Output
```

**Parameters**:

- Frequency: Smoothed control with 10ms ramp
- Amplitude: 5ms smoothing
- Vibrato: Sine LFO with depth and rate control
- Pan: 10ms smoothing
- Compression: Threshold -12dB, ratio 4:1

**Configuration**:

- Sample rate: 44100 Hz
- Buffer size: 512 samples
- Attack: 10ms
- Release: 50ms

#### MIDI Output (`midi_mido.py`)

**Technology**: `mido` (MIDI library)

**Two Modes**:

1. **MidiSonifier**: Renders to MIDI file

   - Each stroke = MIDI note
   - Pitch from initial Y position
   - Velocity from initial force
   - CCs for continuous control:
     - CC 11 (Expression): Force
     - CC 10 (Pan): X position
     - CC 74 (Brightness): Speed

2. **MidiPortSonifier**: Real-time output to MIDI port
   - Same mapping, live output

### 5. Pipeline Module (`sonify/pipeline/`)

**Purpose**: Orchestrate the rendering process

#### `render_offline.py`

**Functions**:

- `load_config()`: Load YAML configuration
- `create_sonifier()`: Factory for sonifier instances
- `render_kanji()`: Main rendering function

  - Loads JSON
  - Extracts features
  - Initializes sonifier
  - Processes strokes/points
  - Saves output

- `render_with_timesync()`: Real-time synchronized rendering

  - Waits for actual timestamps during playback
  - More accurate timing

- `batch_render()`: Process multiple files

**Usage**:

```python
render_kanji(
    input_json="examples/水.json",
    output_path="output/water.wav",
    config_path="presets/default.yaml",
    playback=True
)
```

## Configuration System

YAML-based configuration with presets in `presets/`:

### Available Presets

1. **default.yaml**: Balanced, recognizable mappings

   - Pitch range: A3 (220 Hz) to A5 (880 Hz)
   - Moderate vibrato
   - 10ms attack, 50ms release

2. **wide_range.yaml**: Dramatic pitch range

   - A2 (110 Hz) to A6 (1760 Hz)
   - Strong vibrato
   - Snappier envelope

3. **subtle.yaml**: Gentle, narrow range

   - E4 (330 Hz) to E5 (660 Hz)
   - Minimal vibrato
   - Smooth envelope

4. **midi_default.yaml**: MIDI output
   - Standard MIDI CC assignments
   - 120 BPM, 480 ticks/beat

### Configuration Parameters

```yaml
# Engine selection
engine: additive # or 'midi', 'dummy'

# Audio settings
sample_rate: 44100
buffer_size: 512

# Pitch mapping
min_freq: 220.0
max_freq: 880.0

# Envelope
attack: 0.01
release: 0.05

# Dynamics
gain: 0.3

# Vibrato
max_speed: 1.0
vibrato_depth: 8.0
vibrato_min_rate: 3.0
vibrato_max_rate: 7.0
```

## Data Formats

### Input: PencilKit JSON

```json
{
  "canvas": {
    "width": 1024,
    "height": 1024,
    "ppi": 264
  },
  "metadata": {
    "id": "水",
    "meaning": "water"
  },
  "strokes": [
    {
      "id": 1,
      "points": [
        {
          "x": 512,
          "y": 200,
          "force": 0.5,
          "azimuth": 0.0,
          "altitude": 1.2,
          "t": 0.0
        }
      ]
    }
  ]
}
```

### Output

**Audio**: WAV files (16-bit PCM, stereo)
**MIDI**: Standard MIDI files (Format 0, single track)

## Extension Points

### Adding New Mappings

Create custom mapping functions in `sonify/mapping/`:

```python
def custom_pitch_map(feature_value, config):
    # Your mapping logic
    return frequency_hz
```

Update preset YAML to use new mappings.

### Adding New Engines

Implement the `Sonifier` interface:

```python
from sonify.engines.base import Sonifier

class CustomSonifier(Sonifier):
    def initialize(self):
        # Setup your audio system
        pass

    def update(self, point_features):
        # Process point features
        pass

    # ... implement other methods
```

Register in `create_sonifier()` factory.

### Adding New Features

Add feature extraction in `sonify/features/kinematics.py`:

```python
def compute_custom_feature(points):
    # Your feature extraction
    return feature_values
```

Add to `PointFeatures` or `StrokeFeatures` dataclasses.

## Performance Considerations

**Real-time Constraints**:

- Update rate: ~60 Hz (typical drawing rate)
- Audio buffer: 512-1024 samples
- Latency: ~10-20ms

**Optimization Strategies**:

- EMA smoothing reduces high-frequency noise
- Pre-computation of stroke-level features
- Efficient pyo signal graph (single oscillator)
- Minimal Python overhead in audio loop

**Memory Usage**:

- Typical kanji: <100 KB (JSON + features)
- Audio buffer: <10 MB per minute
- pyo server: ~50 MB overhead

## Testing Strategy

**Unit Tests** (`sonify/tests/`):

- Feature extraction accuracy
- Coordinate normalization
- Mapping functions

**System Test** (`test_system.py`):

- End-to-end pipeline without audio output
- DummySonifier for fast verification

**Integration Test** (`demo.py`):

- Real audio output
- Manual verification of sound quality

## Future Architecture (v2+)

**Phase 2**: Stroke Order Encoding

- Per-stroke timbral shifts
- Harmonic partials based on stroke index
- Percussive onset markers

**Phase 3**: Live Streaming

- OSC server for real-time input
- Adaptive buffering
- Multi-client support

**Phase 4**: Metaphorical Mappings

- Granular synthesis with sample banks
- Semantic meaning integration
- Context-aware timbres

**Phase 5**: Machine Learning

- DDSP-based synthesis
- Learned feature-to-timbre mappings
- Automatic kanji recognition
