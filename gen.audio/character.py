import os
import shutil
import re
import glob
import time

LANGUAGE = "en"
REGION = "in"

def load_available_voices(language=LANGUAGE, region=REGION):
    """
    Automatically load available voices from the voices folder structure
    based on the specified language and region.
    
    Folder structure: voices/{gender}/{region}/{language}/
    Example: voices/male/in/en/ for male English voices from India
    """
    male_voices = []
    female_voices = []
    
    # Define the base path and patterns
    base_path = "voices"
    
    # Pattern for male voices
    male_pattern = os.path.join(base_path, "male", region, language, "*.wav")
    female_pattern = os.path.join(base_path, "female", region, language, "*.wav")
    
    # Load male voices
    male_files = glob.glob(male_pattern)
    for file_path in male_files:
        # Extract voice name from filename (e.g., "alok_en.wav" -> "alok_en")
        voice_name = os.path.splitext(os.path.basename(file_path))[0]
        male_voices.append(voice_name)
    
    # Load female voices
    female_files = glob.glob(female_pattern)
    for file_path in female_files:
        # Extract voice name from filename (e.g., "aisha_en.wav" -> "aisha_en")
        voice_name = os.path.splitext(os.path.basename(file_path))[0]
        female_voices.append(voice_name)
    
    # Sort voices alphabetically for consistency
    male_voices.sort()
    female_voices.sort()
    
    return male_voices, female_voices

# Load available voices based on current language setting
male_voices, female_voices = load_available_voices(LANGUAGE, REGION)

# Default character voice assignments
character_voices = {
    "male_narrator": "alok_en",
    "male_watson": "alok_en",
    "male_holmes": "ramesh_en"
}

