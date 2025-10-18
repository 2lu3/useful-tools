#!/usr/bin/env python3
import glob
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)  # 並列処理用のインポート
from pathlib import Path

from loguru import logger  # ロギングライブラリ
import pandas as pd
from util.openai_wrapper import send_to_openai
from util.config import load_config
from typing import Literal
from dataclasses import dataclass, field
from alive_progress import alive_bar


@dataclass
class File:
    path: Path
    type: Literal["image", "text", "csv"]

@dataclass
class Problem:
    file: File
    text: str
    # CSVの場合の識別子
    cell_id: str = ""




def search_files_by_type(input_dir: Path) -> list[File]:
    config = load_config()
    """inputディレクトリからファイルタイプ別にファイルを検索する"""
    results = []
    extensions = {
        "image": config["file_extensions"]["image"],
        "text": config["file_extensions"]["text"],
        "csv": config["file_extensions"]["csv"],
    }

    for file_type, exts in extensions.items():
        for ext in exts:
            globbed_files = glob.glob(str(input_dir / ext))
            files = [File(path=Path(path), type=file_type) for path in globbed_files]
            results.extend(files)

    logger.info(f"見つかったファイル数: {len(results)}")
    return results

def file2problem(files: list[File]) -> list[Problem]:
    results: list[Problem] = []
    
    for file in files:
        if file.type == "image":
            results.append(Problem(file=file, text=""))
        elif file.type == "text":
            with open(file.path, "r", encoding="utf-8") as f:
                text = f.read()
            results.append(Problem(file=file, text=text))

        elif file.type == "csv":
            df = pd.read_csv(file.path, encoding="utf-8-sig", dtype=str, na_filter=False, header=None)
            for row_idx, row in df.iterrows():
                for col_idx, cell in enumerate(row):
                    if pd.notna(cell) and str(cell).strip():
                        question_text = str(cell).strip().replace("\n", " ").replace("\r", "")
                        cell_id = f"_{row_idx}_{col_idx}"
                        results.append(Problem(file=file, text=question_text, cell_id=cell_id))

    return results


def parallel_openai_request(problems: list[Problem]) -> list[Problem]:
    def worker(prompt: str, problem: Problem):
        if problem.file.type == "image":
            return send_to_openai(prompt=prompt, image_paths=[problem.file.path]), problem
        else:
            return send_to_openai(prompt=prompt, text_content=problem.text), problem
    results: list[Problem] = [None] * len(problems)  # 元の順序を保持するためのリスト
    config = load_config()
    prompt = config["prompt"]["content"]
    with alive_bar(len(problems)) as bar:
        with ThreadPoolExecutor(max_workers=config["general"]["max_workers"]) as executor:
            # 各問題にインデックスを付けて並列処理
            futures = {executor.submit(worker, prompt, problem): i for i, problem in enumerate(problems)}
            for future in as_completed(futures):
                result, problem = future.result()
                index = futures[future]
                results[index] = Problem(file=problem.file, text=result, cell_id=problem.cell_id)
                bar()
    return results


def save_result_to_file(problem: Problem):
    """ファイルごとにtextディレクトリに同名の.txtファイルで保存"""
    file_name = problem.file.path.stem + problem.cell_id
    output_dir = Path(__file__).parent / "text"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"{file_name}.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(problem.text)
    logger.info(f"結果を {output_file} に保存しました。")


def main():
    # 設定ファイルを読み込み
    config = load_config()

    files = search_files_by_type(Path(__file__).parent / "input")

    problems = file2problem(files)

    results = parallel_openai_request(problems)

    for problem in results:
        save_result_to_file(problem)

    logger.info(f"\n処理完了: {len(problems)}個の問題を処理しました。")


if __name__ == "__main__":
    main()
