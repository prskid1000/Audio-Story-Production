import os
import re
import whisper
import time
import math

def format_timestamp(seconds):
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

def get_silence_text(duration):
    """
    Generate silence text with dots based on duration.
    Add 1 dot for every 2 seconds of silence.
    """
    # Calculate number of dots: 1 dot per 2 seconds, minimum 1 dot
    num_dots = max(1, math.ceil(duration / 2.0))
    
    # Build the silence text using a for loop
    silence_text = ""
    for i in range(num_dots):
        silence_text += "."
    
    return silence_text

def handle_initial_gap(segment, continuous_segments, current_time):
    """Handle gap before the first segment"""
    if segment["start"] <= 0.1:
        return current_time
    
    initial_gap = segment["start"]
    if initial_gap < 2.0:  # Extend first segment
        segment["start"] -= initial_gap
        print(f"Adjusted first segment start by -{initial_gap:.3f}s to fill initial gap")
        return current_time
    else:  # Add silence
        silence_text = get_silence_text(initial_gap)
        continuous_segments.append({
            "start": current_time,
            "end": current_time + initial_gap,
            "text": silence_text
        })
        print(f"Added initial silence: {initial_gap:.3f}s ({silence_text})")
        return current_time + initial_gap

def handle_segment_gap(segment, previous_segment, continuous_segments, current_time):
    """Handle gap between segments"""
    gap = segment["start"] - previous_segment["end"]
    if gap <= 0.1:
        return current_time
    
    if gap < 2.0:  # Extend adjacent segments
        extension = gap / 2.0
        if continuous_segments:
            continuous_segments[-1]["end"] += extension
            current_time += extension
            print(f"Extended previous segment by {extension:.3f}s to fill gap")
        
        segment["start"] -= extension
        print(f"Adjusted current segment start by -{extension:.3f}s")
        return current_time
    else:  # Add silence
        silence_text = get_silence_text(gap)
        continuous_segments.append({
            "start": current_time,
            "end": current_time + gap,
            "text": silence_text
        })
        print(f"Added silence gap: {gap:.3f}s at {previous_segment['end']:.3f}s ({silence_text})")
        return current_time + gap

def add_segment(segment, continuous_segments, current_time):
    """Add a segment to the continuous timeline"""
    segment_duration = segment["end"] - segment["start"]
    continuous_segments.append({
        "start": current_time,
        "end": current_time + segment_duration,
        "text": segment["text"]
    })
    return current_time + segment_duration

def add_final_silence(continuous_segments, current_time, target_duration):
    """Add final silence to reach target duration"""
    final_silence = target_duration - current_time
    if final_silence > 0.1:
        silence_text = get_silence_text(final_silence)
        continuous_segments.append({
            "start": current_time,
            "end": target_duration,
            "text": silence_text
        })
        print(f"Added final silence: {final_silence:.3f}s ({silence_text})")



def post_process_segments(segments, target_duration=1978.68):
    """
    Post-process segments to make timeline continuous by adding silent segments.
    Creates a continuous timeline with [SILENCE] markers for gaps.
    For gaps less than 2s, extends adjacent segments to make them continuous.
    """
    if not segments:
        return segments
    
    # Calculate current total duration
    current_duration = segments[-1]["end"] - segments[0]["start"]
    missing_duration = target_duration - current_duration
    
    print(f"Current duration: {current_duration:.3f}s")
    print(f"Target duration: {target_duration:.3f}s")
    print(f"Missing duration: {missing_duration:.3f}s")
    
    if missing_duration <= 0:
        print("No missing duration to add")
        return segments
    
    # Create new continuous timeline
    continuous_segments = []
    current_time = 0.0
    
    for i, segment in enumerate(segments):
        # Handle gaps before segments
        if i == 0:
            current_time = handle_initial_gap(segment, continuous_segments, current_time)
        else:
            current_time = handle_segment_gap(segment, segments[i-1], continuous_segments, current_time)
        
        # Add the actual segment
        current_time = add_segment(segment, continuous_segments, current_time)
    
    # Add final silence if needed
    add_final_silence(continuous_segments, current_time, target_duration)
    
    # Verify final duration
    final_duration = continuous_segments[-1]["end"] - continuous_segments[0]["start"]
    print(f"Final continuous duration: {final_duration:.3f}s")
    print(f"Total segments (including silence): {len(continuous_segments)}")
    
    return continuous_segments

