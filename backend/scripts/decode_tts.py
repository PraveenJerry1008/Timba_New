"""
Dev helper: turn a Sarvam /tts response into a playable WAV file.

Usage:
1. Call POST /tts (see backend/main.py) and copy the "audio_base64" value
   from the response.
2. Paste it into a file called audio_base64.txt in this same folder
   (just the raw string, no quotes).
3. Run: python scripts/decode_tts.py
4. Open the resulting hello.wav in any media player to confirm the
   TTS pipeline is actually producing audio.

Not part of the running app - this is a standalone debugging tool only.
"""
import base64
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(SCRIPT_DIR, "audio_base64.txt")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "hello.wav")

with open(INPUT_PATH) as f:
    b64_string = f.read().strip()

with open(OUTPUT_PATH, "wb") as f:
    f.write(base64.b64decode(b64_string))

print(f"Wrote {OUTPUT_PATH} - open it in any media player.")
