"""
Stream simulator for testing online sonification.

Simulates streaming points from test JSON files with realistic timing.
"""

import time
from typing import Iterator, Optional
from sonify.io.load_pencilkit import load_pencilkit_json, StrokePoint


class JsonStreamSimulator:
    """
    Simulates streaming points from a PencilKit JSON file.
    
    Yields points one-by-one respecting original timestamps, with
    configurable playback rate. Assumes single-stroke kanji.
    """
    
    def __init__(self, json_path: str, playback_rate: float = 1.0):
        """
        Initialize the simulator.
        
        Args:
            json_path: Path to PencilKit JSON file (single-stroke kanji)
            playback_rate: Playback rate multiplier (1.0 = real-time, 2.0 = 2x faster, 0.5 = 2x slower)
        """
        self.json_path = json_path
        self.playback_rate = playback_rate
        
        # Load the drawing
        self.drawing = load_pencilkit_json(json_path)
        
        # Get the first (and only) stroke for single-stroke kanji
        if not self.drawing.strokes:
            raise ValueError(f"No strokes found in {json_path}")
        
        self.stroke = self.drawing.strokes[0]
        if not self.stroke.points:
            raise ValueError(f"No points found in stroke")
        
        # Reset state
        self.reset()
    
    def reset(self):
        """Reset the simulator to the beginning."""
        self.current_index = 0
        self.start_time = None
        self.first_point_time = self.stroke.points[0].t if self.stroke.points else 0.0
    
    def __iter__(self) -> Iterator[StrokePoint]:
        """Make this an iterator."""
        return self
    
    def __next__(self) -> StrokePoint:
        """
        Get the next point, waiting for the appropriate time.
        
        Returns:
            Next StrokePoint
            
        Raises:
            StopIteration: When all points have been yielded
        """
        if self.current_index >= len(self.stroke.points):
            raise StopIteration
        
        point = self.stroke.points[self.current_index]
        
        # On first point, record start time
        if self.start_time is None:
            self.start_time = time.time()
            self.current_index += 1
            return point
        
        # Calculate when this point should be yielded (scaled by playback rate)
        target_elapsed = (point.t - self.first_point_time) / self.playback_rate
        current_elapsed = time.time() - self.start_time
        
        # Wait if necessary
        sleep_duration = target_elapsed - current_elapsed
        if sleep_duration > 0:
            time.sleep(sleep_duration)
        
        self.current_index += 1
        return point
    
    def get_metadata(self) -> dict:
        """Get metadata about the kanji."""
        return {
            'id': self.drawing.metadata.get('id', 'unknown'),
            'num_points': len(self.stroke.points),
            'duration': self.stroke.duration(),
            'canvas': {
                'width': self.drawing.canvas.width,
                'height': self.drawing.canvas.height
            }
        }


def create_point_stream(
    json_path: str,
    playback_rate: float = 1.0
) -> Iterator[StrokePoint]:
    """
    Convenience function to create a point stream from a JSON file.
    
    Args:
        json_path: Path to PencilKit JSON file
        playback_rate: Playback rate multiplier
        
    Returns:
        Iterator of StrokePoint objects
    """
    simulator = JsonStreamSimulator(json_path, playback_rate)
    return iter(simulator)

