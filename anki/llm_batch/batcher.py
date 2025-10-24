#!/usr/bin/env python3
"""
LLM Batch - inputディレクトリのファイルを並列でLLMに投げ、結果をoutputディレクトリに保存
"""

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple

import openai
from alive_progress import alive_bar


def get_input_files(input_dir: Path) -> List[Path]:
    """inputディレクトリから処理対象のファイルを取得"""
    supported_extensions = {'.txt', '.jpg', '.png'}
    files = []
    
    for file_path in input_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
            files.append(file_path)
    
    assert files, f"inputディレクトリに処理対象のファイルが見つかりません: {input_dir}"
    return files




def process_file_with_llm(file_path: Path, prompt: str) -> str:
    """単一ファイルをLLMで処理"""
    client = openai.OpenAI()
    
    # ファイルタイプに応じて処理
    if file_path.suffix.lower() == '.txt':
        # テキストファイルの場合
        content = file_path.read_text(encoding='utf-8')
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": content}
        ]
    else:
        # 画像ファイルの場合
        with open(file_path, 'rb') as image_file:
            image_data = image_file.read()
        
        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "この画像を分析してください。"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{file_path.suffix[1:]};base64,{image_data.hex()}"
                        }
                    }
                ]
            }
        ]
    
    response = client.chat.completions.create(
        model="o3",
        messages=messages,
        max_tokens=4000
    )
    
    return response.choices[0].message.content


def save_result(file_path: Path, result: str, output_dir: Path) -> None:
    """結果をoutputディレクトリに保存"""
    output_file = output_dir / f"{file_path.stem}.txt"
    output_file.write_text(result, encoding='utf-8')


def process_single_file(args: Tuple[Path, str, Path]) -> Tuple[Path, str]:
    """単一ファイルの処理（並列実行用）"""
    file_path, prompt, output_dir = args
    
    try:
        result = process_file_with_llm(file_path, prompt)
        save_result(file_path, result, output_dir)
        return file_path, "成功"
    except Exception as e:
        return file_path, f"エラー: {str(e)}"


def main():
    parser = argparse.ArgumentParser(description="LLM Batch - ファイルを並列でLLMに投げる")
    parser.add_argument("--prompt", required=True, help="プロンプトファイルのパスまたは文字列")
    
    args = parser.parse_args()
    
    # ディレクトリの準備
    input_dir = Path("./input")
    output_dir = Path("./output")
    
    assert input_dir.exists(), f"入力ディレクトリが存在しません: {input_dir}"
    assert output_dir.exists(), f"出力ディレクトリが存在しません: {output_dir}"
    
    # プロンプトの読み込み
    prompt_path = Path(args.prompt)
    if prompt_path.exists():
        prompt = prompt_path.read_text(encoding='utf-8')
    else:
        prompt = args.prompt
    
    # 処理対象ファイルの取得
    input_files = get_input_files(input_dir)
    print(f"処理対象ファイル数: {len(input_files)}")
    
    # 並列処理の実行
    with ThreadPoolExecutor(max_workers=5) as executor:
        # タスクの準備
        tasks = [
            (file_path, prompt, output_dir)
            for file_path in input_files
        ]
        
        # プログレスバー付きで実行
        with alive_bar(len(tasks), title="ファイル処理中") as bar:
            futures = [executor.submit(process_single_file, task) for task in tasks]
            
            results = []
            for future in as_completed(futures):
                file_path, status = future.result()
                results.append((file_path, status))
                bar()
                print(f"{file_path.name}: {status}")
    
    # 結果のサマリー
    success_count = sum(1 for _, status in results if status == "成功")
    print(f"\n処理完了: {success_count}/{len(results)} ファイルが成功")


if __name__ == "__main__":
    main()
