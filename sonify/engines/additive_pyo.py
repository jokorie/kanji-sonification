"""
Additive synthesis engine using pyo.

Real-time procedural synthesis with controllable oscillators.
"""

import time
from typing import Dict, Any, Optional

from pyo import *

from sonify.engines.base import Sonifier
from sonify.features.kinematics import StrokeFeatures, PointFeatures
from sonify.mapping.pitch_maps import y_to_pitch, speed_to_vibrato_depth, speed_to_vibrato_rate
from sonify.mapping.dynamics_maps import force_to_amplitude, x_to_pan


class AdditiveSonifier(Sonifier):
    """
    Additive synthesis sonifier using pyo.
    
    Maps features to synthesis parameters:
    - Pitch ← Y position (inverted: up = high)
    - Amplitude ← Force/pressure
    - Pan ← X position
    - Vibrato ← Speed
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # Configuration with defaults
        self.sample_rate = self.config.get('sample_rate', 44100)
        self.buffer_size = self.config.get('buffer_size', 512)
        self.min_freq = self.config.get('min_freq', 220.0)  # A3
        self.max_freq = self.config.get('max_freq', 880.0)  # A5
        self.attack_time = self.config.get('attack', 0.01)
        self.release_time = self.config.get('release', 0.05)
        self.max_speed = self.config.get('max_speed', 1.0)
        self.vibrato_max_depth = self.config.get('vibrato_depth', 8.0)
        self.vibrato_min_rate = self.config.get('vibrato_min_rate', 3.0)
        self.vibrato_max_rate = self.config.get('vibrato_max_rate', 7.0)
        self.global_gain = self.config.get('gain', 0.3)
        
        # pyo objects (initialized in initialize())
        self.server = None
        self.osc = None
        self.freq_sig = None
        self.freq_sig_raw = None
        self.amp_sig = None
        self.amp_sig_raw = None
        self.vibrato_lfo = None
        self.vibrato_depth_sig = None
        self.vibrato_depth_sig_raw = None
        self.vibrato_rate_sig = None
        self.vibrato_rate_sig_raw = None
        self.pan_sig = None
        self.pan_sig_raw = None
        self.panned_osc = None
        self.output = None
        self.output_left = None
        self.output_right = None
        
        # State
        self.current_pitch = self.min_freq
        self.current_amp = 0.0
        self.current_pan = 0.5
        self.in_stroke = False
        
    def initialize(self):
        """Initialize pyo server and synthesis graph."""
        if self.is_active:
            return
        
        # Boot server
        self.server = Server(sr=self.sample_rate, buffersize=self.buffer_size)
        self.server.boot()
        self.server.start()
        
        # Build synthesis graph with proper panning and vibrato
        # Frequency control with smoothing
        self.freq_sig_raw = Sig(self.min_freq)
        self.freq_sig = Port(self.freq_sig_raw, risetime=0.01, falltime=0.01)

        # Vibrato
        self.vibrato_depth_sig_raw = Sig(0.0)
        self.vibrato_depth_sig = Port(self.vibrato_depth_sig_raw, risetime=0.005, falltime=0.005)
        self.vibrato_rate_sig_raw = Sig(5.0)
        self.vibrato_rate_sig = Port(self.vibrato_rate_sig_raw, risetime=0.005, falltime=0.005)

        self.vibrato_lfo = Sine(freq=self.vibrato_rate_sig, mul=self.vibrato_depth_sig)

        # Oscillator with vibrato modulation
        modulated_freq = self.freq_sig + self.vibrato_lfo
        self.osc = Sine(freq=modulated_freq, mul=1)

        # Amplitude control with smoothing
        self.amp_sig_raw = Sig(0.0)
        self.amp_sig = Port(self.amp_sig_raw, risetime=0.005, falltime=0.005)

        shaped_osc = self.osc * self.amp_sig

        # Pan control with smoothing (0 = left, 1 = right)
        # Using Port for smooth panning transitions
        # Keep reference to raw Sig for direct updates
        self.pan_sig_raw = Sig(0.5)
        self.pan_sig = Port(self.pan_sig_raw, risetime=0.01, falltime=0.01)
        
        # Manual panning with more pronounced effect
        # Apply symmetric curve to make panning more extreme while keeping both channels active
        # Use a symmetric power curve centered at 0.5 to avoid left/right bias
        # Formula: For pan in [0, 0.5]: curve = 2 * pan^2
        #          For pan in [0.5, 1]: curve = 0.5 + 2 * (pan - 0.5)^2
        # We implement this by calculating distance from center, squaring, then restoring
        centered = self.pan_sig - 0.5  # Center around 0: [-0.5, 0.5]
        abs_centered = Abs(centered)  # Distance from center: [0, 0.5]
        scaled_distance = abs_centered * 2.0  # Scale to [0, 1]
        powered_distance = Pow(scaled_distance, 4.0)  # Higher power: [0, 1]

        # Restore direction: if centered < 0, subtract; if centered >= 0, add
        # Use: curve = 0.5 + sign(centered) * 0.5 * squared_distance
        # Since we can't easily get sign, we use: centered / (abs_centered + epsilon)
        # Add small epsilon to avoid division by zero
        epsilon = Sig(0.0001)  # Tiny value to avoid division by zero
        sign_factor = centered / (abs_centered + epsilon)  # Approximate sign: [-1, 1]
        
        pan_curve = sign_factor * scaled_distance
        
        # Left channel: more gain when pan is low (near 0)
        # Right channel: more gain when pan is high (near 1)
        # Keep minimum level of 0.1 (10%) in opposite channel so both channels always have sound
        # This makes panning more pronounced while still keeping some presence in both channels
        # Use clamping to ensure gains stay in valid range [0.02, 1.0]
        left_gain_raw = (-1.0 * pan_curve) * 0.60 + 0.40  # 0.02 to 1.0
        right_gain_raw = pan_curve * 0.60 + 0.40  # 0.02 to 1.0
        # Clamp to ensure exact bounds
        left_gain = Clip(left_gain_raw, min=0.02, max=1.0)
        right_gain = Clip(right_gain_raw, min=0.02, max=1.0)
        
        # Split into left and right channels
        left_channel = shaped_osc * left_gain
        right_channel = shaped_osc * right_gain
        
        # Apply compression to each channel
        left_limited = Compress(
            left_channel,
            thresh=-12,
            ratio=4,
            knee=0.5,
            mul=self.global_gain
        )
        right_limited = Compress(
            right_channel,
            thresh=-12,
            ratio=4,
            knee=0.5,
            mul=self.global_gain
        )
        
        # Output to stereo channels (0 = left, 1 = right)
        self.output_left = left_limited.out(chnl=0)
        self.output_right = right_limited.out(chnl=1)
        self.panned_osc = [left_limited, right_limited]  # Keep reference for compatibility
        
        self.is_active = True
        print("AdditiveSonifier: Initialized")
    
    def shutdown(self):
        """Shutdown pyo server."""
        if not self.is_active:
            return
        
        if self.server:
            self.server.stop()
            time.sleep(0.1)
            self.server.shutdown()
        
        self.is_active = False
        print("AdditiveSonifier: Shutdown")
    
    def begin_kanji(self, metadata: Dict[str, Any]):
        """Begin rendering a kanji."""
        print(f"AdditiveSonifier: Begin kanji {metadata.get('id', 'unknown')}")
        # Reset state
        self.current_amp = 0.0
        if self.amp_sig_raw:
            self.amp_sig_raw.value = 0.0
    
    def start_stroke(self, stroke_features: StrokeFeatures):
        """Start a new stroke."""
        self.current_stroke_id = stroke_features.stroke_id
        self.in_stroke = True
        print(f"AdditiveSonifier: Start stroke {stroke_features.stroke_id}")
        
        # Set pan to first point's position immediately (before Port smoothing)
        # This ensures each stroke starts with correct pan position, not transitioning
        # from the previous stroke's end position
        if stroke_features.points and self.pan_sig_raw:
            first_point = stroke_features.points[0]
            initial_pan = first_point.xN
            self.pan_sig_raw.value = initial_pan
        
        # Quick attack - amplitude will be set in update() method
        # We don't need setTime since we're using direct control
    
    def update(self, point_features: PointFeatures):
        """Update synthesis parameters from point features."""
        if not self.is_active or not self.in_stroke:
            return
        
        # Map Y to pitch (inverted: up = high pitch)
        pitch = y_to_pitch(
            point_features.yN,
            min_freq=self.min_freq,
            max_freq=self.max_freq,
            invert=True
        )
        
        # Map force to amplitude
        amp = force_to_amplitude(
            point_features.force,
            min_amp=0.5,
            max_amp=1.0,
            exponent=1.0
        )

        # Map X to pan [0, 1] -> [0, 1] for pyo Pan
        pan = point_features.xN

        # Map speed to vibrato
        vib_depth = speed_to_vibrato_depth(
            point_features.speed,
            max_speed=self.max_speed,
            max_depth=self.vibrato_max_depth
        )
        vib_rate = speed_to_vibrato_rate(
            point_features.speed,
            max_speed=self.max_speed,
            min_rate=self.vibrato_min_rate,
            max_rate=self.vibrato_max_rate
        )


        # Update pyo signals (update raw Sig objects, Port will smooth)
        if self.freq_sig_raw:
            self.freq_sig_raw.value = pitch
        if self.amp_sig_raw:
            self.amp_sig_raw.value = amp
        if self.pan_sig_raw:
            self.pan_sig_raw.value = pan
        if self.vibrato_depth_sig_raw:
            self.vibrato_depth_sig_raw.value = vib_depth
        if self.vibrato_rate_sig_raw:
            self.vibrato_rate_sig_raw.value = vib_rate
        
        self.current_pitch = pitch
        self.current_amp = amp
        self.current_pan = pan
    
    def end_stroke(self):
        """End the current stroke."""
        if not self.in_stroke:
            return

        print(f"AdditiveSonifier: End stroke {self.current_stroke_id}")

        # Quick release
        if self.amp_sig_raw:
            self.amp_sig_raw.value = 0.0

        self.in_stroke = False
        self.current_stroke_id = None
    
    def end_kanji(self):
        """End the kanji rendering."""
        print("AdditiveSonifier: End kanji")
        
        # Ensure silence
        if self.amp_sig_raw:
            self.amp_sig_raw.value = 0.0
    
    def record_start(self, duration: float, filepath: str):
        """
        Start recording to file.
        
        Args:
            duration: Duration to record (seconds)
            filepath: Output WAV file path
        """
        if self.server and self.is_active:
            self.server.recstart(filepath)
    
    def record_stop(self):
        """Stop recording."""
        if self.server and self.is_active:
            self.server.recstop()
    
    def save(self, filepath: str):
        """
        This is a real-time engine, use record_start/record_stop instead.
        """
        raise NotImplementedError(
            "AdditiveSonifier is real-time. Use record_start() before rendering "
            "and record_stop() after to save audio."
        )


class OfflineAdditiveSonifier(AdditiveSonifier):
    """
    Offline rendering version of AdditiveSonifier.
    
    Uses pyo's offline processing mode to render to a file without real-time playback.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.output_filepath = None
        self.total_duration = 0.0
    
    def initialize(self):
        """Initialize pyo server in offline mode."""
        if self.is_active:
            return
        
        # Create server in offline mode
        self.server = Server(sr=self.sample_rate, buffersize=self.buffer_size, duplex=0)
        self.server.boot()
        # Don't start in offline mode - we'll use recstart/recstop
        
        # Build synthesis graph (same as parent)
        # Frequency control
        self.freq_sig = Port(Sig(self.min_freq))

        # Vibrato
        self.vibrato_depth_sig = Port(Sig(0.0))
        self.vibrato_rate_sig = Port(Sig(5.0))

        self.vibrato_lfo = Sine(freq=self.vibrato_rate_sig, mul=self.vibrato_depth_sig)

        # Oscillator
        modulated_freq = self.freq_sig + self.vibrato_lfo
        self.osc = Sine(freq=modulated_freq, mul=1)

        # Amplitude
        self.amp_sig = Sig(0.0)

        shaped_osc = self.osc * self.amp_sig

        # Pan
        self.pan_sig = Port(Sig(0.5))
        self.panned_osc = Pan(shaped_osc, pan=self.pan_sig)
        
        # Output with limiter
        limited = Compress(
            self.panned_osc,
            thresh=-12,
            ratio=4,
            knee=0.5,
            mul=self.global_gain
        )
        
        self.output = limited.out()
        
        self.is_active = True
        print("OfflineAdditiveSonifier: Initialized (offline mode)")

