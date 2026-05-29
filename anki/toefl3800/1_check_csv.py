#!/usr/bin/env python3
import csv
import sys
from collections import Counter

from config import ORIGIN_CSV as INPUT_CSV


def main() -> int:
    if not INPUT_CSV.exists():
        print(f"error: CSV not found: {INPUT_CSV}", file=sys.stderr)
        return 1

    missing_values: list[tuple[int, str]] = []
    words: list[str] = []

    with INPUT_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            print("error: CSV is empty", file=sys.stderr)
            return 1

        if len(header) < 3:
            print(
                f"error: expected at least 3 columns, got {len(header)}",
                file=sys.stderr,
            )
            return 1

        for line_no, row in enumerate(reader, start=2):
            if len(row) < 3:
                missing_values.append((line_no, "columns 2 and 3 are missing"))
                continue

            word = row[1].strip()
            meaning = row[2].strip()

            if not word:
                missing_values.append((line_no, "column 2 (word) is empty"))
            if not meaning:
                missing_values.append((line_no, "column 3 (meaning) is empty"))

            if word:
                words.append(word)

    if missing_values:
        print("error: missing values found:", file=sys.stderr)
        for line_no, message in missing_values:
            print(f"  line {line_no}: {message}", file=sys.stderr)
        return 1

    duplicates = sorted(
        word for word, count in Counter(words).items() if count > 1
    )
    if duplicates:
        print("error: duplicate words in column 2:", file=sys.stderr)
        for word in duplicates:
            print(f"  {word}", file=sys.stderr)
        return 1

    print(f"ok: {len(words)} rows checked, no issues found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
