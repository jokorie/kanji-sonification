/**
 * Kanji Sonification - Main Entry Point
 *
 * Wires together canvas input → feature extraction → audio synthesis
 */

import { StrokePoint, DEFAULT_SYNTH_CONFIG } from './types';
import { StreamingFeatureExtractor } from './features/kinematics';
import { mapFeaturesToSynthParams, yToPitch, forceToAmplitude } from './audio/mapping';
import { KanjiSynth } from './audio/synth';
import { CanvasInput } from './canvas/input';
import { TemplatePlayer } from './templates/playback';
import { KanjiTemplate, getTemplate, LESSON_GROUPS } from './templates/kanji-data';

// Palette for radical coloring — cycles if a kanji has more radicals than entries.
const RADICAL_PALETTE = [
  'rgba(201, 70, 61, 0.55)',   // red
  'rgba(74, 156, 109, 0.55)',  // green
  'rgba(212, 168, 75, 0.55)',  // gold
  'rgba(80, 150, 210, 0.55)',  // blue
  'rgba(170, 100, 200, 0.55)', // purple
  'rgba(200, 130, 70, 0.55)',  // orange
];

function buildStrokeColors(template: KanjiTemplate): string[] {
  const colors = new Array<string>(template.strokeCount).fill('rgba(201, 70, 61, 0.25)');
  template.radicals.forEach((group, i) => {
    const color = RADICAL_PALETTE[i % RADICAL_PALETTE.length];
    for (const idx of group.strokeIndices) {
      if (idx < colors.length) colors[idx] = color;
    }
  });
  return colors;
}

// ============================================================
// APP
// ============================================================

class App {
  private synth: KanjiSynth;
  private featureExtractor: StreamingFeatureExtractor;
  private canvasInput: CanvasInput;
  private templatePlayer: TemplatePlayer;

  private pointCount = 0;
  private strokeSoundStarted = false;
  private recordedStrokes: StrokePoint[][] = [];
  private currentRecordedStroke: StrokePoint[] | null = null;
  private isRecordingPlayback = false;
  private recordingAbortController: AbortController | null = null;
  private radicalsEnabled = false;
  private playbackSpeed = 2; // multiplier applied to msPerPoint; higher = faster

  private selectedKanji = '';

  // DOM elements
  private statusDot: HTMLElement;
  private statusText: HTMLElement;
  private pointCountEl: HTMLElement;
  private pressureFill: HTMLElement;
  private frequencyValueEl: HTMLElement;
  private playBtn: HTMLButtonElement;
  private replayBtn: HTMLButtonElement;
  private radicalsBtn: HTMLButtonElement;
  private speedSlider: HTMLInputElement;
  private speedValueEl: HTMLElement;
  // Info panel elements
  private infoTop: HTMLElement;
  private kanjiDisplay: HTMLElement;
  private onyomiText: HTMLElement;
  private kunyomiText: HTMLElement;
  private meaningText: HTMLElement;
  private readingBarValue: HTMLElement;

  constructor() {
    this.synth = new KanjiSynth(DEFAULT_SYNTH_CONFIG);
    this.featureExtractor = new StreamingFeatureExtractor(0.3);
    this.templatePlayer = new TemplatePlayer(this.synth);

    // DOM — queried once up front
    this.statusDot = document.getElementById('statusDot')!;
    this.statusText = document.getElementById('statusText')!;
    this.pointCountEl = document.getElementById('pointCount')!;
    this.pressureFill = document.getElementById('pressureFill')!;
    this.frequencyValueEl = document.getElementById('frequencyValue')!;
    this.playBtn = document.getElementById('playBtn') as HTMLButtonElement;
    this.replayBtn = document.getElementById('replayBtn') as HTMLButtonElement;
    this.radicalsBtn = document.getElementById('radicalsBtn') as HTMLButtonElement;
    this.speedSlider = document.getElementById('speedSlider') as HTMLInputElement;
    this.speedValueEl = document.getElementById('speedValue')!;
    // Info panels
    this.infoTop = document.getElementById('infoTop')!;
    this.kanjiDisplay = document.getElementById('kanjiDisplay')!;
    this.onyomiText = document.getElementById('onyomiText')!;
    this.kunyomiText = document.getElementById('kunyomiText')!;
    this.meaningText = document.getElementById('meaningText')!;
    this.readingBarValue = document.getElementById('readingBarValue')!;

    const canvas = document.getElementById('canvas') as HTMLCanvasElement;
    this.canvasInput = new CanvasInput(canvas, {
      onPoint: p => this.handlePoint(p),
      onStrokeStart: () => this.handleStrokeStart(),
      onStrokeEnd: () => this.handleStrokeEnd(),
      onResize: () => this.updateKanjiGuide(),
      drawOnCanvas: true,
    });

    this.buildKanjiPicker();
    this.bindUI();
    this.updateKanjiGuide();
  }

