import { describe, it, expect } from 'vitest';
import {
  linearMap,
  yToPitch,
  forceToAmplitude,
  xToPan,
  speedToVibratoDepth,
  speedToVibratoRate,
  mapFeaturesToSynthParams,
} from '../audio/mapping';
import { DEFAULT_SYNTH_CONFIG } from '../types';

// ─── linearMap ────────────────────────────────────────────────────────────────

describe('linearMap', () => {
  it('maps midpoint to midpoint of output range', () => {
    expect(linearMap(5, 0, 10, 0, 100)).toBe(50);
  });

  it('maps minimum input to minimum output', () => {
    expect(linearMap(0, 0, 10, 20, 40)).toBe(20);
  });

  it('maps maximum input to maximum output', () => {
    expect(linearMap(10, 0, 10, 20, 40)).toBe(40);
  });

  it('clamps values below the input minimum', () => {
    expect(linearMap(-5, 0, 10, 0, 100)).toBe(0);
  });

  it('clamps values above the input maximum', () => {
    expect(linearMap(20, 0, 10, 0, 100)).toBe(100);
  });

  it('returns the midpoint when inMin === inMax (avoids divide-by-zero)', () => {
    // t = 0.5 when inMin === inMax, so output = midpoint of [outMin, outMax]
    expect(linearMap(5, 5, 5, 0, 100)).toBe(50);
  });
});

// ─── yToPitch ─────────────────────────────────────────────────────────────────

describe('yToPitch', () => {
  it('maps y=0 (top of screen) to maxFreq when inverted', () => {
    expect(yToPitch(0, 220, 880, true)).toBe(880);
  });

  it('maps y=1 (bottom of screen) to minFreq when inverted', () => {
    expect(yToPitch(1, 220, 880, true)).toBe(220);
  });

  it('maps y=0.5 to the midpoint frequency when inverted', () => {
    expect(yToPitch(0.5, 220, 880, true)).toBeCloseTo(550, 5);
  });

  it('maps y=0 to minFreq when not inverted', () => {
    expect(yToPitch(0, 220, 880, false)).toBe(220);
  });

  it('maps y=1 to maxFreq when not inverted', () => {
    expect(yToPitch(1, 220, 880, false)).toBe(880);
  });

  it('uses DEFAULT_SYNTH_CONFIG range correctly', () => {
    const { minFreq, maxFreq } = DEFAULT_SYNTH_CONFIG;
    expect(yToPitch(0, minFreq, maxFreq, true)).toBe(maxFreq);
    expect(yToPitch(1, minFreq, maxFreq, true)).toBe(minFreq);
  });
});

// ─── forceToAmplitude ─────────────────────────────────────────────────────────

describe('forceToAmplitude', () => {
  it('maps force=0 to minAmp', () => {
    expect(forceToAmplitude(0, 0.1, 0.6)).toBeCloseTo(0.1, 5);
  });

  it('maps force=1 to maxAmp', () => {
    expect(forceToAmplitude(1, 0.1, 0.6)).toBeCloseTo(0.6, 5);
  });

  it('clamps force above 1 to maxAmp', () => {
    expect(forceToAmplitude(2, 0.1, 0.6)).toBeCloseTo(0.6, 5);
  });

  it('clamps negative force to minAmp', () => {
    expect(forceToAmplitude(-0.5, 0.1, 0.6)).toBeCloseTo(0.1, 5);
  });

  it('is monotonically increasing (more force → more amplitude)', () => {
    const low = forceToAmplitude(0.3, 0.1, 0.6);
    const high = forceToAmplitude(0.7, 0.1, 0.6);
    expect(high).toBeGreaterThan(low);
  });

  it('applies the exponential curve (force=0.5 is less than halfway)', () => {
    // With exponent > 1, midpoint force should map to less than midpoint amplitude
    const mid = forceToAmplitude(0.5, 0, 1);
    expect(mid).toBeLessThan(0.5);
  });
});

// ─── xToPan ───────────────────────────────────────────────────────────────────

describe('xToPan', () => {
  it('maps x=0 (left edge) to -1', () => {
    expect(xToPan(0)).toBe(-1);
  });

  it('maps x=1 (right edge) to +1', () => {
    expect(xToPan(1)).toBe(1);
  });

  it('maps x=0.5 (center) to 0', () => {
    expect(xToPan(0.5)).toBe(0);
  });

  it('clamps x below 0', () => {
    expect(xToPan(-1)).toBe(-1);
  });

  it('clamps x above 1', () => {
    expect(xToPan(2)).toBe(1);
  });
});

