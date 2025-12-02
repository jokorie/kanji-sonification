# Kanji Sonification iOS App

This is the iPad frontend for the Kanji Sonification project. It captures Apple Pencil strokes and sends them via OSC to the Python rendering engine.

## Setup Instructions

### 1. Open in Xcode
1. Open Xcode on your Mac
2. Select "Create a new Xcode project"
3. Choose "iOS" → "App"
4. Fill in:
   - Product Name: `KanjiSonification`
   - Team: Your developer team (or leave as "None" for local testing)
   - Organization Identifier: `com.yourname.kanji` (or whatever you prefer)
   - Interface: **SwiftUI**
   - Language: **Swift**
   - Storage: None (uncheck Core Data, CloudKit)
5. Save it in the `ios-app` folder

### 2. Add SwiftOSC Dependency
1. In Xcode, go to `File` → `Add Package Dependencies...`
2. Enter the URL: `https://github.com/ExistentialAudio/SwiftOSC`
3. Click "Add Package"
4. Select your target and click "Add Package"

### 3. Copy the Source Files
Replace the auto-generated files with the ones in this folder:
- `KanjiSonificationApp.swift` → Replace `KanjiSonificationApp.swift`
- `ContentView.swift` → Replace `ContentView.swift`
- `OSCManager.swift` → Add as new file
- `KanjiCanvasView.swift` → Add as new file
- `SettingsView.swift` → Add as new file

### 4. Configure Capabilities
1. Select your project in the navigator
2. Select your target
3. Go to "Signing & Capabilities"
4. Enable "Local Network" (allows OSC communication)

### 5. Update Info.plist
Add the following keys (Right-click Info.plist → Open As → Source Code):
```xml
<key>NSLocalNetworkUsageDescription</key>
<string>This app needs local network access to send stroke data to the rendering engine.</string>
<key>UIRequiresFullScreen</key>
<true/>
<key>UISupportedInterfaceOrientations</key>
<array>
    <string>UIInterfaceOrientationLandscapeLeft</string>
    <string>UIInterfaceOrientationLandscapeRight</string>
</array>
```

### 6. Run on iPad
1. Connect your iPad via USB
2. Select your iPad as the target device
3. Click Run (⌘R)
4. The app should launch on your iPad

## Usage

1. **Configure Server:** Tap the gear icon and enter your Python server's IP address and port (default: 5005)
2. **Draw:** Use Apple Pencil to draw kanji strokes on the canvas
3. **Clear:** Tap the clear button to reset the canvas

## OSC Protocol

**Address:** `/kanji/stroke`

**Arguments (6 floats):**
1. `x` (0.0 - 1.0, normalized to canvas)
2. `y` (0.0 - 1.0, normalized to canvas)
3. `force` (0.0 - 1.0, normalized pressure)
4. `azimuth` (radians)
5. `altitude` (radians)
6. `timestamp` (device uptime in seconds)

## Troubleshooting

**App won't build:**
- Make sure SwiftOSC is properly added as a package dependency
- Check that your deployment target is iOS 16.0+

**No data received in Python:**
- Verify both devices are on the same WiFi network
- Check the IP address is correct (use `ifconfig` or `ipconfig` on your Mac)
- Try pinging your Mac from another device to verify connectivity
- Check firewall settings on your Mac (System Preferences → Security & Privacy → Firewall)

**Laggy/dropped strokes:**
- Use a 5GHz WiFi network instead of 2.4GHz
- Consider creating an ad-hoc network between your Mac and iPad
- Move closer to the WiFi router

