"""
MIDI output engine using mido.

Converts strokes to MIDI notes and control changes for use with DAWs.
"""

from typing import Dict, Any, Optional
import time

import mido
from mido import Message, MidiFile, MidiTrack, MetaMessage

from sonify.engines.base import Sonifier
from sonify.features.kinematics import StrokeFeatures, PointFeatures
from sonify.mapping.pitch_maps import y_to_pitch, freq_to_midi_note
from sonify.mapping.dynamics_maps import force_to_amplitude


class MidiSonifier(Sonifier):
    """
    MIDI sonification engine.
    
    Each stroke becomes a MIDI note with:
    - Pitch from Y position
    - Velocity from force
    - Control changes (CC) for continuous parameters
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
                
        # Configuration
        self.min_freq = self.config.get('min_freq', 220.0)
        self.max_freq = self.config.get('max_freq', 880.0)
        self.channel = self.config.get('channel', 0)
        self.ticks_per_beat = self.config.get('ticks_per_beat', 480)
        self.tempo = self.config.get('tempo', 120)  # BPM
        
        # CC assignments
        self.cc_pressure = self.config.get('cc_pressure', 11)  # Expression
        self.cc_pan = self.config.get('cc_pan', 10)  # Pan
        self.cc_brightness = self.config.get('cc_brightness', 74)  # Brightness
        
        # MIDI file
        self.midi_file = None
        self.track = None
        self.current_time = 0  # In ticks
        self.last_event_time = 0
        
        # Current note state
        self.current_note = None
        self.note_start_time = 0
        
    def initialize(self):
        """Initialize MIDI file."""
        if self.is_active:
            return
        
        self.midi_file = MidiFile(ticks_per_beat=self.ticks_per_beat)
        self.track = MidiTrack()
        self.midi_file.tracks.append(self.track)
        
        # Add tempo
        tempo_us = mido.bpm2tempo(self.tempo)
        self.track.append(MetaMessage('set_tempo', tempo=tempo_us, time=0))
        
        # Add track name
        self.track.append(MetaMessage('track_name', name='Kanji Sonification', time=0))
        
        self.current_time = 0
        self.last_event_time = 0
        self.is_active = True
        
        print("MidiSonifier: Initialized")
    
    def shutdown(self):
        """Finalize MIDI file."""
        if not self.is_active:
            return
        
        # End of track
        delta = max(0, self.current_time - self.last_event_time)
        self.track.append(MetaMessage('end_of_track', time=delta))
        
        self.is_active = False
        print("MidiSonifier: Shutdown")
    
    def begin_kanji(self, metadata: Dict[str, Any]):
        """Begin a kanji."""
        print(f"MidiSonifier: Begin kanji {metadata.get('id', 'unknown')}")
        # Reset time
        self.current_time = 0
        self.last_event_time = 0
    
    def start_stroke(self, stroke_features: StrokeFeatures):
        """Start a new stroke - send note on."""
        self.current_stroke_id = stroke_features.stroke_id
        
        # Get initial pitch from first point
        if stroke_features.points:
            first_point = stroke_features.points[0]
            
            # Map Y to MIDI note
            freq = y_to_pitch(first_point.yN, self.min_freq, self.max_freq, invert=True)
            note = freq_to_midi_note(freq)
            
            # Map force to velocity
            velocity = int(force_to_amplitude(first_point.force, 40, 127, exponent=1.2))
            
            # Send note on
            delta = max(0, self.current_time - self.last_event_time)
            self.track.append(Message('note_on', note=note, velocity=velocity, 
                                     channel=self.channel, time=delta))
            self.last_event_time = self.current_time
            
            self.current_note = note
            self.note_start_time = self.current_time
            
            print(f"MidiSonifier: Note on - note={note}, velocity={velocity}")
    
    def update(self, point_features: PointFeatures):
        """Update with control changes."""
        if not self.is_active or self.current_note is None:
            return
        
        # Convert time to MIDI ticks
        seconds_per_beat = 60.0 / self.tempo
        ticks_per_second = self.ticks_per_beat / seconds_per_beat
        self.current_time = int(point_features.t * ticks_per_second)
        
        # Send CCs for continuous control
        # Pressure/force -> Expression (CC 11)
        cc_value = int(point_features.force * 127)
        delta = max(0, self.current_time - self.last_event_time)
        self.track.append(Message('control_change', control=self.cc_pressure,
                                 value=cc_value, channel=self.channel, time=delta))
        self.last_event_time = self.current_time
        
        # Pan (CC 10)
        pan_value = int(point_features.xN * 127)
        self.track.append(Message('control_change', control=self.cc_pan,
                                 value=pan_value, channel=self.channel, time=0))
        
        # Brightness from speed (CC 74)
        # Normalize speed (assume max speed of 1.0)
        brightness = min(int(point_features.speed * 127 / 1.0), 127)
        self.track.append(Message('control_change', control=self.cc_brightness,
                                 value=brightness, channel=self.channel, time=0))
    
    def end_stroke(self):
        """End stroke - send note off."""
        if self.current_note is None:
            return
        
        # Send note off
        delta = max(0, self.current_time - self.last_event_time)
        self.track.append(Message('note_off', note=self.current_note, velocity=64,
                                 channel=self.channel, time=delta))
        self.last_event_time = self.current_time
        
        print(f"MidiSonifier: Note off - note={self.current_note}")
        
        self.current_note = None
        self.current_stroke_id = None
        
        # Add a small gap between strokes
        gap_ticks = int(self.ticks_per_beat * 0.1)  # 0.1 beat gap
        self.current_time += gap_ticks
    
    def end_kanji(self):
        """End kanji."""
        print("MidiSonifier: End kanji")
    
    def save(self, filepath: str):
        """Save MIDI file."""
        if self.midi_file:
            self.midi_file.save(filepath)
            print(f"MidiSonifier: Saved to {filepath}")
        else:
            print("MidiSonifier: No MIDI data to save")


class MidiPortSonifier(Sonifier):
    """
    Real-time MIDI output to a port/device.
    
    Sends MIDI messages to a virtual or hardware MIDI port in real-time.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        self.port_name = self.config.get('port_name', None)  # None = use default
        self.min_freq = self.config.get('min_freq', 220.0)
        self.max_freq = self.config.get('max_freq', 880.0)
        self.channel = self.config.get('channel', 0)
        
        self.port = None
        self.current_note = None
    
    def initialize(self):
        """Open MIDI output port."""
        if self.is_active:
            return
        
        try:
            if self.port_name:
                self.port = mido.open_output(self.port_name)
            else:
                # Use default port
                self.port = mido.open_output()
            
            print(f"MidiPortSonifier: Opened port {self.port.name}")
            self.is_active = True
        except Exception as e:
            print(f"MidiPortSonifier: Could not open port - {e}")
            # List available ports
            print("Available ports:", mido.get_output_names())
            raise
    
    def shutdown(self):
        """Close MIDI port."""
        if self.port:
            # Send all notes off
            self.port.send(Message('control_change', control=123, value=0, channel=self.channel))
            self.port.close()
            print("MidiPortSonifier: Closed port")
        
        self.is_active = False
    
    def begin_kanji(self, metadata: Dict[str, Any]):
        """Begin kanji."""
        print(f"MidiPortSonifier: Begin kanji {metadata.get('id', 'unknown')}")
    
    def start_stroke(self, stroke_features: StrokeFeatures):
        """Start stroke - note on."""
        self.current_stroke_id = stroke_features.stroke_id
        
        if stroke_features.points and self.port:
            first_point = stroke_features.points[0]
            
            freq = y_to_pitch(first_point.yN, self.min_freq, self.max_freq, invert=True)
            note = freq_to_midi_note(freq)
            velocity = int(force_to_amplitude(first_point.force, 40, 127))
            
            self.port.send(Message('note_on', note=note, velocity=velocity, channel=self.channel))
            self.current_note = note
            
            print(f"MidiPortSonifier: Note on {note}")
    
    def update(self, point_features: PointFeatures):
        """Send CCs."""
        if not self.port or self.current_note is None:
            return
        
        # Send control changes
        cc_value = int(point_features.force * 127)
        self.port.send(Message('control_change', control=11, value=cc_value, channel=self.channel))
    
    def end_stroke(self):
        """End stroke - note off."""
        if self.current_note is not None and self.port:
            self.port.send(Message('note_off', note=self.current_note, velocity=64, 
                                  channel=self.channel))
            print(f"MidiPortSonifier: Note off {self.current_note}")
            self.current_note = None
            self.current_stroke_id = None
    
    def end_kanji(self):
        """End kanji."""
        print("MidiPortSonifier: End kanji")

