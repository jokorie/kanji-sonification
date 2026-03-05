/**
 * Core types for the Kanji Sonification system.
 */

/** A single point captured from Apple Pencil / pointer input */
export interface StrokePoint {
  x: number;        // X coordinate (normalized 0-1)
  y: number;        // Y coordinate (normalized 0-1)
  force: number;    // Pressure/force [0, 1]
  azimuth: number;  // Azimuth angle in radians
  altitude: number; // Altitude angle in radians
  t: number;        // Timestamp in seconds
}

/** Computed features for a single point */
export interface PointFeatures {
  t: number;            // Timestamp
  xN: number;           // Normalized X [0, 1]
  yN: number;           // Normalized Y [0, 1]
  force: number;        // Force/pressure [0, 1]
  speed: number;        // Speed (units per second)
  direction_rad: number;// Direction in radians [-π, π]
  direction_deg: number;// Direction in degrees
  curvature: number;    // Curvature (rate of direction change)
  azimuth: number;      // Pen azimuth
  altitude: number;     // Pen altitude
}

/** Audio synthesis parameters mapped from features */
export interface SynthParams {
  frequency: number;    // Pitch in Hz
  amplitude: number;    // Volume [0, 1]
  pan: number;          // Stereo pan [-1, 1]
  vibratoDepth: number; // Vibrato depth in Hz
  vibratoRate: number;  // Vibrato rate in Hz
}

/** Configuration for the synthesizer */
export interface SynthConfig {
  minFreq: number;      // Minimum frequency (Hz)
  maxFreq: number;      // Maximum frequency (Hz)
  minAmp: number;       // Minimum amplitude
  maxAmp: number;       // Maximum amplitude
  maxSpeed: number;     // Expected max speed for normalization
  vibratoMaxDepth: number;
  vibratoMinRate: number;
  vibratoMaxRate: number;
  smoothingTime: number; // Parameter smoothing time constant
}

/** Default synth configuration */
export const DEFAULT_SYNTH_CONFIG: SynthConfig = {
  minFreq: 220,        // A3
  maxFreq: 880,        // A5
  minAmp: 0.1,
  maxAmp: 0.6,
  maxSpeed: 2.0,
  vibratoMaxDepth: 8,
  vibratoMinRate: 3,
  vibratoMaxRate: 7,
  smoothingTime: 0.010, // 10ms - lower = less latency but more zipper noise
};

