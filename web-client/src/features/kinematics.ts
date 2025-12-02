/**
 * Streaming/incremental feature extraction for real-time sonification.
 * 
 * Computes kinematic features (speed, direction, curvature) incrementally
 * as points arrive, maintaining state between updates.
 */

import { StrokePoint, PointFeatures } from '../types';

/** State maintained for incremental feature extraction */
interface StreamingState {
  previousPoint: StrokePoint | null;
  previousDirection: number | null;
  pointHistory: StrokePoint[];
  smoothedSpeed: number;
  alpha: number; // EMA smoothing factor
}

/**
 * Compute instantaneous speed from current and previous point.
 */
function computeSpeed(current: StrokePoint, previous: StrokePoint): number {
  const dx = current.x - previous.x;
  const dy = current.y - previous.y;
  const dt = current.t - previous.t;

  if (dt <= 0) return 0;

  const distance = Math.sqrt(dx * dx + dy * dy);
  return distance / dt;
}

/**
 * Compute direction from previous to current point.
 * Returns direction in radians [-π, π]
 */
function computeDirection(current: StrokePoint, previous: StrokePoint): number {
  const dx = current.x - previous.x;
  const dy = current.y - previous.y;

  if (dx === 0 && dy === 0) return 0;

  return Math.atan2(dy, dx);
}

/**
 * Compute curvature from a sequence of points (needs at least 3 points).
 * Returns curvature (change in direction per unit length)
 */
function computeCurvature(points: StrokePoint[]): number {
  if (points.length < 3) return 0;

  const p0 = points[points.length - 3];
  const p1 = points[points.length - 2];
  const p2 = points[points.length - 1];

  // Direction from p0 to p1
  const dx1 = p1.x - p0.x;
  const dy1 = p1.y - p0.y;
  const dir1 = Math.atan2(dy1, dx1);

  // Direction from p1 to p2
  const dx2 = p2.x - p1.x;
  const dy2 = p2.y - p1.y;
  const dir2 = Math.atan2(dy2, dx2);

  // Change in direction
  let dTheta = dir2 - dir1;
  
  // Normalize to [-π, π]
  while (dTheta > Math.PI) dTheta -= 2 * Math.PI;
  while (dTheta < -Math.PI) dTheta += 2 * Math.PI;

  // Arc length from p1 to p2
  const ds = Math.sqrt(dx2 * dx2 + dy2 * dy2);

  return ds > 0 ? Math.abs(dTheta) / ds : 0;
}

/**
 * Incremental feature extractor for streaming points.
 * 
 * Maintains state between updates and computes features on-the-fly.
 */
export class StreamingFeatureExtractor {
  private state: StreamingState;

  constructor(alpha: number = 0.3) {
    this.state = {
      previousPoint: null,
      previousDirection: null,
      pointHistory: [],
      smoothedSpeed: 0,
      alpha,
    };
  }

  /** Reset state for a new stroke */
  reset(): void {
    this.state.previousPoint = null;
    this.state.previousDirection = null;
    this.state.pointHistory = [];
    this.state.smoothedSpeed = 0;
  }

  /**
   * Update with a new point and compute features.
   * 
   * @param point - New point to process
   * @returns PointFeatures if enough data is available, null for first point
   */
  update(point: StrokePoint): PointFeatures | null {
    // First point: just store it, no features yet
    if (this.state.previousPoint === null) {
      this.state.previousPoint = point;
      this.state.pointHistory.push(point);
      return null;
    }

    // Compute speed
    const speed = computeSpeed(point, this.state.previousPoint);

    // Apply EMA smoothing
    if (this.state.smoothedSpeed === 0) {
      this.state.smoothedSpeed = speed;
    } else {
      this.state.smoothedSpeed = 
        this.state.alpha * speed + (1 - this.state.alpha) * this.state.smoothedSpeed;
    }

    // Compute direction
    const directionRad = computeDirection(point, this.state.previousPoint);
    const directionDeg = (directionRad * 180) / Math.PI;

    // Update point history (keep last 3 points)
    this.state.pointHistory.push(point);
    if (this.state.pointHistory.length > 3) {
      this.state.pointHistory.shift();
    }

    // Compute curvature
    const curvature = computeCurvature(this.state.pointHistory);

    // Create point features
    const features: PointFeatures = {
      t: point.t,
      xN: point.x,
      yN: point.y,
      force: point.force,
      speed: this.state.smoothedSpeed,
      direction_rad: directionRad,
      direction_deg: directionDeg,
      curvature,
      azimuth: point.azimuth,
      altitude: point.altitude,
    };

    // Update state
    this.state.previousPoint = point;
    this.state.previousDirection = directionRad;

    return features;
  }
}

