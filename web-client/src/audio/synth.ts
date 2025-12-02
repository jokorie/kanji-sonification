/**
 * Web Audio API Synthesizer for Kanji Sonification.
 * 
 * Creates a real-time synthesis graph that maps pencil input to sound.
 * Uses manual stereo panning with power curves for more pronounced effect.
 */

import { SynthParams, SynthConfig, DEFAULT_SYNTH_CONFIG } from '../types';

/**
 * Apply power curve to pan value for more dramatic stereo separation.
 * 
 * Linear panning sounds weak — power curves make L/R more distinct
 * while keeping some signal in both channels (no dead zones).
 * 
 * @param pan - Input pan value [-1, 1]
 * @param power - Curve power (higher = more extreme, default 2)
 * @returns {left, right} gain values [0, 1]
 */
function panToCurvedGains(pan: number, power: number = 2): { left: number; right: number } {
  // Clamp pan to [-1, 1]
  const p = Math.max(-1, Math.min(1, pan));
  
  // Convert from [-1, 1] to [0, 1] where 0=left, 1=right
  const panNorm = (p + 1) / 2;
  
  // Apply power curve for more dramatic panning
  // Use equal-power-ish curve: ensures consistent loudness across pan range
  const angle = panNorm * Math.PI / 2; // 0 to π/2
  
  // Base equal-power panning
  let right = Math.sin(angle);
  let left = Math.cos(angle);
  
  // Apply additional power curve for more extreme separation
  right = Math.pow(right, power);
  left = Math.pow(left, power);
  
  // Ensure minimum presence in both channels (no dead silence on either side)
  const minGain = 0.05;
  left = minGain + left * (1 - minGain);
  right = minGain + right * (1 - minGain);
  
  return { left, right };
}

export class KanjiSynth {
  private audioCtx: AudioContext | null = null;
  private oscillator: OscillatorNode | null = null;
  private gainNode: GainNode | null = null;
  private leftGain: GainNode | null = null;
  private rightGain: GainNode | null = null;
  private merger: ChannelMergerNode | null = null;
  private vibratoOsc: OscillatorNode | null = null;
  private vibratoGain: GainNode | null = null;
  
  private config: SynthConfig;
  private isPlaying: boolean = false;
  private isInitialized: boolean = false;

  constructor(config: SynthConfig = DEFAULT_SYNTH_CONFIG) {
    this.config = config;
  }

  /**
   * Initialize the audio context and synthesis graph.
   * Must be called from a user gesture (click/touch) due to browser autoplay policy.
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) return;

    // Create audio context with low-latency hint
    // 'interactive' tells the browser to prioritize low latency over power efficiency
    this.audioCtx = new AudioContext({
      latencyHint: 'interactive',
      sampleRate: 44100,
    });
    
    // Resume if suspended (autoplay policy)
    if (this.audioCtx.state === 'suspended') {
      await this.audioCtx.resume();
    }
    
    // Log actual latency for debugging
    console.log(`🎵 Audio latency: base=${(this.audioCtx.baseLatency * 1000).toFixed(1)}ms, output=${((this.audioCtx.outputLatency || 0) * 1000).toFixed(1)}ms`);

    // Create main oscillator
    this.oscillator = this.audioCtx.createOscillator();
    this.oscillator.type = 'sine';
    this.oscillator.frequency.value = this.config.minFreq;

    // Create vibrato LFO
    this.vibratoOsc = this.audioCtx.createOscillator();
    this.vibratoOsc.type = 'sine';
    this.vibratoOsc.frequency.value = 5; // Default vibrato rate

    // Vibrato depth control
    this.vibratoGain = this.audioCtx.createGain();
    this.vibratoGain.gain.value = 0; // Start with no vibrato

    // Connect vibrato: LFO → gain → oscillator frequency
    this.vibratoOsc.connect(this.vibratoGain);
    this.vibratoGain.connect(this.oscillator.frequency);

    // Create main gain node (amplitude/volume control)
    this.gainNode = this.audioCtx.createGain();
    this.gainNode.gain.value = 0; // Start silent

    // Create manual stereo panning with separate L/R gain nodes
    // This allows power-curve panning for more dramatic stereo effect
    this.leftGain = this.audioCtx.createGain();
    this.rightGain = this.audioCtx.createGain();
    this.leftGain.gain.value = 0.5;
    this.rightGain.gain.value = 0.5;

    // Channel merger to combine L/R into stereo output
    this.merger = this.audioCtx.createChannelMerger(2);

    // Connect the graph:
    // oscillator → mainGain → leftGain  → merger[0] (left)
    //                       → rightGain → merger[1] (right)
    // merger → destination
    this.oscillator.connect(this.gainNode);
    this.gainNode.connect(this.leftGain);
    this.gainNode.connect(this.rightGain);
    this.leftGain.connect(this.merger, 0, 0);   // Left channel
    this.rightGain.connect(this.merger, 0, 1);  // Right channel
    this.merger.connect(this.audioCtx.destination);

    // Start oscillators (they run continuously, we control with gain)
    this.oscillator.start();
    this.vibratoOsc.start();

    this.isInitialized = true;
    console.log('🎵 KanjiSynth initialized (with curved stereo panning)');
  }

  /**
   * Start sound (pen down).
   * 
   * @param initialParams - Optional initial parameters to snap to immediately (no smoothing)
   */
  startSound(initialParams?: SynthParams): void {
    if (!this.isInitialized || !this.audioCtx || !this.gainNode) return;
    
    this.isPlaying = true;
    const now = this.audioCtx.currentTime;
    
    // If initial params provided, snap to them immediately (no smoothing)
    // This prevents the "slide" from previous stroke's end position
    if (initialParams) {
      // Snap frequency
      if (this.oscillator) {
        this.oscillator.frequency.cancelScheduledValues(now);
        this.oscillator.frequency.setValueAtTime(initialParams.frequency, now);
      }
      
      // Snap pan
      if (this.leftGain && this.rightGain) {
        const { left, right } = panToCurvedGains(initialParams.pan, 1.5);
        this.leftGain.gain.cancelScheduledValues(now);
        this.rightGain.gain.cancelScheduledValues(now);
        this.leftGain.gain.setValueAtTime(left, now);
        this.rightGain.gain.setValueAtTime(right, now);
      }
      
      // Snap vibrato
      if (this.vibratoOsc) {
        this.vibratoOsc.frequency.cancelScheduledValues(now);
        this.vibratoOsc.frequency.setValueAtTime(initialParams.vibratoRate, now);
      }
      if (this.vibratoGain) {
        this.vibratoGain.gain.cancelScheduledValues(now);
        this.vibratoGain.gain.setValueAtTime(initialParams.vibratoDepth, now);
      }
      
      // Snap amplitude (use initial amplitude, very quick fade to minimize latency)
      this.gainNode.gain.cancelScheduledValues(now);
      this.gainNode.gain.setTargetAtTime(initialParams.amplitude, now, 0.003); // 3ms fade
    } else {
      // No initial params, just fade in to min amplitude
      this.gainNode.gain.cancelScheduledValues(now);
      this.gainNode.gain.setTargetAtTime(this.config.minAmp, now, 0.003); // 3ms fade
    }
  }

