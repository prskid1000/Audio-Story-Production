import os
import re
import whisper
import time

def format_timestamp(seconds):
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

def generate_files(segments, srt_file, text_file, timeline_file):
    """Generate SRT, text, and timeline files from segments"""
    
    # Generate SRT content
    srt_content = ""
    for i, segment in enumerate(segments, 1):
        start_time = format_timestamp(segment["start"])
        end_time = format_timestamp(segment["end"])
        text = re.sub(r'\s+', ' ', segment["text"].strip())
        srt_content += f"{start_time} --> {end_time}\n{text}\n\n"
    
    # Generate text content
    text_content = ""
    for segment in segments:
        text = re.sub(r'\s+', ' ', segment["text"].strip())
        text_content += text + " "
    text_content = text_content.strip()
    
    # Generate timeline content
    timeline_content = ""
    for segment in segments:
        duration = segment["end"] - segment["start"]
        text = re.sub(r'\s+', ' ', segment["text"].strip())
        timeline_content += f"{duration}: {text}\n"
    
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
            word_timestamps=False
        )
        
        print(f"Original segments: {len(result['segments'])}")
        
        # Generate all files
        generate_files(result["segments"], srt_file, text_file, timeline_file)
        return True
        
    except Exception as e:
        print(f"Error during transcription: {str(e)}")
        return False



def main():
    """Main function to transcribe story.wav and generate three output files"""
    start_time = time.time()
    
    audio_file = "story.wav"
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
    success = transcribe_audio(audio_file, srt_file, text_file, timeline_file)
    transcription_time = time.time() - transcription_start
    
    if success:
        print("\nTranscription completed successfully!")
        print(f"\n✅ Process completed! Files generated:")
        print(f"  • {srt_file} (Original SRT format)")
        print(f"  • {text_file} (Plain text format)")
        print(f"  • {timeline_file} (Duration computed format)")
        
        print(f"\n💡 To analyze transcription quality, run: python similarity.py")
    else:
        print("\nTranscription failed!")
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Print detailed timing information
    print("\n" + "=" * 50)
    print("⏱️  TIMING SUMMARY")
    print("=" * 50)
    print(f"📝 Transcription time: {transcription_time:.2f} seconds")
    print(f"⏱️  Total execution time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
    print("=" * 50)

if __name__ == "__main__":
    main()
