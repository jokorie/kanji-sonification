# Quick Start Guide - iOS App

This guide will get you up and running with the iOS app in **5 steps**.

## Prerequisites
- Mac with Xcode 14+ installed
- iPad with Apple Pencil
- Both devices on the same WiFi network

---

## Step 1: Install Python Dependencies

On your Mac/Linux machine:

```bash
cd /home/jokorie/kanji-sonification
pip install python-osc
```

---

## Step 2: Find Your Computer's IP Address

**On Mac:**
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

**On Linux:**
```bash
hostname -I
```

**Note this IP address** (e.g., `192.168.1.50`) - you'll need it for the iPad app.

---

## Step 3: Create Xcode Project

1. Open Xcode
2. Create new project: **File → New → Project**
3. Select **iOS → App**
4. Project settings:
   - Product Name: `KanjiSonification`
   - Team: Your team (or None for local testing)
   - Organization ID: `com.yourname.kanji`
   - Interface: **SwiftUI**
   - Language: **Swift**
   - Storage: None (uncheck Core Data/CloudKit)
5. Save in `/home/jokorie/kanji-sonification/ios-app/`

---

## Step 4: Add SwiftOSC Package

1. In Xcode: **File → Add Package Dependencies...**
2. Enter URL: `https://github.com/ExistentialAudio/SwiftOSC`
3. Click **Add Package**
4. Select target and **Add Package**

---

## Step 5: Replace Files

Copy all `.swift` files from the `KanjiSonification` folder into your Xcode project:

1. Delete the auto-generated `ContentView.swift` and `KanjiSonificationApp.swift`
2. Drag all `.swift` files from the folder into Xcode
3. When prompted, check **"Copy items if needed"**

Files to add:
- ✅ `KanjiSonificationApp.swift`
- ✅ `ContentView.swift`
- ✅ `OSCManager.swift`
- ✅ `KanjiCanvasView.swift`
- ✅ `SettingsView.swift`

---

## Step 6: Configure Info.plist

1. In Xcode, select your project → Select target
2. Click **Info** tab
3. Right-click in the list → **Raw Keys & Values**
4. Add these keys:

| Key | Type | Value |
|-----|------|-------|
| `NSLocalNetworkUsageDescription` | String | This app needs local network access to send stroke data to the rendering engine. |
| `UIRequiresFullScreen` | Boolean | YES |

5. Under **Supported Interface Orientations**, keep only Landscape Left and Landscape Right

---

## Step 7: Test!

### On Your Mac/Linux:

```bash
cd /home/jokorie/kanji-sonification
python test_osc_receiver.py
```

You should see:
```
🎵 OSC Receiver listening on 0.0.0.0:5005
   Waiting for stroke data from iOS app...
```

### On Your iPad:

1. Connect iPad to Mac via USB
2. In Xcode, select your iPad as the target
3. Click **Run** (⌘R)
4. The app will install and launch
5. Tap the **gear icon** → Enter your Mac's IP and port 5005
6. Tap **Save Configuration**
7. Tap **Test Connection**
8. Draw a stroke with Apple Pencil

### On Your Mac - You Should See:

```
📍 Point: x=0.524, y=0.312, force=0.450, t=0.000s
📍 Point: x=0.528, y=0.315, force=0.460, t=0.016s
📍 Point: x=0.532, y=0.318, force=0.470, t=0.032s
...
```

---

## Troubleshooting

### "No data received"
- ✅ Both devices on same WiFi?
- ✅ Firewall disabled on Mac?
- ✅ IP address correct?
- ✅ Port 5005 not in use by another app?

### "Build failed"
- ✅ SwiftOSC package added correctly?
- ✅ All 5 .swift files in project?
- ✅ Deployment target iOS 16.0+?

### "App crashes on launch"
- ✅ Check Xcode console for errors
- ✅ Verify all files copied correctly
- ✅ Clean build folder (⌘⇧K) and rebuild

---

## Next Steps

Once you have data flowing:

1. **Integrate with your audio engine:**
   - Modify `test_osc_receiver.py` to use your actual rendering pipeline
   - See `sonify/pipeline/render_online.py` for streaming examples

2. **Adjust canvas size:**
   - In `test_osc_receiver.py`, change `CANVAS_SIZE` to match your iPad's resolution
   - Or keep normalized 0-1 coordinates (current default)

3. **Optimize network:**
   - For lowest latency, create an ad-hoc network between Mac and iPad
   - Or use 5GHz WiFi instead of 2.4GHz

4. **Customize the app:**
   - Change stroke colors in `KanjiCanvasView.swift`
   - Add visual feedback or controls
   - Implement multi-stroke support

---

## Architecture

```
iPad (iOS App)                    Computer (Python)
┌─────────────────┐              ┌──────────────────┐
│  Touch Events   │              │  OSC Receiver    │
│      ↓          │   UDP/OSC    │       ↓          │
│  Normalize      │─────────────→│  StrokePoint     │
│      ↓          │  Port 5005   │       ↓          │
│  OSC Message    │              │  Sonification    │
│  /kanji/stroke  │              │       ↓          │
│  (x,y,f,az,alt) │              │  Audio Output    │
└─────────────────┘              └──────────────────┘
```

**OSC Message Format:**
- Address: `/kanji/stroke`
- Args: `[x, y, force, azimuth, altitude, timestamp]` (6 floats)
- All values normalized 0.0 - 1.0 (except angles in radians)

---

Happy Drawing! 🎨🎵

