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
import { KanjiTemplate, getTemplate, KANJI_TEMPLATES, LESSON_GROUPS } from './templates/kanji-data';

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

type Mode = 'practice' | 'quiz';
type QuizPhase = 'idle' | 'prompt' | 'draw' | 'reveal';

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

  // Quiz state
  private mode: Mode = 'practice';
  private quizPhase: QuizPhase = 'idle';
  private quizQueue: KanjiTemplate[] = [];
  private quizIndex = 0;
  private quizScore = { correct: 0, total: 0 };
  private selectedLessons = new Set<string>();

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
  // Mode toggle
  private practiceModeBtn: HTMLButtonElement;
  private quizModeBtn: HTMLButtonElement;
  // Quiz panel
  private kanjiPicker: HTMLElement;
  private quizPanel: HTMLElement;
  private quizPhaseIdle: HTMLElement;
  private quizPhasePrompt: HTMLElement;
  private quizPhaseDraw: HTMLElement;
  private quizPhaseReveal: HTMLElement;
  private lessonChecks: HTMLElement;
  private startQuizBtn: HTMLButtonElement;
  private quizCounter: HTMLElement;
  private quizSourceWordPrompt: HTMLElement;
  private quizMeaning: HTMLElement;
  private quizReading: HTMLElement;
  private startDrawingBtn: HTMLButtonElement;
  private quizCounterDraw: HTMLElement;
  private quizSourceWordDraw: HTMLElement;
  private quizMeaningDraw: HTMLElement;
  private quizReadingDraw: HTMLElement;
  private submitDrawingBtn: HTMLButtonElement;
  private quizScoreDisplay: HTMLElement;
  private quizSourceWordReveal: HTMLElement;
  private quizMeaningReveal: HTMLElement;
  private quizReadingReveal: HTMLElement;
  private correctBtn: HTMLButtonElement;
  private incorrectBtn: HTMLButtonElement;
  // Summary modal
  private summaryModal: HTMLElement;
  private summaryScore: HTMLElement;
  private summaryLabel: HTMLElement;
  private tryAgainBtn: HTMLButtonElement;
  private backToPracticeBtn: HTMLButtonElement;
  // Identify
  private identifyBtn: HTMLButtonElement;
  private identifyModal: HTMLElement;
  private identifyResult: HTMLElement;

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
    // Mode toggle
    this.practiceModeBtn = document.getElementById('practiceModeBtn') as HTMLButtonElement;
    this.quizModeBtn = document.getElementById('quizModeBtn') as HTMLButtonElement;
    // Quiz panel
    this.kanjiPicker = document.getElementById('kanjiPicker')!;
    this.quizPanel = document.getElementById('quizPanel')!;
    this.quizPhaseIdle = document.getElementById('quizPhaseIdle')!;
    this.quizPhasePrompt = document.getElementById('quizPhasePrompt')!;
    this.quizPhaseDraw = document.getElementById('quizPhaseDraw')!;
    this.quizPhaseReveal = document.getElementById('quizPhaseReveal')!;
    this.lessonChecks = document.getElementById('lessonChecks')!;
    this.startQuizBtn = document.getElementById('startQuizBtn') as HTMLButtonElement;
    this.quizCounter = document.getElementById('quizCounter')!;
    this.quizSourceWordPrompt = document.getElementById('quizSourceWordPrompt')!;
    this.quizMeaning = document.getElementById('quizMeaning')!;
    this.quizReading = document.getElementById('quizReading')!;
    this.startDrawingBtn = document.getElementById('startDrawingBtn') as HTMLButtonElement;
    this.quizCounterDraw = document.getElementById('quizCounterDraw')!;
    this.quizSourceWordDraw = document.getElementById('quizSourceWordDraw')!;
    this.quizMeaningDraw = document.getElementById('quizMeaningDraw')!;
    this.quizReadingDraw = document.getElementById('quizReadingDraw')!;
    this.submitDrawingBtn = document.getElementById('submitDrawingBtn') as HTMLButtonElement;
    this.quizScoreDisplay = document.getElementById('quizScoreDisplay')!;
    this.quizSourceWordReveal = document.getElementById('quizSourceWordReveal')!;
    this.quizMeaningReveal = document.getElementById('quizMeaningReveal')!;
    this.quizReadingReveal = document.getElementById('quizReadingReveal')!;
    this.correctBtn = document.getElementById('correctBtn') as HTMLButtonElement;
    this.incorrectBtn = document.getElementById('incorrectBtn') as HTMLButtonElement;
    // Summary modal
    this.summaryModal = document.getElementById('summaryModal')!;
    this.summaryScore = document.getElementById('summaryScore')!;
    this.summaryLabel = document.getElementById('summaryLabel')!;
    this.tryAgainBtn = document.getElementById('tryAgainBtn') as HTMLButtonElement;
    this.backToPracticeBtn = document.getElementById('backToPracticeBtn') as HTMLButtonElement;
    // Identify
    this.identifyBtn = document.getElementById('identifyBtn') as HTMLButtonElement;
    this.identifyModal = document.getElementById('identifyModal')!;
    this.identifyResult = document.getElementById('identifyResult')!;

    const canvas = document.getElementById('canvas') as HTMLCanvasElement;
    this.canvasInput = new CanvasInput(canvas, {
      onPoint: p => this.handlePoint(p),
      onStrokeStart: () => this.handleStrokeStart(),
      onStrokeEnd: () => this.handleStrokeEnd(),
      onResize: () => this.updateKanjiGuide(),
      drawOnCanvas: true,
    });

    this.buildKanjiPicker();
    this.buildLessonChecks();
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

  private buildLessonChecks(): void {
    // Select all lessons by default
    for (const { label } of LESSON_GROUPS) {
      this.selectedLessons.add(label);
    }

    for (const { label } of LESSON_GROUPS) {
      const item = document.createElement('label');
      item.className = 'lesson-check-item';

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.checked = true;
      checkbox.addEventListener('change', () => {
        if (checkbox.checked) {
          this.selectedLessons.add(label);
        } else {
          this.selectedLessons.delete(label);
        }
        this.startQuizBtn.disabled = this.selectedLessons.size === 0;
      });

      const labelText = document.createElement('span');
      labelText.className = 'lesson-check-label';
      labelText.textContent = label.replace('Lessons ', 'L').replace('Lesson ', 'L');

      item.appendChild(checkbox);
      item.appendChild(labelText);
      this.lessonChecks.appendChild(item);
    }
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

    // Mode toggle
    this.practiceModeBtn.addEventListener('click', () => this.switchMode('practice'));
    this.quizModeBtn.addEventListener('click', () => this.switchMode('quiz'));

    // Quiz phase buttons
    this.startQuizBtn.addEventListener('click', () => this.startQuiz());
    this.startDrawingBtn.addEventListener('click', () => this.startDrawing());
    this.submitDrawingBtn.addEventListener('click', () => this.submitDrawing());
    this.correctBtn.addEventListener('click', () => this.recordResult(true));
    this.incorrectBtn.addEventListener('click', () => this.recordResult(false));

    // Summary modal buttons
    this.tryAgainBtn.addEventListener('click', () => {
      this.summaryModal.classList.remove('visible');
      this.switchMode('quiz');
    });
    this.backToPracticeBtn.addEventListener('click', () => {
      this.summaryModal.classList.remove('visible');
      this.switchMode('practice');
    });

    // Identify
    this.identifyBtn.addEventListener('click', () => this.identifyKanji());
    this.identifyModal.addEventListener('click', e => {
      if (e.target === this.identifyModal) this.identifyModal.classList.remove('visible');
    });
    document.getElementById('identifyCloseBtn')!.addEventListener('click', () => {
      this.identifyModal.classList.remove('visible');
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
    if (this.mode === 'quiz') return;
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
    if (this.mode === 'quiz') return;
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
  // QUIZ
  // ============================================================

  private switchMode(mode: Mode): void {
    this.mode = mode;

    const isPractice = mode === 'practice';
    this.practiceModeBtn.classList.toggle('active', isPractice);
    this.quizModeBtn.classList.toggle('active', !isPractice);

    this.kanjiPicker.classList.toggle('hidden', !isPractice);
    this.quizPanel.classList.toggle('hidden', isPractice);

    if (isPractice) {
      // Restore practice state
      this.canvasInput.showGuide = true;
      this.updateKanjiGuide();
      this.quizPhase = 'idle';
    } else {
      // Enter quiz mode at idle phase
      this.quizPhase = 'idle';
      this.showQuizPhase('idle');
      this.canvasInput.clear();
      this.clearInfoPanels();
    }
  }

  private showQuizPhase(phase: QuizPhase): void {
    this.quizPhaseIdle.classList.toggle('hidden', phase !== 'idle');
    this.quizPhasePrompt.classList.toggle('hidden', phase !== 'prompt');
    this.quizPhaseDraw.classList.toggle('hidden', phase !== 'draw');
    this.quizPhaseReveal.classList.toggle('hidden', phase !== 'reveal');
    this.quizPhase = phase;
  }

  private startQuiz(): void {
    // Build shuffled queue from selected lessons
    const chars = new Set<string>();
    for (const { label, characters } of LESSON_GROUPS) {
      if (this.selectedLessons.has(label)) {
        for (const ch of characters) chars.add(ch);
      }
    }

    const templates = [...chars]
      .map(ch => KANJI_TEMPLATES[ch])
      .filter((t): t is KanjiTemplate => !!t && !!t.meaning);

    // Fisher-Yates shuffle
    for (let i = templates.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [templates[i], templates[j]] = [templates[j], templates[i]];
    }

    this.quizQueue = templates;
    this.quizIndex = 0;
    this.quizScore = { correct: 0, total: 0 };

    this.showNextPrompt();
  }

  // hideTarget=true for prompt/draw (don't reveal the kanji); false for reveal.
  private renderSourceWord(
    container: HTMLElement,
    sourceWord: string,
    targetChar: string,
    hideTarget: boolean,
  ): void {
    container.innerHTML = '';
    container.className = 'quiz-source-word';
    for (const ch of sourceWord) {
      const span = document.createElement('span');
      if (ch === targetChar) {
        if (hideTarget) {
          span.textContent = '\u00a0'; // non-breaking space — blank space under the underline
          span.className = 'quiz-source-blank';
        } else {
          span.textContent = ch;
          span.className = 'quiz-source-target';
        }
      } else {
        span.textContent = ch;
        span.className = 'quiz-source-context';
      }
      container.appendChild(span);
    }
  }

  private showNextPrompt(): void {
    if (this.quizIndex >= this.quizQueue.length) {
      this.showSummary();
      return;
    }

    const template = this.quizQueue[this.quizIndex];
    const counter = `${this.quizIndex + 1} / ${this.quizQueue.length}`;

    this.quizCounter.textContent = counter;
    this.renderSourceWord(this.quizSourceWordPrompt, template.sourceWord, template.character, true);
    this.quizReading.textContent = template.reading;
    this.quizMeaning.textContent = template.meaning;

    this.canvasInput.showGuide = false;
    this.canvasInput.clear();
    this.showQuizInfoPrompt(template);
    this.showQuizPhase('prompt');
  }

  private startDrawing(): void {
    const template = this.quizQueue[this.quizIndex];
    const counter = `${this.quizIndex + 1} / ${this.quizQueue.length}`;

    this.quizCounterDraw.textContent = counter;
    this.renderSourceWord(this.quizSourceWordDraw, template.sourceWord, template.character, true);
    this.quizReadingDraw.textContent = template.reading;
    this.quizMeaningDraw.textContent = template.meaning;

    // Clear the canvas and keep guide hidden
    this.canvasInput.showGuide = false;
    this.canvasInput.clear();
    this.showQuizPhase('draw');
  }

  private submitDrawing(): void {
    const template = this.quizQueue[this.quizIndex];

    this.quizScoreDisplay.textContent = `${this.quizScore.correct} / ${this.quizScore.total} correct`;
    this.renderSourceWord(this.quizSourceWordReveal, template.sourceWord, template.character, false);
    this.quizReadingReveal.textContent = template.reading;
    this.quizMeaningReveal.textContent = template.meaning;

    // Show the reference guide
    this.canvasInput.showGuide = true;
    const colors = this.radicalsEnabled ? buildStrokeColors(template) : undefined;
    this.canvasInput.drawGuide(template.strokes, colors);

    this.showQuizInfoReveal(template);
    this.showQuizPhase('reveal');
  }

  private recordResult(correct: boolean): void {
    this.quizScore.total++;
    if (correct) this.quizScore.correct++;
    this.quizIndex++;
    this.canvasInput.showGuide = false;
    this.showNextPrompt();
  }

  private showSummary(): void {
    const { correct, total } = this.quizScore;
    this.summaryScore.textContent = `${correct} / ${total}`;
    this.summaryLabel.textContent = `correct  ·  ${Math.round((correct / total) * 100)}%`;
    this.summaryModal.classList.add('visible');
    this.showQuizPhase('idle');
  }

  // Sets the center info panel to quiz prompt state (meaning + reading, no character)
  private showQuizInfoPrompt(template: KanjiTemplate): void {
    this.infoTop.classList.remove('empty');
    this.kanjiDisplay.classList.add('empty');
    this.kanjiDisplay.classList.add('quiz-hidden');
    this.kanjiDisplay.textContent = '';
    this.onyomiText.textContent = '—';
    this.kunyomiText.textContent = template.reading || '—';
    this.meaningText.textContent = template.meaning || '';
    this.readingBarValue.classList.remove('empty');
    this.readingBarValue.textContent = template.reading || '—';
  }

  // Sets the center info panel to reveal state (shows character)
  private showQuizInfoReveal(template: KanjiTemplate): void {
    this.infoTop.classList.remove('empty');
    this.kanjiDisplay.classList.remove('empty');
    this.kanjiDisplay.classList.remove('quiz-hidden');
    this.kanjiDisplay.textContent = template.character;
    this.onyomiText.textContent = '—';
    this.kunyomiText.textContent = template.reading || '—';
    this.meaningText.textContent = template.meaning || '';
    this.readingBarValue.classList.remove('empty');
    this.readingBarValue.textContent = template.reading || '—';
  }

  // ============================================================
  // IDENTIFY (Gemini Vision)
  // ============================================================

  private async identifyKanji(): Promise<void> {
    const apiKey = (import.meta.env.VITE_GEMINI_API_KEY as string | undefined)?.trim();

    this.identifyModal.classList.add('visible');

    if (!apiKey) {
      this.identifyResult.innerHTML = `
        <div class="identify-error">No API key configured.</div>
        <div class="identify-setup">
          1. Get a free key at<br>
          <code>aistudio.google.com/app/apikey</code><br><br>
          2. Add it to<br>
          <code>web-client/.env.local</code><br><br>
          <code>VITE_GEMINI_API_KEY=your_key</code><br><br>
          3. Restart the dev server.
        </div>`;
      return;
    }

    this.identifyResult.innerHTML = '<div class="identify-loading">IDENTIFYING...</div>';

    const canvas = document.getElementById('canvas') as HTMLCanvasElement;
    const base64 = this.canvasToInvertedBase64(canvas);

    try {
      const res = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            contents: [{
              parts: [
                { inlineData: { mimeType: 'image/png', data: base64 } },
                { text: 'This is a hand-drawn Japanese kanji character. What single kanji is this? Reply with only the kanji character itself — no explanation, no other text.' },
              ],
            }],
          }),
        },
      );

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { error?: { message?: string } }).error?.message ?? `HTTP ${res.status}`);
      }

      const data = await res.json() as {
        candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }>;
      };
      const raw = data.candidates?.[0]?.content?.parts?.[0]?.text?.trim() ?? '';
      // Take only the first character in case Gemini returns extras
      const char = [...raw][0] ?? '';
      this.showIdentifyResult(char);
    } catch (e) {
      this.identifyResult.innerHTML =
        `<div class="identify-error">Recognition failed.<br>${(e as Error).message}</div>`;
    }
  }

  private canvasToInvertedBase64(canvas: HTMLCanvasElement): string {
    const offscreen = document.createElement('canvas');
    offscreen.width = canvas.width;
    offscreen.height = canvas.height;
    const ctx = offscreen.getContext('2d')!;
    // White base, then 'difference' blend inverts: dark bg → white, light strokes → dark
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, offscreen.width, offscreen.height);
    ctx.globalCompositeOperation = 'difference';
    ctx.drawImage(canvas, 0, 0);
    return offscreen.toDataURL('image/png').split(',')[1];
  }

  private showIdentifyResult(char: string): void {
    if (!char) {
      this.identifyResult.innerHTML =
        '<div class="identify-error">Could not recognise a kanji.<br>Try drawing more clearly.</div>';
      return;
    }

    const template = getTemplate(char);
    if (template) {
      this.identifyResult.innerHTML = `
        <div class="identify-char">${template.character}</div>
        <div class="identify-reading">${template.reading}</div>
        <div class="identify-meaning">${template.meaning}</div>`;
    } else {
      this.identifyResult.innerHTML = `
        <div class="identify-char">${char}</div>
        <div class="identify-note">Not in Genki dataset</div>`;
    }
  }

  // ============================================================
  // HELPERS
  // ============================================================

  private updateKanjiGuide(): void {
    // In quiz draw/prompt phase the guide is intentionally suppressed.
    if (this.quizPhase === 'draw' || this.quizPhase === 'prompt') {
      this.canvasInput.showGuide = false;
    }

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
    this.kanjiDisplay.classList.remove('quiz-hidden');
    this.kanjiDisplay.textContent = template.character;
    this.onyomiText.textContent = '—';
    this.kunyomiText.textContent = template.reading || '—';
    this.meaningText.textContent = template.meaning || '';

    this.readingBarValue.classList.remove('empty');
    this.readingBarValue.textContent = template.reading || '—';
  }

  private clearInfoPanels(): void {
    this.infoTop.classList.add('empty');
    this.kanjiDisplay.classList.add('empty');
    this.kanjiDisplay.classList.remove('quiz-hidden');
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
