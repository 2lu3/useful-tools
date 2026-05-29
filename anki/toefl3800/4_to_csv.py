#!/usr/bin/env python3
import csv
import sys
from pathlib import Path

import pandas as pd
from loguru import logger

from config import ANKI_CSV, DATA_DIR, ORIGIN_CSV, SOUND_PREFIX

DESCRIPTION_DIR = DATA_DIR / "description"
SOUND_DIR = DATA_DIR / "sound"
def description_path(word: str) -> Path:
    return DESCRIPTION_DIR / f"{word}.txt"


def sound_path(word: str) -> Path:
    return SOUND_DIR / f"{SOUND_PREFIX}_{word}.mp3"


def read_description(word: str) -> str:
    path = description_path(word)
    description = path.read_text(encoding="utf-8-sig").strip()
    if not description:
        raise ValueError(f"description is empty: {path}")
    return description


def build_back(meaning: str, description: str) -> str:
    return f"{meaning.strip()}\n{description}"


def build_sound(word: str) -> str:
    return f"[sound:{SOUND_PREFIX}_{word}.mp3]"


def assert_no_na(df: pd.DataFrame) -> None:
    for col in ("単語", "意味"):
        na_mask = df[col].isna()
        assert not na_mask.any(), (
            f"column {col} contains NA at rows: {df.index[na_mask].tolist()}"
        )


def validate_assets(word: str) -> list[str]:
    errors: list[str] = []

    desc = description_path(word)
    if not desc.exists():
        errors.append(f"missing description: {desc}")
    elif not desc.read_text(encoding="utf-8-sig").strip():
        errors.append(f"empty description: {desc}")

    snd = sound_path(word)
    if not snd.exists():
        errors.append(f"missing sound: {snd}")
    elif snd.stat().st_size == 0:
        errors.append(f"empty sound: {snd}")

    return errors


def load_rows() -> list[tuple[str, str, str]]:
    df = pd.read_csv(
        ORIGIN_CSV, encoding="utf-8-sig", index_col=0, keep_default_na=False
    )
    assert_no_na(df)

    rows: list[tuple[str, str, str]] = []
    errors: list[str] = []

    for line_no, (_, record) in enumerate(df.iterrows(), start=2):
        word_raw = record["単語"]
        meaning_raw = record["意味"]
        assert not pd.isna(word_raw), f"line {line_no}: 単語 is NA"
        assert not pd.isna(meaning_raw), f"line {line_no}: 意味 is NA"

        word = str(word_raw).strip()
        meaning = str(meaning_raw).strip()

        assert word, f"line {line_no}: column 単語 is empty"
        assert meaning, f"line {line_no}: column 意味 is empty"

        row_errors = validate_assets(word)
        if row_errors:
            errors.extend(
                f"line {line_no} ({word}): {message}" for message in row_errors
            )
            continue

        back = build_back(meaning, read_description(word))
        rows.append((word, back, build_sound(word)))

    if errors:
        for message in errors:
            logger.error(message)
        raise RuntimeError(f"found {len(errors)} asset errors")

    return rows


def write_anki_csv(rows: list[tuple[str, str, str]]) -> None:
    ANKI_CSV.parent.mkdir(parents=True, exist_ok=True)
    with ANKI_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def main() -> int:
    if not ORIGIN_CSV.exists():
        logger.error("CSV not found: {}", ORIGIN_CSV)
        return 1

    try:
        rows = load_rows()
    except AssertionError as e:
        logger.error("{}", e)
        return 1
    except RuntimeError:
        return 1

    write_anki_csv(rows)
    logger.info("Wrote {} rows to {}", len(rows), ANKI_CSV)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
