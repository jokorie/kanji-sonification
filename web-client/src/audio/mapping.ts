/**
 * Audio parameter mapping functions.
 * 
 * Maps spatial/kinematic features to synthesis parameters.
 */

import { PointFeatures, SynthParams, SynthConfig, DEFAULT_SYNTH_CONFIG } from '../types';

/**
 * Linear interpolation from input range to output range.
 */
export function linearMap(
  value: number,
  inMin: number,
  inMax: number,
  outMin: number,
  outMax: number
): number {
  // Normalize to [0, 1]
  const t = inMax === inMin ? 0.5 : (value - inMin) / (inMax - inMin);
  
  // Clamp
  const tClamped = Math.max(0, Math.min(1, t));
  
  // Map to output
  return outMin + tClamped * (outMax - outMin);
}

/**
 * Map Y coordinate to pitch.
 * Higher Y (down on screen) → lower pitch (inverted by default)
 */
export function yToPitch(
  yNormalized: number,
  minFreq: number,
  maxFreq: number,
  invert: boolean = true
): number {
  const y = invert ? 1 - yNormalized : yNormalized;
  return linearMap(y, 0, 1, minFreq, maxFreq);
}

/**
 * Map force/pressure to amplitude with optional exponential scaling.
 */
export function forceToAmplitude(
  force: number,
  minAmp: number,
  maxAmp: number,
  exponent: number = 1.5
): number {
  const forceClamped = Math.max(0, Math.min(1, force));
  const scaled = Math.pow(forceClamped, exponent);
  return minAmp + scaled * (maxAmp - minAmp);
}

/**
 * Map X coordinate to stereo pan.
 * Returns value in [-1, 1] where -1=left, 0=center, 1=right
 */
export function xToPan(xNormalized: number): number {
  const xClamped = Math.max(0, Math.min(1, xNormalized));
  return (xClamped * 2) - 1; // Map [0,1] to [-1,1]
}

/**
 * Map speed to vibrato depth (Hz deviation).
 */
export function speedToVibratoDepth(
  speed: number,
  maxSpeed: number,
  maxDepth: number
): number {
  const speedNormalized = maxSpeed > 0 ? Math.min(speed / maxSpeed, 1) : 0;
  return speedNormalized * maxDepth;
}

/**
 * Map speed to vibrato rate (Hz).
 */
export function speedToVibratoRate(
  speed: number,
  maxSpeed: number,
  minRate: number,
  maxRate: number
): number {
  const speedNormalized = maxSpeed > 0 ? Math.min(speed / maxSpeed, 1) : 0;
  return linearMap(speedNormalized, 0, 1, minRate, maxRate);
}

/**
 * Map point features to synthesis parameters.
 */
export function mapFeaturesToSynthParams(
  features: PointFeatures,
  config: SynthConfig = DEFAULT_SYNTH_CONFIG
): SynthParams {
  return {
    frequency: yToPitch(features.yN, config.minFreq, config.maxFreq, true),
    amplitude: forceToAmplitude(features.force, config.minAmp, config.maxAmp),
    pan: xToPan(features.xN),
    vibratoDepth: speedToVibratoDepth(features.speed, config.maxSpeed, config.vibratoMaxDepth),
    vibratoRate: speedToVibratoRate(
      features.speed, 
      config.maxSpeed, 
      config.vibratoMinRate, 
      config.vibratoMaxRate
    ),
  };
}

