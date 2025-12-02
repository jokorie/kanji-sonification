"""
Test script for WebSocket receiver with real-time rendering.

Run this script, then open the web app on your iPad to hear the sonification in real-time.

Usage:
    1. Run this script: python test_websocket_receiver.py
    2. Note your computer's IP address (printed at startup)
    3. Serve the web frontend: python -m http.server 8000 --directory web
    4. Open Safari on iPad: http://YOUR_IP:8000
    5. Enter the WebSocket URL: ws://YOUR_IP:8765
    6. Draw with Apple Pencil!
"""

import time
import socket
from sonify.io.websocket_receiver import WebSocketStrokeReceiver
from sonify.io.load_pencilkit import StrokePoint
from sonify.features.grid_normalize import normalize_point_to_grid, create_default_grid
from sonify.features.streaming_kinematics import StreamingFeatureExtractor
from sonify.features.kinematics import StrokeFeatures
from sonify.pipeline.render_offline import Config, create_sonifier


def get_local_ip():
    """Get the local IP address of this machine."""
    try:
        # Create a socket to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    print("=" * 60)
    print("Kanji Sonification - WebSocket Real-Time Test")
    print("=" * 60)
    
    # Get local IP for easy reference
    local_ip = get_local_ip()
    
    # Configuration
    IP = "0.0.0.0"  # Listen on all interfaces
    WS_PORT = 8765
    HTTP_PORT = 8000
    CANVAS_SIZE = 1024  # Assume normalized 0-1 coordinates scaled to this
    
    print(f"\n📡 Your local IP address: {local_ip}")
    print(f"\n📋 Quick Start:")
    print(f"   1. Open another terminal and run:")
    print(f"      python -m http.server {HTTP_PORT} --directory web")
    print(f"   2. On your iPad, open Safari and go to:")
    print(f"      http://{local_ip}:{HTTP_PORT}")
    print(f"   3. When prompted, enter WebSocket URL:")
    print(f"      ws://{local_ip}:{WS_PORT}")
    
    # Create grid (assuming normalized 0-1 coordinates from web)
    grid = create_default_grid(width=CANVAS_SIZE, height=CANVAS_SIZE)
    
    # Create sonifier
    print("\n🎵 Initializing audio engine...")
    config = Config()
    sonifier = create_sonifier(config)
    sonifier.initialize()
    
    # Create feature extractor
    feature_extractor = StreamingFeatureExtractor()
    
    # Create WebSocket receiver
    receiver = WebSocketStrokeReceiver(ip=IP, port=WS_PORT)
    
    # State tracking
    stroke_active = False
    last_point_time = None
    STROKE_TIMEOUT = 0.5  # If no point for 0.5s, consider stroke ended
    
    def on_point_received(raw_point: StrokePoint):
        nonlocal stroke_active, last_point_time
        
        # Scale point to canvas size (web sends normalized 0-1 coordinates)
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

