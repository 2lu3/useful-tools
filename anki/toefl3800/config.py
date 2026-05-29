from pathlib import Path

ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"
DESCRIPTION_DIR = ROOT_DIR / "description"

SOUND_PREFIX = "toefl3800"

ORIGIN_CSV = DATA_DIR / "origin.csv"
WITH_DESCRIPTION_CSV = DATA_DIR / "with_description.csv"
WITH_SOUND_CSV = DATA_DIR / "with_sound.csv"
ANKI_CSV = DATA_DIR / "anki.csv"
