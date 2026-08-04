#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NoReturn

from openai import OpenAI

DEFAULT_MODEL = "gpt-transcribe"
DEFAULT_LANGUAGE = "ja"
OPENAI_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
SAFE_CHUNK_BYTES = 20 * 1024 * 1024
CHUNK_BITRATE_KBPS = 128
CHUNK_SAMPLE_RATE_HZ = 16000
REQUEST_TIMEOUT_SEC = 300.0
FFMPEG_TIMEOUT_SEC = 600.0
FFPROBE_TIMEOUT_SEC = 30.0

KNOWN_MODELS = (
    "gpt-transcribe",
    "gpt-4o-mini-transcribe",
    "gpt-4o-transcribe",
    "whisper-1",
)


def model_help_text() -> str:
    known = ", ".join(KNOWN_MODELS)
    return f"OpenAI STT model (default: {DEFAULT_MODEL}). Known models: {known}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe an audio file to text with OpenAI Speech-to-Text."
    )
    parser.add_argument(
        "-i", "--input", required=True, type=Path, help="Input audio file"
    )
    parser.add_argument(
        "-o", "--output", required=True, type=Path, help="Output text file"
    )
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, help=model_help_text())
    return parser.parse_args()


def require_api_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return api_key


def raise_command_error(command: list[str], error: Exception) -> NoReturn:
    if isinstance(error, FileNotFoundError):
        raise RuntimeError(f"Required command not found: {command[0]}") from error
    if isinstance(error, subprocess.TimeoutExpired):
        raise RuntimeError(
            f"Command timed out after {error.timeout}s: {' '.join(command)}"
        ) from error
    if isinstance(error, subprocess.CalledProcessError):
        detail = (error.stderr or error.stdout or "").strip()
        raise RuntimeError(
            f"Command failed ({error.returncode}): {' '.join(command)}\n{detail}"
        ) from error
    raise RuntimeError(f"Command failed: {' '.join(command)}") from error


def run_command(command: list[str], timeout_sec: float) -> str:
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except (
        FileNotFoundError,
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
    ) as error:
        raise_command_error(command, error)
    return completed.stdout.strip()


def ffprobe_duration_command(audio_path: Path) -> list[str]:
    return [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]


def parse_duration_sec(output: str, audio_path: Path) -> float:
    try:
        duration_sec = float(output)
    except ValueError as error:
        raise RuntimeError(
            f"Could not parse duration from ffprobe for {audio_path}: {output!r}"
        ) from error
    if duration_sec <= 0:
        raise RuntimeError(f"Invalid audio duration for {audio_path}: {duration_sec}")
    return duration_sec


def get_audio_duration_sec(audio_path: Path) -> float:
    output = run_command(ffprobe_duration_command(audio_path), FFPROBE_TIMEOUT_SEC)
    return parse_duration_sec(output, audio_path)


def max_chunk_duration_sec() -> float:
    bitrate_bps = CHUNK_BITRATE_KBPS * 1000
    return (SAFE_CHUNK_BYTES * 8) / bitrate_bps


def chunk_encode_args() -> list[str]:
    return [
        "-ac",
        "1",
        "-ar",
        str(CHUNK_SAMPLE_RATE_HZ),
        "-b:a",
        f"{CHUNK_BITRATE_KBPS}k",
    ]


def build_chunk_command(
    audio_path: Path,
    output_path: Path,
    start_sec: float,
    duration_sec: float,
) -> list[str]:
    # Input seek (-ss before -i) is fast enough for STT chunk boundaries.
    return [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start_sec:.3f}",
        "-i",
        str(audio_path),
        "-t",
        f"{duration_sec:.3f}",
        *chunk_encode_args(),
        str(output_path),
    ]


def write_audio_chunk(
    audio_path: Path,
    chunk_dir: Path,
    index: int,
    start_sec: float,
    duration_sec: float,
) -> Path:
    output_path = chunk_dir / f"chunk_{index:03d}.mp3"
    run_command(
        build_chunk_command(audio_path, output_path, start_sec, duration_sec),
        FFMPEG_TIMEOUT_SEC,
    )
    return output_path


def split_audio_into_chunks(audio_path: Path, chunk_dir: Path) -> list[Path]:
    duration_sec = get_audio_duration_sec(audio_path)
    chunk_count = max(1, math.ceil(duration_sec / max_chunk_duration_sec()))
    segment_sec = duration_sec / chunk_count
    chunks: list[Path] = []
    for index in range(chunk_count):
        start_sec = index * segment_sec
        remaining_sec = duration_sec - start_sec
        if remaining_sec <= 0:
            break
        chunks.append(
            write_audio_chunk(
                audio_path,
                chunk_dir,
                index,
                start_sec,
                min(segment_sec, remaining_sec),
            )
        )
    if not chunks:
        raise RuntimeError(f"No chunks were created from {audio_path}")
    return chunks


def prepare_audio_parts(audio_path: Path, work_dir: Path) -> list[Path]:
    file_size_bytes = audio_path.stat().st_size
    if file_size_bytes <= OPENAI_MAX_UPLOAD_BYTES:
        return [audio_path]
    print(
        f"Input is {file_size_bytes} bytes (> {OPENAI_MAX_UPLOAD_BYTES}); "
        "splitting into chunks...",
        file=sys.stderr,
    )
    return split_audio_into_chunks(audio_path, work_dir)


def extract_transcript_text(response: object, audio_path: Path) -> str:
    text = getattr(response, "text", None)
    if not isinstance(text, str):
        raise RuntimeError(f"Unexpected transcription response for {audio_path}")
    return text.strip()


def transcribe_file(client: OpenAI, audio_path: Path, model: str) -> str:
    with audio_path.open("rb") as audio_file:
        try:
            response = client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                language=DEFAULT_LANGUAGE,
            )
        except Exception as error:
            raise RuntimeError(
                f"OpenAI transcription failed for {audio_path}: {error}"
            ) from error
    return extract_transcript_text(response, audio_path)


def transcribe_parts(client: OpenAI, parts: list[Path], model: str) -> str:
    texts: list[str] = []
    for index, part in enumerate(parts, start=1):
        print(f"Transcribing part {index}/{len(parts)}: {part.name}", file=sys.stderr)
        part_text = transcribe_file(client, part, model)
        if part_text:
            texts.append(part_text)
    return "\n".join(texts)


def write_output(output_path: Path, text: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text + ("\n" if text else ""), encoding="utf-8")


def run_transcription(input_path: Path, output_path: Path, model: str) -> None:
    api_key = require_api_key()
    client = OpenAI(api_key=api_key, timeout=REQUEST_TIMEOUT_SEC)
    with tempfile.TemporaryDirectory(prefix="audio-to-text-") as temp_dir:
        parts = prepare_audio_parts(input_path, Path(temp_dir))
        text = transcribe_parts(client, parts, model)
    write_output(output_path, text)


def main() -> int:
    args = parse_args()
    input_path: Path = args.input
    if not input_path.is_file():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 1
    try:
        run_transcription(input_path, args.output, args.model)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(f"Wrote transcript to {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
