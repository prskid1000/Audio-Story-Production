import requests
import json
import time
import os
import re
from typing import List, Dict, Any

class TimelineSFXGenerator:
    def __init__(self, lm_studio_url="http://localhost:1234/v1", chunk_size=12, model="qwen/qwen3-14b", use_json_schema=True):
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
        seconds_only = []
        for entry in chunk:
            content_lines.append(f"{entry['seconds']}: {entry['description']}")
            seconds_only.append(entry['seconds'])
        
        content = "\n".join(content_lines)
        seconds_json = json.dumps(seconds_only)
        
        prompt = f"""CONTENT:

{content}

TASK: Convert each line into one or more natural SFX segments.

CONSTRAINTS:
- Alignment: Keep each line's audio inside its time window. Start the main cue at t=0. Do not move audio to other lines.
- Timing: For line i, segment seconds must total SECONDS[i].
- Padding: If the cue is shorter, fill the rest with fitting ambience or "Silence" to reach SECONDS[i].
- Segments: Use as few natural segments as possible; keep durations realistic.
- Relevance: Add only sounds that help the story or clarify cues. Skip trivial/incidental noises; do not fill every gap.
- Sources: Use only sounds from objects/entities in CONTENT. Do not invent new ones.
- Prominence: Mentioned sounds are foreground (loud, clear). Implied sounds are background (soft, muffled, low).
- No voice: No speech or lyrics; only environment/object sounds.
- Comfort: Avoid shrill, piercing, screeching, buzzy, metallic scraping, distorted/clipping, or tinnitus-like sounds. Prefer soft, warm timbres, smooth transitions, and moderate levels.
- Descriptions: Each sound_or_silence_description (can be "Silence") is 12 words or fewer, concrete, present tense; include key qualities when helpful (pitch, timbre, frequency, resonance).
- Specificity: Avoid vague/generic or mood-only terms (e.g., "ambient noise", "whoosh", "rumble", "music", "background noise", "SFX", "effect", "various sounds"). Always name the concrete source and action; include 1–2 acoustic qualities. If unsure or off-context, use "Silence".
- Context: Use the {self.chunk_size}-line context to choose "Silence" over other ambience.
- Output: JSON only (no markdown or extra text).

SECONDS (ordered): {seconds_json}

OUTPUT: JSON object with
- entries: [ {{ "index": integer (0-based), "seconds": number, "sound_or_silence_description": string }} ]"""
        
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
            
            # Use Qwen soft switch to disable reasoning
            prompt_no_think = f"{prompt}\n/no_think"

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a precise SFX timeline generator. "
                            "Return only a strict JSON object matching the schema. "
                            "Favor ear-friendly, non-harsh sounds; avoid piercing, shrill, or distorted noise. "
                            "Use concrete, specific sources and actions with 1–2 acoustic qualities (e.g., material, timbre, pitch). "
                            "Never use vague or generic labels like ambient, whoosh, rumble, background noise, music, SFX, effects, or various sounds. "
                            "If a specific, context-grounded sound is unclear, output 'Silence'. "
                            "No extra text."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt_no_think
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2048,
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
        """Validate segmented SFX entries against original per-line durations"""
        if not sfx_entries:
            print("❌ No SFX entries returned")
            return False
        n = len(original_entries)
        sums = {i: 0.0 for i in range(n)}
        for seg in sfx_entries:
            idx = seg.get('index')
            sec = seg.get('seconds')
            if idx is None or idx < 0 or idx >= n:
                print(f"❌ Invalid index in segment: {seg}")
                return False
            if sec is None or sec < 0:
                print(f"❌ Invalid seconds in segment: {seg}")
                return False
            sums[idx] += sec
        for i, orig in enumerate(original_entries):
            if abs(sums[i] - orig['seconds']) > 0.02:
                print(f"❌ Line {i} duration mismatch: expected {orig['seconds']:.3f}s, got {sums[i]:.3f}s")
                return False
        total_original = sum(e['seconds'] for e in original_entries)
        total_sfx = sum(seg['seconds'] for seg in sfx_entries)
        print(f"✅ Validation passed: {len(sfx_entries)} segments, {total_sfx:.3f}s total (expected {total_original:.3f}s)")
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
            print(f"\n📦 Processing chunk {i+1}/{len(chunks)} ({len(chunk)} entries)")
            
            # Create prompt for this chunk
            prompt = self.create_prompt_for_chunk(chunk)
            
            # Call LM Studio API
            try:
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

                print(f"✅ Chunk {i+1} processed successfully")
                
                # Small delay between API calls
                if i < len(chunks) - 1:
                    time.sleep(1)
                    
            except Exception as e:
                print(f"❌ Error processing chunk {i+1}: {str(e)}")
                return False
        
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