  // ============================================================
  // SETUP
  // ============================================================

  private buildKanjiPicker(): void {
    const picker = document.getElementById('kanjiPicker')!;

    for (const { label, characters } of LESSON_GROUPS) {
      const col = document.createElement('div');
      col.className = 'picker-col';

      const lbl = document.createElement('div');
      lbl.className = 'picker-label';
      lbl.textContent = label.replace('Lessons ', 'L').replace('Lesson ', 'L');
      col.appendChild(lbl);

      const scroll = document.createElement('div');
      scroll.className = 'picker-scroll';

      for (const char of characters) {
        const cell = document.createElement('div');
        cell.className = 'picker-kanji';
        cell.textContent = char;
        cell.addEventListener('click', () => this.selectKanji(char, cell));
        scroll.appendChild(cell);
      }

      col.appendChild(scroll);
      picker.appendChild(col);
    }
  }

  private selectKanji(char: string, cell: HTMLElement): void {
    document.querySelector('.picker-kanji.selected')?.classList.remove('selected');
    this.selectedKanji = char;
    cell.classList.add('selected');
    this.recordedStrokes = [];
    this.currentRecordedStroke = null;
    if (this.isRecordingPlayback) this.stopRecordingPlayback();
    this.updateKanjiGuide();
  }

  // ============================================================
  // UI BINDING
  // ============================================================

  private bindUI(): void {
    document.getElementById('clearBtn')!.addEventListener('click', () => this.handleClear());

    this.radicalsBtn.addEventListener('click', () => {
      this.radicalsEnabled = !this.radicalsEnabled;
      this.radicalsBtn.classList.toggle('toggled', this.radicalsEnabled);
      this.updateKanjiGuide();
    });

    this.speedSlider.addEventListener('input', () => {
      this.playbackSpeed = parseFloat(this.speedSlider.value);
      this.speedValueEl.textContent = `${this.playbackSpeed.toFixed(1)}x`;
    });

    this.playBtn.addEventListener('click', () => this.handlePlayBtn());
    this.replayBtn.addEventListener('click', () => this.handleReplayBtn());

    const initAudioBtn = document.getElementById('initAudioBtn')!;
    const initModal = document.getElementById('initModal')!;

    initAudioBtn.addEventListener('click', async () => {
      try {
        await this.synth.initialize();
        initModal.classList.remove('visible');
        this.statusDot.classList.add('connected');
        this.statusText.textContent = 'READY';
      } catch (e) {
        console.error('Audio initialization failed:', e);
        this.statusText.textContent = 'AUDIO ERROR';
      }
    });
  }

  // ============================================================
  // EVENT HANDLERS
  // ============================================================

  private handleClear(): void {
    this.pointCount = 0;
    this.pointCountEl.textContent = '0';
    this.recordedStrokes = [];
    this.currentRecordedStroke = null;
    this.updateKanjiGuide();
  }

