#!/usr/bin/env python3
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from alive_progress import alive_bar
from loguru import logger
from openai import OpenAI
from pyrate_limiter import Duration, Limiter, Rate

from config import DATA_DIR, ORIGIN_CSV, SOUND_PREFIX

MODEL = "gpt-4o-mini-tts-2025-12-15"
VOICE = "alloy"
RESPONSE_FORMAT = "mp3"
N_WORKERS = 10
CALLS_PER_SECOND = 10

client = OpenAI()
limiter = Limiter(Rate(CALLS_PER_SECOND, Duration.SECOND))


def generate_speech(text: str) -> bytes:
    limiter.try_acquire("openai-tts")
    response = client.audio.speech.create(
        model=MODEL,
        voice=VOICE,
        input=text,
        response_format=RESPONSE_FORMAT,
    )

    if not response.content:
        raise RuntimeError("OpenAI API returned empty audio")

    return response.content


def sound_path(english_word: str) -> Path:
    return DATA_DIR / "sound" / f"{SOUND_PREFIX}_{english_word}.mp3"


def filter_words(words: list[str]) -> list[str]:
    filtered: list[str] = []
    skipped = 0

    for word in words:
        path = sound_path(word)
        if path.exists() and path.stat().st_size > 0:
            skipped += 1
            continue
        filtered.append(word)

    if skipped:
        logger.info("Skipping {} words with existing sound files", skipped)

    return filtered


def generate_and_save_sound(english_word: str) -> None:
    audio_bytes = generate_speech(english_word)
    sound_path(english_word).write_bytes(audio_bytes)


def load_words() -> list[str]:
    df = pd.read_csv(ORIGIN_CSV, encoding="utf-8-sig", index_col=0, keep_default_na=False)
    return df["単語"].astype(str).str.strip().tolist()


def main() -> None:
    sound_dir = DATA_DIR / "sound"
    sound_dir.mkdir(parents=True, exist_ok=True)

    words = load_words()
    words_to_process = filter_words(words)

    if not words_to_process:
        logger.info("All sounds already exist. Nothing to do.")
        return

    logger.info(
        "Using model: {}, voice: {} ({} / {} words)",
        MODEL,
        VOICE,
        len(words_to_process),
        len(words),
    )

    with alive_bar(len(words_to_process)) as bar:
        with ThreadPoolExecutor(max_workers=N_WORKERS) as executor:
            futures = [
                executor.submit(generate_and_save_sound, word)
                for word in words_to_process
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    logger.exception("Failed to generate sound")
                bar()

    logger.info("Done. Sounds: {}", sound_dir)


if __name__ == "__main__":
    main()