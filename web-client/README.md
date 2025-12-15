# Kanji Sonification (Web Client)

## Overview

This project explores real-time **sonification of handwritten Japanese kanji**.  
An iPad (Apple Pencil) sends pen input directly to a **browser-based DSP engine** written in TypeScript using the **Web Audio API**, which turns stroke dynamics into sound in real time.

The original Python codebase (in `sonify/`) contains the offline and server-side sonification pipeline. The current focus of development is the **web client** in `web-client/`, which runs entirely in the browser.

---

## Status

- ✅ Real-time stroke capture from Apple Pencil using Pointer Events.
- ✅ Streaming feature extraction (speed, direction, curvature) in TypeScript.
- ✅ Web Audio synthesizer with pitch, amplitude, vibrato, and stereo panning mappings.
- ✅ Template playback for a small set of kanji (e.g. 一, 二, 三, 人, 大, 日, 月, 山, 川, 木, 火).
- ✅ Visual stroke guide (outline) of the selected template kanji on the canvas.
- ⬜ Audio → kanji “inverse” recognition: **conceptually designed, not yet implemented.**
- ⬜ Larger kanji template set and robust recognition / radical analysis.

---

## Requirements

- Node.js and npm installed on your development machine.
- iPad (or tablet) with a modern browser (Safari 15+ recommended).
- Access to the same local network between your dev machine and the iPad.

---

## Installation

From the project root:

```bash
cd web-client
npm install
```

This installs the TypeScript + Vite toolchain (no runtime dependencies beyond the browser).

---

## Running the Web Version

From `web-client/`:

```bash
npm run dev
```

Vite will start a dev server, typically on port `3000`. The terminal will print a URL like:

```text
Local:   http://localhost:3000/
Network: http://192.168.x.y:3000/
```

Use the **Network** URL on your iPad.

---

## Using the Web App (iPad)

1. **Open Safari** (or another modern browser) on your iPad.
2. Enter the Network URL from the dev server, e.g.:

   ```text
   http://192.168.x.y:3000/
   ```

3. When the page loads:

   - Tap **“ENABLE AUDIO”** in the modal. This is required to start the Web Audio `AudioContext` due to browser autoplay policies.
   - You should see:
     - A square **canvas** with a kanji stroke **guide** (faint red outline).
     - A **pressure bar** on the right.
     - A footer with:
       - `POINTS` (number of sampled points),
       - `PRESSURE` (current pressure),
       - `FREQ` (current pitch),
       - A **kanji selector dropdown**,
       - A **PLAY** button,
       - A **CLEAR** button.

4. **Drawing (live sonification):**

   - Use Apple Pencil on the canvas.
   - As you draw:
     - **Vertical position (Y)** controls pitch.
     - **Horizontal position (X)** controls stereo pan.
     - **Pressure** controls loudness.
     - **Speed** controls vibrato depth/rate.
   - Lifting the pen ends the stroke and quickly fades the sound out.

5. **Template playback (reference kanji):**
   - Choose a kanji from the dropdown (e.g. `人` or `大`).
   - Tap **▶ PLAY**:
     - The system plays back a canonical stroke sequence for that character through the same DSP engine.
     - The status dot and frequency readout will animate as strokes are “drawn” virtually.
   - Tap **■ STOP** to stop early.
   - Tap **CLEAR** to reset your drawing while keeping the current guide visible.

---

## Notes

- All DSP (feature extraction + synthesis) runs **entirely in the browser**; the server is only serving static files.
- The mapping is intentionally simple and transparent:
  - It is designed to be invertible for future work on **audio → kanji** recognition.
- The Python code in `sonify/` can still be used for offline rendering, analysis, or comparison, but is not required for running the web-based instrument.
