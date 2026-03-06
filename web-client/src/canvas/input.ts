/**
 * Canvas input handling for Apple Pencil / pointer events.
 *
 * Captures high-frequency pen data using coalesced events.
 */

import { StrokePoint } from '../types';

export type PointCallback = (point: StrokePoint) => void;
export type StrokeStartCallback = () => void;
export type StrokeEndCallback = () => void;

export interface CanvasInputOptions {
  onPoint: PointCallback;
  onStrokeStart?: StrokeStartCallback;
  onStrokeEnd?: StrokeEndCallback;
  /** Called after each resize so callers can redraw overlays (e.g. kanji guide). */
  onResize?: () => void;
  drawOnCanvas?: boolean;
}

export class CanvasInput {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private options: CanvasInputOptions;

  private isDrawing = false;
  private strokeStartTime = 0;
  private currentPath: Array<{ x: number; y: number; pressure: number }> = [];

  // When false, drawGuide() is a no-op — used to hide the reference during quiz draw phase.
  showGuide = true;

  // Logical (CSS) pixel dimensions — kept as class state instead of stapled onto the DOM element.
  private logicalWidth = 0;
  private logicalHeight = 0;

  // Tracks the previous point during template playback drawing.
  private lastPlaybackPoint: { x: number; y: number } | null = null;

  // Stored so it can be removed in destroy().
  private readonly resizeHandler: () => void;

  constructor(canvas: HTMLCanvasElement, options: CanvasInputOptions) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d')!;
    this.options = { drawOnCanvas: true, ...options };

    // Fire onResize only on subsequent resizes, not during initial construction.
    // The caller is responsible for any initial guide/overlay drawing after construction.
    this.resizeHandler = () => {
      this.setupCanvas();
      this.options.onResize?.();
    };

