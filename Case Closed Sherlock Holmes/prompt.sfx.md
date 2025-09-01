TASK: Analyse the duration-transcription content, and output duration-Sound/Silence content, to generate a Sound prompt for stable audio



RULES:



* Total duration of Sound + Silence must be EQUAL to the Total duration of the original transcription.
* Always split each transcription line into multiple Sound/Silence lines.
* Duration of each Sound must correspond to a comparable actual/natural duration of action/event in real life, but must be x >= 1.00000s.
* Each Sound/Silence timing must precisely fit the transcription timeline.
* Always Prefer Silence over Sound.
* Do not add any speech/vocal expression-related Sound.



FORMAT:



x.xxxxx (duration in s, where x >= 1.00000s): Silence

x.xxxxx: Sound description with loudness, timbre, pitch, sonance, frequency within 12 words.

x.xxxxx: Silence





OUTPUT: Single txt file containing duration-sound lines