// ─── speedToVibratoDepth ──────────────────────────────────────────────────────

describe('speedToVibratoDepth', () => {
  it('returns 0 at speed=0', () => {
    expect(speedToVibratoDepth(0, 2.0, 8)).toBe(0);
  });

  it('returns maxDepth at speed=maxSpeed', () => {
    expect(speedToVibratoDepth(2.0, 2.0, 8)).toBe(8);
  });

  it('clamps speed above maxSpeed to maxDepth', () => {
    expect(speedToVibratoDepth(10, 2.0, 8)).toBe(8);
  });

  it('returns 0 when maxSpeed is 0 (avoids divide-by-zero)', () => {
    expect(speedToVibratoDepth(1, 0, 8)).toBe(0);
  });

  it('is proportional to speed within range', () => {
    const half = speedToVibratoDepth(1.0, 2.0, 8);
    expect(half).toBeCloseTo(4, 5);
  });
});

// ─── speedToVibratoRate ───────────────────────────────────────────────────────

describe('speedToVibratoRate', () => {
  it('returns minRate at speed=0', () => {
    expect(speedToVibratoRate(0, 2.0, 3, 7)).toBe(3);
  });

  it('returns maxRate at speed=maxSpeed', () => {
    expect(speedToVibratoRate(2.0, 2.0, 3, 7)).toBe(7);
  });

  it('clamps speed above maxSpeed to maxRate', () => {
    expect(speedToVibratoRate(100, 2.0, 3, 7)).toBe(7);
  });

  it('returns the midpoint rate at half speed', () => {
    expect(speedToVibratoRate(1.0, 2.0, 3, 7)).toBeCloseTo(5, 5);
  });
});

// ─── mapFeaturesToSynthParams ─────────────────────────────────────────────────

describe('mapFeaturesToSynthParams', () => {
  const baseFeatures = {
    t: 0,
    xN: 0.5,
    yN: 0.5,
    force: 0.5,
    speed: 0,
    direction_rad: 0,
    direction_deg: 0,
    curvature: 0,
    azimuth: 0,
    altitude: Math.PI / 2,
  };

  it('returns a SynthParams with all required fields', () => {
    const params = mapFeaturesToSynthParams(baseFeatures);
    expect(params).toHaveProperty('frequency');
    expect(params).toHaveProperty('amplitude');
    expect(params).toHaveProperty('pan');
    expect(params).toHaveProperty('vibratoDepth');
    expect(params).toHaveProperty('vibratoRate');
  });

  it('center X produces pan=0', () => {
    const params = mapFeaturesToSynthParams({ ...baseFeatures, xN: 0.5 });
    expect(params.pan).toBe(0);
  });

  it('left X produces negative pan', () => {
    const params = mapFeaturesToSynthParams({ ...baseFeatures, xN: 0 });
    expect(params.pan).toBe(-1);
  });

  it('right X produces positive pan', () => {
    const params = mapFeaturesToSynthParams({ ...baseFeatures, xN: 1 });
    expect(params.pan).toBe(1);
  });

  it('frequency is within the configured range', () => {
    const { minFreq, maxFreq } = DEFAULT_SYNTH_CONFIG;
    for (const yN of [0, 0.25, 0.5, 0.75, 1]) {
      const { frequency } = mapFeaturesToSynthParams({ ...baseFeatures, yN });
      expect(frequency).toBeGreaterThanOrEqual(minFreq);
      expect(frequency).toBeLessThanOrEqual(maxFreq);
    }
  });

  it('amplitude is within the configured range', () => {
    const { minAmp, maxAmp } = DEFAULT_SYNTH_CONFIG;
    for (const force of [0, 0.5, 1]) {
      const { amplitude } = mapFeaturesToSynthParams({ ...baseFeatures, force });
      expect(amplitude).toBeGreaterThanOrEqual(minAmp);
      expect(amplitude).toBeLessThanOrEqual(maxAmp);
    }
  });

  it('zero speed produces zero vibratoDepth', () => {
    const params = mapFeaturesToSynthParams({ ...baseFeatures, speed: 0 });
    expect(params.vibratoDepth).toBe(0);
  });

  it('max speed produces max vibratoDepth', () => {
    const { maxSpeed, vibratoMaxDepth } = DEFAULT_SYNTH_CONFIG;
    const params = mapFeaturesToSynthParams({ ...baseFeatures, speed: maxSpeed });
    expect(params.vibratoDepth).toBe(vibratoMaxDepth);
  });
});
