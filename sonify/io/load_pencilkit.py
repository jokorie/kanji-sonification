"""
PencilKit JSON loader.

Parses exported PencilKit drawings into our unified stroke representation.
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class StrokePoint:
    """A single point in a stroke with raw PencilKit data."""
    x: float              # Absolute X coordinate
    y: float              # Absolute Y coordinate
    force: float          # Pressure/force [0, 1] (typically)
    azimuth: float        # Azimuth angle in radians # TODO: a bit curioius why this is importatin. would think that instead we should track the angle from the zenith to the star
    altitude: float       # Altitude angle in radians
    t: float              # Timestamp relative to stroke start (seconds)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for serialization."""
        return {
            'x': self.x,
            'y': self.y,
            'force': self.force,
            'azimuth': self.azimuth,
            'altitude': self.altitude,
            't': self.t
        }


@dataclass
class Stroke:
    """A single continuous stroke (pen-down to pen-up)."""
    id: int
    points: List[StrokePoint] = field(default_factory=list)
    
    def duration(self) -> float:
        """Total duration of the stroke in seconds."""
        if not self.points:
            return 0.0
        return self.points[-1].t - self.points[0].t
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'points': [pt.to_dict() for pt in self.points]
        }


@dataclass
class Canvas:
    """Canvas metadata."""
    width: float
    height: float
    ppi: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {'width': self.width, 'height': self.height}
        if self.ppi is not None:
            result['ppi'] = self.ppi
        return result


@dataclass
class Drawing:
    """Complete drawing with canvas metadata and strokes."""
    canvas: Canvas
    strokes: List[Stroke] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def total_duration(self) -> float:
        """Total duration across all strokes, including pauses between strokes."""
        if not self.strokes:
            return 0.0
        # Get first and last timestamps across all strokes
        first_t = min(stroke.points[0].t for stroke in self.strokes if stroke.points)
        last_t = max(stroke.points[-1].t for stroke in self.strokes if stroke.points)
        return last_t - first_t
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            'canvas': self.canvas.to_dict(),
            'strokes': [s.to_dict() for s in self.strokes]
        }
        if self.metadata:
            result['metadata'] = self.metadata
        return result


def load_pencilkit_json(filepath: str) -> Drawing:
    """
    Load a PencilKit drawing from JSON export.
    
    Expected format:
    {
      "canvas": {"width": 2048, "height": 1536, "ppi": 264},
      "strokes": [
        {
          "id": 1,
          "points": [
            {"x": 1023.2, "y": 410.7, "force": 0.55, 
             "azimuth": 0.61, "altitude": 1.05, "t": 0.000},
            ...
          ]
        },
        ...
      ],
      "metadata": {...}  # optional
    }
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        Drawing object with parsed canvas and strokes
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If JSON structure is invalid
    """
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    # Parse canvas
    if 'canvas' not in data:
        raise ValueError("JSON must contain 'canvas' field")
    
    canvas_data = data['canvas']
    canvas = Canvas(
        width=float(canvas_data['width']),
        height=float(canvas_data['height']),
        ppi=float(canvas_data['ppi']) if 'ppi' in canvas_data else None
    )
    
    # Parse strokes
    if 'strokes' not in data:
        raise ValueError("JSON must contain 'strokes' field")
    
    strokes = []
    for stroke_data in data['strokes']:
        stroke_id = stroke_data['id']
        points = []
        
        for pt_data in stroke_data['points']:
            point = StrokePoint(
                x=float(pt_data['x']),
                y=float(pt_data['y']),
                force=float(pt_data['force']),
                azimuth=float(pt_data['azimuth']),
                altitude=float(pt_data['altitude']),
                t=float(pt_data['t'])
            )
            points.append(point)
        
        stroke = Stroke(id=stroke_id, points=points)
        strokes.append(stroke)
    
    # Parse optional metadata
    metadata = data.get('metadata', {})
    
    return Drawing(canvas=canvas, strokes=strokes, metadata=metadata)


def save_drawing_json(drawing: Drawing, filepath: str) -> None:
    """
    Save a Drawing object to JSON format.
    
    Args:
        drawing: Drawing object to save
        filepath: Output JSON file path
    """
    with open(filepath, 'w') as f:
        json.dump(drawing.to_dict(), f, indent=2)

