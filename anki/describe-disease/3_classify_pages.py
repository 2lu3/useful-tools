#!/usr/bin/env python3

from natsort import natsorted
from pathlib import Path
from loguru import logger
from util import ask_openai, settings
import shutil
import csv


def glob_images() -> list[Path]:
    # tmp/image/xxx.jpeg をすべて取得し以下の形式で返す
    # 画像の並び順はnatsortedでソートすること
    # ["tmp/image/001.jpeg", "tmp/image/002.jpeg", ...]
    tmp_dir = Path("tmp/image")
    image_files = list(tmp_dir.glob("*.jpeg"))
    return natsorted(image_files, key=lambda x: x.stem)


def classify_page(path: Path) -> str:
    # 画像は解説パートと問題パートが存在する
    # OpenAI APIを利用して解説パートなのか問題パートなのかを判定する

    prompt = """与えられた画像は医学テキストの一部です。
以下に列挙する種類のどれに該当するかを判定し、その種類を「目次」「説明」「問題」「その他」のいずれかで答えてください。

- 目次
- 説明
- 問題
- その他

目次は疾患名もしくはトピックと対応するページ数が必ず1対1で記載されています。

説明では疾患もしくはトピックに関する情報を記述しています。以下の要素が含まれています。
- 名称
- 病態
- 症状
- 検査
- 診断
- 治療

問題は疾患もしくはトピックに関連する問題が書かれています。以下のような要素が含まれています。
- 問題番号
- 問題文
- 選択肢

その他では、上3に分類できないものがあります。以下のようなページがあります。
- 表紙
"""
    response = ask_openai(prompt, "", [path], model=settings.classification_model)
    if "目次" in response:  
        return "目次"
    elif "説明" in response:
        return "説明"
    elif "問題" in response:
        return "問題"
    elif "その他" in response:
        return "その他"
    else:
        logger.warning(f"Unexpected response for {path}: {response}")
        return "不明"
        



def main():
    images = glob_images()
    
    # 分類結果を保存するリスト
    classification_results = []

    for image in images:
        # ファイル名から番号部分を抽出（xxx.jpegのxxx部分）
        number_part = image.stem
        page_number = int(number_part)
        
        # ページを分類
        classification = classify_page(image)
        
        # 結果をリストに追加
        classification_results.append({
            'page': page_number,
            'type': classification
        })
        
        logger.info(f"Page {page_number}: {classification}")

    # CSVファイルに保存
    csv_path = Path("tmp/classification.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['page', 'type']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in classification_results:
            writer.writerow(result)
    
    logger.info(f"Classification results saved to {csv_path}")


if __name__ == "__main__":
    main()
