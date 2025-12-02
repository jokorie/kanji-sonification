"""
OSC receiver for real-time stroke data from iOS app.

Receives stroke points via OSC protocol and converts them to StrokePoint objects.
"""

from pythonosc import dispatcher
from pythonosc import osc_server
import threading
import queue
from typing import Optional, Callable
from sonify.io.load_pencilkit import StrokePoint


class OSCStrokeReceiver:
    """
    Receives stroke points from iOS app via OSC protocol.
    
    Listens for messages on the `/kanji/stroke` address and converts
    them to StrokePoint objects that can be fed into the streaming pipeline.
    """
    
    def __init__(self, ip: str = "0.0.0.0", port: int = 5005):
        """
        Initialize OSC receiver.
        
        Args:
            ip: IP address to bind to (0.0.0.0 for all interfaces)
            port: Port to listen on (default 5005)
        """
        self.ip = ip
        self.port = port
        self.point_queue = queue.Queue()
        self.server: Optional[osc_server.ThreadingOSCUDPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.callback: Optional[Callable[[StrokePoint], None]] = None
        self.first_timestamp: Optional[float] = None
        self.points_received = 0
        
    def start(self, callback: Optional[Callable[[StrokePoint], None]] = None):
        """
        Start the OSC server in a background thread.
        
        Args:
            callback: Optional callback function to call when a point is received.
                      If not provided, points are queued and can be retrieved with get_point().
        """
        self.callback = callback
        self.first_timestamp = None
        
        # Create dispatcher and map address to handler
        disp = dispatcher.Dispatcher()
        disp.map("/kanji/stroke", self._handle_stroke_point)
        
        # Create server
        self.server = osc_server.ThreadingOSCUDPServer((self.ip, self.port), disp)
        
        # Start server thread
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        print(f"🎵 OSC Receiver listening on {self.ip}:{self.port}")
        print(f"   Waiting for stroke data from iOS app...")
        
    def stop(self):
        """Stop the OSC server."""
        if self.server:
            self.server.shutdown()
            self.server = None
        if self.server_thread:
            self.server_thread.join(timeout=1.0)
            self.server_thread = None
        print("OSC Receiver stopped")
        
    def get_point(self, timeout: Optional[float] = None) -> Optional[StrokePoint]:
        """
        Get the next point from the queue (blocking).
        
        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)
            
        Returns:
            StrokePoint or None if timeout
        """
        try:
            return self.point_queue.get(timeout=timeout)
        except queue.Empty:
            return None
            
    def has_points(self) -> bool:
        """Check if there are points in the queue."""
        return not self.point_queue.empty()
    
    def clear_queue(self):
        """Clear all pending points from the queue."""
        while not self.point_queue.empty():
            try:
                self.point_queue.get_nowait()
            except queue.Empty:
                break
        self.first_timestamp = None
        self.points_received = 0
                
    def _handle_stroke_point(self, unused_addr, *args):
        """
        Internal callback for OSC messages.
        
        Expected args: [x, y, force, azimuth, altitude, timestamp]
        """
        if len(args) != 6:
            print(f"Warning: Expected 6 arguments, got {len(args)}")
            return
            
        # Unpack raw OSC data
        raw_x, raw_y, raw_force, raw_azimuth, raw_altitude, raw_timestamp = args
        
        # Initialize relative timestamp on first point
        if self.first_timestamp is None:
            self.first_timestamp = raw_timestamp
            
        # Convert to relative timestamp (seconds since stroke start)
        relative_t = raw_timestamp - self.first_timestamp
        
        # Create StrokePoint
        point = StrokePoint(
            x=float(raw_x),
            y=float(raw_y),
            force=float(raw_force),
            azimuth=float(raw_azimuth),
            altitude=float(raw_altitude),
            t=float(relative_t)
        )
        
        self.points_received += 1
        
        # Either call callback or queue the point
        if self.callback:
            self.callback(point)
        else:
            self.point_queue.put(point)
            
        # Debug output (can be disabled for production)
        if self.points_received % 10 == 0:  # Print every 10th point
            print(f"   Received {self.points_received} points (latest: x={raw_x:.2f}, y={raw_y:.2f}, f={raw_force:.2f})")


def create_osc_point_stream(
    ip: str = "0.0.0.0",
    port: int = 5005,
    timeout: float = 0.1
):
    """
    Create an iterator that yields StrokePoint objects from OSC messages.
    
    This is a generator function that can be used with the streaming pipeline.
    It will block waiting for points, and yield None if no point arrives within timeout.
    
    Args:
        ip: IP address to bind to
        port: Port to listen on
        timeout: Maximum time to wait for each point
        
    Yields:
        StrokePoint objects as they arrive from OSC
        
    Example:
        >>> from sonify.io.osc_receiver import create_osc_point_stream
        >>> point_stream = create_osc_point_stream()
        >>> for point in point_stream:
        >>>     if point is None:
        >>>         break  # No more points
        >>>     print(f"Received: {point}")
    """
    receiver = OSCStrokeReceiver(ip, port)
    receiver.start()
    
    try:
        while True:
            point = receiver.get_point(timeout=timeout)
            if point is None:
                break  # Timeout - assume stroke is complete
            yield point
    finally:
        receiver.stop()


# Example usage
if __name__ == "__main__":
    import time
    
    print("Testing OSC Receiver")
    print("-" * 50)
    
    receiver = OSCStrokeReceiver(ip="0.0.0.0", port=5005)
    
    def on_point_received(point: StrokePoint):
        print(f"📍 Point: x={point.x:.3f}, y={point.y:.3f}, force={point.force:.3f}, t={point.t:.3f}s")
    
    receiver.start(callback=on_point_received)
    
    try:
        print("\nListening for stroke data...")
        print("Draw on your iPad to send data!")
        print("Press Ctrl+C to stop\n")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping...")
        receiver.stop()

