"""
Coordinate normalization utilities.
"""

from typing import Tuple
from sonify.io.load_pencilkit import Drawing, Stroke, StrokePoint


def normalize_coordinates(drawing: Drawing) -> Drawing:
    """
    Normalize all (x, y) coordinates to [0, 1] using canvas bounds.
    
    This creates a copy of the drawing with normalized coordinates.
    Canvas dimensions are preserved for reference.
    
    Args:
        drawing: Input drawing with absolute coordinates
        
    Returns:
        New Drawing with normalized coordinates
    """
    canvas = drawing.canvas
    normalized_strokes = []
    
    min_x, max_x, min_y, max_y = get_bounding_box(drawing)
    
    width = max_x - min_x
    height = max_y - min_y   

    for stroke in drawing.strokes:
        normalized_points = []
        for point in stroke.points:
            normalized_point = StrokePoint(
                x=(point.x - min_x) / width,
                y=(point.y - min_y) / height,
                force=point.force,
                azimuth=point.azimuth,
                altitude=point.altitude,
                t=point.t
            )
            normalized_points.append(normalized_point)
        
        normalized_stroke = Stroke(id=stroke.id, points=normalized_points)
        normalized_strokes.append(normalized_stroke)
    
    return Drawing(
        canvas=canvas,
        strokes=normalized_strokes,
        metadata={**drawing.metadata, 'normalized': True}
    )

def get_bounding_box(drawing: Drawing) -> Tuple[float, float, float, float]:
    """
    Get the bounding box of all strokes in the drawing.
    
    Returns:
        (min_x, min_y, max_x, max_y) in the drawing's coordinate system
    """
    if not drawing.strokes:
        return (0, 0, 0, 0)
    
    min_x = min(point.x for stroke in drawing.strokes for point in stroke.points)
    max_x = max(point.x for stroke in drawing.strokes for point in stroke.points)
    min_y = min(point.y for stroke in drawing.strokes for point in stroke.points)
    max_y = max(point.y for stroke in drawing.strokes for point in stroke.points)
    
    return (min_x, max_x, min_y, max_y)


def center_normalize(drawing: Drawing, margin: float = 0.1) -> Drawing:
    """
    Normalize drawing to [0, 1] based on actual content bounding box,
    centered with optional margin.
    
    Args:
        drawing: Input drawing
        margin: Fraction of space to leave as margin (0.1 = 10% on each side)
        
    Returns:
        New Drawing centered and normalized
    """
    min_x, max_x, min_y, max_y = get_bounding_box(drawing)
    
    if max_x <= min_x or max_y <= min_y:
        # Degenerate case, just return normalized version
        return normalize_coordinates(drawing)
    
    width = max_x - min_x
    height = max_y - min_y
    
    # Calculate scale to fit in [margin, 1-margin] range
    scale = (1.0 - 2 * margin) / max(width, height)
    
    # Center in the [0, 1] space
    center_x = 0.5
    center_y = 0.5
    content_center_x = (min_x + max_x) / 2
    content_center_y = (min_y + max_y) / 2
    
    normalized_strokes = []
    for stroke in drawing.strokes:
        normalized_points = []
        for point in stroke.points:
            # Translate to origin, scale, translate to center
            nx = (point.x - content_center_x) * scale + center_x
            ny = (point.y - content_center_y) * scale + center_y
            
            normalized_point = StrokePoint(
                x=nx,
                y=ny,
                force=point.force,
                azimuth=point.azimuth,
                altitude=point.altitude,
                t=point.t
            )
            normalized_points.append(normalized_point)
        
        normalized_stroke = Stroke(id=stroke.id, points=normalized_points)
        normalized_strokes.append(normalized_stroke)
    
    return Drawing(
        canvas=drawing.canvas,
        strokes=normalized_strokes,
        metadata={**drawing.metadata, 'normalized': True, 'centered': True}
    )

