TASK: Analyse the duration-transcription content, and output duration-Sound content, to generate Sound prompt for stable audio

LENGTH: Double Check and Match, Total duration of Sound + Silence = Total duration of transcript in duration-transcription file

CONTENT: Either Sound Prompt for x.xxxxx seconds or Silence for x.xxxxx seconds

FORMAT:

x.xxxxx (duration in s, where x >= 1.00000s): Silence
x.xxxxx: Sound Prompt that include sound description, loudness, timbre, pitch, sonance, frequency within 12 words. 
x.xxxxx: Silence

RULES:

- Always split a single duration-transcription line multiple(at least 3) duration-Sound lines.
- Duration of each Sound must corresponds to comparable actual duration in real life.
- Each Sound/Silence timing must corresponds to timing of action/event in the given transcription.
- Do not add any speech/vocal expression related Sound.
- Add Background Atmospheric Sound(Faint/Soft/Gentle) Effects where needed.

OUTPUT: Single txt file containing duration-sound lines