#!/usr/bin/env python3

import os
import shutil
import csv
import openai
from PIL import Image
from pydantic import BaseModel
from pathlib import Path
from dataclasses import dataclass
from loguru import logger
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)
from alive_progress import alive_bar


class Config(BaseModel):
    INPUT_DIR: Path = Path("input")
    OUTPUT_PATH: Path = Path("output") / "cards.csv"
    PROMPT_PATH: Path = Path("prompt.txt")
    OPENAI_API_KEY: str

    
@dataclass
class Card:
    front: str
    back: str


def clean_input_dir():
    input_dir = Path("input")
    for item in input_dir.iterdir():
        if item.name not in [".gitignore", ".gitkeep"]:
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)


def clean_output_dir():
    output_dir = Path("output")
    for item in output_dir.iterdir():
        if item.name not in [".gitignore", ".gitkeep"]:
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)


def load_prompt() -> str:
    prompt_path = Path("prompt.txt")
    with prompt_path.open("r", encoding="utf-8") as f:
        return f.read()


def list_disease_images() -> list[Path]:
    input_dir = Path("input")
    # 画像拡張子のみ対象
    exts = [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"]
    return [p for p in input_dir.iterdir() if p.suffix.lower() in exts and p.is_file()]


def ask_openai(prompt: str, image_path: Path) -> str:
    # OpenAI Vision API (GPT-4o) を利用
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    with image_path.open("rb") as img_file:
        image_bytes = img_file.read()
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": [
                    # {"type": "text", "text": "この画像について指示に従って説明してください。"},
                    {"type": "image_url", "image_url": {"url": f"data:image/{image_path.suffix[1:]};base64," + image_bytes.hex()}},
                ],
            },
        ],
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()


def split_front_and_back(text: str) -> Card:
    # "説明" で分割し、前後をfront/backに
    if "説明" in text:
        parts = text.split("説明", 1)
        front = parts[0].strip()
        back = "説明" + parts[1].strip()
    else:
        raise RuntimeError("説明が見つかりませんでした")
    return Card(front, back)


def image2card(prompt: str, image_path: Path) -> Card:
    res = ask_openai(prompt, image_path)
    card = split_front_and_back(res)
    return card



def save_result(cards: list[Card]):
    output_path = Path("output") / "cards.csv"
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["front", "back"])
        for card in cards:
            writer.writerow([card.front, card.back])


def main():
    logger.info("Starting describe-disease process...")
    clean_input_dir()
    clean_output_dir()

    prompt = load_prompt()
    images = list_disease_images()
    logger.info(f"Found {len(images)} disease images.")

    cards = []
    max_workers = min(100, len(images))  # ワーカー数を制限
    with alive_bar(len(images)) as bar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(image2card, prompt,img) for img in images]
            for future in as_completed(futures):
                card = future.result()
                cards.append(card)
                bar()

    save_result(cards)
    logger.info(f"saved {len(cards)}")



if __name__ == "__main__":
    main()
