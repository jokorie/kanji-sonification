/**
 * Kanji Sonification - Main Entry Point
 * 
 * Wires together canvas input → feature extraction → audio synthesis
 */

import { StrokePoint, DEFAULT_SYNTH_CONFIG } from './types';
import { StreamingFeatureExtractor } from './features/kinematics';
import { mapFeaturesToSynthParams } from './audio/mapping';
import { KanjiSynth } from './audio/synth';
import { CanvasInput } from './canvas/input';
import { TemplatePlayer } from './templates/playback';
import { getTemplate } from './templates/kanji-data';

// ============================================================
// APP STATE
// ============================================================

let synth: KanjiSynth;
let featureExtractor: StreamingFeatureExtractor;
let canvasInput: CanvasInput;
let templatePlayer: TemplatePlayer;
let pointCount = 0;
let strokeSoundStarted = false; // Track if we've started sound for current stroke
let recordedStrokes: StrokePoint[][] = [];
let currentRecordedStroke: StrokePoint[] | null = null;
let isRecordingPlayback = false;
let recordingAbortController: AbortController | null = null;

// DOM Elements
let statusDot: HTMLElement;
let statusText: HTMLElement;
let pointCountEl: HTMLElement;
let pressureValueEl: HTMLElement;
let pressureFill: HTMLElement;
let frequencyValueEl: HTMLElement;
let kanjiSelect: HTMLSelectElement;
let playBtn: HTMLButtonElement;
  let replayBtn: HTMLButtonElement;

// ============================================================
// INITIALIZATION
// ============================================================

function initializeUI(): void {
  // Get DOM elements
  statusDot = document.getElementById('statusDot')!;
  statusText = document.getElementById('statusText')!;
  pointCountEl = document.getElementById('pointCount')!;
  pressureValueEl = document.getElementById('pressureValue')!;
  pressureFill = document.getElementById('pressureFill')!;
  frequencyValueEl = document.getElementById('frequencyValue')!;
  kanjiSelect = document.getElementById('kanjiSelect') as HTMLSelectElement;
  playBtn = document.getElementById('playBtn') as HTMLButtonElement;
  replayBtn = document.getElementById('replayBtn') as HTMLButtonElement;

  // Force blank (no-template) mode on initial load
  kanjiSelect.value = '';

  // Clear button
  const clearBtn = document.getElementById('clearBtn')!;
  clearBtn.addEventListener('click', () => {
    pointCount = 0;
    pointCountEl.textContent = '0';
    recordedStrokes = [];
    currentRecordedStroke = null;
    // Clear and redraw the guide for currently selected kanji
    updateKanjiGuide();
  });

  // Update guide when kanji selection changes
  kanjiSelect.addEventListener('change', () => {
    // Switching kanji modes should discard previously recorded strokes
    recordedStrokes = [];
    currentRecordedStroke = null;
    if (isRecordingPlayback) {
      stopRecordingPlayback();
    }

    updateKanjiGuide();
  });

  // Play template button
  playBtn.addEventListener('click', async () => {
    const character = kanjiSelect.value;
    if (!character) {
      console.warn('No kanji selected for template playback.');
      return;
    }

    if (templatePlayer.playing) {
      templatePlayer.stop();
      playBtn.textContent = '▶ PLAY';
      playBtn.classList.remove('playing');
      statusDot.classList.remove('active');
    } else {
      playBtn.textContent = '■ STOP';
      playBtn.classList.add('playing');
      
      await templatePlayer.play(character, {
        strokeDuration: 600,
        strokePause: 300,
        pressure: 0.6,
        onStrokeStart: (i) => {
          statusDot.classList.add('active');
          console.log(`Stroke ${i + 1} started`);
        },
        onStrokeEnd: (i) => {
          statusDot.classList.remove('active');
          console.log(`Stroke ${i + 1} ended`);
        },
        onPoint: (point) => {
          frequencyValueEl.textContent = `${mapYToFreq(point.y).toFixed(0)}Hz`;
        },
        onComplete: () => {
          playBtn.textContent = '▶ PLAY';
          playBtn.classList.remove('playing');
          statusDot.classList.remove('active');
          console.log('Playback complete');
        }
      });
    }
  });

  // Replay recorded strokes button
  replayBtn.addEventListener('click', async () => {
    if (isRecordingPlayback) {
      stopRecordingPlayback();
      return;
    }

    if (!recordedStrokes.length) {
      console.warn('No recorded strokes to replay.');
      return;
    }

    await playRecordedStrokes();
  });

  // Initialize synth on first interaction (required by browser autoplay policy)
  const initAudioBtn = document.getElementById('initAudioBtn')!;
  const initModal = document.getElementById('initModal')!;
  
  initAudioBtn.addEventListener('click', async () => {
    await synth.initialize();
    initModal.classList.remove('visible');
    statusDot.classList.add('connected');
    statusText.textContent = 'READY';
  });
}

