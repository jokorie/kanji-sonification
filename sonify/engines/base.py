"""
Base Sonifier interface.

All synthesis engines should implement this interface for plug-and-play compatibility.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from sonify.features.kinematics import StrokeFeatures, PointFeatures


class Sonifier(ABC):
    """
    Abstract base class for sonification engines.
    
    The lifecycle for rendering a kanji is:
    1. begin_kanji(metadata)
    2. For each stroke:
       a. start_stroke(stroke_features)
       b. For each point:
          update(point_features)
       c. end_stroke()
    3. end_kanji()
    4. (optional) save() or get_audio_buffer()
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the sonifier with optional configuration.
        
        Args:
            config: Configuration dictionary with engine-specific parameters
        """
        self.config = config or {}
        self.is_active = False
        self.current_stroke_id : Optional[int] = None
    
    @abstractmethod
    def initialize(self):
        """
        Initialize the audio engine (boot server, allocate resources).
        
        Call this before begin_kanji().
        """
        pass
    
    @abstractmethod
    def shutdown(self):
        """
        Shutdown the audio engine and release resources.
        
        Call this after end_kanji() when done.
        """
        pass
    
    @abstractmethod
    def begin_kanji(self, metadata: Dict[str, Any]):
        """
        Signal the start of a new kanji rendering.
        
        Args:
            metadata: Dictionary with kanji info (e.g., {"id": "水", "num_strokes": 4})
        """
        pass
    
    @abstractmethod
    def start_stroke(self, stroke_features: StrokeFeatures):
        """
        Signal the start of a new stroke.
        
        Args:
            stroke_features: Complete feature set for this stroke
        """
        pass
    
    @abstractmethod
    def update(self, point_features: PointFeatures):
        """
        Update synthesis parameters based on current point.
        
        This is called for each point in the stroke.
        
        Args:
            point_features: Features for the current point
        """
        pass
    
    @abstractmethod
    def end_stroke(self):
        """
        Signal the end of the current stroke.
        """
        pass
    
    @abstractmethod
    def end_kanji(self):
        """
        Signal the end of the kanji rendering.
        """
        pass
    
    def save(self, filepath: str):
        """
        Save rendered audio to file (if applicable).
        
        Args:
            filepath: Output file path
        """
        raise NotImplementedError("save() not implemented for this engine")
    
    def get_audio_buffer(self):
        """
        Get the rendered audio as a buffer (if applicable).
        
        Returns:
            Audio buffer (format depends on engine)
        """
        raise NotImplementedError("get_audio_buffer() not implemented for this engine")
    
    def record_start(self, duration: float, filepath: str):
        """
        Start recording output to file (if supported by engine).
        
        Override in engines that support real-time recording (e.g., pyo).
        Default implementation does nothing.
        
        Args:
            duration: Duration to record (seconds)
            filepath: Output file path
        """
        pass  # Default: no-op
    
    def record_stop(self):
        """
        Stop recording output (if supported by engine).
        
        Override in engines that support real-time recording.
        Default implementation does nothing.
        """
        pass  # Default: no-op


class DummySonifier(Sonifier):
    """
    A no-op sonifier for testing the pipeline without audio output.
    """
    
    def initialize(self):
        print("DummySonifier: Initialized")
        self.is_active = True
    
    def shutdown(self):
        print("DummySonifier: Shutdown")
        self.is_active = False
    
    def begin_kanji(self, metadata: Dict[str, Any]):
        print(f"DummySonifier: Begin kanji {metadata}")
    
    def start_stroke(self, stroke_features: StrokeFeatures):
        self.current_stroke_id = stroke_features.stroke_id
        print(f"DummySonifier: Start stroke {stroke_features.stroke_id}")
    
    def update(self, point_features: PointFeatures):
        pass  # Silent updates
    
    def end_stroke(self):
        print(f"DummySonifier: End stroke {self.current_stroke_id}")
        self.current_stroke_id = None
    
    def end_kanji(self):
        print("DummySonifier: End kanji")

