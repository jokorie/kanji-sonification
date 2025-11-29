#!/usr/bin/env python3
"""
Demo script for kanji sonification.

Usage:
    python demo.py                    # Run all examples with default preset
    python demo.py --kanji 水         # Render specific kanji
    python demo.py --preset wide      # Use different preset
    python demo.py --midi             # Generate MIDI instead of audio
    python demo.py --no-playback      # Don't play audio (just save)
"""

import argparse
import os
import sys

from sonify.pipeline.render_offline import batch_render, load_config


def main():
    parser = argparse.ArgumentParser(description='Kanji Sonification Demo')
    parser.add_argument('--kanji', type=str, default=None,
                       help='Specific kanji to render (e.g., 水, 川, 一)')
    parser.add_argument('--preset', type=str, default='default',
                       help='Preset name (default, wide_range, subtle, midi_default)')
    parser.add_argument('--midi', action='store_true',
                       help='Generate MIDI output instead of audio')
    parser.add_argument('--no-playback', action='store_true',
                       help='Disable real-time playback (only save to file)')
    parser.add_argument('--batch', action='store_true',
                       help='Render all example kanji')
    parser.add_argument('--rate', type=float, default=1.0,
                       help='Playback rate multiplier (2.0 = 2x slower, 0.5 = 2x faster, default: 1.0)')
    
    args = parser.parse_args()
    
    # Determine preset path
    if args.midi:
        preset_path = 'presets/midi_default.yaml'
    else:
        preset_path = f'presets/{args.preset}.yaml'
    
    if not os.path.exists(preset_path):
        print(f"Error: Preset not found: {preset_path}")
        print("Available presets: default, wide_range, subtle, midi_default")
        return 1
    
    # Load config from preset file
    config = load_config(preset_path)
    
    # Override config with command-line arguments
    config.rate_multiplier = args.rate
    config.playback = not args.no_playback
    # Create output directory
    os.makedirs('output', exist_ok=True)
    
    # Batch mode
    input_files = []
    if args.kanji:
        input_files = [f'examples/{args.kanji}.json']
        
    if args.batch:
        input_files.extend([
            'examples/一.json',
            'examples/川.json',
            'examples/三.json',
            'examples/水.json',
        ])
        
    # Filter existing files
    input_files = [f for f in input_files if os.path.exists(f)]
        
    if not input_files:
        print("Error: No example kanji files found in examples/")
        return 1
    
    print(f"Batch rendering {len(input_files)} kanji files...")
    print(f"Preset: {preset_path}")
    print(f"Rate multiplier: {config.rate_multiplier}x")
    print()
    
    batch_render(
        input_files=input_files,
        config=config,
    )
        
    return 0


if __name__ == '__main__':
    sys.exit(main())

