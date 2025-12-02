"""
Test script for OSC receiver with real-time rendering.

Run this script, then draw on your iPad to hear the sonification in real-time.
"""

import time
from sonify.io.osc_receiver import OSCStrokeReceiver
from sonify.io.load_pencilkit import StrokePoint
from sonify.features.grid_normalize import normalize_point_to_grid, create_default_grid
from sonify.features.streaming_kinematics import StreamingFeatureExtractor
from sonify.features.kinematics import StrokeFeatures
from sonify.pipeline.render_offline import Config, create_sonifier


def main():
    print("=" * 60)
    print("Kanji Sonification - OSC Real-Time Test")
    print("=" * 60)
    
    # Configuration
    IP = "0.0.0.0"  # Listen on all interfaces
    PORT = 5005
    CANVAS_SIZE = 1024  # Assume iPad is using 1024x1024 logical canvas
    
    # Create grid (assuming normalized 0-1 coordinates from iOS)
    grid = create_default_grid(width=CANVAS_SIZE, height=CANVAS_SIZE)
    
    # Create sonifier
    print("\n🎵 Initializing audio engine...")
    config = Config()
    sonifier = create_sonifier(config)
    sonifier.initialize()
    
    # Create feature extractor
    feature_extractor = StreamingFeatureExtractor()
    
    # Create OSC receiver
    receiver = OSCStrokeReceiver(ip=IP, port=PORT)
    
    # State tracking
    stroke_active = False
    last_point_time = None
    STROKE_TIMEOUT = 0.5  # If no point for 0.5s, consider stroke ended
    
    def on_point_received(raw_point: StrokePoint):
        nonlocal stroke_active, last_point_time
        
        # Scale point to canvas size (iOS sends normalized 0-1 coordinates)
        scaled_point = StrokePoint(
            x=raw_point.x * CANVAS_SIZE,
            y=raw_point.y * CANVAS_SIZE,
            force=raw_point.force,
            azimuth=raw_point.azimuth,
            altitude=raw_point.altitude,
            t=raw_point.t
        )
        
        # Normalize to grid
        normalized_point = normalize_point_to_grid(scaled_point, grid)
        
        # Start stroke if not active
        if not stroke_active:
            print("\n✏️  Stroke started!")
            feature_extractor.reset()
            
            # Create minimal StrokeFeatures for start_stroke
            stroke_features = StrokeFeatures(
                stroke_id=1,
                duration_s=0.0,
                mean_speed=0.0,
                max_speed=0.0,
                mean_force=normalized_point.force,
                dominant_direction="none",
                curvature_mean=0.0,
                curvature_max=0.0,
                points=[]
            )
            
            sonifier.begin_kanji({'id': 'live', 'num_strokes': 1})
            sonifier.start_stroke(stroke_features)
            stroke_active = True
        
        # Extract features and update sonifier
        point_features = feature_extractor.update(normalized_point)
        if point_features is not None:
            sonifier.update(point_features)
        
        last_point_time = time.time()
    
    # Start receiver
    receiver.start(callback=on_point_received)
    
    try:
        print("\n✅ Ready! Draw on your iPad to hear sonification.")
        print("   Press Ctrl+C to stop\n")
        
        while True:
            time.sleep(0.1)
            
            # Check for stroke timeout
            if stroke_active and last_point_time:
                if time.time() - last_point_time > STROKE_TIMEOUT:
                    print("✏️  Stroke ended!")
                    sonifier.end_stroke()
                    sonifier.end_kanji()
                    stroke_active = False
                    last_point_time = None
                    print("\n🎤 Ready for next stroke...\n")
                    
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping...")
        if stroke_active:
            sonifier.end_stroke()
            sonifier.end_kanji()
        receiver.stop()
        sonifier.shutdown()
        print("Done!")


if __name__ == "__main__":
    main()

