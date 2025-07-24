#!/usr/bin/env python3

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
    # remove all files and directories in the input directory except .gitignore and .gitkeep
    pass

def clean_output_dir():
    # remove all files and directories in the output directory except .gitignore and .gitkeep
    pass

def load_prompt() -> str:
    # load the prompt from the PROMPT_PATH
    return ""

def list_disease_images() -> list[Path]:
    # list all images which describe diseases from the input directory
    return []

def ask_openai(prompt: str, image_path: Path) -> str:
    # ask OpenAI with the given prompt and image by openai library
    return ""

def split_front_and_back(text: str) -> Card:
    # split the text into front and back parts by "説明"
    # OO
    # 説明
    # XX
    
    return Card("", "")


def image2card(prompt: str, image_path: Path) -> Card:
    res = ask_openai(prompt, image_path)
    card = split_front_and_back(res)
    return card



def save_result(cards: list[Card]):
    # save the result to the OUTPUT_PATH as a csv file
    pass


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
