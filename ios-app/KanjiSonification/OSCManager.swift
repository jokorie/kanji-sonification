//
//  OSCManager.swift
//  KanjiSonification
//
//  Manages OSC communication with the Python rendering engine.
//

import Foundation
import SwiftOSC

/// Manages OSC client and sends stroke data to Python backend
class OSCManager: ObservableObject {
    // MARK: - Published Properties
    @Published var serverAddress: String {
        didSet {
            UserDefaults.standard.set(serverAddress, forKey: "serverAddress")
            updateClient()
        }
    }
    
    @Published var serverPort: Int {
        didSet {
            UserDefaults.standard.set(serverPort, forKey: "serverPort")
            updateClient()
        }
    }
    
    @Published var isConnected: Bool = false
    @Published var packetsSent: Int = 0
    @Published var lastError: String?
    
    // MARK: - Private Properties
    private var client: OSCClient?
    
    // MARK: - Initialization
    init() {
        // Load saved settings or use defaults
        self.serverAddress = UserDefaults.standard.string(forKey: "serverAddress") ?? "192.168.1.50"
        self.serverPort = UserDefaults.standard.integer(forKey: "serverPort")
        if self.serverPort == 0 {
            self.serverPort = 5005
        }
        
        updateClient()
    }
    
    // MARK: - Public Methods
    
    /// Send a stroke point to the Python backend
    /// - Parameters:
    ///   - x: Normalized x coordinate (0.0 - 1.0)
    ///   - y: Normalized y coordinate (0.0 - 1.0)
    ///   - force: Normalized force (0.0 - 1.0)
    ///   - azimuth: Azimuth angle in radians
    ///   - altitude: Altitude angle in radians
    ///   - timestamp: Device uptime timestamp in seconds
    func sendStrokePoint(
        x: Float,
        y: Float,
        force: Float,
        azimuth: Float,
        altitude: Float,
        timestamp: Float
    ) {
        guard let client = client else {
            lastError = "OSC client not initialized"
            return
        }
        
        // Create OSC message with the agreed-upon format
        let message = OSCMessage(
            OSCAddressPattern("/kanji/stroke"),
            x,
            y,
            force,
            azimuth,
            altitude,
            timestamp
        )
        
        // Send the message
        do {
            try client.send(message)
            
            DispatchQueue.main.async {
                self.packetsSent += 1
                self.isConnected = true
                self.lastError = nil
            }
        } catch {
            DispatchQueue.main.async {
                self.lastError = "Failed to send: \(error.localizedDescription)"
                self.isConnected = false
            }
        }
    }
    
    /// Test the connection by sending a test packet
    func testConnection() {
        sendStrokePoint(
            x: 0.5,
            y: 0.5,
            force: 0.5,
            azimuth: 0.0,
            altitude: Float.pi / 2,
            timestamp: Float(ProcessInfo.processInfo.systemUptime)
        )
    }
    
    /// Reset packet counter
    func resetCounter() {
        packetsSent = 0
    }
    
    // MARK: - Private Methods
    
    private func updateClient() {
        client = OSCClient(
            address: serverAddress,
            port: UInt16(serverPort)
        )
        isConnected = false
        lastError = nil
        
        print("OSC client configured: \(serverAddress):\(serverPort)")
    }
}

// MARK: - StrokePoint Extension
extension OSCManager {
    /// Convenience method to send a complete stroke point bundle
    func sendStrokePoint(_ point: StrokePointData) {
        sendStrokePoint(
            x: point.x,
            y: point.y,
            force: point.force,
            azimuth: point.azimuth,
            altitude: point.altitude,
            timestamp: point.timestamp
        )
    }
}

// MARK: - Data Models
struct StrokePointData {
    let x: Float
    let y: Float
    let force: Float
    let azimuth: Float
    let altitude: Float
    let timestamp: Float
}