function initializeSynth(): void {
  synth = new KanjiSynth(DEFAULT_SYNTH_CONFIG);
  featureExtractor = new StreamingFeatureExtractor(0.3);
  templatePlayer = new TemplatePlayer(synth);
}

function initializeCanvas(): void {
  const canvas = document.getElementById('canvas') as HTMLCanvasElement;
  
  canvasInput = new CanvasInput(canvas, {
    onPoint: handlePoint,
    onStrokeStart: handleStrokeStart,
    onStrokeEnd: handleStrokeEnd,
    drawOnCanvas: true,
  });
}

// ============================================================
// EVENT HANDLERS
// ============================================================

function handleStrokeStart(): void {
  // Reset feature extractor for new stroke
  featureExtractor.reset();
  strokeSoundStarted = false; // Will start sound on first point with correct position
  statusDot.classList.add('active');
  currentRecordedStroke = [];
}

function handleStrokeEnd(): void {
  synth.stopSound();
  strokeSoundStarted = false;
  statusDot.classList.remove('active');
  pressureFill.style.height = '0%';

  if (currentRecordedStroke && currentRecordedStroke.length > 0) {
    recordedStrokes.push(currentRecordedStroke);
  }
  currentRecordedStroke = null;
}

function handlePoint(point: StrokePoint): void {
  // Update point count
  pointCount++;
  pointCountEl.textContent = pointCount.toString();
  
  // Update pressure display
  pressureValueEl.textContent = point.force.toFixed(2);
  pressureFill.style.height = `${point.force * 100}%`;

  // Extract features
  const features = featureExtractor.update(point);

  // Record point for potential playback
  if (currentRecordedStroke) {
    currentRecordedStroke.push(point);
  }
  
  // For the first point of a stroke, snap to its position (no slide from previous stroke)
  if (!strokeSoundStarted) {
    // Compute initial params from the raw point position
    const initialParams = {
      frequency: mapYToFreq(point.y),
      amplitude: mapForceToAmplitude(point.force),
      pan: (point.x * 2) - 1, // Convert 0-1 to -1 to 1
      vibratoDepth: 0,
      vibratoRate: 5,
    };
    
    // Start sound snapped to initial position
    synth.startSound(initialParams);
    strokeSoundStarted = true;
    
    frequencyValueEl.textContent = `${initialParams.frequency.toFixed(0)}Hz`;
  } else if (features) {
    // Subsequent points: use full feature extraction with smoothing
    const synthParams = mapFeaturesToSynthParams(features);
    synth.update(synthParams);
    frequencyValueEl.textContent = `${synthParams.frequency.toFixed(0)}Hz`;
  }
}

/**
 * Replay the recorded strokes using the same DSP pipeline.
 */
