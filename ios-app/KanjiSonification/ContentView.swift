//
//  ContentView.swift
//  KanjiSonification
//
//  Main interface for drawing kanji strokes.
//

import SwiftUI

struct ContentView: View {
    @EnvironmentObject var oscManager: OSCManager
    @State private var showingSettings = false
    @State private var canvasKey = UUID()  // For forcing canvas refresh
    
    var body: some View {
        ZStack {
            // Canvas (full screen)
            TouchTrackingCanvas {
                canvasKey = UUID()
            }
            .id(canvasKey)
            .edgesIgnoringSafeArea(.all)
            
            // Overlay UI
            VStack {
                // Top bar
                HStack {
                    // Connection indicator
                    HStack(spacing: 8) {
                        Circle()
                            .fill(oscManager.isConnected ? Color.green : Color.red)
                            .frame(width: 12, height: 12)
                        Text("\(oscManager.packetsSent) pts")
                            .font(.system(size: 14, weight: .medium, design: .monospaced))
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(Color.white.opacity(0.9))
                    .cornerRadius(8)
                    
                    Spacer()
                    
                    // Settings button
                    Button(action: { showingSettings = true }) {
                        Image(systemName: "gear")
                            .font(.system(size: 24))
                            .foregroundColor(.primary)
                            .padding(12)
                            .background(Color.white.opacity(0.9))
                            .cornerRadius(8)
                    }
                }
                .padding()
                
                Spacer()
                
                // Bottom controls
                HStack {
                    Spacer()
                    
                    // Clear button
                    Button(action: clearCanvas) {
                        HStack {
                            Image(systemName: "trash")
                            Text("Clear")
                        }
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundColor(.white)
                        .padding(.horizontal, 20)
                        .padding(.vertical, 12)
                        .background(Color.red)
                        .cornerRadius(10)
                    }
                    
                    Spacer()
                }
                .padding(.bottom, 20)
            }
        }
        .sheet(isPresented: $showingSettings) {
            SettingsView()
        }
    }
    
    // MARK: - Actions
    
    private func clearCanvas() {
        canvasKey = UUID()  // Force canvas to recreate
    }
}

#Preview {
    ContentView()
        .environmentObject(OSCManager())
}

