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

    console.log(`🎬 Playing template: ${template.character} (${template.meaning})`);

    try {
      for (let strokeIndex = 0; strokeIndex < template.strokes.length; strokeIndex++) {
        if (!this.isPlaying) break;

        const stroke = template.strokes[strokeIndex];
        await this.playStroke(stroke, strokeIndex, opts);

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
    opts: PlaybackOptions
  ): Promise<void> {
    if (points.length === 0) return;

    opts.onStrokeStart?.(strokeIndex);
    this.featureExtractor.reset();

    // Calculate time per point
    const timePerPoint = opts.strokeDuration / points.length;

    // Start synth with first point
    const firstPoint = this.createStrokePoint(points[0], 0, opts.pressure);
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
      const point = this.createStrokePoint(points[i], t, opts.pressure);

      // Notify visualization
      opts.onPoint?.(point, strokeIndex);

      // Extract features and update synth
      const features = this.featureExtractor.update(point);
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
  private createStrokePoint(coords: number[], t: number, pressure: number): StrokePoint {
    return {
      x: coords[0],
      y: coords[1],
      force: pressure,
      azimuth: 0,
      altitude: Math.PI / 2,
      t,
    };
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