def generate_files(segments, srt_file, text_file, timeline_file):
    """Generate SRT, text, and timeline files from segments"""
    
    # Generate SRT content
    srt_content = ""
    for i, segment in enumerate(segments, 1):
        start_time = format_timestamp(segment["start"])
        end_time = format_timestamp(segment["end"])
        text = re.sub(r'\s+', ' ', segment["text"].strip())
        srt_content += f"{start_time} --> {end_time}\n{text}\n\n"
    
    # Generate text content (excluding silence markers)
    text_content = ""
    for segment in segments:
        text = re.sub(r'\s+', ' ', segment["text"].strip())
        # Skip segments that are just dots (silence markers)
        if not re.match(r'^\.+$', text):  # Only dots from start to end
            text_content += text + " "
    text_content = text_content.strip()
    
    # Generate timeline content
    timeline_content = ""
    total_duration = 0
    for segment in segments:
        duration = segment["end"] - segment["start"]
        total_duration += duration
        text = re.sub(r'\s+', ' ', segment["text"].strip())
        timeline_content += f"{duration:.3f}: {text}\n"
    
    # Write files
    with open(srt_file, 'w', encoding='utf-8') as f:
        f.write(srt_content)
    
    with open(text_file, 'w', encoding='utf-8') as f:
        f.write(text_content)
    
    with open(timeline_file, 'w', encoding='utf-8') as f:
        f.write(timeline_content)
    
    print(f"SRT file saved to: {srt_file}")
    print(f"Text file saved to: {text_file}")
    print(f"Timeline file saved to: {timeline_file}")
    
    return total_duration

def transcribe_audio(audio_path, srt_file, text_file, timeline_file, model_name="large"):
    """Transcribe audio and generate all output files"""
    try:
        print(f"Loading Whisper model: {model_name}")
        model = whisper.load_model(model_name)
        
        print(f"Transcribing audio file: {audio_path}")
        result = model.transcribe(
            audio_path, 
            verbose=True,
            temperature=0.0,
            compression_ratio_threshold=1.0,
            logprob_threshold=-0.5,
            condition_on_previous_text=False,
            no_speech_threshold=0.1
        )
        
        segment_count = len(result['segments'])
        print(f"Original segments: {segment_count}")
        
        # Post-process segments to make timeline continuous
        print("\nPost-processing segments...")
        processed_segments = post_process_segments(result["segments"])
        
        # Generate all files
        total_duration = generate_files(processed_segments, srt_file, text_file, timeline_file)
        return True, total_duration, segment_count
        
    except Exception as e:
        print(f"Error during transcription: {str(e)}")
        return False, 0, 0



def main():
    """Main function to transcribe story.wav and generate three output files"""
    start_time = time.time()
    
    audio_file = "output/story.wav"
    srt_file = "story.srt"
    text_file = "story.str.txt"
    timeline_file = "timeline.txt"
    original_text_file = "story.txt"
    
    if not os.path.exists(audio_file):
        print(f"Error: Audio file '{audio_file}' not found!")
        return
    
    print("Starting audio transcription with OpenAI Whisper...")
    print("=" * 50)
    
    # Time the transcription process
    transcription_start = time.time()
    result = transcribe_audio(audio_file, srt_file, text_file, timeline_file)
    transcription_time = time.time() - transcription_start
    
    if result[0]:  # success
        total_duration = result[1]
        segment_count = result[2]
        print("\nTranscription completed successfully!")
        print(f"\n✅ Process completed! Files generated:")
        print(f"  • {srt_file} (Original SRT format)")
        print(f"  • {text_file} (Plain text format)")
        print(f"  • {timeline_file} (Duration computed format)")
        
        # Display total duration
        minutes = int(total_duration // 60)
        seconds = total_duration % 60
        print(f"\n📊 TRANSCRIPTION SUMMARY:")
        print(f"  • Total audio duration: {total_duration:.3f} seconds ({minutes}m {seconds:.3f}s)")
        print(f"  • Number of segments: {segment_count}")
        
        print(f"\n💡 To analyze transcription quality, run: python similarity.py")
    else:
        print("\nTranscription failed!")
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Print detailed timing information
    print("\n" + "=" * 50)
    print("⏱️  TIMING SUMMARY")
    print("=" * 50)
    print(f"📝 Transcription time: {transcription_time:.3f} seconds")
    print(f"⏱️  Total execution time: {total_time:.3f} seconds ({total_time/60:.3f} minutes)")
    print("=" * 50)

if __name__ == "__main__":
    main()
