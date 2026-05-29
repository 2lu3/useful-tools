#!/usr/bin/env python3
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from alive_progress import alive_bar
from loguru import logger
from openai import OpenAI
from pyrate_limiter import Duration, Limiter, Rate

from config import DATA_DIR, ORIGIN_CSV

MODEL = "gpt-5-mini-2025-08-07"
N_WORKERS = 10
CALLS_PER_SECOND = 100
USER_PROMPT_TEMPLATE = """次の英単語について、語源・例文1・例文2を作成してください。

単語: {word}"""

SYSTEM_PROMPT = f"""あなたはTOEFL学習者向けの英単語解説を書くアシスタントです。
与えられた英単語と日本語の意味に基づき、語源・例文1・例文2を日本語で解説してください。

ルール:
- 語源は3〜5行の箇条書き（各行は「- 」で始める）
- 例文はTOEFLレベルの自然な英文にする
- 各例文の直後に「訳：」で日本語訳を1行で書く
- 見出しは「語源：」「例文1：」「例文2：」をそのまま使う
- 余計な前置きやMarkdown記法は使わない

出力形式の例:
語源：
- "remark"は、中英語の「remarken」から派生。
- 「re-」（再度）と「mark」（印をつける）から成る。
- つまり、何かに注目し、再び印をつけることを指す。
- 現在の意味は、観察したことや意見を伝えることに繋がる。

例文1：
She made a remarkable remark during the meeting.
訳：彼女は会議中に素晴らしい意見を述べた。

例文2：
His remark about the weather made everyone laugh.
訳：彼の天気についてのコメントは、皆を笑わせた。
"""

client = OpenAI()
limiter = Limiter(Rate(CALLS_PER_SECOND, Duration.SECOND))


def build_user_prompt(word: str) -> str:
    return USER_PROMPT_TEMPLATE.format(word=word)


def generate_description(word: str) -> str:
    limiter.try_acquire("openai-description")
    response = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(word)},
        ],
    )
    text = response.output_text
    if not text or not text.strip():
        raise RuntimeError("OpenAI API returned empty response")
    return text.strip()

def generate_and_save_description(english_word: str) -> None:
    description_path = DATA_DIR / "description" / f"{english_word}.txt"
    if description_path.exists():
        description = description_path.read_text(encoding="utf-8-sig")
        if description.strip():
            logger.warning("Description already exists: {}", description)
            return
    description = generate_description(english_word)
    description_path.write_text(description, encoding="utf-8-sig")

def main() -> None:
    df = pd.read_csv(ORIGIN_CSV, encoding="utf-8-sig", index_col=0)
    description_dir = DATA_DIR / "description"
    description_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Using model: {}", MODEL)

    with alive_bar(len(df)) as bar:
        with ThreadPoolExecutor(max_workers=N_WORKERS) as executor:
            futures = [executor.submit(generate_and_save_description, str(row["単語"]).strip()) for _, row in df.iterrows()]
            for future in as_completed(futures):
                future.result()
                bar()

    logger.info("Done. Descriptions: {}", description_dir)


if __name__ == "__main__":
    main()