  private async handlePlayBtn(): Promise<void> {
    const character = this.selectedKanji;
    if (!character) {
      console.warn('No kanji selected for template playback.');
      return;
    }

    if (this.templatePlayer.playing) {
      this.templatePlayer.stop();
      this.playBtn.textContent = '▶ PLAY';
      this.playBtn.classList.remove('playing');
      this.statusDot.classList.remove('active');
      this.updateKanjiGuide();
    } else {
      this.playBtn.textContent = '■ STOP';
      this.playBtn.classList.add('playing');

      // Reset canvas to just the faint guide before playback starts.
      this.updateKanjiGuide();

      await this.templatePlayer.play(character, {
        msPerPoint: 25 / this.playbackSpeed,
        strokePause: 150 / this.playbackSpeed,
        pressure: 0.6,
        onStrokeStart: i => {
          this.statusDot.classList.add('active');
          this.canvasInput.startPlaybackStroke();
          console.log(`Stroke ${i + 1} started`);
        },
        onStrokeEnd: i => {
          this.statusDot.classList.remove('active');
          console.log(`Stroke ${i + 1} ended`);
        },
        onPoint: (point, _strokeIndex) => {
          this.frequencyValueEl.textContent =
            `${yToPitch(point.y, DEFAULT_SYNTH_CONFIG.minFreq, DEFAULT_SYNTH_CONFIG.maxFreq, true).toFixed(0)}Hz`;
          this.canvasInput.drawPlaybackPoint(point.x, point.y, point.force);
        },
        onComplete: () => {
          this.playBtn.textContent = '▶ PLAY';
          this.playBtn.classList.remove('playing');
          this.statusDot.classList.remove('active');
        },
      });
    }
  }

  private async handleReplayBtn(): Promise<void> {
    if (this.isRecordingPlayback) {
      this.stopRecordingPlayback();
      return;
    }

    if (!this.recordedStrokes.length) {
      console.warn('No recorded strokes to replay.');
      return;
    }

    await this.playRecordedStrokes();
  }

  private handleStrokeStart(): void {
    this.featureExtractor.reset();
    this.strokeSoundStarted = false;
    this.statusDot.classList.add('active');
    this.currentRecordedStroke = [];
  }

  private handleStrokeEnd(): void {
    this.synth.stopSound();
    this.strokeSoundStarted = false;
    this.statusDot.classList.remove('active');
    this.pressureFill.style.height = '0%';

    if (this.currentRecordedStroke && this.currentRecordedStroke.length > 0) {
      this.recordedStrokes.push(this.currentRecordedStroke);
    }
    this.currentRecordedStroke = null;
  }

  private handlePoint(point: StrokePoint): void {
    this.pointCount++;
    this.pointCountEl.textContent = this.pointCount.toString();

    this.pressureFill.style.height = `${point.force * 100}%`;

    const features = this.featureExtractor.update(point);

    if (this.currentRecordedStroke) {
      this.currentRecordedStroke.push(point);
    }

    if (!this.strokeSoundStarted) {
      // Snap to the stroke's initial position — no slide from a previous stroke's endpoint.
      const initialParams = {
        frequency: yToPitch(point.y, DEFAULT_SYNTH_CONFIG.minFreq, DEFAULT_SYNTH_CONFIG.maxFreq, true),
        amplitude: forceToAmplitude(point.force, DEFAULT_SYNTH_CONFIG.minAmp, DEFAULT_SYNTH_CONFIG.maxAmp),
        pan: point.x * 2 - 1,
        vibratoDepth: 0,
        vibratoRate: 5,
      };
      this.synth.startSound(initialParams);
      this.strokeSoundStarted = true;
      this.frequencyValueEl.textContent = `${initialParams.frequency.toFixed(0)}Hz`;
    } else if (features) {
      const synthParams = mapFeaturesToSynthParams(features);
      this.synth.update(synthParams);
      this.frequencyValueEl.textContent = `${synthParams.frequency.toFixed(0)}Hz`;
    }
  }

  // ============================================================
  // RECORDED PLAYBACK
  // ============================================================

