"""I/O module for loading and saving stroke data."""

from sonify.io.load_pencilkit import StrokePoint, Stroke, Drawing, Canvas
from sonify.io.load_pencilkit import load_pencilkit_json, save_drawing_json
from sonify.io.osc_receiver import OSCStrokeReceiver, create_osc_point_stream

# WebSocket receiver (requires 'websockets' package)
from sonify.io.websocket_receiver import WebSocketStrokeReceiver, create_websocket_point_stream

