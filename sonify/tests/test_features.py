"""
Tests for feature extraction module.
"""

import pytest
import math
from sonify.io.load_pencilkit import StrokePoint, Stroke, Canvas, Drawing
from sonify.features.kinematics import (
    compute_speed, compute_direction, compute_curvature,
    extract_stroke_features, extract_drawing_features
)
from sonify.features.normalize import normalize_coordinates


def test_normalize_coordinates():
    """Test coordinate normalization."""
    canvas = Canvas(width=1024, height=1024)
    stroke = Stroke(
        id=1,
        points=[
            StrokePoint(x=0, y=0, force=0.5, azimuth=0, altitude=1, t=0),
            StrokePoint(x=1024, y=1024, force=0.5, azimuth=0, altitude=1, t=1)
        ]
    )
    drawing = Drawing(canvas=canvas, strokes=[stroke])
    
    normalized = normalize_coordinates(drawing)
    
    assert normalized.strokes[0].points[0].x == 0.0
    assert normalized.strokes[0].points[0].y == 0.0
    assert abs(normalized.strokes[0].points[1].x - 1.0) < 0.001
    assert abs(normalized.strokes[0].points[1].y - 1.0) < 0.001


def test_compute_speed():
    """Test speed computation."""
    points = [
        StrokePoint(x=0, y=0, force=0.5, azimuth=0, altitude=1, t=0.0),
        StrokePoint(x=1, y=0, force=0.5, azimuth=0, altitude=1, t=0.1),
        StrokePoint(x=2, y=0, force=0.5, azimuth=0, altitude=1, t=0.2),
    ]
    
    speeds = compute_speed(points, smooth=False)
    
    assert len(speeds) == 3
    assert speeds[0] == 0.0  # First point
    assert abs(speeds[1] - 10.0) < 0.1  # 1 unit / 0.1 sec = 10 units/sec
    assert abs(speeds[2] - 10.0) < 0.1


def test_compute_direction():
    """Test direction computation."""
    points = [
        StrokePoint(x=0, y=0, force=0.5, azimuth=0, altitude=1, t=0.0),
        StrokePoint(x=1, y=0, force=0.5, azimuth=0, altitude=1, t=0.1),  # Right (0 rad)
        StrokePoint(x=1, y=1, force=0.5, azimuth=0, altitude=1, t=0.2),  # Down (π/2 rad)
    ]
    
    directions = compute_direction(points)
    
    assert len(directions) == 3
    assert directions[0] == 0.0  # First point
    assert abs(directions[1] - 0.0) < 0.01  # Right
    assert abs(directions[2] - math.pi/2) < 0.01  # Down


def test_extract_stroke_features():
    """Test stroke feature extraction."""
    points = [
        StrokePoint(x=0.5, y=0.3, force=0.5, azimuth=0, altitude=1, t=0.0),
        StrokePoint(x=0.5, y=0.4, force=0.6, azimuth=0, altitude=1, t=0.1),
        StrokePoint(x=0.5, y=0.5, force=0.7, azimuth=0, altitude=1, t=0.2),
    ]
    stroke = Stroke(id=1, points=points)
    
    features = extract_stroke_features(stroke, normalized=True)
    
    assert features.stroke_id == 1
    assert features.duration_s == 0.2
    assert len(features.points) == 3
    assert features.mean_speed > 0
    assert features.dominant_direction == "down"


def test_extract_drawing_features():
    """Test full drawing feature extraction."""
    canvas = Canvas(width=1024, height=1024)
    stroke1 = Stroke(
        id=1,
        points=[
            StrokePoint(x=512, y=200, force=0.5, azimuth=0, altitude=1, t=0.0),
            StrokePoint(x=512, y=400, force=0.6, azimuth=0, altitude=1, t=0.2),
        ]
    )
    stroke2 = Stroke(
        id=2,
        points=[
            StrokePoint(x=300, y=500, force=0.5, azimuth=0, altitude=1, t=0.4),
            StrokePoint(x=600, y=500, force=0.6, azimuth=0, altitude=1, t=0.6),
        ]
    )
    drawing = Drawing(canvas=canvas, strokes=[stroke1, stroke2])
    
    features = extract_drawing_features(drawing, normalize=True)
    
    assert features.num_strokes == 2
    assert len(features.strokes) == 2
    assert abs(features.total_duration - 0.6) < 0.001  # t=0.0 to t=0.6 (includes pause between strokes)
    
    # Check first stroke (vertical down)
    assert features.strokes[0].dominant_direction == "down"
    
    # Check second stroke (horizontal right)
    assert features.strokes[1].dominant_direction == "right"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

