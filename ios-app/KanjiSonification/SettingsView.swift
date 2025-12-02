//
//  SettingsView.swift
//  KanjiSonification
//
//  Settings screen for configuring OSC server connection.
//

import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var oscManager: OSCManager
    @Environment(\.dismiss) var dismiss
    
    @State private var localAddress: String = ""
    @State private var localPort: String = ""
    @State private var showingTestAlert = false
    
    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Server Configuration")) {
                    HStack {
                        Text("IP Address")
                        Spacer()
                        TextField("192.168.1.50", text: $localAddress)
                            .multilineTextAlignment(.trailing)
                            .keyboardType(.decimalPad)
                            .autocapitalization(.none)
                            .disableAutocorrection(true)
                    }
                    
                    HStack {
                        Text("Port")
                        Spacer()
                        TextField("5005", text: $localPort)
                            .multilineTextAlignment(.trailing)
                            .keyboardType(.numberPad)
                    }
                    
                    Button("Save Configuration") {
                        saveSettings()
                    }
                    .disabled(localAddress.isEmpty || localPort.isEmpty)
                }
                
                Section(header: Text("Connection Status")) {
                    HStack {
                        Text("Status")
                        Spacer()
                        HStack {
                            Circle()
                                .fill(oscManager.isConnected ? Color.green : Color.gray)
                                .frame(width: 10, height: 10)
                            Text(oscManager.isConnected ? "Connected" : "Not Connected")
                                .foregroundColor(.secondary)
                        }
                    }
                    
                    HStack {
                        Text("Packets Sent")
                        Spacer()
                        Text("\(oscManager.packetsSent)")
                            .foregroundColor(.secondary)
                    }
                    
                    if let error = oscManager.lastError {
                        HStack {
                            Text("Last Error")
                            Spacer()
                            Text(error)
                                .foregroundColor(.red)
                                .font(.caption)
                        }
                    }
                    
                    Button("Test Connection") {
                        testConnection()
                    }
                    
                    Button("Reset Counter") {
                        oscManager.resetCounter()
                    }
                }
                
                Section(header: Text("Network Information")) {
                    HStack {
                        Text("iPad IP")
                        Spacer()
                        Text(getIPAddress() ?? "Unknown")
                            .foregroundColor(.secondary)
                            .font(.caption)
                    }
                    
                    Text("Make sure your iPad and computer are on the same WiFi network.")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                
                Section(header: Text("Quick Setup")) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("On your Mac/PC, find your IP address:")
                            .font(.subheadline)
                            .fontWeight(.semibold)
                        
                        Text("Mac: System Preferences → Network")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        
                        Text("Linux: ifconfig or ip addr")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        
                        Text("Windows: ipconfig")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
            .onAppear {
                localAddress = oscManager.serverAddress
                localPort = String(oscManager.serverPort)
            }
            .alert("Connection Test", isPresented: $showingTestAlert) {
                Button("OK", role: .cancel) {}
            } message: {
                Text("Test packet sent! Check your Python console for received data.")
            }
        }
    }
    
    // MARK: - Helper Methods
    
    private func saveSettings() {
        oscManager.serverAddress = localAddress
        if let port = Int(localPort) {
            oscManager.serverPort = port
        }
    }
    
    private func testConnection() {
        oscManager.testConnection()
        showingTestAlert = true
    }
    
    private func getIPAddress() -> String? {
        var address: String?
        var ifaddr: UnsafeMutablePointer<ifaddrs>?
        
        if getifaddrs(&ifaddr) == 0 {
            var ptr = ifaddr
            while ptr != nil {
                defer { ptr = ptr?.pointee.ifa_next }
                
                guard let interface = ptr?.pointee else { continue }
                let addrFamily = interface.ifa_addr.pointee.sa_family
                
                if addrFamily == UInt8(AF_INET) {
                    let name = String(cString: interface.ifa_name)
                    if name == "en0" || name == "en1" {  // WiFi interfaces
                        var hostname = [CChar](repeating: 0, count: Int(NI_MAXHOST))
                        getnameinfo(
                            interface.ifa_addr,
                            socklen_t(interface.ifa_addr.pointee.sa_len),
                            &hostname,
                            socklen_t(hostname.count),
                            nil,
                            socklen_t(0),
                            NI_NUMERICHOST
                        )
                        address = String(cString: hostname)
                    }
                }
            }
            freeifaddrs(ifaddr)
        }
        
        return address
    }
}

#Preview {
    SettingsView()
        .environmentObject(OSCManager())
}

