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
  drawOnCanvas?: boolean;
}

export class CanvasInput {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private options: CanvasInputOptions;
  
  private isDrawing: boolean = false;
  private strokeStartTime: number = 0;
  private currentPath: Array<{ x: number; y: number; pressure: number }> = [];

  constructor(canvas: HTMLCanvasElement, options: CanvasInputOptions) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d')!;
    this.options = {
      drawOnCanvas: true,
      ...options,
    };

    this.setupCanvas();
    this.bindEvents();
  }

  private setupCanvas(): void {
    // Handle high-DPI displays
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.ctx.scale(dpr, dpr);
    
    // Store logical dimensions
    (this.canvas as any).logicalWidth = rect.width;
    (this.canvas as any).logicalHeight = rect.height;
    
    // Canvas styling
    this.ctx.lineCap = 'round';
    this.ctx.lineJoin = 'round';
  }

  private bindEvents(): void {
    this.canvas.addEventListener('pointerdown', this.handlePointerDown.bind(this));
    this.canvas.addEventListener('pointermove', this.handlePointerMove.bind(this));
    this.canvas.addEventListener('pointerup', this.handlePointerUp.bind(this));
    this.canvas.addEventListener('pointerleave', this.handlePointerUp.bind(this));
    this.canvas.addEventListener('pointercancel', this.handlePointerUp.bind(this));
    
    // Prevent default touch behaviors
    this.canvas.addEventListener('touchstart', e => e.preventDefault(), { passive: false });
    this.canvas.addEventListener('touchmove', e => e.preventDefault(), { passive: false });

    // Handle resize
    window.addEventListener('resize', () => this.setupCanvas());
  }

  private handlePointerDown(e: PointerEvent): void {
    // Ignore palm/finger touch if pressure is 0
    if (e.pointerType === 'touch' && e.pressure === 0) return;

    this.isDrawing = true;
    this.strokeStartTime = performance.now() / 1000;
    this.currentPath = [];
    
    this.options.onStrokeStart?.();
    this.handlePointerMove(e);
  }

  private handlePointerMove(e: PointerEvent): void {
    if (!this.isDrawing) return;
    if (e.pressure === 0) return;

    // Get coalesced events for high-frequency sampling (240Hz on Apple Pencil)
    const events = e.getCoalescedEvents ? e.getCoalescedEvents() : [e];
    
    const logicalWidth = (this.canvas as any).logicalWidth || this.canvas.clientWidth;
    const logicalHeight = (this.canvas as any).logicalHeight || this.canvas.clientHeight;

    for (const p of events) {
      // Get canvas-relative coordinates
      const rect = this.canvas.getBoundingClientRect();
      const x = p.clientX - rect.left;
      const y = p.clientY - rect.top;

      // Normalize to 0-1 range
      const nX = x / logicalWidth;
      const nY = y / logicalHeight;

      // Get pen angles (in radians)
      const azimuth = (p as any).azimuthAngle || 0;
      const altitude = (p as any).altitudeAngle || Math.PI / 2; // Default to perpendicular

      // Create stroke point
      const point: StrokePoint = {
        x: nX,
        y: nY,
        force: p.pressure,
        azimuth,
        altitude,
        t: (performance.now() / 1000) - this.strokeStartTime,
      };

      // Call the point callback
      this.options.onPoint(point);

      // Store for drawing
      this.currentPath.push({ x, y, pressure: p.pressure });

      // Draw on canvas if enabled
      if (this.options.drawOnCanvas) {
        this.drawPoint(x, y, p.pressure);
      }
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

    // Draw point
    this.ctx.fillStyle = `rgba(232, 228, 220, ${alpha})`;
    this.ctx.beginPath();
    this.ctx.arc(x, y, radius, 0, Math.PI * 2);
    this.ctx.fill();

    // Connect to previous point for smooth lines
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

  /**
   * Clear the canvas.
   */
  clear(): void {
    const logicalWidth = (this.canvas as any).logicalWidth || this.canvas.clientWidth;
    const logicalHeight = (this.canvas as any).logicalHeight || this.canvas.clientHeight;
    this.ctx.clearRect(0, 0, logicalWidth, logicalHeight);
    this.currentPath = [];
  }

  /**
   * Check if currently drawing.
   */
  get drawing(): boolean {
    return this.isDrawing;
  }
}

