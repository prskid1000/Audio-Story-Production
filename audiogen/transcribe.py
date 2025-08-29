import os
import json
from pathlib import Path
import re
import whisper

def transcribe_audio_to_srt(audio_path, output_path, model_name="base"):
    """
    Transcribe audio file to SRT format using OpenAI Whisper
    
    Args:
        audio_path (str): Path to the audio file
        output_path (str): Path to save the SRT file
        model_name (str): Whisper model size (tiny, base, small, medium, large)
    """
    try:
        print(f"Loading Whisper model: {model_name}")
        model = whisper.load_model(model_name)
        
        print(f"Transcribing audio file: {audio_path}")
        result = model.transcribe(audio_path, verbose=True)
        
        # Generate SRT content
        srt_content = generate_srt_from_segments(result["segments"])
        
        # Write to output file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        print(f"SRT file saved to: {output_path}")
        return True
        
    except Exception as e:
        print(f"Error during transcription: {str(e)}")
        return False

def generate_srt_from_segments(segments):
    """
    Convert Whisper segments to SRT format
    
    Args:
        segments (list): List of segments from Whisper result
        
    Returns:
        str: SRT formatted content
    """
    srt_content = ""
    
    for i, segment in enumerate(segments, 1):
        start_time = format_timestamp(segment["start"])
        end_time = format_timestamp(segment["end"])
        text = segment["text"].strip()
        
        # Clean up text (remove extra spaces, normalize)
        text = re.sub(r'\s+', ' ', text)
        
        srt_content += f"{i}\n"
        srt_content += f"{start_time} --> {end_time}\n"
        srt_content += f"{text}\n\n"
    
    return srt_content

def format_timestamp(seconds):
    """
    Convert seconds to SRT timestamp format (HH:MM:SS,mmm)
    
    Args:
        seconds (float): Time in seconds
        
    Returns:
        str: Formatted timestamp
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

def extract_text_from_srt(srt_path, output_path):
    """
    Extract plain text from SRT file for SFX generation
    
    Args:
        srt_path (str): Path to the SRT file
        output_path (str): Path to save the plain text
    """
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract text lines (skip timestamp and subtitle number lines)
        lines = content.split('\n')
        text_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip empty lines, subtitle numbers, and timestamp lines
            if (line and 
                not line.isdigit() and 
                not '-->' in line and 
                not re.match(r'^\d{2}:\d{2}:\d{2},\d{3}$', line)):
                text_lines.append(line)
        
        # Join text lines
        full_text = ' '.join(text_lines)
        
        # Write to output file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        
        print(f"Plain text extracted and saved to: {output_path}")
        return True
        
    except Exception as e:
        print(f"Error extracting text from SRT: {str(e)}")
        return False

def main():
    """
    Main function to transcribe story.wav and generate sfx.txt
    """
    # File paths
    audio_file = "story.wav"
    srt_file = "story.srt"
    sfx_text_file = "story.str.txt"
    
    # Check if audio file exists
    if not os.path.exists(audio_file):
        print(f"Error: Audio file '{audio_file}' not found!")
        return
    
    print("Starting audio transcription with OpenAI Whisper...")
    print("=" * 50)
    
    # Step 1: Transcribe audio to SRT
    success = transcribe_audio_to_srt(audio_file, srt_file, model_name="large")
    
    if success:
        print("\nTranscription completed successfully!")
        
        # Step 2: Extract plain text for SFX generation
        print("\nExtracting plain text for SFX generation...")
        extract_success = extract_text_from_srt(srt_file, sfx_text_file)
        
        if extract_success:
            print("\nProcess completed successfully!")
            print(f"SRT file: {srt_file}")
            print(f"SFX text file: {sfx_text_file}")
        else:
            print("\nError extracting text from SRT file!")
    else:
        print("\nTranscription failed!")

if __name__ == "__main__":
    main()
