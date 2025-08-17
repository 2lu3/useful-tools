#!/usr/bin/env python3

from natsort import natsorted
from pathlib import Path
from loguru import logger
import hashlib
import csv
import shutil


def glob_images() -> list[Path]:
    # tmp/image/xxx.jpeg をすべて取得し以下の形式で返す
    # 画像の並び順はnatsortedでソートすること
    # ["tmp/image/001.jpeg", "tmp/image/002.jpeg", ...]
    tmp_dir = Path("tmp/image")
    image_files = list(tmp_dir.glob("*.jpeg"))
    return natsorted(image_files, key=lambda x: x.stem)


def calculate_file_hash(file_path: Path) -> str:
    """ファイルのハッシュ値を計算する"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def main():
    images = glob_images()
    
    # ハッシュ化結果を保存するリスト
    hash_results = []
    
    # ハッシュ化された画像を保存するディレクトリを作成
    hashed_dir = Path("output/image")
    hashed_dir.mkdir(parents=True, exist_ok=True)

    for image in images:
        # ファイル名から番号部分を抽出（xxx.jpegのxxx部分）
        number_part = image.stem
        page_number = int(number_part)
        
        # ファイルのハッシュ値を計算
        file_hash = calculate_file_hash(image)
        
        # ハッシュ化されたファイル名を作成
        hashed_filename = f"{file_hash}.jpeg"
        hashed_path = hashed_dir / hashed_filename
        
        # ファイルをコピー
        shutil.copy2(image, hashed_path)
        
        # 結果をリストに追加
        hash_results.append({
            'page': page_number,
            'hash': file_hash
        })
        
        logger.info(f"Page {page_number}: {file_hash}")

    # CSVファイルに保存
    csv_path = Path("tmp/hashed_images.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['page', 'hash']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in hash_results:
            writer.writerow(result)
    
    logger.info(f"Hash results saved to {csv_path}")
    logger.info(f"Hashed images saved to {hashed_dir}")


if __name__ == "__main__":
    main()
