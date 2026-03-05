/**
 * Template playback system.
 * 
 * Plays back pre-recorded kanji strokes through the synthesizer.
 */

import { StrokePoint, DEFAULT_SYNTH_CONFIG } from '../types';
import { KanjiTemplate, getTemplate } from './kanji-data';
import { KanjiSynth } from '../audio/synth';
import { StreamingFeatureExtractor } from '../features/kinematics';
import { mapFeaturesToSynthParams, yToPitch, forceToAmplitude } from '../audio/mapping';

/**
 * Uniform normalization frame for a radical.
 *
 * Both axes are scaled by the same factor (the larger extent), so the
 * directional character of strokes is preserved — a mostly-vertical stroke
 * still sounds mostly-vertical after remapping.
 */
interface RadicalFrame {
  centerX: number;  // center of the bounding box
  centerY: number;
  extent: number;   // half-size of the larger dimension (uniform scale)
}

/**
 * Build a map from stroke index to the uniform normalization frame of its radical.
 * Strokes not assigned to any radical are absent from the map (fall back to global coords).
 */
function computeRadicalBoundsMap(template: KanjiTemplate): Map<number, RadicalFrame> {
  const map = new Map<number, RadicalFrame>();

  for (const radical of template.radicals) {
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;

    for (const idx of radical.strokeIndices) {
      for (const [x, y] of template.strokes[idx]) {
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
    }

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    const extent = Math.max(maxX - minX, maxY - minY) / 2;

    const frame: RadicalFrame = { centerX, centerY, extent };
    for (const idx of radical.strokeIndices) {
      map.set(idx, frame);
    }
  }

  return map;
}

export interface PlaybackOptions {
  /** Duration per stroke in milliseconds */
  strokeDuration: number;
  /** Pause between strokes in milliseconds */
  strokePause: number;
  /** Constant pressure to use (0-1) */
  pressure: number;
  /** Callback when a point is played (for visualization) */
  onPoint?: (point: StrokePoint, strokeIndex: number) => void;
  /** Callback when stroke starts */
  onStrokeStart?: (strokeIndex: number) => void;
  /** Callback when stroke ends */
  onStrokeEnd?: (strokeIndex: number) => void;
  /** Callback when playback completes */
  onComplete?: () => void;
}

const DEFAULT_OPTIONS: PlaybackOptions = {
  strokeDuration: 500,  // 500ms per stroke
  strokePause: 200,     // 200ms pause between strokes
  pressure: 0.6,        // Constant medium pressure
};

export class TemplatePlayer {
  private synth: KanjiSynth;
  private featureExtractor: StreamingFeatureExtractor;
  private isPlaying: boolean = false;
  private abortController: AbortController | null = null;

  constructor(synth: KanjiSynth) {
    this.synth = synth;
    this.featureExtractor = new StreamingFeatureExtractor(0.3);
  }

  /**
   * Play a kanji template
   */
  async play(character: string, options: Partial<PlaybackOptions> = {}): Promise<void> {
    const template = getTemplate(character);
    if (!template) {
      console.warn(`No template found for character: ${character}`);
      return;
    }

    await this.playTemplate(template, options);
  }

  /**
   * Play a template directly
   */
  async playTemplate(template: KanjiTemplate, options: Partial<PlaybackOptions> = {}): Promise<void> {
    if (this.isPlaying) {
      this.stop();
    }

    const opts = { ...DEFAULT_OPTIONS, ...options };
    this.isPlaying = true;
    this.abortController = new AbortController();

    console.log(`🎬 Playing template: ${template.character} (${template.reading})`);

    const radicalBounds = computeRadicalBoundsMap(template);

    try {
      for (let strokeIndex = 0; strokeIndex < template.strokes.length; strokeIndex++) {
        if (!this.isPlaying) break;

        const stroke = template.strokes[strokeIndex];
        const frame = radicalBounds.get(strokeIndex) ?? null;
        await this.playStroke(stroke, strokeIndex, opts, frame);

        // Pause between strokes (except after last)
        if (strokeIndex < template.strokes.length - 1) {
          await this.sleep(opts.strokePause);
        }
      }

      opts.onComplete?.();
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        console.error('Playback error:', e);
      }
    } finally {
      this.isPlaying = false;
      this.abortController = null;
    }
  }

  /**
   * Play a single stroke
   */
  private async playStroke(
    points: number[][],
    strokeIndex: number,
    opts: PlaybackOptions,
    frame: RadicalFrame | null = null
  ): Promise<void> {
    if (points.length === 0) return;

    opts.onStrokeStart?.(strokeIndex);
    this.featureExtractor.reset();

    // Calculate time per point
    const timePerPoint = opts.strokeDuration / points.length;

    // Start synth with first point
    const firstPoint = this.createStrokePoint(points[0], 0, opts.pressure, frame);
    const initialParams = {
      frequency: yToPitch(firstPoint.y, DEFAULT_SYNTH_CONFIG.minFreq, DEFAULT_SYNTH_CONFIG.maxFreq, true),
      amplitude: forceToAmplitude(firstPoint.force, DEFAULT_SYNTH_CONFIG.minAmp, DEFAULT_SYNTH_CONFIG.maxAmp),
      pan: firstPoint.x * 2 - 1,
      vibratoDepth: 0,
      vibratoRate: 5,
    };
    this.synth.startSound(initialParams);

    // Play through all points
    for (let i = 0; i < points.length; i++) {
      if (!this.isPlaying) break;

      const t = (i / (points.length - 1)) * (opts.strokeDuration / 1000);

      // Original coords for visualization; remapped coords for sonification
      const displayPoint = this.createStrokePoint(points[i], t, opts.pressure, null);
      const synthPoint = this.createStrokePoint(points[i], t, opts.pressure, frame);

      // Notify visualization with original coordinates
      opts.onPoint?.(displayPoint, strokeIndex);

      // Extract features and update synth with radical-frame coordinates
      const features = this.featureExtractor.update(synthPoint);
      if (features) {
        const synthParams = mapFeaturesToSynthParams(features);
        this.synth.update(synthParams);
      }

      // Wait for next point
      await this.sleep(timePerPoint);
    }

    this.synth.stopSound();
    opts.onStrokeEnd?.(strokeIndex);
  }

  /**
   * Create a StrokePoint from raw coordinates
   */
  private createStrokePoint(
    coords: number[],
    t: number,
    pressure: number,
    frame: RadicalFrame | null = null
  ): StrokePoint {
    let x = coords[0];
    let y = coords[1];

    if (frame && frame.extent > 0) {
      // Uniform scale: same factor for both axes, preserves directional character
      x = ((coords[0] - frame.centerX) / (2 * frame.extent)) + 0.5;
      y = ((coords[1] - frame.centerY) / (2 * frame.extent)) + 0.5;
    }

    return { x, y, force: pressure, azimuth: 0, altitude: Math.PI / 2, t };
  }

  /**
   * Stop playback
   */
  stop(): void {
    this.isPlaying = false;
    this.abortController?.abort();
    this.synth.stopSound();
  }

  /**
   * Check if currently playing
   */
  get playing(): boolean {
    return this.isPlaying;
  }

  /**
   * Sleep helper
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(resolve, ms);
      this.abortController?.signal.addEventListener('abort', () => {
        clearTimeout(timeout);
        reject(new DOMException('Aborted', 'AbortError'));
      });
    });
  }
}

