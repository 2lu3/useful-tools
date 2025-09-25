#!/usr/bin/env python3
"""
画像ファイルをハッシュ値に変換してコピーするスクリプト
共通規格に従って実装
"""

import os
import json
import hashlib
import shutil
from pathlib import Path
import logging
import sys

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 画像・動画の拡張子
IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', 
    '.svg', '.ico', '.heic', '.heif', '.raw', '.cr2', '.nef', '.arw',
    '.dng', '.orf', '.rw2', '.pef', '.srw', '.x3f'
}

VIDEO_EXTENSIONS = {
    '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v',
    '.3gp', '.ogv', '.mts', '.m2ts', '.ts'
}

def get_all_extensions(directory):
    """ディレクトリ内のすべてのファイルの拡張子を取得"""
    extensions = set()
    for root, dirs, files in os.walk(directory):
        for file in files:
            ext = Path(file).suffix.lower()
            if ext:
                extensions.add(ext)
    return extensions

def is_media_file(file_path):
    """ファイルが画像または動画かどうかを判定"""
    ext = Path(file_path).suffix.lower()
    return ext in IMAGE_EXTENSIONS or ext in VIDEO_EXTENSIONS

def calculate_file_hash(file_path):
    """ファイルのMD5ハッシュを計算"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"ハッシュ計算エラー {file_path}: {e}")
        return None

def main():
    input_dir = Path("/workspace/photos-metadata-restore/input")
    output_dir = Path("/workspace/photos-metadata-restore/output")
    images_dir = output_dir / "images"
    tmp_dir = Path("/workspace/photos-metadata-restore/tmp")
    
    # 入力ディレクトリの存在確認
    if not input_dir.exists():
        logger.error(f"入力ディレクトリが存在しません: {input_dir}")
        return
    
    # 出力ディレクトリの準備
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # tmpディレクトリのリセット
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    
    # すべての拡張子を取得
    all_extensions = get_all_extensions(input_dir)
    logger.info(f"発見された拡張子: {sorted(all_extensions)}")
    
    # 画像・動画以外の拡張子を表示
    media_extensions = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
    non_media_extensions = all_extensions - media_extensions
    if non_media_extensions:
        logger.info(f"画像・動画以外の拡張子: {sorted(non_media_extensions)}")
    
    # メディアファイルを収集
    media_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            file_path = Path(root) / file
            if is_media_file(file_path):
                media_files.append(file_path)
    
    logger.info(f"処理対象のメディアファイル数: {len(media_files)}")
    
    # ファイルをコピー
    pair_data = []
    success_count = 0
    error_count = 0
    
    for i, file_path in enumerate(media_files):
        try:
            print(f"処理中: {i+1}/{len(media_files)} - {file_path.name}")
            
            # ハッシュ計算
            file_hash = calculate_file_hash(file_path)
            if not file_hash:
                error_count += 1
                continue
            
            # 新しいファイル名
            ext = file_path.suffix.lower()
            new_filename = f"{file_hash}{ext}"
            dest_path = images_dir / new_filename
            
            # ファイルコピー
            shutil.copy2(file_path, dest_path)
            
            # pair.json用のデータ（共通規格に従う）
            pair_data.append({
                "source": str(file_path),
                "destination": str(dest_path),
                "filename": new_filename,
                "hash": file_hash
            })
            
            success_count += 1
            
        except Exception as e:
            logger.error(f"ファイルコピーエラー {file_path}: {e}")
            error_count += 1
    
    # pair.jsonを保存（共通規格に従う）
    pair_file = output_dir / "pair.json"
    with open(pair_file, 'w', encoding='utf-8') as f:
        json.dump(pair_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"処理完了: 成功 {success_count}件, エラー {error_count}件")
    logger.info(f"pair.jsonを保存しました: {pair_file}")

if __name__ == "__main__":
    main()