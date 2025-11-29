"""
Dynamics and amplitude mapping functions.

Maps force/pressure and speed to amplitude, pan, and other dynamic parameters.
"""

import math


def force_to_amplitude(force: float, min_amp: float = 0.1, max_amp: float = 1.0,
                       exponent: float = 1.5) -> float:
    """
    Map force/pressure to amplitude with optional exponential scaling.
    
    Args:
        force: Force value (typically [0, 1])
        min_amp: Minimum amplitude
        max_amp: Maximum amplitude
        exponent: Exponent for perceptual scaling (>1 = more sensitive at low force)
        
    Returns:
        Amplitude [min_amp, max_amp]
    """
    force_clamped = max(0.0, min(1.0, force))
    scaled = force_clamped ** exponent
    return min_amp + scaled * (max_amp - min_amp)


def x_to_pan(x_normalized: float, min_pan: float = -1.0, max_pan: float = 1.0) -> float:
    """
    Map X coordinate to stereo pan.
    
    Args:
        x_normalized: X position [0, 1]
        min_pan: Minimum pan (-1.0 = full left)
        max_pan: Maximum pan (1.0 = full right)
        
    Returns:
        Pan value [-1, 1] where -1=left, 0=center, 1=right
    """
    x_clamped = max(0.0, min(1.0, x_normalized))
    return min_pan + x_clamped * (max_pan - min_pan)


def speed_to_brightness(speed: float, max_speed: float = 1.0,
                         min_brightness: float = 0.2, max_brightness: float = 1.0) -> float:
    """
    Map speed to timbral brightness (filter cutoff or harmonic content).
    
    Args:
        speed: Instantaneous speed
        max_speed: Expected maximum speed
        min_brightness: Minimum brightness [0, 1]
        max_brightness: Maximum brightness [0, 1]
        
    Returns:
        Brightness value [0, 1]
    """
    speed_normalized = min(speed / max_speed, 1.0) if max_speed > 0 else 0.0
    return min_brightness + speed_normalized * (max_brightness - min_brightness)

# TODO: Review
def curvature_to_roughness(curvature: float, max_curvature: float = 1.0) -> float:
    """
    Map curvature to roughness/noise amount.
    
    Higher curvature = sharper turns = more roughness.
    
    Args:
        curvature: Instantaneous curvature
        max_curvature: Expected maximum curvature
        
    Returns:
        Roughness [0, 1]
    """
    curvature_normalized = min(curvature / max_curvature, 1.0) if max_curvature > 0 else 0.0
    return curvature_normalized


def adsr_envelope(time: float, attack: float = 0.01, decay: float = 0.05,
                  sustain: float = 0.7, release: float = 0.1, 
                  duration: float = 1.0) -> float:
    """
    ADSR envelope function.
    
    Args:
        time: Current time in seconds
        attack: Attack time (sec)
        decay: Decay time (sec)
        sustain: Sustain level [0, 1]
        release: Release time (sec)
        duration: Total note duration (sec)
        
    Returns:
        Envelope value [0, 1]
    """
    if time < 0:
        return 0.0
    
    # Attack phase
    if time < attack:
        return time / attack if attack > 0 else 1.0
    
    # Decay phase
    if time < attack + decay:
        t = (time - attack) / decay if decay > 0 else 1.0
        return 1.0 - (1.0 - sustain) * t
    
    # Sustain phase
    release_start = duration - release
    if time < release_start:
        return sustain
    
    # Release phase
    if time < duration:
        t = (time - release_start) / release if release > 0 else 0.0
        return sustain * (1.0 - t)
    
    return 0.0

# TODO: Review
def soft_clip(value: float, threshold: float = 0.9) -> float:
    """
    Soft clipping/saturation function.
    
    Args:
        value: Input value
        threshold: Threshold above which clipping starts
        
    Returns:
        Clipped value
    """
    if abs(value) <= threshold:
        return value
    
    sign = 1.0 if value >= 0 else -1.0
    excess = abs(value) - threshold
    # Soft knee using tanh
    clipped_excess = threshold * math.tanh(excess / threshold)
    return sign * (threshold + clipped_excess)

