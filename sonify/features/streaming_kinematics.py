"""
Streaming/incremental feature extraction for real-time sonification.

Computes kinematic features (speed, direction, curvature) incrementally
as points arrive, maintaining state between updates.
"""

import math
from typing import Optional, List
from dataclasses import dataclass, field

from sonify.io.load_pencilkit import StrokePoint
from sonify.features.kinematics import PointFeatures


@dataclass
class StreamingFeatureState:
    """State maintained for incremental feature extraction."""
    previous_point: Optional[StrokePoint] = None
    previous_direction: Optional[float] = None
    point_history: List[StrokePoint] = field(default_factory=list)  # Last 3 points for curvature
    smoothed_speed: float = 0.0  # EMA-smoothed speed
    alpha: float = 0.3  # EMA smoothing factor
    
    def reset(self):
        """Reset state for a new stroke."""
        self.previous_point = None
        self.previous_direction = None
        self.point_history.clear()
        self.smoothed_speed = 0.0


def compute_speed_incremental(
    current_point: StrokePoint,
    previous_point: StrokePoint
) -> float:
    """
    Compute instantaneous speed from current and previous point.
    
    Args:
        current_point: Current point
        previous_point: Previous point
        
    Returns:
        Speed in units per second
    """
    dx = current_point.x - previous_point.x
    dy = current_point.y - previous_point.y
    dt = current_point.t - previous_point.t
    
    if dt <= 0:
        return 0.0
    
    distance = math.sqrt(dx * dx + dy * dy)
    speed = distance / dt
    
    return speed


def compute_direction_incremental(
    current_point: StrokePoint,
    previous_point: StrokePoint
) -> float:
    """
    Compute direction from previous to current point.
    
    Args:
        current_point: Current point
        previous_point: Previous point
        
    Returns:
        Direction in radians [-π, π]
    """
    dx = current_point.x - previous_point.x
    dy = current_point.y - previous_point.y
    
    if dx == 0 and dy == 0:
        return 0.0
    
    direction = math.atan2(dy, dx)
    return direction


def compute_curvature_incremental(
    points: List[StrokePoint]
) -> float:
    """
    Compute curvature from a sequence of points (needs at least 3 points).
    
    Args:
        points: List of points (should be last 3 points)
        
    Returns:
        Curvature (change in direction per unit length)
    """
    if len(points) < 3:
        return 0.0
    
    p0, p1, p2 = points[-3], points[-2], points[-1]
    
    # Direction from p0 to p1
    dx1 = p1.x - p0.x
    dy1 = p1.y - p0.y
    dir1 = math.atan2(dy1, dx1)
    
    # Direction from p1 to p2
    dx2 = p2.x - p1.x
    dy2 = p2.y - p1.y
    dir2 = math.atan2(dy2, dx2)
    
    # Change in direction
    d_theta = dir2 - dir1
    # Normalize to [-π, π]
    while d_theta > math.pi:
        d_theta -= 2 * math.pi
    while d_theta < -math.pi:
        d_theta += 2 * math.pi
    
    # Arc length from p1 to p2
    ds = math.sqrt(dx2 * dx2 + dy2 * dy2)
    
    if ds > 0:
        curvature = abs(d_theta) / ds
    else:
        curvature = 0.0
    
    return curvature


class StreamingFeatureExtractor:
    """
    Incremental feature extractor for streaming points.
    
    Maintains state between updates and computes features on-the-fly.
    """
    
    def __init__(self, alpha: float = 0.3):
        """
        Initialize the extractor.
        
        Args:
            alpha: EMA smoothing factor for speed (0.0 = no smoothing, 1.0 = no memory)
        """
        self.state = StreamingFeatureState(alpha=alpha)
        self.alpha = alpha
    
    def reset(self):
        """Reset state for a new stroke."""
        self.state.reset()
    
    def update(self, point: StrokePoint) -> Optional[PointFeatures]:
        """
        Update with a new point and compute features.
        
        Args:
            point: New point to process
            
        Returns:
            PointFeatures if enough data is available, None for first point
        """
        # First point: just store it, no features yet
        if self.state.previous_point is None:
            self.state.previous_point = point
            self.state.point_history.append(point)
            return None
        
        # Compute speed
        speed = compute_speed_incremental(point, self.state.previous_point)
        
        # Apply EMA smoothing
        if self.state.smoothed_speed == 0.0:
            self.state.smoothed_speed = speed
        else:
            self.state.smoothed_speed = (
                self.alpha * speed + (1.0 - self.alpha) * self.state.smoothed_speed
            )
        
        # Compute direction
        direction_rad = compute_direction_incremental(point, self.state.previous_point)
        direction_deg = math.degrees(direction_rad)
        
        # Update point history (keep last 3 points)
        self.state.point_history.append(point)
        if len(self.state.point_history) > 3:
            self.state.point_history.pop(0)
        
        # Compute curvature (needs at least 3 points)
        curvature = compute_curvature_incremental(self.state.point_history)
        
        # Create point features
        # Note: xN and yN should already be normalized by the grid normalizer
        point_features = PointFeatures(
            t=point.t,
            xN=point.x,  # Assumes point is already normalized
            yN=point.y,  # Assumes point is already normalized
            force=point.force,
            speed=self.state.smoothed_speed,
            direction_rad=direction_rad,
            direction_deg=direction_deg,
            curvature=curvature,
            azimuth=point.azimuth,
            altitude=point.altitude
        )
        
        # Update state
        self.state.previous_point = point
        self.state.previous_direction = direction_rad
        
        return point_features

