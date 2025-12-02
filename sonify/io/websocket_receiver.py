"""
WebSocket receiver for real-time stroke data from web frontend.

Receives stroke points via WebSocket protocol and converts them to StrokePoint objects.
This allows iPad Safari to send Apple Pencil data to the Python audio engine.
"""

import asyncio
import json
import threading
import queue
from typing import Optional, Callable
from sonify.io.load_pencilkit import StrokePoint

import websockets
from websockets.server import serve


class WebSocketStrokeReceiver:
    """
    Receives stroke points from web frontend via WebSocket protocol.
    
    Listens for JSON messages and converts them to StrokePoint objects
    that can be fed into the streaming pipeline.
    
    The web frontend sends JSON with: {x, y, force, azimuth, altitude, t}
    where x and y are normalized to 0-1 range.
    """
    
    def __init__(self, ip: str = "0.0.0.0", port: int = 8765):
        """
        Initialize WebSocket receiver.
        
        Args:
            ip: IP address to bind to (0.0.0.0 for all interfaces)
            port: Port to listen on (default 8765)
        """
        self.ip = ip
        self.port = port
        self.point_queue: queue.Queue[StrokePoint] = queue.Queue()
        self.callback: Optional[Callable[[StrokePoint], None]] = None
        self.first_timestamp: Optional[float] = None
        self.points_received = 0
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._server_thread: Optional[threading.Thread] = None
        self._running = False
        self._connected_clients: set[websockets.WebSocketServerProtocol] = set()
        
    def start(self, callback: Optional[Callable[[StrokePoint], None]] = None):
        """
        Start the WebSocket server in a background thread.
        
        Args:
            callback: Optional callback function to call when a point is received.
                      If not provided, points are queued and can be retrieved with get_point().
        """
        self.callback = callback
        self.first_timestamp = None
        self._running = True
        
        # Start server in a background thread with its own event loop
        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._server_thread.start()
        
        print(f"🌐 WebSocket Receiver listening on ws://{self.ip}:{self.port}")
        print(f"   Waiting for connection from iPad browser...")
        
    def stop(self):
        """Stop the WebSocket server."""
        self._running = False
        
        # Stop the event loop
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
            
        if self._server_thread:
            self._server_thread.join(timeout=2.0)
            self._server_thread = None
            
        print("WebSocket Receiver stopped")
        
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
        
    def _run_server(self):
        """Run the WebSocket server (called in background thread)."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(self._serve())
        except Exception as e:
            if self._running:  # Only print if not intentionally stopped
                print(f"WebSocket server error: {e}")
        finally:
            self._loop.close()
            
    async def _serve(self):
        """Async WebSocket server coroutine."""
        async with serve(self._handle_client, self.ip, self.port):
            # Run until stopped
            while self._running:
                await asyncio.sleep(0.1)
                
    async def _handle_client(self, websocket):
        """Handle a connected WebSocket client."""
        client_addr = websocket.remote_address
        self._connected_clients.add(websocket)
        print(f"📱 iPad connected from {client_addr}")
        
        try:
            async for message in websocket:
                if not self._running:
                    break
                self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self._connected_clients.discard(websocket)
            print(f"📱 iPad disconnected from {client_addr}")
            
    def _handle_message(self, message: str):
        """
        Handle incoming JSON message from web frontend.
        
        Expected format: {x, y, force, azimuth, altitude, t}
        """
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON received: {message[:50]}")
            return
                    
        # Extract fields with defaults
        raw_x = data['x']
        raw_y = data['y']
        raw_force = data['force']
        raw_azimuth = data['azimuth']
        raw_altitude = data['altitude']
        raw_timestamp = data['t']
        
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
        if self.points_received % 20 == 0:  # Print every 20th point
            print(f"   Received {self.points_received} points (latest: x={raw_x:.2f}, y={raw_y:.2f}, f={raw_force:.2f})")


def create_websocket_point_stream(
    ip: str = "0.0.0.0",
    port: int = 8765,
    timeout: float = 0.1
):
    """
    Create an iterator that yields StrokePoint objects from WebSocket messages.
    
    This is a generator function that can be used with the streaming pipeline.
    It will block waiting for points, and yield None if no point arrives within timeout.
    
    Args:
        ip: IP address to bind to
        port: Port to listen on
        timeout: Maximum time to wait for each point
        
    Yields:
        StrokePoint objects as they arrive from WebSocket
    """
    receiver = WebSocketStrokeReceiver(ip, port)
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
    
    print("Testing WebSocket Receiver")
    print("-" * 50)
    
    receiver = WebSocketStrokeReceiver(ip="0.0.0.0", port=8765)
    
    def on_point_received(point: StrokePoint):
        print(f"📍 Point: x={point.x:.3f}, y={point.y:.3f}, force={point.force:.3f}, t={point.t:.3f}s")
    
    receiver.start(callback=on_point_received)
    
    try:
        print("\nListening for stroke data...")
        print("Open the web app on your iPad to send data!")
        print("Press Ctrl+C to stop\n")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping...")
        receiver.stop()