  private async playRecordedStrokes(): Promise<void> {
    if (!this.recordedStrokes.length || this.isRecordingPlayback) return;

    this.isRecordingPlayback = true;
    this.recordingAbortController = new AbortController();

    const playbackExtractor = new StreamingFeatureExtractor(0.3);
    this.statusDot.classList.add('active');

    // Start with a clean slate showing just the guide.
    this.updateKanjiGuide();

    try {
      for (let strokeIndex = 0; strokeIndex < this.recordedStrokes.length; strokeIndex++) {
        const stroke = this.recordedStrokes[strokeIndex];
        if (!stroke.length) continue;

        playbackExtractor.reset();
        this.canvasInput.startPlaybackStroke();

        const firstPoint = stroke[0];
        const initialParams = {
          frequency: yToPitch(firstPoint.y, DEFAULT_SYNTH_CONFIG.minFreq, DEFAULT_SYNTH_CONFIG.maxFreq, true),
          amplitude: forceToAmplitude(firstPoint.force, DEFAULT_SYNTH_CONFIG.minAmp, DEFAULT_SYNTH_CONFIG.maxAmp),
          pan: firstPoint.x * 2 - 1,
          vibratoDepth: 0,
          vibratoRate: 5,
        };
        this.synth.startSound(initialParams);
        this.frequencyValueEl.textContent = `${initialParams.frequency.toFixed(0)}Hz`;

        for (let i = 0; i < stroke.length; i++) {
          if (this.recordingAbortController?.signal.aborted) {
            throw new DOMException('Aborted', 'AbortError');
          }

          const point = stroke[i];
          this.pressureFill.style.height = `${point.force * 100}%`;
          this.canvasInput.drawUserReplayPoint(point.x, point.y, point.force);

          const features = playbackExtractor.update(point);
          if (features) {
            const synthParams = mapFeaturesToSynthParams(features);
            this.synth.update(synthParams);
            this.frequencyValueEl.textContent = `${synthParams.frequency.toFixed(0)}Hz`;
          }

          if (i < stroke.length - 1) {
            const dtMs = Math.max(0, (stroke[i + 1].t - point.t) * 1000) / this.playbackSpeed;
            await this.sleepWithAbort(dtMs, this.recordingAbortController.signal);
          }
        }

        this.synth.stopSound();

        if (strokeIndex < this.recordedStrokes.length - 1) {
          await this.sleepWithAbort(200, this.recordingAbortController.signal);
        }
      }
    } catch (e) {
      if ((e as DOMException).name !== 'AbortError') {
        console.error('Recording playback error:', e);
      }
    } finally {
      this.synth.stopSound();
      this.statusDot.classList.remove('active');
      this.pressureFill.style.height = '0%';
      this.isRecordingPlayback = false;
      this.recordingAbortController = null;
    }
  }

  private stopRecordingPlayback(): void {
    if (!this.isRecordingPlayback) return;
    this.recordingAbortController?.abort();
  }

  // ============================================================
  // HELPERS
  // ============================================================

  private updateKanjiGuide(): void {
    const character = this.selectedKanji;
    const template = getTemplate(character);

    if (template) {
      const colors = this.radicalsEnabled ? buildStrokeColors(template) : undefined;
      this.canvasInput.clearAndDrawGuide(template.strokes, colors);
      this.updateInfoPanels(template);
    } else {
      this.canvasInput.clear();
      this.clearInfoPanels();
    }
  }

  private updateInfoPanels(template: KanjiTemplate): void {
    this.infoTop.classList.remove('empty');
    this.kanjiDisplay.classList.remove('empty');
    this.kanjiDisplay.textContent = template.character;
    this.onyomiText.textContent = '—';
    this.kunyomiText.textContent = template.reading || '—';
    this.meaningText.textContent = '';

    this.readingBarValue.classList.remove('empty');
    this.readingBarValue.textContent = template.reading || '—';
  }

  private clearInfoPanels(): void {
    this.infoTop.classList.add('empty');
    this.kanjiDisplay.classList.add('empty');
    this.kanjiDisplay.textContent = '漢';
    this.onyomiText.textContent = '—';
    this.kunyomiText.textContent = '—';
    this.meaningText.textContent = 'select a kanji to begin';

    this.readingBarValue.classList.add('empty');
    this.readingBarValue.textContent = 'select a kanji';
  }

  private sleepWithAbort(ms: number, signal: AbortSignal): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(resolve, ms);
      signal.addEventListener('abort', () => {
        clearTimeout(timeout);
        reject(new DOMException('Aborted', 'AbortError'));
      });
    });
  }
}

// ============================================================
// BOOTSTRAP
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
  console.log('🎌 Kanji Sonification starting...');
  new App();
  console.log('✅ Ready! Tap "Enable Audio" to start.');
});
