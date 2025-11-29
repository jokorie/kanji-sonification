"""
Pitch mapping functions.

Maps spatial/kinematic features to pitch (frequency in Hz).
"""

import math
from typing import Optional


def linear_map(value: float, in_min: float, in_max: float, 
               out_min: float, out_max: float) -> float:
    """
    Linear interpolation (lerp) from input range to output range.
    
    Args:
        value: Input value
        in_min, in_max: Input range
        out_min, out_max: Output range
        
    Returns:
        Mapped value (clamped to output range)
    """
    # Normalize to [0, 1]
    if in_max == in_min:
        t = 0.5
    else:
        t = (value - in_min) / (in_max - in_min)
    
    # Clamp
    t = max(0.0, min(1.0, t))
    
    # Map to output
    return out_min + t * (out_max - out_min)


def exponential_map(value: float, in_min: float, in_max: float,
                     out_min: float, out_max: float, exponent: float = 2.0) -> float:
    """
    Exponential mapping (useful for perceptual scaling).
    
    Args:
        value: Input value
        in_min, in_max: Input range
        out_min, out_max: Output range
        exponent: Exponent for curve (>1 = convex, <1 = concave)
        
    Returns:
        Mapped value
    """
    # Normalize to [0, 1]
    if in_max == in_min:
        t = 0.5
    else:
        t = (value - in_min) / (in_max - in_min)
    
    # Clamp
    t = max(0.0, min(1.0, t))
    
    # Apply exponent
    t = t ** exponent
    
    # Map to output
    return out_min + t * (out_max - out_min)


def y_to_pitch(y_normalized: float, min_freq: float = 220.0, max_freq: float = 880.0,
               invert: bool = True) -> float:
    """
    Map Y coordinate to pitch.
    
    Args:
        y_normalized: Y position in [0, 1]
        min_freq: Minimum frequency (Hz)
        max_freq: Maximum frequency (Hz)
        invert: If True, higher Y (down on screen) → lower pitch
        
    Returns:
        Frequency in Hz
    """
    if invert:
        # Invert so up = high pitch
        y_normalized = 1.0 - y_normalized
    
    return linear_map(y_normalized, 0.0, 1.0, min_freq, max_freq)


def xy_to_pitch(x_normalized: float, y_normalized: float,
                y_weight: float = 1.0, x_weight: float = 0.0,
                min_freq: float = 220.0, max_freq: float = 880.0,
                invert_y: bool = True) -> float:
    """
    Map X and Y to pitch with configurable weights.
    
    Args:
        x_normalized: X position [0, 1]
        y_normalized: Y position [0, 1]
        y_weight: Weight for Y contribution (typically 1.0)
        x_weight: Weight for X contribution (typically 0.0-0.1)
        min_freq: Minimum frequency (Hz)
        max_freq: Maximum frequency (Hz)
        invert_y: If True, higher Y (down) → lower pitch
        
    Returns:
        Frequency in Hz
    """
    if invert_y:
        y_normalized = 1.0 - y_normalized
    
    # Weighted combination
    total_weight = y_weight + x_weight
    if total_weight == 0:
        combined = 0.5
    else:
        combined = (y_normalized * y_weight + x_normalized * x_weight) / total_weight
    
    return linear_map(combined, 0.0, 1.0, min_freq, max_freq)

# TODO: unclear
def speed_to_vibrato_depth(speed: float, max_speed: float = 1.0,
                            max_depth: float = 10.0) -> float:
    """
    Map speed to vibrato depth (Hz deviation).
    
    Args:
        speed: Instantaneous speed
        max_speed: Expected maximum speed (for normalization)
        max_depth: Maximum vibrato depth in Hz
        
    Returns:
        Vibrato depth in Hz
    """
    speed_normalized = min(speed / max_speed, 1.0) if max_speed > 0 else 0.0
    return speed_normalized * max_depth

# TODO: unclear
def speed_to_vibrato_rate(speed: float, max_speed: float = 1.0,
                           min_rate: float = 2.0, max_rate: float = 8.0) -> float:
    """
    Map speed to vibrato rate (Hz).
    
    Args:
        speed: Instantaneous speed
        max_speed: Expected maximum speed
        min_rate: Minimum vibrato rate (Hz)
        max_rate: Maximum vibrato rate (Hz)
        
    Returns:
        Vibrato rate in Hz
    """
    speed_normalized = min(speed / max_speed, 1.0) if max_speed > 0 else 0.0
    return linear_map(speed_normalized, 0.0, 1.0, min_rate, max_rate)


def midi_note_to_freq(note: int) -> float:
    """
    Convert MIDI note number to frequency.
    
    Args:
        note: MIDI note (0-127)
        
    Returns:
        Frequency in Hz
    """
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def freq_to_midi_note(freq: float) -> int:
    """
    Convert frequency to nearest MIDI note number.
    
    Args:
        freq: Frequency in Hz
        
    Returns:
        MIDI note (0-127)
    """
    if freq <= 0:
        return 0
    note = 69 + 12 * math.log2(freq / 440.0)
    return max(0, min(127, int(round(note))))