    this.setupCanvas();
    this.bindEvents();
  }

  private setupCanvas(): void {
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;

    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.ctx.scale(dpr, dpr);

    this.logicalWidth = rect.width;
    this.logicalHeight = rect.height;

    this.ctx.lineCap = 'round';
    this.ctx.lineJoin = 'round';
  }

  private bindEvents(): void {
    this.canvas.addEventListener('pointerdown', this.handlePointerDown.bind(this));
    this.canvas.addEventListener('pointermove', this.handlePointerMove.bind(this));
    this.canvas.addEventListener('pointerup', this.handlePointerUp.bind(this));
    this.canvas.addEventListener('pointerleave', this.handlePointerUp.bind(this));
    this.canvas.addEventListener('pointercancel', this.handlePointerUp.bind(this));

    this.canvas.addEventListener('touchstart', e => e.preventDefault(), { passive: false });
    this.canvas.addEventListener('touchmove', e => e.preventDefault(), { passive: false });

    window.addEventListener('resize', this.resizeHandler);
  }

  private handlePointerDown(e: PointerEvent): void {
    if (e.pointerType === 'touch' && e.pressure === 0) return;

    this.isDrawing = true;
    this.strokeStartTime = performance.now() / 1000;
    this.currentPath = [];

    this.options.onStrokeStart?.();

    // Some platforms (e.g. mouse in Chrome) report pressure=0 on the pointerdown
    // event itself, even with a button held. Fall back to 0.5 so sound always
    // starts immediately on press, not only once the pointer starts moving.
    const rect = this.canvas.getBoundingClientRect();
    this.emitPoint(e, e.pressure > 0 ? e.pressure : 0.5, rect);
  }

  private handlePointerMove(e: PointerEvent): void {
    if (!this.isDrawing) return;
    if (e.pressure === 0) return;

    const events = e.getCoalescedEvents ? e.getCoalescedEvents() : [e];
    // Hoist out of the loop — getBoundingClientRect() forces a layout reflow.
    const rect = this.canvas.getBoundingClientRect();

    for (const p of events) {
      this.emitPoint(p, p.pressure, rect);
    }
  }

  private emitPoint(e: PointerEvent, pressure: number, rect: DOMRect): void {
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Use rect.width/height (current rendered size) rather than the stored logicalWidth/Height,
    // which may have been captured at a different layout moment (e.g. before a Safari reflow
    // triggered by setting canvas.height on iPad).
    const nX = x / rect.width;
    const nY = y / rect.height;

    const azimuth = (e as PointerEvent & { azimuthAngle?: number }).azimuthAngle ?? 0;
    const altitude = (e as PointerEvent & { altitudeAngle?: number }).altitudeAngle ?? Math.PI / 2;

    const point: StrokePoint = {
      x: nX,
      y: nY,
      force: pressure,
      azimuth,
      altitude,
      t: performance.now() / 1000 - this.strokeStartTime,
    };

    this.options.onPoint(point);
    this.currentPath.push({ x, y, pressure });

    if (this.options.drawOnCanvas) {
      this.drawPoint(x, y, pressure);
    }
  }

  private handlePointerUp(_e: PointerEvent): void {
    if (!this.isDrawing) return;

    this.isDrawing = false;
    this.options.onStrokeEnd?.();
  }

  private drawPoint(x: number, y: number, pressure: number): void {
    const radius = pressure * 4 + 0.5;
    const alpha = 0.3 + pressure * 0.7;

    this.ctx.fillStyle = `rgba(232, 228, 220, ${alpha})`;
    this.ctx.beginPath();
    this.ctx.arc(x, y, radius, 0, Math.PI * 2);
    this.ctx.fill();

    if (this.currentPath.length > 1) {
      const prev = this.currentPath[this.currentPath.length - 2];
      this.ctx.strokeStyle = `rgba(232, 228, 220, ${alpha * 0.8})`;
      this.ctx.lineWidth = pressure * 6 + 0.5;
      this.ctx.beginPath();
      this.ctx.moveTo(prev.x, prev.y);
      this.ctx.lineTo(x, y);
      this.ctx.stroke();
    }
  }

  clear(): void {
    this.ctx.clearRect(0, 0, this.logicalWidth, this.logicalHeight);
    this.currentPath = [];
  }

  drawGuide(strokes: number[][][], strokeColors?: string[]): void {
    if (!this.showGuide) return;
    const defaultColor = 'rgba(201, 70, 61, 0.25)';
    const padding = 0.1;
    const scale = 1 - padding * 2;
    const offsetX = padding * this.logicalWidth;
    const offsetY = padding * this.logicalHeight;

    this.ctx.lineWidth = 3;
    this.ctx.lineCap = 'round';
    this.ctx.lineJoin = 'round';

    for (let i = 0; i < strokes.length; i++) {
      const stroke = strokes[i];
      if (stroke.length < 2) continue;

      this.ctx.strokeStyle = strokeColors?.[i] ?? defaultColor;
      this.ctx.beginPath();

      const startX = stroke[0][0] * this.logicalWidth * scale + offsetX;
      const startY = stroke[0][1] * this.logicalHeight * scale + offsetY;
      this.ctx.moveTo(startX, startY);

      for (let j = 1; j < stroke.length; j++) {
        const x = stroke[j][0] * this.logicalWidth * scale + offsetX;
        const y = stroke[j][1] * this.logicalHeight * scale + offsetY;
        this.ctx.lineTo(x, y);
      }

      this.ctx.stroke();
    }
  }

  clearAndDrawGuide(strokes: number[][][], strokeColors?: string[]): void {
    this.clear();
    this.drawGuide(strokes, strokeColors);
  }

  /** Reset the tracked position between playback strokes. */
  startPlaybackStroke(): void {
    this.lastPlaybackPoint = null;
  }

  /**
   * Draw one point of an animating playback stroke.
   * Coordinates are normalized (0–1), matching the guide's coordinate space
   * (padded by 10% on each side). Use drawUserReplayPoint for user-recorded
   * strokes, which are in full-canvas normalized space.
   */
  drawPlaybackPoint(normX: number, normY: number, pressure = 0.6): void {
    const padding = 0.1;
    const scale = 1 - padding * 2;
    const x = normX * this.logicalWidth * scale + padding * this.logicalWidth;
    const y = normY * this.logicalHeight * scale + padding * this.logicalHeight;
    const lineWidth = pressure * 3 + 1;

    this.ctx.save();

    if (this.lastPlaybackPoint) {
      this.ctx.shadowColor = 'rgba(201, 70, 61, 0.4)';
      this.ctx.shadowBlur = 6;
      this.ctx.strokeStyle = 'rgba(232, 228, 220, 0.9)';
      this.ctx.lineWidth = lineWidth;
      this.ctx.lineCap = 'round';
      this.ctx.lineJoin = 'round';
      this.ctx.beginPath();
      this.ctx.moveTo(this.lastPlaybackPoint.x, this.lastPlaybackPoint.y);
      this.ctx.lineTo(x, y);
      this.ctx.stroke();
    }

    // Glowing tip dot
    this.ctx.shadowColor = '#c9463d';
    this.ctx.shadowBlur = 10;
    this.ctx.fillStyle = '#ffffff';
    this.ctx.beginPath();
    this.ctx.arc(x, y, lineWidth / 2 + 0.5, 0, Math.PI * 2);
    this.ctx.fill();

    this.ctx.restore();

    this.lastPlaybackPoint = { x, y };
  }

  /**
   * Draw one point of a user-recorded stroke replay.
   * Coordinates are normalized (0–1) over the full canvas — the same space
   * that live drawing uses. Shares the glowing visual style with drawPlaybackPoint.
   */
  drawUserReplayPoint(normX: number, normY: number, pressure = 0.6): void {
    const x = normX * this.logicalWidth;
    const y = normY * this.logicalHeight;
    const lineWidth = pressure * 3 + 1;

    this.ctx.save();

    if (this.lastPlaybackPoint) {
      this.ctx.shadowColor = 'rgba(201, 70, 61, 0.4)';
      this.ctx.shadowBlur = 6;
      this.ctx.strokeStyle = 'rgba(232, 228, 220, 0.9)';
      this.ctx.lineWidth = lineWidth;
      this.ctx.lineCap = 'round';
      this.ctx.lineJoin = 'round';
      this.ctx.beginPath();
      this.ctx.moveTo(this.lastPlaybackPoint.x, this.lastPlaybackPoint.y);
      this.ctx.lineTo(x, y);
      this.ctx.stroke();
    }

    this.ctx.shadowColor = '#c9463d';
    this.ctx.shadowBlur = 10;
    this.ctx.fillStyle = '#ffffff';
    this.ctx.beginPath();
    this.ctx.arc(x, y, lineWidth / 2 + 0.5, 0, Math.PI * 2);
    this.ctx.fill();

    this.ctx.restore();

    this.lastPlaybackPoint = { x, y };
  }

  /** Remove all event listeners. Call when tearing down this instance. */
  destroy(): void {
    window.removeEventListener('resize', this.resizeHandler);
  }

  get drawing(): boolean {
    return this.isDrawing;
  }
}
