#!/usr/bin/env python3
"""
テキスト問題と対応画像をLLMに投げ、Anki用CSVを生成する
"""

import base64
import csv
import hashlib
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from alive_progress import alive_bar
from loguru import logger
from openai import OpenAI


class TextAndImageBatcher:
    def __init__(self, openai_api_key: str | None = None):
        self.client = OpenAI(api_key=openai_api_key)
        self.input_dir = Path("input")
        self.output_dir = Path("output")
        self.image_dir = self.output_dir / "image"
        self.prompt_path = Path("prompt/text_and_image.txt")
        self.csv_file = self.output_dir / "anki_cards.csv"
        self.max_workers = 5

        self.output_dir.mkdir(exist_ok=True)
        self.image_dir.mkdir(exist_ok=True)

        assert self.input_dir.exists()
        assert self.prompt_path.exists()
        self.prompt_text = self.prompt_path.read_text(encoding="utf-8").strip()
        self.image_lookup = self.build_image_lookup()

    def load_questions(self) -> List[str]:
        csv_files = list(self.input_dir.glob("*.csv"))
        assert len(csv_files) == 1
        csv_path = csv_files[0]

        questions: List[str] = []
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for row in reader:
                assert len(row) >= 1
                question = row[0].rstrip("\r\n")
                assert question
                questions.append(question)

        logger.info(f"問題数: {len(questions)} ({csv_path.name})")
        return questions

    def build_image_lookup(self) -> Dict[int, Path]:
        image_extensions = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}
        lookup: Dict[int, Path] = {}
        for path in self.input_dir.iterdir():
            if not (path.is_file() and path.suffix in image_extensions):
                continue
            stem = path.stem.lstrip("0") or "0"
            if stem.isdigit():
                lookup[int(stem)] = path
        logger.info(f"画像枚数: {len(lookup)}")
        return lookup

    def encode_image(self, image_path: Path) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def copy_image_with_hash(self, image_path: Path) -> str:
        file_hash = hashlib.md5(image_path.read_bytes()).hexdigest()
        extension = image_path.suffix.lower()
        new_name = f"{file_hash}{extension}"
        shutil.copy2(image_path, self.image_dir / new_name)
        return new_name

    def build_prompt_message(
        self, question_text: str, image_path: Optional[Path]
    ) -> List[dict]:
        prompt_body = f"{self.prompt_text}\n\n問題:\n{question_text}"
        contents = [
            {
                "type": "text",
                "text": prompt_body,
            }
        ]
        if image_path:
            base64_image = self.encode_image(image_path)
            contents.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                    },
                }
            )
        return contents

    def call_model(
        self, question_text: str, image_path: Optional[Path]
    ) -> str:
        message_content = self.build_prompt_message(question_text, image_path)
        response = self.client.chat.completions.create(
            model="gpt-4.1-2025-04-14",
            messages=[
                {
                    "role": "user",
                    "content": message_content,
                }
            ],
            max_tokens=1000,
        )
        answer_text = response.choices[0].message.content.strip()
        return answer_text

    def split_response_sections(self, response_text: str) -> Tuple[str, str]:
        marker = "解答"
        idx = response_text.find(marker)
        if idx == -1:
            return response_text.strip(), ""
        question_part = response_text[:idx].strip()
        answer_part = response_text[idx:].lstrip()
        return question_part, answer_part

    @staticmethod
    def remove_code_fences(text: str) -> str:
        return text.replace("```", "").strip()

    def process_single_entry(
        self, idx: int, question_text: str, image_path: Optional[Path]
    ) -> Tuple[int, str, str]:
        hashed_filename = (
            self.copy_image_with_hash(image_path) if image_path else None
        )
        response_text = self.call_model(question_text, image_path)
        question_piece, answer_text = self.split_response_sections(response_text)
        if not answer_text:
            answer_text = response_text.strip()
        question_piece = self.remove_code_fences(question_piece)
        answer_text = self.remove_code_fences(answer_text)
        base_question = question_piece or question_text
        if hashed_filename:
            question_with_image = (
                f"{base_question}\n<img src=\"{hashed_filename}\">"
            )
        else:
            question_with_image = base_question
        return idx, question_with_image, answer_text

    def create_output(self, cards_data: List[Tuple[str, str]]) -> None:
        with open(self.csv_file, "w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.writer(csvfile)
            for question, answer in cards_data:
                writer.writerow([question, answer])
        logger.info(f"CSV出力: {self.csv_file}")

    def run(self) -> None:
        questions = self.load_questions()

        targets: List[Tuple[str, Optional[Path]]] = []
        for idx, question in enumerate(questions, start=1):
            targets.append((question, self.image_lookup.get(idx)))

        results: list[Tuple[int, str, str]] = []
        with alive_bar(len(targets), title="LLM処理中") as bar:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_idx = {
                    executor.submit(self.process_single_entry, idx, question, image): idx
                    for idx, (question, image) in enumerate(targets)
                }
                for future in as_completed(future_to_idx):
                    results.append(future.result())
                    bar()

        ordered = [pair for _, pair in sorted((idx, (q, a)) for idx, q, a in results)]
        self.create_output(ordered)
        logger.info(f"完了: {len(ordered)}件")


def main():
    api_key = os.getenv("OPENAI_API_KEY")
    assert api_key
    batcher = TextAndImageBatcher(api_key)
    batcher.run()


if __name__ == "__main__":
    main()

