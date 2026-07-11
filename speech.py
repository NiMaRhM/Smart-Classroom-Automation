import os
from pathlib import Path

import librosa
import noisereduce as nr
import soundfile as sf

import whisper

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


RECORDINGS_DIR = Path("recordings")
CLEAN_DIR = RECORDINGS_DIR / "clean"
SUMMARY_OUT_DIR = RECORDINGS_DIR / "texts" / "summery"
SPEECH_OUT_DIR = RECORDINGS_DIR / "texts" / "speech"

CLEAN_DIR.mkdir(parents=True, exist_ok=True)
SUMMARY_OUT_DIR.mkdir(parents=True, exist_ok=True)
SPEECH_OUT_DIR.mkdir(parents=True, exist_ok=True)


wav_files = list(RECORDINGS_DIR.glob("*.wav"))
if not wav_files:
    print("[EXIT] No wav files found in recordings/")
    raise SystemExit(0)

all_already_clean = True
for wav_path in wav_files:
    base = wav_path.stem
    clean_path = SPEECH_OUT_DIR / f"{base}_clean.txt"
    if not clean_path.exists():
        all_already_clean = False
        break

if all_already_clean:
    print("[EXIT] All wav files already have _clean versions. Nothing to do.")
    raise SystemExit(0)


model = whisper.load_model("large-v3")

initial_prompt = """
متن گفتگوی کلاسی به زبان فارسی محاوره‌ای است.
"""


OPENAI_API_KEY = "CHANGE ME"
AVALAI_BASE_URL = "https://api.cerebras.ai/v1"
MODEL_NAME = "llama-3.3-70b"


for wav_path in sorted(RECORDINGS_DIR.glob("*.wav")):
    base = wav_path.stem
    clean_wav_name = f"{base}_clean.wav"
    clean_path = CLEAN_DIR / clean_wav_name

    if clean_path.exists():
        print(f"[SKIP] Clean exists: {clean_path.name}")
        continue

    input_path = str(wav_path)

    y, sr = librosa.load(input_path, sr=None)

    noise_clip = y[:int(0.5 * sr)]
    y_clean = nr.reduce_noise(y=y, sr=sr, y_noise=noise_clip, prop_decrease=0.9)

    sf.write(str(clean_path), y_clean, sr)

    result = model.transcribe(
        str(clean_path),
        language="fa",
        initial_prompt=initial_prompt,
        beam_size=5,
        temperature=0.0,
    )

    asr_text = result["text"].strip()

    RAW_FILE = f"{base}_asr_raw.txt"
    with open(RAW_FILE, "w", encoding="utf-8") as f:
        f.write(asr_text)

    with open(RAW_FILE, "r", encoding="utf-8") as f:
        raw_text = f.read().strip()

    if len(raw_text) < 20:
        raise ValueError("asr_raw.txt is empty/too short. Your ASR step didn't produce usable text.")

    llm = ChatOpenAI(
        model=MODEL_NAME,
        base_url=AVALAI_BASE_URL,
        api_key=OPENAI_API_KEY,
        temperature=0.0,
    )

    system_msg = SystemMessage(content=
        "You are a Persian ASR post-editor. "
        "Your job is to correct recognition errors while preserving meaning. "
        "Do NOT add new information."
    )

    user_prompt = f"""
You will receive Persian text produced by an automatic speech recognition (ASR) system.
It contains typical ASR errors: nonsense words, wrong word boundaries, missing/extra words, and bad punctuation.

TASK:
Rewrite it into fluent, readable Persian, staying максимально faithful to the spoken content.

HARD RULES (must follow):
1) Do NOT add any new facts. Do NOT invent details.
2) Keep the same meaning. Keep the same order of actions as much as possible.
3) Keep colloquial tone, but make it readable.
4) Preserve all time expressions and numbers .
5) Fix punctuation and spacing (use Persian comma "،" and "؟" where appropriate).
6) If you see a nonsense word, replace it with the most likely intended Persian word.
7) Return ONLY the corrected Persian text. No explanations.

ASR TEXT:
<<<
{raw_text}
>>>

CORRECTED PERSIAN TEXT (only the final text):
"""

    resp = llm.invoke([system_msg, HumanMessage(content=user_prompt)])
    clean_text = resp.content.strip()

    transcript_out_path = SPEECH_OUT_DIR / f"{base}_clean.txt"
    with open(transcript_out_path, "w", encoding="utf-8") as f:
        f.write(clean_text)

    llm = ChatOpenAI(
        model=MODEL_NAME,
        base_url=AVALAI_BASE_URL,
        api_key=OPENAI_API_KEY,
        temperature=0.2,
    )

    system_msg = SystemMessage(content=
        "You summarize Persian transcripts. Be faithful to the source and do not invent details."
    )

    user_prompt = f"""
Summarize the following Persian transcript.

Requirements:
- Output language: Persian.
- Be faithful to the transcript; do NOT add new information.
- Keep it concise.
- Use this exact structure:

عنوان:
خلاصه ۳ خطی:
نکات کلیدی (Bullet):
اقدامات/کارهای لازم (اگر وجود دارد) (Bullet):
زمان/جزئیات مهم (Bullet):

Transcript:
<<<
{clean_text}
>>>
"""

    resp = llm.invoke([system_msg, HumanMessage(content=user_prompt)])
    summary_text = resp.content.strip()

    summary_out_path = SUMMARY_OUT_DIR / f"{base}_clean.txt"
    with open(summary_out_path, "w", encoding="utf-8") as f:
        f.write(summary_text)

try:
    if os.path.exists(RAW_FILE):
        os.remove(RAW_FILE)
except Exception:
    pass
