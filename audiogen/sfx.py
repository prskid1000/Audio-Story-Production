import json
import requests
import time
import os
from pydub import AudioSegment
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class DirectTimelineProcessor:
    def __init__(self, comfyui_url="http://127.0.0.1:8188/", max_workers=3):
        self.comfyui_url = comfyui_url
        self.output_folder = "../ComfyUI/output/audio/sfx"
        self.final_output = "sfx.wav"
        self.max_workers = max_workers
        self.lock = threading.Lock()
        
        # Create output folder if it doesn't exist
        os.makedirs(self.output_folder, exist_ok=True)
        
        # Clear the output folder
        self.clear_output_folder()
        
        # Clear the final output file if it exists
        if os.path.exists(self.final_output):
            os.remove(self.final_output)
            print(f"Removed existing final output: {self.final_output}")
        
    def parse_timeline(self, timeline_text):
        """Parse the timeline text into structured data"""
        timeline_entries = []
        
        # Split by lines and process each entry
        lines = timeline_text.strip().split('\n')
        for line in lines:
            if ':' in line:
                # Extract duration and description
                parts = line.split(':', 1)
                if len(parts) == 2:
                    description = parts[1].strip()
                    
                    # Convert duration string to seconds
                    seconds = self.duration_to_seconds(parts[0].strip())
                    
                    timeline_entries.append({
                        'seconds': seconds,
                        'description': description
                    })
        
        return timeline_entries
    
    def clear_output_folder(self):
        """Clear all files from the output folder"""
        print(f"Clearing output folder: {self.output_folder}")
        try:
            if os.path.exists(self.output_folder):
                for file in os.listdir(self.output_folder):
                    file_path = os.path.join(self.output_folder, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"Removed: {file}")
                print("Output folder cleared successfully")
            else:
                print("Output folder does not exist, creating it")
        except Exception as e:
            print(f"Error clearing output folder: {e}")
    
    def duration_to_seconds(self, duration_str):
        """Convert duration string (e.g., '10', '15', '25') to seconds"""
        try:
            # Handle both integer and float strings, convert to int
            return float(duration_str)
        except ValueError:
            print(f"Failed to convert duration '{duration_str}' to number")
            return 0
    
    def load_sfx_workflow(self):
        """Load the SFX workflow from JSON"""
        with open('sfx.json', 'r') as f:
            return json.load(f)
    
    def find_node_by_type(self, workflow, node_type):
        """Find a node by its type"""
        for node_id, node in workflow.items():
            if node.get('class_type') == node_type:
                return node
        return None
    
    def update_workflow_text(self, workflow, text_prompt):
        """Update the text prompt in the workflow"""
        # Find the CLIPTextEncode node and update its text
        node = self.find_node_by_type(workflow, 'CLIPTextEncode')
        if node:
            node['inputs']['text'] = text_prompt
        return workflow
    
    def update_workflow_duration(self, workflow, duration):
        """Update the duration in the workflow"""
        # Find the EmptyLatentAudio node and update its duration
        node = self.find_node_by_type(workflow, 'EmptyLatentAudio')
        if node:
            node['inputs']['seconds'] = duration
        return workflow
    
    def update_workflow_filename(self, workflow, filename):
        """Update the filename in the SaveAudio node"""
        # Find the SaveAudio node and update its filename
        node = self.find_node_by_type(workflow, 'SaveAudio')
        if node:
            node['inputs']['filename_prefix'] = f"audio/sfx/{filename}"
        return workflow
    
    def generate_single_sfx(self, entry_data):
        """Generate a single SFX audio file"""
        i, entry = entry_data
        
        # Get duration from entry
        duration = entry['seconds']
        print(f"Duration from entry: {duration} (type: {type(duration)})")
        
        # Skip entries with 0 duration
        if duration <= 0:
            print(f"Skipping entry with duration <= 0: {duration}")
            return None
        
        # Create filename with duration info
        filename = f"sfx_{i:03d}_{entry['seconds']}"
        
        try:
            print(f"Generating: {entry['description']} (duration: {duration}s)")
            
            # Load and update workflow
            workflow = self.load_sfx_workflow()
            workflow = self.update_workflow_text(workflow, entry['description'])
            workflow = self.update_workflow_duration(workflow, duration)
            workflow = self.update_workflow_filename(workflow, filename)
            
            # Send workflow to ComfyUI
            print(f"Sending workflow to ComfyUI...")
            try:
                response = requests.post(f"{self.comfyui_url}prompt", json={"prompt": workflow}, timeout=30)
                print(f"Response status: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"ComfyUI response: {response.text}")
                    raise Exception(f"Failed to send workflow: {response.text}")
                
                response_json = response.json()
                print(f"Response JSON: {response_json}")
                prompt_id = response_json["prompt_id"]
                print(f"Workflow sent successfully, prompt_id: {prompt_id}")
                
            except requests.exceptions.Timeout:
                print("Timeout while sending workflow to ComfyUI")
                raise Exception("Timeout while sending workflow to ComfyUI")
            except Exception as e:
                print(f"Error sending workflow: {e}")
                raise
            
            # Wait for completion
            while True:
                history_response = requests.get(f"{self.comfyui_url}history/{prompt_id}")
                if history_response.status_code == 200:
                    history_data = history_response.json()
                    if prompt_id in history_data:
                        status = history_data[prompt_id].get('status', {})
                        if status.get('exec_info', {}).get('queue_remaining', 0) == 0:
                            # Check if there are outputs
                            outputs = history_data[prompt_id].get('outputs', {})
                            for node_id, node_output in outputs.items():
                                if 'audio' in node_output:
                                    for audio_file in node_output['audio']:
                                        # The file is already saved in the ComfyUI output folder
                                        # Look for it in the expected location
                                        # Wait a bit longer for the file to be written
                                        time.sleep(3)
                                        
                                        # Try to find the file with the correct pattern
                                        # Look for files that start with our filename and end with .flac
                                        print(f"Looking for files starting with '{filename}' in {self.output_folder}")
                                        files_in_folder = os.listdir(self.output_folder)
                                        print(f"Files in folder: {files_in_folder}")
                                        
                                        # Look for files that start with our base filename and end with .flac
                                        # ComfyUI adds duration info like "_00001_" to the filename
                                        matching_files = []
                                        for file in files_in_folder:
                                            if file.startswith(filename) and file.endswith('.flac'):
                                                matching_files.append(file)
                                        
                                        if matching_files:
                                            # Sort by modification time and get the most recent
                                            matching_files.sort(key=lambda x: os.path.getmtime(os.path.join(self.output_folder, x)), reverse=True)
                                            most_recent_file = matching_files[0]
                                            found_path = os.path.join(self.output_folder, most_recent_file)
                                            print(f"Found generated file: {found_path}")
                                            return {
                                                'file': found_path,
                                                'start_time': entry['seconds'],
                                                'duration': duration,
                                                'description': entry['description']
                                            }
                                        
                                        print(f"No files found starting with '{filename}'")
                            break
                time.sleep(5)
            
            raise Exception(f"Failed to generate audio for: {entry['description']}")
                
        except Exception as e:
            print(f"Error generating audio for '{entry['description']}': {e}")
            return None
    

    
    def generate_all_sfx_batch(self, timeline_entries):
        """Generate all SFX audio files using batch processing"""
        generated_files = []
        
        # Prepare data for batch processing
        batch_data = []
        for i, entry in enumerate(timeline_entries):
            batch_data.append((i, entry))
        
        # Process in batches using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_entry = {executor.submit(self.generate_single_sfx, data): data for data in batch_data}
            
            # Collect results as they complete
            for future in as_completed(future_to_entry):
                result = future.result()
                if result:
                    generated_files.append(result)
        
        return generated_files
    
    def concatenate_audio_files(self, generated_files):
        """Concatenate all generated audio files into final audio"""
        print("Concatenating audio files...")
        
        # Sort files by start time
        generated_files.sort(key=lambda x: x['start_time'])
        
        # Load and concatenate audio files
        final_audio = AudioSegment.empty()
        
        for file_info in generated_files:
            try:
                # Handle both FLAC and WAV files
                if file_info['file'].endswith('.flac'):
                    audio_segment = AudioSegment.from_file(file_info['file'], format="flac")
                else:
                    audio_segment = AudioSegment.from_wav(file_info['file'])
                final_audio = final_audio + audio_segment
                print(f"Added: {file_info['file']} ({file_info['description']})")
            except Exception as e:
                print(f"Error loading {file_info['file']}: {e}")
                continue
        
        # Export final audio
        final_audio.export(self.final_output, format="wav")
        print(f"Final audio saved as: {self.final_output}")
        
        return self.final_output
    
    def process_timeline(self, timeline_text):
        """Main processing function"""
        print("Processing timeline...")
        
        # Parse timeline
        timeline_entries = self.parse_timeline(timeline_text)
        print(f"Parsed {len(timeline_entries)} timeline entries")
        
        # Generate all SFX files using batch processing
        generated_files = self.generate_all_sfx_batch(timeline_entries)
        print(f"Generated {len(generated_files)} audio files")
        
        # Concatenate into final audio
        final_audio = self.concatenate_audio_files(generated_files)
        
        print("Processing complete!")
        return final_audio

def read_timeline_from_file(filename="sfx.txt"):
    """Read timeline data from a text file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Timeline file '{filename}' not found.")
        print("Please create a sfx.txt file with your timeline data in the format:")
        print("10: Description of first sound (10 seconds duration)")
        print("15: Description of second sound (15 seconds duration)")
        print("25: Description of third sound (25 seconds duration)")
        return None
    except Exception as e:
        print(f"Error reading timeline file: {e}")
        return None

if __name__ == "__main__":
    # Read timeline data from file
    timeline_text = read_timeline_from_file()
    
    if timeline_text is None:
        print("Exiting due to timeline file error.")
        exit(1)
    
    # Create processor and run
    processor = DirectTimelineProcessor(max_workers=3)
    final_audio = processor.process_timeline(timeline_text)
    print(f"Final audio file: {final_audio}")