class CharacterManager:
    def __init__(self, language=LANGUAGE, region=REGION):
        self.language = language
        self.region = region
        self.character_voices = character_voices.copy()
        # Reload voices for the specified language and region
        self.male_voices, self.female_voices = load_available_voices(language, region)
    
    def set_language(self, language):
        """Change the language and reload available voices"""
        self.language = language
        self.male_voices, self.female_voices = load_available_voices(language, self.region)
        print(f"Language changed to: {language}")
        print(f"Available male voices: {', '.join(self.male_voices)}")
        print(f"Available female voices: {', '.join(self.female_voices)}")
    
    def set_region(self, region):
        """Change the region and reload available voices"""
        self.region = region
        self.male_voices, self.female_voices = load_available_voices(self.language, region)
        print(f"Region changed to: {region}")
        print(f"Available male voices: {', '.join(self.male_voices)}")
        print(f"Available female voices: {', '.join(self.female_voices)}")
    
    def set_language_and_region(self, language, region):
        """Change both language and region and reload available voices"""
        self.language = language
        self.region = region
        self.male_voices, self.female_voices = load_available_voices(language, region)
        print(f"Language changed to: {language}, Region changed to: {region}")
        print(f"Available male voices: {', '.join(self.male_voices)}")
        print(f"Available female voices: {', '.join(self.female_voices)}")
    
    def get_available_languages(self, region=None):
        """Get list of available languages from the voices folder for a specific region"""
        if region is None:
            region = self.region
            
        languages = set()
        base_path = "voices"
        
        # Check both male and female folders
        for gender in ["male", "female"]:
            gender_path = os.path.join(base_path, gender, region)
            if os.path.exists(gender_path):
                for item in os.listdir(gender_path):
                    item_path = os.path.join(gender_path, item)
                    if os.path.isdir(item_path) and not item.startswith('.'):
                        languages.add(item)
        
        return sorted(list(languages))
    
    def get_available_regions(self):
        """Get list of available regions from the voices folder"""
        regions = set()
        base_path = "voices"
        
        # Check both male and female folders
        for gender in ["male", "female"]:
            gender_path = os.path.join(base_path, gender)
            if os.path.exists(gender_path):
                for item in os.listdir(gender_path):
                    item_path = os.path.join(gender_path, item)
                    if os.path.isdir(item_path) and not item.startswith('.'):
                        regions.add(item)
        
        return sorted(list(regions))
    
    def extract_characters_from_story(self, story_text):
        """Extract all unique characters from the story text"""
        # Find all text in square brackets
        character_pattern = r'\[([^\]]+)\]'
        characters = re.findall(character_pattern, story_text)
        
        # Remove duplicates and return unique characters
        unique_characters = list(set(characters))
        return unique_characters
    
    def assign_voices_to_characters(self, characters):
        """Assign voices to characters through user interaction"""
        updated_character_voices = self.character_voices.copy()
        
        print("\n=== CHARACTER VOICE ASSIGNMENT ===")
        print("I found the following characters in your story:")
        
        for char in characters:
            print(f"- {char}")
        
        print(f"\nCurrently assigned voices:")
        for char, voice in updated_character_voices.items():
            print(f"- {char}: {voice}")
        
        # Process characters not already assigned
        unassigned_chars = [char for char in characters if char not in updated_character_voices]
        
        if unassigned_chars:
            print(f"\nNeed to assign voices for: {', '.join(unassigned_chars)}")
            
            for char in unassigned_chars:
                # Check if character name has gender prefix
                if char.lower().startswith('male_'):
                    # Auto-assign male voice - avoid reusing already assigned voices
                    used_male_voices = [v for v in updated_character_voices.values() if v in self.male_voices]
                    available_male_voices = [v for v in self.male_voices if v not in used_male_voices]
                    
                    if available_male_voices:
                        voice = available_male_voices[0]  # Use first available voice
                        updated_character_voices[char] = voice
                        print(f"Auto-assigned male voice '{voice}' to '{char}' (male_ prefix detected)")
                    else:
                        print(f"Warning: No available male voices left for '{char}'. All male voices are already assigned.")
                        # Fallback to cycling through voices
                        male_voice_index = len(used_male_voices) % len(self.male_voices)
                        voice = self.male_voices[male_voice_index]
                        updated_character_voices[char] = voice
                        print(f"Fallback: Reused male voice '{voice}' for '{char}'")
                        
                elif char.lower().startswith('female_'):
                    # Auto-assign female voice - avoid reusing already assigned voices
                    used_female_voices = [v for v in updated_character_voices.values() if v in self.female_voices]
                    available_female_voices = [v for v in self.female_voices if v not in used_female_voices]
                    
                    if available_female_voices:
                        voice = available_female_voices[0]  # Use first available voice
                        updated_character_voices[char] = voice
                        print(f"Auto-assigned female voice '{voice}' to '{char}' (female_ prefix detected)")
                    else:
                        print(f"Warning: No available female voices left for '{char}'. All female voices are already assigned.")
                        # Fallback to cycling through voices
                        female_voice_index = len(used_female_voices) % len(self.female_voices)
                        voice = self.female_voices[female_voice_index]
                        updated_character_voices[char] = voice
                        print(f"Fallback: Reused female voice '{voice}' for '{char}'")
                        
                else:
                    # Ask for gender if no prefix found
                    while True:
                        gender = input(f"\nIs '{char}' male or female? (m/f): ").lower().strip()
                        if gender in ['m', 'male']:
                            # Assign a male voice - avoid reusing already assigned voices
                            used_male_voices = [v for v in updated_character_voices.values() if v in self.male_voices]
                            available_male_voices = [v for v in self.male_voices if v not in used_male_voices]
                            
                            if available_male_voices:
                                voice = available_male_voices[0]  # Use first available voice
                                updated_character_voices[char] = voice
                                print(f"Assigned male voice '{voice}' to '{char}'")
                            else:
                                print(f"Warning: No available male voices left for '{char}'. All male voices are already assigned.")
                                # Fallback to cycling through voices
                                male_voice_index = len(used_male_voices) % len(self.male_voices)
                                voice = self.male_voices[male_voice_index]
                                updated_character_voices[char] = voice
                                print(f"Fallback: Reused male voice '{voice}' for '{char}'")
                            break
                        elif gender in ['f', 'female']:
                            # Assign a female voice - avoid reusing already assigned voices
                            used_female_voices = [v for v in updated_character_voices.values() if v in self.female_voices]
                            available_female_voices = [v for v in self.female_voices if v not in used_female_voices]
                            
                            if available_female_voices:
                                voice = available_female_voices[0]  # Use first available voice
                                updated_character_voices[char] = voice
                                print(f"Assigned female voice '{voice}' to '{char}'")
                            else:
                                print(f"Warning: No available female voices left for '{char}'. All female voices are already assigned.")
                                # Fallback to cycling through voices
                                female_voice_index = len(used_female_voices) % len(self.female_voices)
                                voice = self.female_voices[female_voice_index]
                                updated_character_voices[char] = voice
                                print(f"Fallback: Reused female voice '{voice}' for '{char}'")
                            break
                        else:
                            print("Please enter 'm' for male or 'f' for female.")
        else:
            print("\nAll characters already have voice assignments!")
        
        # Show final character->voice mapping
        print(f"\n=== FINAL CHARACTER-VOICE MAPPING ===")
        for char in characters:
            voice = updated_character_voices.get(char, "UNASSIGNED")
            print(f"- {char}: {voice}")
        
        # Ask for confirmation
        while True:
            confirm = input(f"\nDo you accept this voice assignment? (y/n): ").lower().strip()
            if confirm in ['y', 'yes']:
                self.character_voices.update(updated_character_voices)
                print("Voice assignment confirmed!")
                
                # Update the character alias map file
                self.update_character_alias_map_file(updated_character_voices)
                
                return updated_character_voices
            elif confirm in ['n', 'no']:
                print("Exiting program as requested.")
                exit(0)
            else:
                print("Please enter 'y' for yes or 'n' for no.")
    
    def update_character_alias_map_file(self, character_voices_dict):
        """Update the character alias map file with current character-voice mappings"""
        alias_map_path = "../ComfyUI/custom_nodes/tts_audio_suite/voices_examples/#character_alias_map.txt"
        
        try:
            # Create a backup of the original file
            backup_path = alias_map_path + ".backup"
            if os.path.exists(alias_map_path):
                shutil.copy2(alias_map_path, backup_path)
                print(f"Created backup: {backup_path}")
            
            # Write the updated character-voice mappings
            with open(alias_map_path, 'w') as f:
                f.write("# Character Voice Mapping\n")
                f.write("# Format: character=voice\n\n")
                
                for character, voice in character_voices_dict.items():
                    f.write(f"{character}={voice}\n")
            
            print(f"Updated character alias map file: {alias_map_path}")
            print("Format: character=voice")
            
        except Exception as e:
            print(f"Error updating character alias map file: {e}")
            # Restore backup if update failed
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, alias_map_path)
                print("Restored original file from backup")
    
    def get_character_voices(self):
        """Get the current character voice assignments"""
        return self.character_voices.copy()
    
    def set_character_voices(self, voices_dict):
        """Set character voice assignments"""
        self.character_voices.update(voices_dict)
    
    def preprocess_story(self, story_text):
        """Preprocess the story to identify and assign voices to characters"""
        print("=== STORY PREPROCESSING ===")
        
        # Extract characters from story
        characters = self.extract_characters_from_story(story_text)
        print(f"Found {len(characters)} unique characters: {', '.join(characters)}")
        
        # Show available voices
        print(f"\nAvailable male voices: {', '.join(self.male_voices)}")
        print(f"Available female voices: {', '.join(self.female_voices)}")
        
        # Assign voices to characters
        return self.assign_voices_to_characters(characters)

