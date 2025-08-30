import os
import json
from pathlib import Path
import re
import whisper

# Configuration
SIMILARITY_THRESHOLD = 0.8  # 80% word similarity threshold for merging

def merge_adjacent_same_words(segments):
    """
    Merge adjacent timestamp entries that contain similar words to reduce repetition
    
    Args:
        segments (list): List of segments from Whisper result
        
    Returns:
        list: Merged segments with adjacent similar words combined
    """
    if not segments:
        return segments
    
    def get_word_frequency(text):
        """Get word frequency map from text"""
        words = re.findall(r'\b\w+\b', text.lower())
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        return word_freq
    
    def calculate_similarity(freq1, freq2):
        """Calculate similarity between two word frequency maps"""
        if not freq1 or not freq2:
            return 0.0
        
        # Calculate total word counts for each segment
        total_words1 = sum(freq1.values())
        total_words2 = sum(freq2.values())
        
        # Determine which is larger and which is smaller
        if total_words1 >= total_words2:
            larger_freq = freq1
            smaller_freq = freq2
        else:
            larger_freq = freq2
            smaller_freq = freq1
        
        # Store larger segment as array of words
        larger_words = []
        for word, count in larger_freq.items():
            larger_words.extend([word] * count)
        
        # Search for all words of larger in map of smaller
        found_words = 0
        for word in larger_words:
            if word in smaller_freq and smaller_freq[word] > 0:
                found_words += 1
                smaller_freq[word] -= 1  # Decrease count as we use it
        
        # Calculate similarity as percentage of larger segment found in smaller
        similarity = found_words / len(larger_words) if larger_words else 0.0
        
        return similarity
    
    merged_segments = []
    current_segment = segments[0].copy()
    
    for i in range(1, len(segments)):
        next_segment = segments[i]
        
        # Get word frequency maps
        current_freq = get_word_frequency(current_segment["text"])
        next_freq = get_word_frequency(next_segment["text"])
        
        # Calculate similarity
        similarity = calculate_similarity(current_freq, next_freq)
        
        # Check if similarity meets threshold
        if similarity >= SIMILARITY_THRESHOLD:
            # Merge the segments by extending the end time
            old_end = current_segment["end"]
            current_segment["end"] = next_segment["end"]
            print(f"✅ MERGED ({similarity:.1%} similar): '{current_segment['text'].strip()}' - Extended time from {format_timestamp(old_end)} to {format_timestamp(current_segment['end'])}")
            continue
        else:
            # Different text, add current segment to results and start new one
            merged_segments.append(current_segment)
            current_segment = next_segment.copy()
    
    # Add the last segment
    merged_segments.append(current_segment)
    
    print(f"📊 Merging complete: {len(segments)} → {len(merged_segments)} entries")
    return merged_segments

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
        result = model.transcribe(
            audio_path, 
            verbose=True,
            temperature=0.0,  # Deterministic, no creativity
            compression_ratio_threshold=1.0,  # Lower threshold to catch more repetition
            logprob_threshold=-0.5,  # Higher confidence threshold
            condition_on_previous_text=False,  # Don't use previous text to avoid repetition
            word_timestamps=False
        )
        
        # Merge adjacent same words before generating SRT
        merged_segments = merge_adjacent_same_words(result["segments"])
        
        print(f"Original segments: {len(result['segments'])}, Merged segments: {len(merged_segments)}")
        
        # Generate SRT content from merged segments
        srt_content = generate_srt_from_segments(merged_segments)
        
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
            print(f"\n✅ Process completed! Files generated:")
            print(f"  • {srt_file}")
            print(f"  • {sfx_text_file}")
        else:
            print("\nError extracting text from SRT file!")
    else:
        print("\nTranscription failed!")

if __name__ == "__main__":
    main()
