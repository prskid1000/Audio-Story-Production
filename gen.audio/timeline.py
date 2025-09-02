import requests
import json
import time
import os
import re
from typing import List, Dict, Any

class TimelineSFXGenerator:
    def __init__(self, lm_studio_url="http://localhost:1234/v1", chunk_size=16, model="qwen/qwen3-14b", use_json_schema=True):
        self.lm_studio_url = lm_studio_url
        self.chunk_size = chunk_size
        self.output_file = "sfx.txt"
        self.model = model
        self.use_json_schema = use_json_schema
        
    def read_timeline_content(self, filename="timeline.txt") -> str:
        """Read timeline content from file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Error: Timeline file '{filename}' not found.")
            return None
        except Exception as e:
            print(f"Error reading timeline file: {e}")
            return None
    
    def parse_timeline_entries(self, content: str) -> List[Dict[str, Any]]:
        """Parse timeline content into structured entries"""
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
    
    def chunk_entries(self, entries: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Split entries into chunks of specified size"""
        chunks = []
        for i in range(0, len(entries), self.chunk_size):
            chunk = entries[i:i + self.chunk_size]
            chunks.append(chunk)
        
        print(f"📦 Split {len(entries)} entries into {len(chunks)} chunks of {self.chunk_size} lines each")
        return chunks
    
    def create_prompt_for_chunk(self, chunk: List[Dict[str, Any]]) -> str:
        """Create the prompt for LM Studio API"""
        # Build the content section
        content_lines = []
        for entry in chunk:
            content_lines.append(f"{entry['seconds']}: {entry['description']}")
        
        content = "\n".join(content_lines)
        
        prompt = f"""CONTENT:{content}"""
        
        return prompt

    def _build_response_format(self, expected_count: int) -> Dict[str, Any]:
        """Always build a strict JSON Schema response_format for segmented output."""
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "sfx_timeline",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "entries": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "index": {"type": "integer", "minimum": 0, "maximum": max(0, expected_count - 1)},
                                    "seconds": {"type": "number", "minimum": 0},
                                    "sound_or_silence_description": {"type": "string"}
                                },
                                "required": ["index", "seconds", "sound_or_silence_description"]
                            }
                        }
                    },
                    "required": ["entries"]
                },
                "strict": True
            }
        }
    
    def call_lm_studio_api(self, prompt: str, expected_count: int) -> str:
        """Call LM Studio API to generate SFX"""
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
"""You are an SFX(Sound or Silence) generator for Sound Generating AI Models.

RULES:
- Each transcript line produces exactly one Sound or one Silence line of exact same duration. Sum of all the durations should be exactly the same as the duration of the transcript line.
- Keep descriptions under 12 words, concrete, specific, unambiguous, descriptive(pitch, amplitude, timbre, sonance, frequency, etc.) and present tense.
- If no clear Sound related words or an important Action/Object that is producing sound is present in the transcript line, use 'Silence'; invent nothing yourself.
- No speech, lyrics, music, or vocal sounds. May include sounds like atmosphere/ambience deduced from the transcript line.
- Return only JSON matching the schema.

OUTPUT: JSON with entries array containing objects with index, seconds, and sound_or_silence_description"""
                    },
                    {
                        "role": "user",
                        "content": f"{prompt}\n/no_think"
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 4096,
                "stream": False
            }

            # Request structured output
            payload["response_format"] = self._build_response_format(expected_count)
            
            print(f"🤖 Calling LM Studio API...")
            response = requests.post(
                f"{self.lm_studio_url}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    print(f"✅ API call successful")
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
    
    def parse_sfx_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse the SFX response from LM Studio"""
        sfx_entries = []
        
        # Try JSON first
        json_obj = None
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
        except Exception:
            json_obj = None
        
        if json_obj is not None:
            if isinstance(json_obj, list):
                sfx_entries = json_obj
            elif isinstance(json_obj, dict):
                if "entries" in json_obj and isinstance(json_obj["entries"], list):
                    sfx_entries = json_obj["entries"]
            # Normalize segmented output
            normalized = []
            for item in sfx_entries:
                try:
                    idx = int(item["index"]) if isinstance(item, dict) and "index" in item else None
                    seconds = float(item["seconds"]) if isinstance(item, dict) and "seconds" in item else None
                    description = str(item["sound_or_silence_description"]) if isinstance(item, dict) and "sound_or_silence_description" in item else None
                    if idx is not None and seconds is not None and description is not None:
                        normalized.append({"index": idx, "seconds": seconds, "sound_or_silence_description": description})
                except Exception:
                    continue
            if normalized:
                print(f"🎯 Parsed {len(normalized)} SFX segments from JSON response")
                return normalized
        
        for line in response.strip().split('\n'):
            line = line.strip()
            if ':' in line and '"' in line:
                try:
                    # Split on first colon
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        seconds = float(parts[0].strip())
                        # Extract content between quotes
                        content_part = parts[1].strip()
                        if content_part.startswith('"') and content_part.endswith('"'):
                            description = content_part[1:-1]  # Remove quotes
                        else:
                            # Handle cases where quotes might be missing
                            description = content_part.strip('"')
                        
                        sfx_entries.append({
                            'index': 0,
                            'seconds': seconds,
                            'sound_or_silence_description': description
                        })
                except ValueError:
                    print(f"Warning: Could not parse line: {line}")
                    continue
        
        print(f"🎵 Parsed {len(sfx_entries)} SFX segments from response")
        return sfx_entries
    
    def validate_sfx_entries(self, original_entries: List[Dict[str, Any]], sfx_entries: List[Dict[str, Any]]) -> bool:
        """Validate that each input line produces exactly one output segment"""
        if not sfx_entries:
            print("❌ No SFX entries returned")
            return False
        
        n = len(original_entries)
        
        # Check that we have exactly one segment per input line
        if len(sfx_entries) != n:
            print(f"❌ Segment count mismatch: expected {n} segments, got {len(sfx_entries)}")
            return False
        
        # Validate each segment
        for i, seg in enumerate(sfx_entries):
            idx = seg.get('index')
            sec = seg.get('seconds')
            
            if idx is None or idx < 0 or idx >= n:
                print(f"❌ Invalid index in segment: {seg}")
                return False
            if sec is None or sec < 0:
                print(f"❌ Invalid seconds in segment: {seg}")
                return False
            
            # Check that duration matches the original
            orig_seconds = original_entries[idx]['seconds']
            if abs(sec - orig_seconds) > 0.02:
                print(f"❌ Line {idx} duration mismatch: expected {orig_seconds:.3f}s, got {sec:.3f}s")
                return False
        
        total_original = sum(e['seconds'] for e in original_entries)
        total_sfx = sum(seg['seconds'] for seg in sfx_entries)
        print(f"✅ Validation passed: {len(sfx_entries)} segments (1:1 mapping), {total_sfx:.3f}s total")
        return True
    
    def save_sfx_to_file(self, all_sfx_entries: List[Dict[str, Any]]) -> None:
        """Save all SFX entries to sfx.txt"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                for entry in all_sfx_entries:
                    f.write(f"{entry['seconds']}: {entry['sound_or_silence_description']}\n")
            
            total_duration = sum(entry['seconds'] for entry in all_sfx_entries)
            print(f"💾 Saved {len(all_sfx_entries)} SFX entries to {self.output_file}")
            print(f"⏱️  Total duration: {total_duration:.3f} seconds ({total_duration/60:.2f} minutes)")
            
        except Exception as e:
            raise Exception(f"Failed to save SFX file: {str(e)}")
    
    def process_timeline(self, timeline_filename="timeline.txt") -> bool:
        """Main processing function"""
        print("🚀 Starting Timeline SFX Generation...")
        print(f"📁 Reading timeline from: {timeline_filename}")
        
        # Read timeline content
        content = self.read_timeline_content(timeline_filename)
        if content is None:
            return False
        
        # Parse timeline entries
        entries = self.parse_timeline_entries(content)
        if not entries:
            print("❌ No valid timeline entries found")
            return False
        
        # Split into chunks
        chunks = self.chunk_entries(entries)
        
        # Process each chunk
        all_sfx_entries = []
        
        for i, chunk in enumerate(chunks):
            chunk_start_time = time.time()
            print(f"\n📦 Processing chunk {i+1}/{len(chunks)} ({len(chunk)} entries)")
            
            # Create prompt for this chunk
            prompt = self.create_prompt_for_chunk(chunk)
            
            try:
                # Call LM Studio API
                response = self.call_lm_studio_api(prompt, expected_count=len(chunk))
                
                # Parse SFX response
                sfx_entries = self.parse_sfx_response(response)
                
                # Validate the response
                if not self.validate_sfx_entries(chunk, sfx_entries):
                    print(f"❌ Validation failed for chunk {i+1}")
                    return False
                
                # Add to all entries
                all_sfx_entries.extend(sfx_entries)
                
                # Live preview for this chunk in duration:text format
                print("📝 Chunk output (duration:text):", flush=True)
                for seg in sfx_entries:
                    try:
                        print(f"{seg['seconds']}: {seg['sound_or_silence_description']}", flush=True)
                    except Exception:
                        continue

                chunk_end_time = time.time()
                chunk_duration = chunk_end_time - chunk_start_time
                print(f"✅ Chunk {i+1} processed successfully in {chunk_duration:.2f} seconds")
                
            except Exception as e:
                chunk_end_time = time.time()
                chunk_duration = chunk_end_time - chunk_start_time
                print(f"❌ Error processing chunk {i+1}: {str(e)} (took {chunk_duration:.2f} seconds)")
                return False
            
            # Small delay between API calls
            if i < len(chunks) - 1:
                time.sleep(1)
        
        # Save all SFX entries to file
        try:
            self.save_sfx_to_file(all_sfx_entries)
            print(f"\n🎉 Timeline SFX generation completed successfully!")
            print(f"📄 Output saved to: {self.output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving SFX file: {str(e)}")
            return False

def main():
    """Main function"""
    import sys
    
    # Check command line arguments
    timeline_file = "timeline.txt"
    if len(sys.argv) > 1:
        timeline_file = sys.argv[1]
    
    # Check if timeline file exists
    if not os.path.exists(timeline_file):
        print(f"❌ Timeline file '{timeline_file}' not found")
        print("Usage: python timeline.py [timeline_file]")
        return 1
    
    # Create generator and process
    generator = TimelineSFXGenerator()
    
    start_time = time.time()
    success = generator.process_timeline(timeline_file)
    end_time = time.time()
    
    if success:
        print(f"⏱️  Total processing time: {end_time - start_time:.2f} seconds")
        return 0
    else:
        print("❌ Processing failed")
        return 1

if __name__ == "__main__":
    exit(main())