def read_story_from_file(filename="story.txt"):
        """Read story data from a text file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Error: Story file '{filename}' not found.")
            print("Please create a story.txt file with your story text.")
            return None
        except Exception as e:
            print(f"Error reading story file: {e}")
            return None

if __name__ == "__main__":
    start_time = time.time()
    
    # Show available regions and languages
    setup_start = time.time()
    character_manager = CharacterManager()
    available_regions = character_manager.get_available_regions()
    available_languages = character_manager.get_available_languages()
    setup_time = time.time() - setup_start
    
    print("=== VOICE REGION AND LANGUAGE SELECTION ===")
    print(f"Available regions: {', '.join(available_regions)}")
    print(f"Available languages: {', '.join(available_languages)}")
    print(f"Current region: {REGION}, Current language: {LANGUAGE}")
    
    # Allow user to change region and language
    if len(available_regions) > 1 or len(available_languages) > 1:
        while True:
            change_settings = input(f"\nDo you want to change region/language settings? (y/n): ").lower().strip()
            if change_settings in ['y', 'yes']:
                # Region selection
                if len(available_regions) > 1:
                    print(f"Available regions: {', '.join(available_regions)}")
                    new_region = input(f"Enter region code (e.g., in): ").strip()
                    if new_region in available_regions:
                        character_manager.set_region(new_region)
                        # Update available languages for the new region
                        available_languages = character_manager.get_available_languages(new_region)
                    else:
                        print(f"Invalid region. Please choose from: {', '.join(available_regions)}")
                        continue
                
                # Language selection
                if len(available_languages) > 1:
                    print(f"Available languages for region '{character_manager.region}': {', '.join(available_languages)}")
                    new_lang = input(f"Enter language code (e.g., en, hi, ba): ").strip()
                    if new_lang in available_languages:
                        character_manager.set_language(new_lang)
                    else:
                        print(f"Invalid language. Please choose from: {', '.join(available_languages)}")
                        continue
                
                print(f"\nFinal settings - Region: {character_manager.region}, Language: {character_manager.language}")
                break
            elif change_settings in ['n', 'no']:
                break
            else:
                print("Please enter 'y' for yes or 'n' for no.")

    # Read and process story
    story_read_start = time.time()
    story_text = read_story_from_file()
    story_read_time = time.time() - story_read_start
    
    if story_text is None:
        print("Exiting due to story file error.")
        exit(1)
    
    # Time the character preprocessing
    preprocessing_start = time.time()
    character_manager.preprocess_story(story_text)
    preprocessing_time = time.time() - preprocessing_start
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Print detailed timing information
    print("\n" + "=" * 50)
    print("⏱️  TIMING SUMMARY")
    print("=" * 50)
    print(f"⚙️  Setup time: {setup_time:.3f} seconds")
    print(f"📖 Story reading time: {story_read_time:.3f} seconds")
    print(f"👥 Character preprocessing time: {preprocessing_time:.3f} seconds")
    print(f"⏱️  Total execution time: {total_time:.3f} seconds ({total_time/60:.3f} minutes)")
    print("=" * 50)
