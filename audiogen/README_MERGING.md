# Audio Transcription with Adjacent Word Merging

This enhanced transcription system can merge adjacent segments that contain the same or similar words, reducing repetition in the output SRT files.

## Features

- **Simple Merging**: Merges only exact duplicate phrases
- **Advanced Merging**: Uses similarity-based merging with configurable threshold
- **JSON Debug Files**: Saves both original and merged segments for comparison
- **Command-line Options**: Flexible control over merging behavior
- **Multiple Output Formats**: SRT subtitles and plain text files

## Usage

### Basic Usage

```bash
# Transcribe with default advanced merging (80% similarity threshold)
python transcribe.py

# Transcribe with custom audio file
python transcribe.py --audio my_audio.wav --output my_output.srt
```

### Merging Options

```bash
# Disable merging completely (original behavior)
python transcribe.py --no-merge

# Use simple merging (exact matches only)
python transcribe.py --simple-merge

# Use advanced merging with custom similarity threshold
python transcribe.py --similarity-threshold 0.7

# Use aggressive merging (lower threshold = more merging)
python transcribe.py --similarity-threshold 0.6
```

### Full Command-line Options

```bash
python transcribe.py [OPTIONS]

Options:
  --audio FILE              Input audio file (default: story.wav)
  --output FILE             Output SRT file (default: story.srt)
  --model {tiny,base,small,medium,large}
                            Whisper model size (default: large)
  --similarity-threshold FLOAT
                            Similarity threshold for merging (0.0-1.0, default: 0.8)
  --no-merge               Disable merging of adjacent same words
  --simple-merge           Use simple merging instead of advanced merging
```

## Output Files

For each transcription, the system generates:

1. **`story.srt`** - Final merged SRT subtitles
2. **`story.str.txt`** - Plain text extracted from SRT for SFX generation
3. **`story_original_segments.json`** - Original transcription segments (for debugging)
4. **`story_merged_segments.json`** - Merged transcription segments (for debugging)

## Merging Algorithms

### Simple Merging
- Merges only segments with **exact** text matches
- Case-insensitive comparison
- Normalizes whitespace

### Advanced Merging
- Uses **similarity-based** merging with configurable threshold
- Calculates word overlap similarity between adjacent segments
- Detects common repetitive patterns
- More intelligent handling of similar phrases

### Similarity Threshold
- **0.8 (default)**: Balanced merging - merges similar but not identical phrases
- **0.6**: Aggressive merging - merges more similar phrases
- **1.0**: Conservative merging - only exact matches
- **0.0**: Very aggressive - merges almost everything

## Demonstration

Run the demonstration script to see all merging options in action:

```bash
python merge_demo.py
```

This will create multiple versions of the transcription with different merging strategies for comparison.

## Example Output

### Before Merging (Original)
```
1
[00:00:00,000 --> 00:00:02,500]
Anved Doyo, redescended once more, and said,

2
[00:00:02,500 --> 00:00:04,800]
Anved Doyo, redescended once more, and said,

3
[00:00:04,800 --> 00:00:07,200]
Anved Doyo, redescended once more, and said,
```

### After Merging (Advanced)
```
1
[00:00:00,000 --> 00:00:07,200]
Anved Doyo, redescended once more, and said,
```

## Use Cases

- **Repetitive Speech**: Handles stuttering, repeated phrases, or speech artifacts
- **Audio Quality Issues**: Reduces noise in transcriptions from poor audio
- **Whisper Artifacts**: Addresses common Whisper model repetition issues
- **Clean Subtitles**: Produces cleaner, more readable subtitle files

## Technical Details

### Similarity Calculation
The advanced merging uses Jaccard similarity:
```
similarity = |words1 ∩ words2| / |words1 ∪ words2|
```

### Repetitive Pattern Detection
Detects common patterns like:
- Same word repeated: `"word, word"`
- Same phrase repeated: `"phrase, phrase"`
- High word overlap between adjacent segments

### JSON Debug Format
```json
{
  "index": 1,
  "start": 0.0,
  "end": 2.5,
  "duration": 2.5,
  "text": "Anved Doyo, redescended once more, and said,",
  "start_formatted": "00:00:00,000",
  "end_formatted": "00:00:02,500"
}
```

## Troubleshooting

### Too Much Merging
- Increase similarity threshold: `--similarity-threshold 0.9`
- Use simple merging: `--simple-merge`
- Disable merging: `--no-merge`

### Not Enough Merging
- Decrease similarity threshold: `--similarity-threshold 0.6`
- Check JSON files to see what's being merged

### Debugging
- Check the JSON files to see original vs merged segments
- Compare different merging strategies using the demo script
- Adjust similarity threshold based on your specific audio content
