//
//  KanjiCanvasView.swift
//  KanjiSonification
//
//  Canvas view that captures Apple Pencil input and sends OSC data.
//

import SwiftUI
import PencilKit

struct KanjiCanvasView: UIViewRepresentable {
    @EnvironmentObject var oscManager: OSCManager
    @Binding var canvasView: PKCanvasView
    
    func makeUIView(context: Context) -> PKCanvasView {
        canvasView.tool = PKInkingTool(.pen, color: .black, width: 3)
        canvasView.drawingPolicy = .pencilOnly  // Only accept Apple Pencil input
        canvasView.backgroundColor = .white
        canvasView.isOpaque = true
        
        // Set delegate to capture touch events
        canvasView.delegate = context.coordinator
        
        return canvasView
    }
    
    func updateUIView(_ uiView: PKCanvasView, context: Context) {
        // No updates needed
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }
    
    class Coordinator: NSObject, PKCanvasViewDelegate {
        var parent: KanjiCanvasView
        
        init(_ parent: KanjiCanvasView) {
            self.parent = parent
        }
        
        // This fires when drawing updates
        func canvasViewDrawingDidChange(_ canvasView: PKCanvasView) {
            // We'll capture points in a custom gesture instead
        }
    }
}

// MARK: - Custom Canvas with Touch Tracking
/// Custom UIView that intercepts touch events for Apple Pencil
class TouchTrackingCanvasView: UIView {
    var oscManager: OSCManager?
    var strokeStartTime: TimeInterval?
    
    // Visual feedback path
    private var currentPath = UIBezierPath()
    private var pathLayer = CAShapeLayer()
    
    override init(frame: CGRect) {
        super.init(frame: frame)
        setupLayer()
    }
    
    required init?(coder: NSCoder) {
        super.init(coder: coder)
        setupLayer()
    }
    
    private func setupLayer() {
        backgroundColor = .white
        
        pathLayer.strokeColor = UIColor.black.cgColor
        pathLayer.fillColor = UIColor.clear.cgColor
        pathLayer.lineWidth = 3.0
        pathLayer.lineCap = .round
        pathLayer.lineJoin = .round
        
        layer.addSublayer(pathLayer)
    }
    
    // MARK: - Touch Handling
    
    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard let touch = touches.first, touch.type == .pencil else { return }
        
        strokeStartTime = touch.timestamp
        currentPath = UIBezierPath()
        
        let location = touch.location(in: self)
        currentPath.move(to: location)
        
        // Send first point
        sendTouchData(touch)
    }
    
    override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard let touch = touches.first, touch.type == .pencil else { return }
        
        let location = touch.location(in: self)
        currentPath.addLine(to: location)
        
        // Update visual feedback
        pathLayer.path = currentPath.cgPath
        
        // Send touch data via OSC
        sendTouchData(touch)
    }
    
    override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard let touch = touches.first, touch.type == .pencil else { return }
        
        // Send final point
        sendTouchData(touch)
        strokeStartTime = nil
    }
    
    override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent?) {
        strokeStartTime = nil
    }
    
    // MARK: - Data Extraction & Sending
    
    private func sendTouchData(_ touch: UITouch) {
        guard let oscManager = oscManager else { return }
        
        let location = touch.location(in: self)
        let w = bounds.width
        let h = bounds.height
        
        // Normalize X and Y to 0.0 - 1.0 range
        let x = Float(location.x / w)
        let y = Float(location.y / h)
        
        // Normalize Force (0 to 1)
        let maxForce = touch.maximumPossibleForce > 0 ? touch.maximumPossibleForce : 1.0
        let force = Float(touch.force / maxForce)
        
        // Extract azimuth and altitude
        let azimuth = Float(touch.azimuthAngle(in: self))
        let altitude = Float(touch.altitudeAngle)
        
        // Timestamp (device uptime)
        let timestamp = Float(touch.timestamp)
        
        // Send via OSC
        oscManager.sendStrokePoint(
            x: x,
            y: y,
            force: force,
            azimuth: azimuth,
            altitude: altitude,
            timestamp: timestamp
        )
    }
    
    // MARK: - Public Methods
    
    func clearCanvas() {
        currentPath = UIBezierPath()
        pathLayer.path = nil
        strokeStartTime = nil
    }
}

// MARK: - SwiftUI Wrapper
struct TouchTrackingCanvas: UIViewRepresentable {
    @EnvironmentObject var oscManager: OSCManager
    let onClear: () -> Void
    
    func makeUIView(context: Context) -> TouchTrackingCanvasView {
        let view = TouchTrackingCanvasView()
        view.oscManager = oscManager
        return view
    }
    
    func updateUIView(_ uiView: TouchTrackingCanvasView, context: Context) {
        // Update if needed
    }
    
    static func dismantleUIView(_ uiView: TouchTrackingCanvasView, coordinator: ()) {
        uiView.clearCanvas()
    }
}

