"""
Kinematic feature extraction: velocity, direction, curvature, etc.
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import numpy as np

from sonify.io.load_pencilkit import Drawing, Stroke, StrokePoint


@dataclass
class PointFeatures:
    """Derived features for a single point in a stroke."""
    t: float                    # Time (seconds)
    xN: float                   # Normalized x [0, 1]
    yN: float                   # Normalized y [0, 1]
    force: float                # Pressure
    speed: float                # Instantaneous speed (units/sec)
    direction_rad: float        # Direction in radians (-π to π)
    direction_deg: float        # Direction in degrees
    curvature: float            # Curvature (change in direction per unit length)
    azimuth: float              # Original azimuth
    altitude: float             # Original altitude
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            't': self.t,
            'xN': self.xN,
            'yN': self.yN,
            'force': self.force,
            'speed': self.speed,
            'dir_rad': self.direction_rad,
            'dir_deg': self.direction_deg,
            'curv': self.curvature,
            'azimuth': self.azimuth,
            'altitude': self.altitude
        }


@dataclass
class StrokeFeatures:
    """Complete feature set for one stroke."""
    stroke_id: int
    duration_s: float
    mean_speed: float
    max_speed: float
    mean_force: float
    dominant_direction: str     # "up", "down", "left", "right", etc.
    curvature_mean: float
    curvature_max: float
    points: List[PointFeatures] = field(default_factory=list)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'stroke_id': self.stroke_id,
            'duration_s': self.duration_s,
            'mean_speed': self.mean_speed,
            'max_speed': self.max_speed,
            'mean_force': self.mean_force,
            'dominant_direction': self.dominant_direction,
            'curvature_mean': self.curvature_mean,
            'curvature_max': self.curvature_max,
            'points': [p.to_dict() for p in self.points]
        }


@dataclass
class DrawingFeatures:
    """Complete feature set for a drawing."""
    total_duration: float
    num_strokes: int
    strokes: List[StrokeFeatures] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'total_duration': self.total_duration,
            'num_strokes': self.num_strokes,
            'strokes': [s.to_dict() for s in self.strokes],
            'metadata': self.metadata
        }


def smooth_ema(values: List[float], alpha: float = 0.3) -> List[float]:
    """
    Exponential moving average smoothing.
    
    Args:
        values: Input values
        alpha: Smoothing factor [0, 1]. Lower = more smoothing
        
    Returns:
        Smoothed values (same length as input)
    """
    if not values:
        return []
    
    smoothed = [values[0]]
    for v in values[1:]:
        smoothed.append(alpha * v + (1 - alpha) * smoothed[-1])
    return smoothed


def compute_speed(points: List[StrokePoint], smooth: bool = True, alpha: float = 0.3) -> List[float]:
    """
    Compute instantaneous speed between consecutive points.
    
    Args:
        points: List of stroke points
        smooth: Whether to apply EMA smoothing
        alpha: Smoothing parameter if smooth=True
        
    Returns:
        List of speeds (same length as points; first is 0)
    """
    if len(points) < 2:
        return [0.0] * len(points)
    
    speeds = [0.0]  # First point has no predecessor
    
    for i in range(1, len(points)):
        dx = points[i].x - points[i-1].x
        dy = points[i].y - points[i-1].y
        dt = points[i].t - points[i-1].t
        
        if dt > 0:
            distance = math.hypot(dx, dy)
            speed = distance / dt
        else:
            speed = 0.0
        
        speeds.append(speed)
    
    if smooth:
        speeds = smooth_ema(speeds, alpha)
    
    return speeds


def compute_direction(points: List[StrokePoint]) -> List[float]:
    """
    Compute direction (angle) of motion in radians.
    
    Args:
        points: List of stroke points
        
    Returns:
        List of directions in radians (-π to π); first is 0
    """
    if len(points) < 2:
        return [0.0] * len(points)
    
    directions = [0.0]
    
    for i in range(1, len(points)):
        dx = points[i].x - points[i-1].x
        dy = points[i].y - points[i-1].y
        
        direction = math.atan2(dy, dx)
        directions.append(direction)
    
    return directions

# TODO: skipped
def compute_curvature(points: List[StrokePoint], directions: List[float]) -> List[float]:
    """
    Compute curvature as change in direction per unit length.
    
    Args:
        points: List of stroke points
        directions: List of directions (from compute_direction)
        
    Returns:
        List of curvatures (same length as points)
    """
    if len(points) < 3:
        return [0.0] * len(points)
    
    curvatures = [0.0, 0.0]  # First two points
    
    for i in range(2, len(points)):
        # Change in direction
        d_theta = directions[i] - directions[i-1]
        
        # Normalize to [-π, π]
        while d_theta > math.pi:
            d_theta -= 2 * math.pi
        while d_theta < -math.pi:
            d_theta += 2 * math.pi
        
        # Arc length
        dx = points[i].x - points[i-1].x
        dy = points[i].y - points[i-1].y
        ds = math.hypot(dx, dy)
        
        if ds > 0:
            curvature = abs(d_theta) / ds
        else:
            curvature = 0.0
        
        curvatures.append(curvature)
    
    return curvatures

# TODO: skipped
def quantize_direction(rad: float, bins: int = 8) -> str:
    """
    Quantize direction to cardinal/ordinal labels.
    
    Args:
        rad: Direction in radians
        bins: Number of directional bins (8 or 4)
        
    Returns:
        Direction label like "right", "down", "up-right", etc.
    """
    deg = math.degrees(rad) % 360
    
    if bins == 8:
        labels = ["right", "down-right", "down", "down-left", 
                  "left", "up-left", "up", "up-right"]
        bin_size = 360 / 8
        idx = int((deg + bin_size/2) % 360 // bin_size)
        return labels[idx]
    elif bins == 4:
        labels = ["right", "down", "left", "up"]
        bin_size = 360 / 4
        idx = int((deg + bin_size/2) % 360 // bin_size)
        return labels[idx]
    else:
        return "unknown"

# TODO: skipped
def extract_stroke_features(stroke: Stroke, normalized: bool = False) -> StrokeFeatures:
    """
    Extract all features for a single stroke.
    
    Args:
        stroke: Input stroke
        normalized: Whether coordinates are already normalized to [0,1]
        
    Returns:
        StrokeFeatures object with point-wise and summary statistics
    """
    if not stroke.points:
        return StrokeFeatures(
            stroke_id=stroke.id,
            duration_s=0.0,
            mean_speed=0.0,
            max_speed=0.0,
            mean_force=0.0,
            dominant_direction="none",
            curvature_mean=0.0,
            curvature_max=0.0,
            points=[]
        )
    
    # Compute kinematic features
    speeds = compute_speed(stroke.points, smooth=True)
    directions = compute_direction(stroke.points)
    curvatures = compute_curvature(stroke.points, directions)
    
    # Build point features
    point_features = []
    for i, point in enumerate(stroke.points):
        pf = PointFeatures(
            t=point.t,
            xN=point.x,
            yN=point.y,
            force=point.force,
            speed=speeds[i],
            direction_rad=directions[i],
            direction_deg=math.degrees(directions[i]),
            curvature=curvatures[i],
            azimuth=point.azimuth,
            altitude=point.altitude
        )
        point_features.append(pf)
    
    # Compute summary statistics
    duration = stroke.duration()
    
    valid_speeds = [s for s in speeds if s > 0]
    mean_speed = sum(valid_speeds) / len(valid_speeds) if valid_speeds else 0.0
    max_speed = max(speeds) if speeds else 0.0
    
    forces = [p.force for p in stroke.points]
    mean_force = sum(forces) / len(forces) if forces else 0.0
    
    # Dominant direction (average of non-zero directions)
    valid_directions = [d for d, s in zip(directions, speeds) if s > 0.01]
    if valid_directions:
        # Use circular mean
        sin_sum = sum(math.sin(d) for d in valid_directions)
        cos_sum = sum(math.cos(d) for d in valid_directions)
        mean_direction = math.atan2(sin_sum, cos_sum)
        dominant_dir = quantize_direction(mean_direction, bins=8)
    else:
        dominant_dir = "none"
    
    curvature_mean = sum(curvatures) / len(curvatures) if curvatures else 0.0
    curvature_max = max(curvatures) if curvatures else 0.0
    
    return StrokeFeatures(
        stroke_id=stroke.id,
        duration_s=duration,
        mean_speed=mean_speed,
        max_speed=max_speed,
        mean_force=mean_force,
        dominant_direction=dominant_dir,
        curvature_mean=curvature_mean,
        curvature_max=curvature_max,
        points=point_features
    )

# TODO: skipped
def extract_drawing_features(drawing: Drawing, normalize: bool = True) -> DrawingFeatures:
    """
    Extract features for an entire drawing.
    
    Args:
        drawing: Input drawing
        normalize: Whether to normalize coordinates first
        
    Returns:
        DrawingFeatures with all strokes processed
    """
    # Normalize if requested
    if normalize and not drawing.metadata.get('normalized', False):
        from sonify.features.normalize import center_normalize
        drawing = center_normalize(drawing)
    
    # Extract features for each stroke
    stroke_features = []
    for stroke in drawing.strokes:
        sf = extract_stroke_features(stroke, normalized=True)
        stroke_features.append(sf)
    
    total_duration = drawing.total_duration()
    
    return DrawingFeatures(
        total_duration=total_duration,
        num_strokes=len(drawing.strokes),
        strokes=stroke_features,
        metadata=drawing.metadata
    )

