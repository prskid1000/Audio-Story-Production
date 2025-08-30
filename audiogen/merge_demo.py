#!/usr/bin/env python3
"""
Demonstration script for the audio transcription and merging functionality.
This script shows how to use different merging options to handle repetitive phrases.
"""

import os
import sys
from transcribe import transcribe_audio_to_srt, merge_adjacent_same_words, merge_adjacent_same_words_advanced

def demo_merging_options():
    """Demonstrate different merging options"""
    
    audio_file = "story.wav"
    
    if not os.path.exists(audio_file):
        print(f"Error: Audio file '{audio_file}' not found!")
        print("Please ensure you have a 'story.wav' file in the current directory.")
        return
    
    print("=" * 60)
    print("AUDIO TRANSCRIPTION WITH MERGING DEMONSTRATION")
    print("=" * 60)
    
    # Option 1: No merging (original behavior)
    print("\n1. TRANSCRIBING WITH NO MERGING (Original segments)")
    print("-" * 40)
    success1 = transcribe_audio_to_srt(
        audio_file, 
        "story_no_merge.srt", 
        model_name="large",
        no_merge=True
    )
    
    if success1:
        print("✅ No-merge transcription completed")
    
    # Option 2: Simple merging (exact matches only)
    print("\n2. TRANSCRIBING WITH SIMPLE MERGING (Exact matches)")
    print("-" * 40)
    success2 = transcribe_audio_to_srt(
        audio_file, 
        "story_simple_merge.srt", 
        model_name="large",
        simple_merge=True
    )
    
    if success2:
        print("✅ Simple merge transcription completed")
    
    # Option 3: Advanced merging (similarity-based)
    print("\n3. TRANSCRIBING WITH ADVANCED MERGING (Similarity-based)")
    print("-" * 40)
    success3 = transcribe_audio_to_srt(
        audio_file, 
        "story_advanced_merge.srt", 
        model_name="large",
        similarity_threshold=0.8
    )
    
    if success3:
        print("✅ Advanced merge transcription completed")
    
    # Option 4: Aggressive merging (lower similarity threshold)
    print("\n4. TRANSCRIBING WITH AGGRESSIVE MERGING (Lower threshold)")
    print("-" * 40)
    success4 = transcribe_audio_to_srt(
        audio_file, 
        "story_aggressive_merge.srt", 
        model_name="large",
        similarity_threshold=0.6
    )
    
    if success4:
        print("✅ Aggressive merge transcription completed")
    
    # Summary
    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETED")
    print("=" * 60)
    
    files_created = []
    if success1:
        files_created.extend([
            "story_no_merge.srt",
            "story_no_merge.str.txt",
            "story_no_merge_original_segments.json",
            "story_no_merge_merged_segments.json"
        ])
    
    if success2:
        files_created.extend([
            "story_simple_merge.srt",
            "story_simple_merge.str.txt",
            "story_simple_merge_original_segments.json",
            "story_simple_merge_merged_segments.json"
        ])
    
    if success3:
        files_created.extend([
            "story_advanced_merge.srt",
            "story_advanced_merge.str.txt",
            "story_advanced_merge_original_segments.json",
            "story_advanced_merge_merged_segments.json"
        ])
    
    if success4:
        files_created.extend([
            "story_aggressive_merge.srt",
            "story_aggressive_merge.str.txt",
            "story_aggressive_merge_original_segments.json",
            "story_aggressive_merge_merged_segments.json"
        ])
    
    print(f"\n📁 Files created: {len(files_created)}")
    print("\nGenerated files:")
    for file in files_created:
        if os.path.exists(file):
            size = os.path.getsize(file)
            print(f"  ✅ {file} ({size} bytes)")
        else:
            print(f"  ❌ {file} (not found)")
    
    print("\n📋 Comparison:")
    print("  • No merge: Original transcription without any merging")
    print("  • Simple merge: Merges only exact duplicate phrases")
    print("  • Advanced merge: Merges similar phrases (80% similarity)")
    print("  • Aggressive merge: Merges more similar phrases (60% similarity)")
    
    print("\n💡 Usage tips:")
    print("  • Use '--no-merge' to disable merging completely")
    print("  • Use '--simple-merge' for exact phrase matching only")
    print("  • Use '--similarity-threshold 0.8' for balanced merging")
    print("  • Use '--similarity-threshold 0.6' for aggressive merging")
    print("  • Check the JSON files to see what was merged")

if __name__ == "__main__":
    demo_merging_options()
