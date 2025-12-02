#!/usr/bin/env python3
"""
Test script for online sonifier.

Tests the streaming sonifier with single-stroke kanji (e.g., 一).
"""

import os
import sys
from sonify.pipeline.render_online import stream_kanji_from_json
from sonify.pipeline.render_offline import Config, load_config
from sonify.features.grid_normalize import create_default_grid


def test_online_sonifier():
    """Test the online sonifier with 一.json."""
    print("=" * 60)
    print("Online Sonifier Test")
    print("=" * 60)
    print()
    
    # Test file
    test_file = "examples/一.json"
    
    if not os.path.exists(test_file):
        print(f"Error: Test file not found: {test_file}")
        print("Please ensure examples/一.json exists")
        return False
    
    print(f"Testing with: {test_file}")
    print()
    
    # Load config
    try:
        config = load_config("presets/default.yaml")
        print(f"Loaded config: engine={config.engine}, min_freq={config.min_freq}Hz")
    except Exception as e:
        print(f"Warning: Could not load config, using defaults: {e}")
        config = Config()
    
    # Create output directory
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Test 1: Basic streaming
    print("Test 1: Basic streaming sonification...")
    try:
        output_path = os.path.join(output_dir, "一_online.wav")
        
        stream_kanji_from_json(
            json_path=test_file,
            output_path=output_path,
            config=config
        )
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"  ✓ Success! Output saved to: {output_path} ({file_size} bytes)")
        else:
            print(f"  ✗ Output file not created: {output_path}")
            return False
            
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    
    # # Test 2: Custom grid
    # print("Test 2: Custom grid normalization...")
    # try:
    #     output_path = os.path.join(output_dir, "一_online_custom_grid.wav")
    #     custom_grid = (0, 0, 1024, 1024)
        
    #     stream_kanji_from_json(
    #         json_path=test_file,
    #         grid=custom_grid,
    #         sonifier=None,
    #         output_path=output_path,
    #         playback_rate=1.0,
    #         config=config
    #     )
        
    #     if os.path.exists(output_path):
    #         print(f"  ✓ Success! Output saved to: {output_path}")
    #     else:
    #         print(f"  ✗ Output file not created: {output_path}")
    #         return False
            
    # except Exception as e:
    #     print(f"  ✗ Failed: {e}")
    #     import traceback
    #     traceback.print_exc()
    #     return False
    
    # print()
    
    # # Test 3: Faster playback
    # print("Test 3: Faster playback rate (2x)...")
    # try:
    #     output_path = os.path.join(output_dir, "一_online_2x.wav")
        
    #     stream_kanji_from_json(
    #         json_path=test_file,
    #         grid=None,
    #         sonifier=None,
    #         output_path=output_path,
    #         playback_rate=2.0,  # 2x faster
    #         config=config
    #     )
        
    #     if os.path.exists(output_path):
    #         print(f"  ✓ Success! Output saved to: {output_path}")
    #     else:
    #         print(f"  ✗ Output file not created: {output_path}")
    #         return False
            
    # except Exception as e:
    #     print(f"  ✗ Failed: {e}")
    #     import traceback
    #     traceback.print_exc()
    #     return False
    
    print()
    print("=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    print()
    print("Output files:")
    print(f"  - {output_dir}/一_online.wav")
    # print(f"  - {output_dir}/一_online_custom_grid.wav")
    # print(f"  - {output_dir}/一_online_2x.wav")
    print()
    
    return True


if __name__ == '__main__':
    success = test_online_sonifier()
    sys.exit(0 if success else 1)

