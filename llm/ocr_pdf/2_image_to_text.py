#!/usr/bin/env python3
"""
画像ファイルをテキスト化するスクリプト
output/image/内の画像ファイルをOpenAIのVision APIでテキスト化し、
output/text/に保存する
"""

import glob
import os
import base64
from pathlib import Path
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

import toml
from openai import OpenAI
from alive_progress import alive_bar


def load_config() -> dict:
    """config.tomlから設定を読み込む"""
    config_path = Path("config.toml")
    assert config_path.exists(), "config.tomlが見つかりません"
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = toml.load(f)
    
    assert "llm" in config, "config.tomlに[llm]セクションがありません"
    assert "model" in config["llm"], "config.tomlにmodel設定がありません"
    
    return config


def get_image_files() -> List[Path]:
    """output/image/内の画像ファイルを取得"""
    image_dir = Path("output/image")
    assert image_dir.exists(), "output/image/ディレクトリが存在しません"
    
    # 対応する画像拡張子を検索
    image_extensions = ["*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp", "*.webp"]
    image_files = []
    
    for ext in image_extensions:
        pattern = str(image_dir / ext)
        image_files.extend(glob.glob(pattern))
    
    return [Path(f) for f in image_files]


def encode_image(image_path: Path) -> str:
    """画像ファイルをbase64エンコード"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def image_to_text(client: OpenAI, model: str, image_path: Path) -> str:
    """画像をテキスト化"""
    base64_image = encode_image(image_path)
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "医学の勉強に使いたいので、与えた画像のテキストの全文を可能な限り忠実にテキスト化して、抽出したテキストのみを出力してください。スペースや改行は、自然になるように改変してください。ただし、それ以外は改変は認めません。また、プライバシー等の理由で出力できない場合は、その部分のみ出力しない等の対策をしてください。"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
    )
    
    return response.choices[0].message.content


def save_text(text: str, output_path: Path) -> None:
    """テキストをファイルに保存"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)


def process_single_image(image_path: Path, model: str) -> tuple[Path, str]:
    """単一の画像を処理してテキスト化"""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # テキスト化
    text = image_to_text(client, model, image_path)
    
    # 出力ファイルパス生成
    output_path = Path("output/text") / f"{image_path.stem}.txt"
    
    # 保存
    save_text(text, output_path)
    
    return image_path, output_path


def main():
    """メイン処理"""
    # 設定読み込み
    config = load_config()
    model = config["llm"]["model"]
    
    # 画像ファイル取得
    image_files = get_image_files()
    assert len(image_files) > 0, "処理する画像ファイルが見つかりません"
    
    print(f"見つかった画像ファイル: {len(image_files)}個")
    
    # 並列処理で画像をテキスト化
    with alive_bar(len(image_files), title="画像をテキスト化中") as bar:
        with ThreadPoolExecutor(max_workers=4) as executor:
            # 各画像の処理を並列実行
            future_to_image = {
                executor.submit(process_single_image, image_path, model): image_path 
                for image_path in image_files
            }
            
            # 完了したタスクを順次処理
            for future in as_completed(future_to_image):
                image_path = future_to_image[future]
                try:
                    processed_path, output_path = future.result()
                    print(f"完了: {processed_path.name} -> {output_path}")
                except Exception as e:
                    print(f"エラー: {image_path.name} - {e}")
                finally:
                    bar()
    
    print("すべての画像のテキスト化が完了しました")


if __name__ == "__main__":
    main()