  /**
   * Stop sound (pen up).
   */
  stopSound(): void {
    if (!this.isInitialized || !this.audioCtx || !this.gainNode) return;
    
    this.isPlaying = false;
    
    // Quick fade out to avoid click (but fast enough to feel responsive)
    const now = this.audioCtx.currentTime;
    this.gainNode.gain.cancelScheduledValues(now);
    this.gainNode.gain.setTargetAtTime(0, now, 0.015); // 15ms fade out
  }

  /**
   * Update synthesis parameters in real-time.
   */
  update(params: SynthParams): void {
    if (!this.isInitialized || !this.isPlaying || !this.audioCtx) return;

    const now = this.audioCtx.currentTime;
    const smoothing = this.config.smoothingTime;

    // Update frequency (pitch)
    if (this.oscillator) {
      this.oscillator.frequency.setTargetAtTime(params.frequency, now, smoothing);
    }

    // Update amplitude (volume)
    if (this.gainNode) {
      this.gainNode.gain.setTargetAtTime(params.amplitude, now, smoothing);
    }

    // Update pan with power-curve stereo separation
    if (this.leftGain && this.rightGain) {
      const { left, right } = panToCurvedGains(params.pan, 1.5); // power=1.5 for noticeable but not extreme
      this.leftGain.gain.setTargetAtTime(left, now, smoothing);
      this.rightGain.gain.setTargetAtTime(right, now, smoothing);
    }

    // Update vibrato
    if (this.vibratoOsc) {
      this.vibratoOsc.frequency.setTargetAtTime(params.vibratoRate, now, smoothing);
    }
    if (this.vibratoGain) {
      this.vibratoGain.gain.setTargetAtTime(params.vibratoDepth, now, smoothing);
    }
  }

  /**
   * Get whether synth is currently playing.
   */
  get playing(): boolean {
    return this.isPlaying;
  }

  /**
   * Get whether synth is initialized.
   */
  get initialized(): boolean {
    return this.isInitialized;
  }

  /**
   * Shutdown and clean up.
   */
  shutdown(): void {
    if (this.oscillator) {
      this.oscillator.stop();
      this.oscillator.disconnect();
    }
    if (this.vibratoOsc) {
      this.vibratoOsc.stop();
      this.vibratoOsc.disconnect();
    }
    if (this.gainNode) {
      this.gainNode.disconnect();
    }
    if (this.leftGain) {
      this.leftGain.disconnect();
    }
    if (this.rightGain) {
      this.rightGain.disconnect();
    }
    if (this.merger) {
      this.merger.disconnect();
    }
    if (this.audioCtx) {
      this.audioCtx.close();
    }
    
    this.isInitialized = false;
    this.isPlaying = false;
    console.log('🔇 KanjiSynth shutdown');
  }
}

