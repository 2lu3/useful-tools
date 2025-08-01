#!/usr/bin/env python3

from natsort import natsorted
from pathlib import Path
from loguru import logger
from util import ask_openai
import shutil


def glob_images() -> list[Path]:
    # tmp/image-xxx.jpeg をすべて取得し以下の形式で返す
    # 画像の並び順はnatsortedでソートすること
    # ["image-000.jpeg", image-001.jpg", ...]
    tmp_dir = Path("tmp")
    image_files = list(tmp_dir.glob("image-*.jpeg"))
    return natsorted(image_files, key=lambda x: x.name)


def is_explaination_part(path: Path) -> bool:
    # 画像は解説パートと問題パートが存在する
    # OpenAI APIを利用して解説パートなのか問題パートなのかを判定する

    prompt = """与えられた画像は医学テキストの一部です。説明パートか問題パート、それ以外かを判定し、説明パートなら\"yes\"、問題パートなら\"no\"、それ以外なら\"other\"と答えてください。\n\n

説明パートには以下のような要素が含まれています。
- 名称
- 病態
- 症状
- 検査
- 診断
- 治療

問題パートには以下のような要素が含まれています。
- 問題番号
- 問題文
- 選択肢

それ以外は上2つに分類できないものです。例えば、以下のものがあります。
- 目次
- 表紙

"""

    try:
        response = ask_openai(prompt, [path], 0.1)
        logger.debug(f"Response for {path}: {response}")
        if "yes" in response.lower() or "はい" in response:
            return True
        elif "no" in response.lower() or "いいえ" in response:
            return False
        elif "other" in response.lower() or "その他" in response:
            return False
        logger.warning(f"Unexpected response for {path}: {response}")
        return False  # デフォルトは問題パートとする
    except Exception as e:
        logger.error(f"Error determining if {path} is explanation part: {e}")
        return False



def main():
    images = glob_images()

    explanation_parts = []

    for image in images:
        if not is_explaination_part(image):
            continue

        explanation_parts.append(image)

    logger.debug(f"Found {len(explanation_parts)} explanation parts.")

    for image in explanation_parts:
        suffix = image.suffix
        # ファイル名から番号部分を抽出（image-xxxのxxx部分）
        number_part = image.stem.replace("image-", "")
        new_filename = f"tmp/explaination-{number_part}{suffix}"
        shutil.copy(image, new_filename)



    # save as text
    with open("tmp/explanation.txt", "w") as f:
        for part in explanation_parts:
            f.write(f"{part}\n")


if __name__ == "__main__":
    main()
