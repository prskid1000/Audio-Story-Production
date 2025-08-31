TASK: Analyse the duration-transcription content, and output duration-Sound content, to generate Sound prompt for stable audio

LENGTH: Double Check and Match, Total duration of Sound + Silence = Total duration of transcript in duration-transcription file

CONTENT: Either Sound Prompt for x seconds or Silence for x seconds

FORMAT:

x(duration in s): Silence
x: Sound Prompt that include sound description, loudness, timbre, pitch, sonance, frequency within 12 words. 
x: Silence

RULES:

- Always split a single duration-transcription line multiple(at least 3) duration-Sound lines.
- Duration of each Sound must corresponds to comparable actual duration in real life.
- Each SFX timing must corresponds to timing of action/event in the given transcription.
- Do not add any speech/tone related  Sound. 

OUTPUT: Single txt file containing duration-sound lines