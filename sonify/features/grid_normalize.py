"""
Grid-based normalization utilities.

Normalizes points to a fixed grid square instead of using bounding box.
This is useful for online/streaming sonification where we expect kanji
to fit within a predefined square.
"""

from typing import Tuple
from sonify.io.load_pencilkit import StrokePoint


def normalize_point_to_grid(
    point: StrokePoint,
    grid: Tuple[float, float, float, float]
) -> StrokePoint:
    """
    Normalize a single point to [0, 1] within a fixed grid square.
    
    Grid is defined as (x_min, y_min, x_max, y_max).
    Points outside the grid are clamped to [0, 1].
    
    Args:
        point: Input point with absolute coordinates
        grid: Grid bounds as (x_min, y_min, x_max, y_max)
        
    Returns:
        New StrokePoint with normalized coordinates (x, y in [0, 1])
    """
    x_min, y_min, x_max, y_max = grid
    
    grid_width = x_max - x_min
    grid_height = y_max - y_min
    
    if grid_width <= 0 or grid_height <= 0:
        raise ValueError(f"Invalid grid: width={grid_width}, height={grid_height}")
    
    # Normalize coordinates
    x_norm = (point.x - x_min) / grid_width
    y_norm = (point.y - y_min) / grid_height
    
    # Clamp to [0, 1] if outside grid
    x_norm = max(0.0, min(1.0, x_norm))
    y_norm = max(0.0, min(1.0, y_norm))
    
    return StrokePoint(
        x=x_norm,
        y=y_norm,
        force=point.force,
        azimuth=point.azimuth,
        altitude=point.altitude,
        t=point.t
    )


def create_grid_from_canvas(
    canvas_width: float,
    canvas_height: float
) -> Tuple[float, float, float, float]:
    """
    Create a square grid from canvas dimensions.
    
    Args:
        canvas_width: Canvas width in pixels
        canvas_height: Canvas height in pixels
        center_x: X coordinate of grid center (default: canvas center)
        center_y: Y coordinate of grid center (default: canvas center)
        size: Grid size (width/height of square). If None, uses min(canvas_width, canvas_height)
        
    Returns:
        Grid bounds as (x_min, y_min, x_max, y_max)
    """
    center_x = canvas_width / 2.0
    center_y = canvas_height / 2.0
    size = min(canvas_width, canvas_height)
    
    half_size = size / 2.0
    
    x_min = center_x - half_size
    x_max = center_x + half_size
    y_min = center_y - half_size
    y_max = center_y + half_size
    
    return (x_min, y_min, x_max, y_max)


def create_default_grid(width: float = 1024.0, height: float = 1024.0) -> Tuple[float, float, float, float]:
    """
    Create a default square grid.
    
    Args:
        width: Grid width (default: 1024)
        height: Grid height (default: 1024)
        
    Returns:
        Grid bounds as (x_min, y_min, x_max, y_max)
    """
    return (0.0, 0.0, width, height)