async function playRecordedStrokes(): Promise<void> {
  if (!recordedStrokes.length || isRecordingPlayback) return;

  isRecordingPlayback = true;
  recordingAbortController = new AbortController();

  const playbackExtractor = new StreamingFeatureExtractor(0.3);

  statusDot.classList.add('active');

  try {
    for (let strokeIndex = 0; strokeIndex < recordedStrokes.length; strokeIndex++) {
      const stroke = recordedStrokes[strokeIndex];
      if (!stroke.length) continue;

      playbackExtractor.reset();

      // Start sound from first point of this stroke
      const firstPoint = stroke[0];
      const initialParams = {
        frequency: mapYToFreq(firstPoint.y),
        amplitude: mapForceToAmplitude(firstPoint.force),
        pan: (firstPoint.x * 2) - 1,
        vibratoDepth: 0,
        vibratoRate: 5,
      };
      synth.startSound(initialParams);
      frequencyValueEl.textContent = `${initialParams.frequency.toFixed(0)}Hz`;

      for (let i = 0; i < stroke.length; i++) {
        if (recordingAbortController?.signal.aborted) {
          throw new DOMException('Aborted', 'AbortError');
        }

        const point = stroke[i];

        // Update UI to reflect playback state
        pressureValueEl.textContent = point.force.toFixed(2);
        pressureFill.style.height = `${point.force * 100}%`;

        const features = playbackExtractor.update(point);
        if (features) {
          const synthParams = mapFeaturesToSynthParams(features);
          synth.update(synthParams);
          frequencyValueEl.textContent = `${synthParams.frequency.toFixed(0)}Hz`;
        }

        // Wait based on recorded timing between points
        if (i < stroke.length - 1) {
          const currentT = point.t;
          const nextT = stroke[i + 1].t;
          const dtMs = Math.max(0, (nextT - currentT) * 1000);
          await sleepWithAbort(dtMs, recordingAbortController.signal);
        }
      }

      synth.stopSound();

      // Short pause between strokes
      if (strokeIndex < recordedStrokes.length - 1) {
        await sleepWithAbort(200, recordingAbortController.signal);
      }
    }
  } catch (e) {
    if ((e as DOMException).name !== 'AbortError') {
      console.error('Recording playback error:', e);
    }
  } finally {
    synth.stopSound();
    statusDot.classList.remove('active');
    pressureFill.style.height = '0%';
    isRecordingPlayback = false;
    recordingAbortController = null;
  }
}

function stopRecordingPlayback(): void {
  if (!isRecordingPlayback) return;
  recordingAbortController?.abort();
}

/**
 * Update the canvas guide to show the currently selected kanji
 */
function updateKanjiGuide(): void {
  const character = kanjiSelect.value;
  const template = getTemplate(character);
  
  if (template) {
    canvasInput.clearAndDrawGuide(template.strokes);
    console.log(`📝 Showing guide for: ${character} (${template.meaning})`);
  } else {
    canvasInput.clear();
  }
}

// Helper functions for initial point (before features are available)
function mapYToFreq(y: number): number {
  const minFreq = DEFAULT_SYNTH_CONFIG.minFreq;
  const maxFreq = DEFAULT_SYNTH_CONFIG.maxFreq;
  // Invert: top of screen (y=0) = high pitch, bottom (y=1) = low pitch
  return maxFreq - y * (maxFreq - minFreq);
}

function mapForceToAmplitude(force: number): number {
  const minAmp = DEFAULT_SYNTH_CONFIG.minAmp;
  const maxAmp = DEFAULT_SYNTH_CONFIG.maxAmp;
  const clamped = Math.max(0, Math.min(1, force));
  return minAmp + Math.pow(clamped, 1.5) * (maxAmp - minAmp);
}

function sleepWithAbort(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(resolve, ms);
    signal.addEventListener('abort', () => {
      clearTimeout(timeout);
      reject(new DOMException('Aborted', 'AbortError'));
    });
  });
}

// ============================================================
// BOOTSTRAP
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
  console.log('🎌 Kanji Sonification starting...');
  
  initializeSynth();
  initializeCanvas();
  initializeUI();
  
  // Show initial kanji guide
  updateKanjiGuide();
  
  console.log('✅ Ready! Tap "Enable Audio" to start.');
});


