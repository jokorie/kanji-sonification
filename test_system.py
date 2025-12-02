#!/usr/bin/env python3
"""
Quick system test to verify the pipeline works.

This script tests the system without requiring pyo (uses DummySonifier).
"""

import os
import sys

from sonify.io.load_pencilkit import load_pencilkit_json
from sonify.features.kinematics import extract_drawing_features
from sonify.engines.base import DummySonifier


def test_system():
    """Test the complete pipeline."""
    print("=" * 60)
    print("Kanji Sonifier System Test")
    print("=" * 60)
    print()
    
    # Test 1: Load example file
    print("Test 1: Loading example kanji...")
    try:
        drawing = load_pencilkit_json("examples/水.json")
        print(f"  ✓ Loaded kanji: {drawing.metadata.get('id', 'unknown')}")
        print(f"  ✓ Canvas: {drawing.canvas.width}x{drawing.canvas.height}")
        print(f"  ✓ Strokes: {len(drawing.strokes)}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False
    
    print()
    
    # Test 2: Extract features
    print("Test 2: Extracting features...")
    try:
        features = extract_drawing_features(drawing, normalize=True)
        print(f"  ✓ Extracted features for {features.num_strokes} strokes")
        print(f"  ✓ Total duration: {features.total_duration:.2f}s")
        print(f"  ✓ Point features computed: {len(features.strokes[0].points)} points in first stroke")
        
        # Verify some feature values
        first_point = features.strokes[0].points[0]
        print(f"  ✓ First point: x={first_point.xN:.2f}, y={first_point.yN:.2f}, speed={first_point.speed:.2f}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    
    # Test 3: Run through sonifier (dummy)
    print("Test 3: Running through sonifier...")
    try:
        sonifier = DummySonifier()
        sonifier.initialize()
        
        metadata = {'id': drawing.metadata.get('id', 'unknown')}
        sonifier.begin_kanji(metadata)
        
        for stroke_features in features.strokes:
            sonifier.start_stroke(stroke_features)
            
            for point_features in stroke_features.points:
                sonifier.update(point_features)
            
            sonifier.end_stroke()
        
        sonifier.end_kanji()
        sonifier.shutdown()
        
        print("  ✓ Sonifier pipeline executed successfully")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    
    # Test 4: Test all example files
    print("Test 4: Testing all example files...")
    example_files = ['examples/一.json', 'examples/川.json', 'examples/水.json']
    
    for example_file in example_files:
        if not os.path.exists(example_file):
            print(f"  ⚠ Skipping {example_file} (not found)")
            continue
        
        try:
            d = load_pencilkit_json(example_file)
            f = extract_drawing_features(d)
            kanji_id = d.metadata.get('id', '?')
            print(f"  ✓ {kanji_id}: {f.num_strokes} strokes, {f.total_duration:.2f}s")
        except Exception as e:
            print(f"  ✗ Failed {example_file}: {e}")
            return False
    
    print()
    print("=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Install pyo for audio synthesis:")
    print("     - Linux: sudo apt-get install portaudio19-dev && pip install pyo")
    print("     - macOS: brew install portaudio && pip install pyo")
    print("  2. Run the demo: python demo.py")
    print("  3. See QUICKSTART.md for more examples")
    print()
    
    return True


if __name__ == '__main__':
    success = test_system()
    sys.exit(0 if success else 1)

