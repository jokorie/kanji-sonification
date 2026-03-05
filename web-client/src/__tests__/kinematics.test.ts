import { describe, it, expect, beforeEach } from 'vitest';
import { StreamingFeatureExtractor } from '../features/kinematics';
import type { StrokePoint } from '../types';

function pt(x: number, y: number, t: number, force = 0.5): StrokePoint {
  return { x, y, force, azimuth: 0, altitude: Math.PI / 2, t };
}

describe('StreamingFeatureExtractor', () => {
  let extractor: StreamingFeatureExtractor;

  beforeEach(() => {
    extractor = new StreamingFeatureExtractor(0.3);
  });

  // ─── First point ───────────────────────────────────────────────────────────

  it('returns null for the first point (no previous point to diff against)', () => {
    expect(extractor.update(pt(0.5, 0.5, 0))).toBeNull();
  });

  // ─── Second point — basic feature presence ─────────────────────────────────

  it('returns features on the second point', () => {
    extractor.update(pt(0.0, 0.0, 0));
    const features = extractor.update(pt(0.1, 0.0, 0.1));
    expect(features).not.toBeNull();
  });

  it('passes through normalized coordinates unchanged', () => {
    extractor.update(pt(0.2, 0.3, 0));
    const features = extractor.update(pt(0.4, 0.6, 0.1));
    expect(features!.xN).toBeCloseTo(0.4, 5);
    expect(features!.yN).toBeCloseTo(0.6, 5);
  });

  it('passes through force unchanged', () => {
    extractor.update(pt(0, 0, 0, 0.7));
    const features = extractor.update(pt(0.1, 0, 0.1, 0.8));
    expect(features!.force).toBeCloseTo(0.8, 5);
  });

  // ─── Speed ─────────────────────────────────────────────────────────────────

  it('computes positive speed when the pen moves', () => {
    extractor.update(pt(0, 0, 0));
    const features = extractor.update(pt(0.1, 0, 0.1)); // dx=0.1, dt=0.1 → speed=1.0
    expect(features!.speed).toBeGreaterThan(0);
  });

  it('produces speed=0 when no movement occurs', () => {
    extractor.update(pt(0.5, 0.5, 0));
    const features = extractor.update(pt(0.5, 0.5, 0.1)); // same coords
    expect(features!.speed).toBe(0);
  });

  it('produces speed proportional to distance / time', () => {
    // With alpha=1 (no EMA smoothing) the first speed is raw.
    const fast = new StreamingFeatureExtractor(1.0);
    fast.update(pt(0, 0, 0));
    const features = fast.update(pt(0.3, 0.4, 0.5)); // distance=0.5, dt=0.5 → speed=1.0
    expect(features!.speed).toBeCloseTo(1.0, 5);
  });

  // ─── Direction ─────────────────────────────────────────────────────────────

  it('computes direction_deg in degrees equivalent to direction_rad', () => {
    extractor.update(pt(0, 0, 0));
    const features = extractor.update(pt(0.1, 0, 0.1));
    expect(features!.direction_deg).toBeCloseTo(
      (features!.direction_rad * 180) / Math.PI,
      5,
    );
  });

  it('moving right produces direction ~0 radians', () => {
    extractor.update(pt(0, 0.5, 0));
    const features = extractor.update(pt(0.1, 0.5, 0.1)); // purely rightward
    expect(features!.direction_rad).toBeCloseTo(0, 5);
  });

  it('moving down produces direction ~π/2 radians', () => {
    extractor.update(pt(0.5, 0, 0));
    const features = extractor.update(pt(0.5, 0.1, 0.1)); // purely downward
    expect(features!.direction_rad).toBeCloseTo(Math.PI / 2, 5);
  });

  it('moving left produces direction ~π radians', () => {
    extractor.update(pt(0.5, 0.5, 0));
    const features = extractor.update(pt(0.4, 0.5, 0.1)); // purely leftward
    expect(Math.abs(features!.direction_rad)).toBeCloseTo(Math.PI, 5);
  });

  // ─── Curvature ─────────────────────────────────────────────────────────────

  it('returns 0 curvature until 3 points have been seen', () => {
    extractor.update(pt(0, 0, 0));
    const features = extractor.update(pt(0.1, 0, 0.1));
    expect(features!.curvature).toBe(0);
  });

  it('computes near-zero curvature for a straight line', () => {
    extractor.update(pt(0.0, 0.5, 0));
    extractor.update(pt(0.1, 0.5, 0.1));
    const features = extractor.update(pt(0.2, 0.5, 0.2)); // collinear
    expect(features!.curvature).toBeCloseTo(0, 5);
  });

  it('computes non-zero curvature for a sharp turn', () => {
    extractor.update(pt(0.0, 0.5, 0));
    extractor.update(pt(0.1, 0.5, 0.1)); // going right
    const features = extractor.update(pt(0.1, 0.6, 0.2)); // sharp 90° turn down
    expect(features!.curvature).toBeGreaterThan(0);
  });

  // ─── EMA smoothing ─────────────────────────────────────────────────────────

  it('smoothed speed approaches raw speed over multiple points', () => {
    // alpha=0.3 means each update blends 30% new + 70% old
    const e = new StreamingFeatureExtractor(0.3);
    e.update(pt(0, 0, 0));
    const f1 = e.update(pt(0.1, 0, 0.1))!; // raw speed=1.0, smoothed starts at 1.0
    const f2 = e.update(pt(0.2, 0, 0.2))!; // raw speed=1.0, should stay ~1.0
    expect(f2.speed).toBeCloseTo(f1.speed, 2);
  });

  it('speed smoothing dampens a sudden spike', () => {
    // Establish a baseline speed then introduce a 10x spike
    const e = new StreamingFeatureExtractor(0.3);
    e.update(pt(0, 0, 0));
    e.update(pt(0.1, 0, 0.1)); // speed = 1.0, smoothed = 1.0
    const features = e.update(pt(0.2, 0, 0.01))!; // dt=0.01 → raw speed ≈ 10
    // With alpha=0.3: smoothed = 0.3*10 + 0.7*1.0 = 3.7 — much less than 10
    expect(features.speed).toBeLessThan(8);
  });

  // ─── reset() ───────────────────────────────────────────────────────────────

  it('returns null after reset (treats next point as stroke-start)', () => {
    extractor.update(pt(0, 0, 0));
    extractor.update(pt(0.1, 0, 0.1));
    extractor.reset();
    expect(extractor.update(pt(0.2, 0, 0.2))).toBeNull();
  });

  it('does not carry speed state across reset', () => {
    // Build up high speed
    extractor.update(pt(0, 0, 0));
    extractor.update(pt(1, 0, 0.01)); // very high speed
    extractor.reset();

    // New stroke starting from rest
    extractor.update(pt(0, 0, 0));
    const features = extractor.update(pt(0.1, 0, 0.5))!; // slow movement
    expect(features.speed).toBeLessThan(1);
  });
});
