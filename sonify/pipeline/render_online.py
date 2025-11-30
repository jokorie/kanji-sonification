"""
Online/streaming rendering pipeline.

Processes points in real-time as they arrive, with grid-based normalization
and incremental feature extraction. Designed for single-stroke kanji.
"""

import time
from typing import Iterator, Optional, Tuple, Dict, Any
from sonify.io.load_pencilkit import StrokePoint
from sonify.io.stream_simulator import create_point_stream
from sonify.features.grid_normalize import normalize_point_to_grid, create_default_grid
from sonify.features.streaming_kinematics import StreamingFeatureExtractor
from sonify.features.kinematics import StrokeFeatures
from sonify.pipeline.render_offline import Config
from sonify.engines.base import Sonifier


def stream_kanji(
    point_stream: Iterator[StrokePoint],
    grid: Tuple[float, float, float, float],
    sonifier: Sonifier,
    metadata: Dict[str, Any],
    output_path: Optional[str] = None
) -> None:
    """
    Stream a kanji from a point iterator and sonify it in real-time.
    
    Args:
        point_stream: Iterator of StrokePoint objects (raw, not normalized)
        grid: Grid bounds as (x_min, y_min, x_max, y_max)
        sonifier: Sonifier instance (must be initialized)
        output_path: Optional output path for recording (if supported by engine)
        metadata: Optional metadata dict (e.g., {'id': '一'})
    """
    # Initialize feature extractor
    feature_extractor = StreamingFeatureExtractor()
    feature_extractor.reset()
    
    # Collect points for stroke features (needed for start_stroke)
    collected_points = []
    collected_point_features = []
    
    # For recording, we need to know duration ahead of time
    # In a real streaming scenario, we'd use an estimate, but for file-based
    # we can calculate the duration exactly.
           
    # Start recording if output path provided
    if output_path and hasattr(sonifier, 'record_start'):
        # Add padding for audio tail
        estimated_duration = 5 # TODO: find way to deduce the [estimated_duration] without having all the points
        sonifier.record_start(estimated_duration, output_path)
        
    # Begin kanji
    kanji_metadata = metadata
    sonifier.begin_kanji(kanji_metadata)
    
    # Start stroke (single stroke for now)
    stroke_started = False
    first_point_time = None
    
    try:
        # Process points as they stream in
        for raw_point in point_stream:
            # Record first point time
            if first_point_time is None:
                first_point_time = raw_point.t
            
            # Normalize point to grid
            normalized_point = normalize_point_to_grid(raw_point, grid)
            collected_points.append(normalized_point)
            
            # Extract features incrementally
            point_features = feature_extractor.update(normalized_point)
            
            # Start stroke after we have the first point (even if no features yet)
            if not stroke_started:
                # Create minimal StrokeFeatures for start_stroke
                stroke_features = StrokeFeatures(
                    stroke_id=1,
                    duration_s=0.0,  # Will be updated
                    mean_speed=0.0,
                    max_speed=0.0,
                    mean_force=normalized_point.force,
                    dominant_direction="none",
                    curvature_mean=0.0,
                    curvature_max=0.0,
                    points=[]  # Will be populated
                )
                sonifier.start_stroke(stroke_features)
                stroke_started = True
            
            # Update sonifier with point features (skip first point which has None)
            if point_features is not None:
                collected_point_features.append(point_features)
                sonifier.update(point_features)
        
            
        sonifier.end_stroke()
            
        # Brief pause after stroke (for audio processing)
        time.sleep(0.01)

        # End kanji
        sonifier.end_kanji()
        
        # Stop recording if started
        if output_path and hasattr(sonifier, 'record_stop'):
            # Add padding for audio tail
            time.sleep(0.5)
            sonifier.record_stop()
        
    finally:
        # Clean shutdown
        sonifier.shutdown()
    
    print("Rendering complete!")
    print(f"Saved to: {output_path}")



def stream_kanji_from_json(
    json_path: str,
    config: Config,
    output_path: Optional[str] = None,
    playback_rate: float = 1.0,
) -> None:
    """
    Convenience function to stream a kanji from a JSON file.
    
    Args:
        json_path: Path to PencilKit JSON file (single-stroke kanji)
        grid: Grid bounds. If None, uses default grid from canvas
        sonifier: Sonifier instance. If None, creates one from config
        output_path: Optional output path for recording
        playback_rate: Playback rate multiplier
        config: Config dict for creating sonifier (if sonifier is None)
    """
    from sonify.io.load_pencilkit import load_pencilkit_json
    from sonify.pipeline.render_offline import create_sonifier, Config
    
    # Load drawing to get metadata and canvas
    drawing = load_pencilkit_json(json_path)
    
    # Create grid if not provided
    grid = create_default_grid(
        width=drawing.canvas.width,
        height=drawing.canvas.height
    )

    # Create sonifier if not provided
    config = Config()
    sonifier = create_sonifier(config)
    sonifier.initialize()
    should_shutdown = True    
    # Create point stream
    point_stream = create_point_stream(json_path, playback_rate)
    metadata = {
        'id': drawing.metadata.get('id', 'unknown'),
        'num_strokes': 1
    }
    
    try:
        stream_kanji(
            point_stream=point_stream,
            grid=grid,
            sonifier=sonifier,
            output_path=output_path,
            metadata=metadata
        )
    finally:
        if should_shutdown:
            sonifier.shutdown()
