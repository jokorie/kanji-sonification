"""
Offline rendering pipeline.

Loads a kanji JSON, extracts features, and renders to audio/MIDI.
"""

import time
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any
import yaml

from sonify.io.load_pencilkit import load_pencilkit_json
from sonify.features.kinematics import extract_drawing_features
from sonify.engines.base import Sonifier


@dataclass
class Config:
    """Configuration for kanji sonification."""
    engine: str = 'additive'
    sample_rate: int = 44100
    min_freq: float = 220.0
    max_freq: float = 880.0
    attack: float = 0.01
    release: float = 0.05
    gain: float = 0.3
    max_speed: float = 1.0
    vibrato_depth: float = 8.0
    vibrato_min_rate: float = 3.0
    vibrato_max_rate: float = 7.0
    rate_multiplier: float = 1.0  # Multiply playback rate (2.0 = 2x slower, 0.5 = 2x faster)
    playback: bool = True
    duration_padding: float = 0.5
    output_dir: str = 'output'
    
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create Config from dictionary, ignoring unknown keys."""
        # Get all field names from the dataclass
        field_names = {f.name for f in cls.__dataclass_fields__.values()}
        # Only include keys that are valid fields
        filtered_data = {k: v for k, v in data.items() if k in field_names}
        return cls(**filtered_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Config to dictionary."""
        return {
            'engine': self.engine,
            'sample_rate': self.sample_rate,
            'min_freq': self.min_freq,
            'max_freq': self.max_freq,
            'attack': self.attack,
            'release': self.release,
            'gain': self.gain,
            'max_speed': self.max_speed,
            'vibrato_depth': self.vibrato_depth,
            'vibrato_min_rate': self.vibrato_min_rate,
            'vibrato_max_rate': self.vibrato_max_rate,
            'rate_multiplier': self.rate_multiplier,
            'playback': self.playback,
            'duration_padding': self.duration_padding,
        }


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to YAML config file, or None for defaults
        
    Returns:
        Config instance
    """
    # Start with default Config
    default_config = Config()
    
    # Load user config from file if provided
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r') as f:
            user_config = yaml.safe_load(f) or {}
        # Update default config with user values
        user_dict = default_config.to_dict()
        user_dict.update(user_config)
        return Config.from_dict(user_dict)
    
    return default_config


def create_sonifier(config: Config) -> Sonifier:
    """
    Create a sonifier instance from config.
    
    Args:
        config: Config instance
    
    Returns:
        Sonifier instance
    """
    # Convert Config to dict for engine constructors (they expect dict)
    config_dict = config.to_dict()
    
    if config.engine == 'additive':
        # For now, always use regular AdditiveSonifier
        # TODO: Use OfflineAdditiveSonifier for better offline rendering
        from sonify.engines.additive_pyo import AdditiveSonifier
        return AdditiveSonifier(config_dict)
    elif config.engine == 'midi':
        from sonify.engines.midi_mido import MidiSonifier
        return MidiSonifier(config_dict)
    elif config.engine == 'dummy':
        from sonify.engines.base import DummySonifier
        return DummySonifier(config_dict)
    else:
        raise ValueError(f"Unknown engine type: {config.engine}")


def render_kanji(input_json: str,
                 config: Config,
                 output_path: str) -> None:
    """
    Render a kanji to audio or MIDI.
    
    Args:
        input_json: Path to PencilKit JSON file
        config: Config instance (required)
        playback: Whether to play audio in real-time (overrides config.playback)
        duration_padding: Extra time (seconds) to pad at the end (overrides config.duration_padding)
    """
    
    print(f"Loading kanji from: {input_json}")
    
    # Load and process drawing
    drawing = load_pencilkit_json(input_json)
    features = extract_drawing_features(drawing, normalize=True)
    
    print(f"Kanji: {drawing.metadata.get('id', 'unknown')}")
    print(f"Strokes: {features.num_strokes}")
    print(f"Duration: {features.total_duration:.2f}s")
    
    # Create sonifier
    sonifier = create_sonifier(config)
    
    try:
        # Initialize engine
        sonifier.initialize()
        
        # Start recording if applicable
        if config.engine == 'additive':
            # For pyo, start recording
            total_duration = (features.total_duration * config.rate_multiplier) + config.duration_padding
            print(f"Recording to: {output_path} ({total_duration:.2f}s, rate: {config.rate_multiplier}x)")
            sonifier.record_start(total_duration, output_path)
        
        # Begin kanji
        metadata = {
            'id': drawing.metadata.get('id', 'unknown'),
            'num_strokes': features.num_strokes,
            'duration': features.total_duration
        }
        sonifier.begin_kanji(metadata)
        
        # Track time for proper synchronization
        start_time = time.time()
                
        # Process each stroke
        for stroke_features in features.strokes:
            sonifier.start_stroke(stroke_features)
            
            # Process each point
            for point_features in stroke_features.points:
                # Wait until we reach this point's timestamp (multiplied by rate)
                if config.engine == 'additive':
                    target_time = point_features.t * config.rate_multiplier
                    current_elapsed = time.time() - start_time
                    sleep_duration = target_time - current_elapsed
                    if sleep_duration > 0:
                        time.sleep(sleep_duration)
                
                sonifier.update(point_features)
            
            sonifier.end_stroke()
            
            # Brief pause after stroke (for audio processing)
            if config.engine == 'additive':
                time.sleep(0.01 * config.rate_multiplier)
        
        # End kanji
        sonifier.end_kanji()
        
        # Padding for audio tail
        if config.engine == 'additive':
            time.sleep(config.duration_padding)   
            sonifier.record_stop()
        elif config.engine == 'midi':
            # MIDI saves on shutdown
            sonifier.save(output_path)
        
    finally:
        # Clean shutdown
        sonifier.shutdown()
    
    print("Rendering complete!")
    print(f"Saved to: {output_path}")


def batch_render(input_files: list,
                 config: Config) -> None:
    """
    Render multiple kanji files.
    
    Args:
        input_files: List of input JSON file paths
        config: Config instance (required)
        output_dir: Output directory for rendered files (default: 'output')
        playback: Whether to play each file (overrides config.playback)
    """
    
    os.makedirs(config.output_dir, exist_ok=True)
    
    ext = '.wav' if config.engine == 'additive' else '.mid'
    
    for input_file in input_files:
        basename = os.path.splitext(os.path.basename(input_file))[0]
        output_file = os.path.join(config.output_dir, basename + ext)
        
        print(f"\n{'='*60}")
        print(f"Rendering: {basename}")
        print(f"{'='*60}\n")
        
        try:
            # Create a copy of config with output_path for this file
            render_kanji(
                input_json=input_file,
                config=config,
                output_path=output_file)
        except Exception as e:
            print(f"Error rendering {input_file}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"Batch rendering complete! Files saved to: {config.output_dir}/ directory")
    print(f"{'='*60}")