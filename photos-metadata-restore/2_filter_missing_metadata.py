#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path
import datetime
from alive_progress import alive_bar
from loguru import logger
from typing import Optional
from utils.exif_utils import get_exif_data, get_exif_datetime, get_gps_data, GPSData, PhotoMetadata
import json
import multiprocessing
from concurrent.futures import ThreadPoolExecutor


def process_single_file(file_path: Path) -> PhotoMetadata:
    exif_data = get_exif_data(str(file_path))
    
    if exif_data is None:
        logger.error(f"EXIFデータが見つかりません: {file_path}")
        logger.error(f"exiftool {file_path}を実行してみてください")
        sys.exit(1)
    
    return PhotoMetadata(
        file_name=file_path.name,
        exif_datetime=get_exif_datetime(exif_data),
        exif_gps=get_gps_data(exif_data)
    )

def load_pair_mapping(base_path):
    pair_file = base_path / "output" / "pair.json"

    assert pair_file.exists()
    
    with open(pair_file, 'r', encoding='utf-8') as f:
        pair_data = json.load(f)
    
    mapping = {}
    for item in pair_data:
        destination = Path(item['destination'])
        source = Path(item['source'])
        mapping[destination] = source
    
    logger.info(f"pair.jsonから{len(mapping)}個の対応関係を読み込みました")
    return mapping


def get_image_files_from_pairs(pair_mapping):
    """pair.jsonから画像ファイルのリストを取得"""
    image_files = list(pair_mapping.keys())
    logger.info(f"pair.jsonから{len(image_files)}個のファイルを取得しました")
    return image_files

def process_all_files(all_photo_files):
    metadata_list = []
    
    logger.info(f"outputディレクトリ内の写真ファイルをスキャン中...")
    
    with alive_bar(len(all_photo_files), title="📸 ファイル分析中", bar='smooth', spinner='dots_waves') as bar:
        for file_path in all_photo_files:
            bar.text = f"🔍 分析中: {file_path.name}"
            
            metadata = process_single_file(file_path)
            metadata_list.append(metadata)
            
            bar()

    return metadata_list


def process_all_files_multi(all_photo_files, max_workers=None):
    """マルチスレッドでファイルを並列処理する"""
    if max_workers is None:
        max_workers = multiprocessing.cpu_count() * 2  # I/OバウンドなのでCPUコア数の2倍
    
    metadata_list = []
    
    logger.info(f"outputディレクトリ内の写真ファイルをスキャン中... (並列処理: {max_workers}スレッド)")
    
    with alive_bar(len(all_photo_files), title="📸 ファイル分析中 (並列)", bar='smooth', spinner='dots_waves') as bar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 並列処理を実行
            futures = [executor.submit(process_single_file, file_path) for file_path in all_photo_files]
            
            for future in futures:
                bar.text = f"🔍 分析中: {future.result().file_name}"
                metadata = future.result()
                metadata_list.append(metadata)
                bar()
    
    return metadata_list


def save_metadata(metadata_list, base_path):
    import pickle
    
    metadata_file = base_path / "output" / "photo_metadata.pkl"
    
    with open(metadata_file, 'wb') as f:
        pickle.dump(metadata_list, f)
    
    logger.info(f"💾 メタデータを保存しました: {metadata_file}")


def main():
    script_dir = Path(__file__).parent
    base_path = script_dir
    output_path = base_path / "output"
    
    assert base_path.exists(), f"ディレクトリ '{base_path}' が存在しません"
    assert output_path.exists(), f"outputディレクトリが存在しません: {output_path}"
    
    pair_mapping = load_pair_mapping(base_path)
    
    all_photo_files = get_image_files_from_pairs(pair_mapping)
    
    # 並列処理を使用（元の関数に戻したい場合は process_all_files に変更）
    metadata_list = process_all_files_multi(all_photo_files)
    
    save_metadata(metadata_list, base_path)

if __name__ == "__main__":
    main()