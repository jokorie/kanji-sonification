#!/usr/bin/env python3
"""
Analyze left and right channel amplitudes in WAV files.

Usage:
    python analyze_channels.py output/川.wav
    python analyze_channels.py output/川.wav --window 0.1  # Use 100ms windows for RMS
"""

import argparse
import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile
from scipy import signal
import os
import sys


def load_wav(filepath: str):
    """Load WAV file and return sample rate and audio data."""
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    
    sample_rate, audio_data = wavfile.read(filepath)
    
    # Convert to float32 if needed
    if audio_data.dtype == np.int16:
        audio_data = audio_data.astype(np.float32) / 32768.0
    elif audio_data.dtype == np.int32:
        audio_data = audio_data.astype(np.float32) / 2147483648.0
    
    return sample_rate, audio_data


def analyze_channels(filepath: str, window_size: float = 0.1):
    """
    Analyze left and right channels of a stereo WAV file.
    
    Args:
        filepath: Path to WAV file
        window_size: Window size in seconds for RMS calculation
    """
    print(f"Loading: {filepath}")
    sample_rate, audio_data = load_wav(filepath)
    
    # Handle mono files
    if len(audio_data.shape) == 1:
        print("Warning: File is mono, duplicating to stereo for analysis")
        audio_data = np.column_stack([audio_data, audio_data])
    
    # Extract channels
    if audio_data.shape[1] < 2:
        print("Error: File must be stereo (2 channels)")
        sys.exit(1)
    
    left_channel = audio_data[:, 0]
    right_channel = audio_data[:, 1]
    
    duration = len(left_channel) / sample_rate
    time_axis = np.arange(len(left_channel)) / sample_rate
    
    print(f"Sample rate: {sample_rate} Hz")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Channels: {audio_data.shape[1]}")
    print()
    
    # Calculate statistics
    left_rms = np.sqrt(np.mean(left_channel ** 2))
    right_rms = np.sqrt(np.mean(right_channel ** 2))
    left_peak = np.max(np.abs(left_channel))
    right_peak = np.max(np.abs(right_channel))
    
    print("=== Overall Statistics ===")
    print(f"Left channel RMS:  {left_rms:.6f}")
    print(f"Right channel RMS: {right_rms:.6f}")
    print(f"RMS ratio (L/R):   {left_rms / right_rms:.3f}" if right_rms > 0 else "RMS ratio: N/A")
    print()
    print(f"Left channel peak:  {left_peak:.6f}")
    print(f"Right channel peak: {right_peak:.6f}")
    print(f"Peak ratio (L/R):  {left_peak / right_peak:.3f}" if right_peak > 0 else "Peak ratio: N/A")
    print()
    
    # Calculate RMS over time windows
    window_samples = int(window_size * sample_rate)
    if window_samples < 1:
        window_samples = 1
    
    num_windows = len(left_channel) // window_samples
    left_rms_time = []
    right_rms_time = []
    time_windows = []
    
    for i in range(num_windows):
        start_idx = i * window_samples
        end_idx = start_idx + window_samples
        left_window = left_channel[start_idx:end_idx]
        right_window = right_channel[start_idx:end_idx]
        
        left_rms_time.append(np.sqrt(np.mean(left_window ** 2)))
        right_rms_time.append(np.sqrt(np.mean(right_window ** 2)))
        time_windows.append((start_idx + end_idx) / 2 / sample_rate)
    
    left_rms_time = np.array(left_rms_time)
    right_rms_time = np.array(right_rms_time)
    time_windows = np.array(time_windows)
    
    # Calculate amplitude envelope (for visualization)
    # Use a simple moving average of absolute values
    envelope_window = int(0.01 * sample_rate)  # 10ms window
    if envelope_window < 1:
        envelope_window = 1
    
    left_envelope = np.convolve(np.abs(left_channel), 
                                np.ones(envelope_window) / envelope_window, 
                                mode='same')
    right_envelope = np.convolve(np.abs(right_channel), 
                                 np.ones(envelope_window) / envelope_window, 
                                 mode='same')
    
    # Create plots
    fig, axes = plt.subplots(4, 1, figsize=(12, 10))
    fig.suptitle(f'Channel Analysis: {os.path.basename(filepath)}', fontsize=14, fontweight='bold')
    
    # Plot 1: Waveforms (first 1 second or full if shorter)
    ax1 = axes[0]
    plot_duration = min(1.0, duration)
    plot_samples = int(plot_duration * sample_rate)
    ax1.plot(time_axis[:plot_samples], left_channel[:plot_samples], 
             label='Left', alpha=0.7, linewidth=0.5)
    ax1.plot(time_axis[:plot_samples], right_channel[:plot_samples], 
             label='Right', alpha=0.7, linewidth=0.5)
    ax1.set_xlabel('Time (seconds)')
    ax1.set_ylabel('Amplitude')
    ax1.set_title(f'Waveforms (first {plot_duration:.1f}s)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
    
    # Plot 2: Amplitude envelopes (full duration)
    ax2 = axes[1]
    ax2.plot(time_axis, left_envelope, label='Left envelope', alpha=0.8, linewidth=1)
    ax2.plot(time_axis, right_envelope, label='Right envelope', alpha=0.8, linewidth=1)
    ax2.set_xlabel('Time (seconds)')
    ax2.set_ylabel('Amplitude')
    ax2.set_title('Amplitude Envelopes (10ms smoothing)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: RMS over time
    ax3 = axes[2]
    ax3.plot(time_windows, left_rms_time, label='Left RMS', alpha=0.8, linewidth=1.5)
    ax3.plot(time_windows, right_rms_time, label='Right RMS', alpha=0.8, linewidth=1.5)
    ax3.set_xlabel('Time (seconds)')
    ax3.set_ylabel('RMS Amplitude')
    ax3.set_title(f'RMS Levels (window size: {window_size*1000:.0f}ms)')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: RMS ratio over time
    ax4 = axes[3]
    ratio = left_rms_time / (right_rms_time + 1e-10)  # Add small epsilon to avoid division by zero
    ax4.plot(time_windows, ratio, label='L/R Ratio', color='purple', linewidth=1.5)
    ax4.axhline(y=1.0, color='k', linestyle='--', linewidth=1, label='Equal (1.0)')
    ax4.set_xlabel('Time (seconds)')
    ax4.set_ylabel('RMS Ratio (Left/Right)')
    ax4.set_title('Channel Balance Over Time')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save plot
    output_plot = filepath.rsplit('.', 1)[0] + '_channels.png'
    plt.savefig(output_plot, dpi=150, bbox_inches='tight')
    print(f"Plot saved to: {output_plot}")
    
    # Show plot
    plt.show()
    
    # Print time-based statistics
    print("=== Time-Based Analysis ===")
    print(f"Average RMS ratio (L/R): {np.mean(ratio):.3f}")
    print(f"Max RMS ratio (L/R):     {np.max(ratio):.3f}")
    print(f"Min RMS ratio (L/R):     {np.min(ratio):.3f}")
    print(f"Std dev of ratio:        {np.std(ratio):.3f}")
    print()
    
    # Check for bias
    if np.mean(ratio) > 1.2:
        print("⚠️  WARNING: Left channel is significantly louder (bias detected)")
    elif np.mean(ratio) < 0.8:
        print("⚠️  WARNING: Right channel is significantly louder (bias detected)")
    else:
        print("✓ Channels appear balanced")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze left and right channel amplitudes in WAV files'
    )
    parser.add_argument('filepath', type=str, help='Path to WAV file')
    parser.add_argument('--window', type=float, default=0.1,
                       help='Window size in seconds for RMS calculation (default: 0.1)')
    
    args = parser.parse_args()
    
    analyze_channels(args.filepath, args.window)


if __name__ == '__main__':
    main()

