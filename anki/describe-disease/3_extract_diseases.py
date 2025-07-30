#!/usr/bin/env python3

import os
import openai
from typing import Dict, Tuple
from loguru import logger
from pathlib import Path
from glob import glob
from natsort import natsorted
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from alive_progress import alive_bar
from tenacity import (
    retry,  # デコレータ
    stop_after_attempt,  # 最大リトライ回数
    wait_exponential,  # 指数バックオフ
    retry_if_exception,
    before_log,
)
import logging


def is_rate_limit_error(e: BaseException) -> bool:
    # openai-python 1.x
    if isinstance(e, openai.RateLimitError):
        return True
    # 将来バージョンで APIStatusError が来ても 429 だけ拾う
    return (
        isinstance(e, openai.APIStatusError) and getattr(e, "status_code", None) == 429
    )


retry_openai = retry(
    reraise=True,
    retry=retry_if_exception(is_rate_limit_error),  # ← 判定関数
    wait=wait_exponential(multiplier=2, min=30, max=60),
    stop=stop_after_attempt(6),
    before_sleep=before_log(logger, logging.WARNING),
)


def load_all_images() -> list[Path]:
    # tmp/image-xxx.jpeg をすべて取得し以下の形式で返す
    # 画像の並び順はnatsortedでソートすること
    # ["image-000.jpeg", image-001.jpg", ...]
    tmp_dir = Path("tmp")
    image_files = list(tmp_dir.glob("image-*.jpeg"))
    return natsorted(image_files, key=lambda x: x.name)


# tenacity で自動リトライ
@retry_openai
def ask_openai(prompt: str, image_path: Path) -> str:
    # OpenAI Vision API (GPT-4o) を利用
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    with image_path.open("rb") as img_file:
        image_b64 = base64.b64encode(img_file.read()).decode("ascii")
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{image_path.suffix[1:]};base64,{image_b64}"
                        },
                    }
                ],
            },
        ],
        max_tokens=1024,
    )
    assert response.choices[0].message.content, "OpenAI response is empty"
    return response.choices[0].message.content.strip()


def is_explaination_part(path: Path) -> bool:
    # 画像は解説パートと問題パートが存在する
    # OpenAI APIを利用して解説パートなのか問題パートなのかを判定する

    prompt = "画像ページの主な内容を判定してください。主に疾患とその特徴を解説しているならyes、表紙や問題が中心ならnoと答えてください。\n\n"

    try:
        response = ask_openai(prompt, path)
        return response.lower().strip() == "yes"
    except Exception as e:
        logger.error(f"Error determining if {path} is explanation part: {e}")
        return True  # エラーの場合は解説パートとして扱う


def extract_diseases(path: Path) -> list[str]:
    # 画像から疾患名を抽出する
    # OpenAI APIを利用して、画像の内容から疾患名を抽出する
    # 疾患名は日本語で返すこと

    prompt = '画像で主に解説している疾患名を","で区切ってすべて抽出してください。\n\n'

    try:
        response = ask_openai(prompt, path)
        if response.strip():
            # カンマで区切って疾患名のリストを作成
            diseases = [
                disease.strip() for disease in response.split(",") if disease.strip()
            ]
            return diseases
        else:
            return []
    except Exception as e:
        logger.error(f"Error extracting diseases from {path}: {e}")
        return []


def process_single_image(image: Path) -> Tuple[Path, list[str]]:
    """単一画像を処理して疾患名を抽出する"""
    if not is_explaination_part(image):
        return image, []

    diseases = extract_diseases(image)

    if not diseases:
        return image, []

    return image, diseases


def group_images_by_disease(images: list[Path]) -> dict[str, list[Path]]:
    # ThreadPoolExecutorを使用して並列処理
    max_workers = min(3, len(images))  # ワーカー数を制限
    grouped_images: Dict[str, list[Path]] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 各画像の処理を並列実行
        futures = [executor.submit(process_single_image, image) for image in images]

        # alive_progressを使って進捗を表示
        with alive_bar(len(futures), title="画像処理中") as bar:
            # 結果を収集
            for future in as_completed(futures):
                image, diseases = future.result()

                # 疾患名ごとに画像をグループ化
                for disease in diseases:
                    if disease not in grouped_images:
                        grouped_images[disease] = []
                    grouped_images[disease].append(image)

                bar()  # 進捗バーを更新

    return grouped_images


def main():
    logger.info("Extracting diseases from images...")

    images = load_all_images()

    if not images:
        logger.warning("No images found to process.")
        return

    grouped_images = group_images_by_disease(images)

    if not grouped_images:
        logger.warning("No diseases were extracted from the images.")
        return

    for disease, imgs in grouped_images.items():
        print(f"{disease}: {[img.name for img in imgs]}")

    output_dir = Path("tmp/grouped_images.pkl")

    with open(output_dir, "wb") as f:
        import pickle

        pickle.dump(grouped_images, f)


if __name__ == "__main__":
    main()
