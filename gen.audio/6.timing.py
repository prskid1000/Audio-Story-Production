import requests
import json
import time
import os
import re
from typing import List, Dict, Any

class TimingSFXGenerator:
    def __init__(self, lm_studio_url="http://localhost:1234/v1", model="qwen/qwen3-14b", use_json_schema=True):
        self.lm_studio_url = lm_studio_url
        self.output_file = "sfx.txt"
        self.model = model
        self.use_json_schema = use_json_schema
        self.timeline_file = "timeline.txt"
        
    def read_timing_content(self, filename="timing.txt") -> str:
        """Read timing content from file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Error: Timing file '{filename}' not found.")
            return None
        except Exception as e:
            print(f"Error reading timing file: {e}")
            return None
    
    def read_timeline_content(self, filename="timeline.txt") -> str:
        """Read timeline content from file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"Error reading timeline file: {e}")
            return None
    
    def parse_timing_entries(self, content: str) -> List[Dict[str, Any]]:
        """Parse timing content into structured entries"""
        entries = []
        for line in content.strip().split('\n'):
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    try:
                        seconds = float(parts[0].strip())
                        description = parts[1].strip()
                        entries.append({
                            'seconds': seconds,
                            'description': description,
                            'original_line': line
                        })
                    except ValueError:
                        print(f"Warning: Invalid duration format in line: {line}")
                        continue
        
        print(f"📋 Parsed {len(entries)} timing entries")
        return entries
    
    def parse_timeline_entries(self, content: str) -> List[Dict[str, Any]]:
        """Parse timeline content into structured entries (same format as timing)"""
        entries = []
        for line in content.strip().split('\n'):
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    try:
                        seconds = float(parts[0].strip())
                        description = parts[1].strip()
                        entries.append({
                            'seconds': seconds,
                            'description': description,
                            'original_line': line
                        })
                    except ValueError:
                        print(f"Warning: Invalid duration format in line: {line}")
                        continue
        
        print(f"📋 Parsed {len(entries)} timeline entries")
        return entries
    
    def create_prompt_for_sound_duration(self, entry: Dict[str, Any], transcript_context: str = "") -> str:
        """Create the prompt for estimating realistic sound duration and position"""
        # Count words in transcript
        word_count = len(transcript_context.split())
        
        prompt = f"""Transcript: {transcript_context}

SFX: {entry['description']}

Duration: {entry['seconds']} seconds
Word count: {word_count} words

Consider:
- Realistic physics timing for this sound
- Proportion of words that need this sound effect
- Don't over-extend sounds for very long sentences
- Match sound duration to relevant action/description portion"""
        return prompt

    def _build_response_format(self) -> Dict[str, Any]:
        """Build JSON Schema response format for sound duration and position estimation."""
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "sound_timing",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "realistic_duration_seconds": {"type": "number"},
                        "position_float": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                    },
                    "required": ["realistic_duration_seconds", "position_float"]
                },
                "strict": True
            }
        }
    
    def call_lm_studio_api(self, prompt: str) -> str:
        """Call LM Studio API to estimate realistic sound duration"""
        try:
            headers = {
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": 
 """You are an audio timing expert. Estimate realistic sound effect duration and optimal placement within a transcript line.

TASK: Given a sound effect description and transcript context, estimate:
1. Realistic duration in seconds (consider physics and human experience)
2. Optimal position (0.0=start, 0.5=middle, 1.0=end of transcript line)

IMPORTANT RULES:
- Sound duration should match the relevant portion of the transcript, not the entire line
- For long sentences, don't extend sounds unnecessarily (e.g., waterfall shouldn't play for entire 20-word sentence)
- Consider word count and context - match sound to action/description portion
- Be realistic about physics (footsteps = 1-2s, door knock = 0.5s, etc.)

OUTPUT: JSON with realistic_duration_seconds and position_float fields."""
                    },
                    {
                        "role": "user",
                        "content": f"{prompt}\n/no_think"
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 128,
                "stream": False
            }

            # Request structured output
            payload["response_format"] = self._build_response_format()
            
            response = requests.post(
                f"{self.lm_studio_url}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    return content
                else:
                    raise Exception("No content in API response")
            else:
                raise Exception(f"API call failed with status {response.status_code}: {response.text}")
                
        except requests.exceptions.ConnectionError:
            raise Exception("Could not connect to LM Studio API. Make sure LM Studio is running on localhost:1234")
        except requests.exceptions.Timeout:
            raise Exception("API call timed out")
        except Exception as e:
            raise Exception(f"API call failed: {str(e)}")
    
    def parse_timing_response(self, response: str) -> Dict[str, Any]:
        """Parse the timing response from LM Studio"""
        # Try JSON first
        text = response.strip()
        # Remove code fences if present
        if text.startswith("```"):
            m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
            if m:
                text = m.group(1).strip()
        # Fallback: extract braces region
        if not text.startswith("{"):
            first = text.find("{")
            last = text.rfind("}")
            if first != -1 and last != -1 and last > first:
                text = text[first:last+1]
        
        try:
            json_obj = json.loads(text)
            if isinstance(json_obj, dict) and "realistic_duration_seconds" in json_obj:
                duration = json_obj["realistic_duration_seconds"]
                position_float = json_obj.get("position_float", 0.5)
                
                if isinstance(duration, (int, float)) and duration > 0:
                    return {
                        "duration": float(duration),
                        "position": float(position_float)
                    }
        except Exception:
            pass
        
        # Fallback: try to extract numbers from response
        numbers = re.findall(r'\d+\.?\d*', response)
        if numbers:
            try:
                return {
                    "duration": float(numbers[0]),
                    "position": 0.5
                }
            except ValueError:
                pass
        
        # Default fallback
        return None
    
    def split_entry_into_sound_and_silence(self, entry: Dict[str, Any], timing_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split a timing entry into silence + sound + silence based on position"""
        original_duration = entry['seconds']
        realistic_duration = timing_info['duration']
        position_float = timing_info['position']
        
        # Cap realistic duration at original duration
        sound_duration = min(realistic_duration, original_duration)
        
        # Calculate silence + sound + silence based on float position (0.0 to 1.0)
        before_sound = max(0, (original_duration - sound_duration) * position_float)
        after_sound = max(0, original_duration - sound_duration - before_sound)
        
        result = []
        
        # Add silence before sound (if any)
        if before_sound > 0:
            result.append({
                'seconds': before_sound,
                'description': 'Silence'
            })
        
        # Add sound entry
        if sound_duration > 0:
            result.append({
                'seconds': sound_duration,
                'description': entry['description']
            })
        
        # Add silence after sound (if any)
        if after_sound > 0:
            result.append({
                'seconds': after_sound,
                'description': 'Silence'
            })
        
        return result
    
    def post_process_entries(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Post-process entries: merge consecutive silence and adjust short durations"""
        if not entries:
            return entries
        
        print("🔧 Post-processing entries...")
        
        # Step 1: Merge consecutive silence entries
        merged_entries = []
        current_silence = None
        
        for entry in entries:
            if entry['description'] == 'Silence':
                if current_silence is None:
                    current_silence = entry.copy()
                else:
                    # Merge with existing silence
                    current_silence['seconds'] += entry['seconds']
            else:
                # Add accumulated silence if exists
                if current_silence is not None:
                    merged_entries.append(current_silence)
                    current_silence = None
                merged_entries.append(entry)
        
        # Add final silence if exists
        if current_silence is not None:
            merged_entries.append(current_silence)
        
        print(f"📊 Merged silence: {len(entries)} → {len(merged_entries)} entries")
        
        # Step 2: Convert short sounds to silence, then adjust short silence
        final_entries = []
        for i, entry in enumerate(merged_entries):
            # Convert short sounds to silence first
            if entry['seconds'] < 1.0 and entry['description'] != 'Silence':
                print(f"⚠️  Short sound converted to silence: {entry['description']} ({entry['seconds']:.3f}s)")
                entry['description'] = 'Silence'
            
            # Now adjust short silence (can borrow from any previous/next entry)
            if entry['seconds'] < 1.0 and entry['description'] == 'Silence':
                print(f"⚠️  Short silence detected: {entry['seconds']:.3f}s")
                
                # Calculate how much to borrow
                target_duration = 1.0
                needed_duration = target_duration - entry['seconds']
                
                # Try to borrow from previous entry (any type) - but don't make it < 1s
                prev_available = 0
                if i > 0 and merged_entries[i-1]['seconds'] > 1.0:
                    prev_available = min(merged_entries[i-1]['seconds'] * 0.1, needed_duration / 2)
                    # Ensure we don't make previous entry < 1s
                    if merged_entries[i-1]['seconds'] - prev_available < 1.0:
                        prev_available = max(0, merged_entries[i-1]['seconds'] - 1.0)
                
                # Try to borrow from next entry (any type) - but don't make it < 1s
                next_available = 0
                if i < len(merged_entries) - 1 and merged_entries[i+1]['seconds'] > 1.0:
                    next_available = min(merged_entries[i+1]['seconds'] * 0.1, needed_duration / 2)
                    # Ensure we don't make next entry < 1s
                    if merged_entries[i+1]['seconds'] - next_available < 1.0:
                        next_available = max(0, merged_entries[i+1]['seconds'] - 1.0)
                
                # If we can't borrow enough, distribute this entry among prev/next
                if prev_available + next_available < needed_duration:
                    print(f"   ⚠️  Cannot borrow enough time, distributing short entry")
                    
                    # Distribute current entry's duration among prev/next
                    distribute_amount = entry['seconds'] / 2
                    
                    if i > 0:
                        merged_entries[i-1]['seconds'] += distribute_amount
                        print(f"   📈 Distributed {distribute_amount:.3f}s to previous entry")
                    
                    if i < len(merged_entries) - 1:
                        merged_entries[i+1]['seconds'] += distribute_amount
                        print(f"   📈 Distributed {distribute_amount:.3f}s to next entry")
                    
                    # Mark this entry for removal
                    entry['seconds'] = 0
                    print(f"   🗑️  Entry distributed and marked for removal")
                    
                else:
                    # Apply normal borrowing adjustments
                    if prev_available > 0:
                        merged_entries[i-1]['seconds'] -= prev_available
                        print(f"   📉 Borrowed {prev_available:.3f}s from previous entry")
                    
                    if next_available > 0:
                        merged_entries[i+1]['seconds'] -= next_available
                        print(f"   📉 Borrowed {next_available:.3f}s from next entry")
                    
                    # Adjust current entry
                    entry['seconds'] += prev_available + next_available
                    print(f"   ✅ Adjusted to {entry['seconds']:.3f}s")
            
            final_entries.append(entry)
        
        # Filter out entries with 0 seconds (distributed entries)
        final_entries = [entry for entry in final_entries if entry['seconds'] > 0]
        
        print(f"🔧 Post-processing completed")
        return final_entries
    
    def save_sfx_to_file(self, all_sfx_entries: List[Dict[str, Any]]) -> None:
        """Save all SFX entries to sfx.txt"""
        try:
            # Post-process entries before saving
            processed_entries = self.post_process_entries(all_sfx_entries)
            
            with open(self.output_file, 'w', encoding='utf-8') as f:
                for entry in processed_entries:
                    f.write(f"{entry['seconds']:.3f}: {entry['description']}\n")
            
            total_duration = sum(entry['seconds'] for entry in processed_entries)
            print(f"💾 Saved {len(processed_entries)} processed SFX entries to {self.output_file}")
            print(f"⏱️  Total duration: {total_duration:.3f} seconds ({total_duration/60:.2f} minutes)")
            
        except Exception as e:
            raise Exception(f"Failed to save SFX file: {str(e)}")
    
    def process_timing(self, timing_filename="timing.txt") -> bool:
        """Main processing function - process timing and timeline together"""
        print("🚀 Starting Timing SFX Generation...")
        print(f"📁 Reading timing from: {timing_filename}")
        print(f"📁 Reading timeline from: {self.timeline_file}")
        
        # Read both files
        timing_content = self.read_timing_content(timing_filename)
        timeline_content = self.read_timeline_content(self.timeline_file)
        
        if timing_content is None or timeline_content is None:
            print("❌ Could not read one or both files")
            return False
        
        # Parse both files
        timing_entries = self.parse_timing_entries(timing_content)
        timeline_entries = self.parse_timeline_entries(timeline_content)
        
        if not timing_entries or not timeline_entries:
            print("❌ No valid entries found in one or both files")
            return False
        
        # Check if line counts match
        if len(timing_entries) != len(timeline_entries):
            print(f"⚠️  Warning: Line count mismatch! Timing: {len(timing_entries)}, Timeline: {len(timeline_entries)}")
            print("   Processing only the minimum number of lines")
            min_lines = min(len(timing_entries), len(timeline_entries))
            timing_entries = timing_entries[:min_lines]
            timeline_entries = timeline_entries[:min_lines]
        
        print(f"📋 Processing {len(timing_entries)} line pairs")
        
        # Process each pair together
        all_sfx_entries = []
        
        for i in range(len(timing_entries)):
            timing_entry = timing_entries[i]
            timeline_entry = timeline_entries[i]
            
            # Skip silence entries - only process actual sound effects
            if timing_entry['description'].lower().strip() == 'silence':
                print(f"⏭️  Skipping silence entry {i+1}: {timing_entry['seconds']}s")
                all_sfx_entries.append({
                    'seconds': timing_entry['seconds'],
                    'description': 'Silence'
                })
                continue
            
            entry_start_time = time.time()
            print(f"\n📝 Processing sound effect {i+1}/{len(timing_entries)}:")
            print(f"   🎬 Transcript: {timeline_entry['description'][:60]}...")
            print(f"   🎵 SFX: {timing_entry['description']} ({timing_entry['seconds']}s)")
            
            try:
                # Create prompt with both transcript and SFX context
                prompt = self.create_prompt_for_sound_duration(timing_entry, timeline_entry['description'])
                
                # Call LM Studio API to get realistic duration and position
                response = self.call_lm_studio_api(prompt)
                
                # Parse timing response
                timing_info = self.parse_timing_response(response)
                
                if timing_info is None:
                    print(f"⚠️  Could not parse response for line {i+1}, using default middle position")
                    timing_info = {
                        "duration": timing_entry['seconds'] * 0.3,  # 30% of original
                        "position": 0.5
                    }
                
                print(f"🎯 Original: {timing_entry['seconds']}s, Realistic: {timing_info['duration']:.2f}s, Position: {timing_info['position']:.2f}")
                
                # Split entry into silence + sound + silence based on position
                split_entries = self.split_entry_into_sound_and_silence(timing_entry, timing_info)
                
                # Add to all entries
                for split_entry in split_entries:
                    all_sfx_entries.append(split_entry)
                    print(f"🎵 {split_entry['seconds']:.3f}s - {split_entry['description']}")

                entry_end_time = time.time()
                entry_duration = entry_end_time - entry_start_time
                print(f"✅ Sound effect {i+1} processed successfully in {entry_duration:.2f} seconds")
                
            except Exception as e:
                entry_end_time = time.time()
                entry_duration = entry_end_time - entry_start_time
                print(f"❌ Error processing sound effect {i+1}: {str(e)} (took {entry_duration:.2f} seconds)")
                # Continue with next entry instead of failing completely
                all_sfx_entries.append({
                    'seconds': timing_entry['seconds'],
                    'description': timing_entry['description']
                })
            
            # Small delay between API calls
            if i < len(timing_entries) - 1:
                time.sleep(1)
        
        # Save all SFX entries to file
        try:
            self.save_sfx_to_file(all_sfx_entries)
            print(f"\n🎉 Timing SFX generation completed successfully!")
            print(f"📄 Output saved to: {self.output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving SFX file: {str(e)}")
            return False

def main():
    """Main function"""
    import sys
    
    # Check command line arguments
    timing_file = "timing.txt"
    if len(sys.argv) > 1:
        timing_file = sys.argv[1]
    
    # Check if timing file exists
    if not os.path.exists(timing_file):
        print(f"❌ Timing file '{timing_file}' not found")
        print("Usage: python timing.py [timing_file]")
        return 1
    
    # Check if timeline file exists
    if not os.path.exists("timeline.txt"):
        print(f"❌ Timeline file 'timeline.txt' not found")
        print("Both timing.txt and timeline.txt are required")
        return 1
    
    # Create generator and process
    generator = TimingSFXGenerator()
    
    start_time = time.time()
    success = generator.process_timing(timing_file)
    end_time = time.time()
    
    if success:
        print(f"⏱️  Total processing time: {end_time - start_time:.2f} seconds")
        return 0
    else:
        print("❌ Processing failed")
        return 1

if __name__ == "__main__":
    exit(main())
