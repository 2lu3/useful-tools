#!/usr/bin/env python3

import hashlib
import json
import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Set

import toml
from alive_progress import alive_bar
from loguru import logger


def get_all_extensions(input_dir: Path) -> Set[str]:
    extensions = set()

    for file_path in input_dir.rglob("*"):
        if file_path.is_file():
            ext = file_path.suffix.lower()
            if ext:
                extensions.add(ext)

    return extensions


def load_config(config_path: Path) -> Dict[str, Any]:
    with open(config_path, 'r', encoding='utf-8') as f:
        return toml.load(f)


def get_image_extensions(config: Dict[str, Any]) -> Set[str]:
    return set(config["file_types"]["image_extensions"])


def get_video_extensions(config: Dict[str, Any]) -> Set[str]:
    return set(config["file_types"]["video_extensions"])


def calculate_file_hash(file_path: Path) -> str:
    hash_md5 = hashlib.md5()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)

    return hash_md5.hexdigest()


def process_single_file(source_path: Path, output_dir: Path, processed_hashes: dict, lock: threading.Lock) -> tuple[Dict[str, Any] | None, bool]:
    """
    単一ファイルを処理する関数（スレッドセーフ）
    
    Returns:
        tuple: (pair_info, is_duplicate)
    """
    file_hash = calculate_file_hash(source_path)
    
    # 重複チェック（スレッドセーフ）
    with lock:
        if file_hash in processed_hashes:
            # 重複の場合、既存のエントリにソースファイルを追加
            processed_hashes[file_hash]["sources"].append(str(source_path))
            return None, True  # 重複
        else:
            # 新しいハッシュの場合、新しいエントリを作成
            processed_hashes[file_hash] = {
                "sources": [str(source_path)],
                "destination": None,
                "filename": None
            }
    
    # ファイルコピー
    new_filename = f"{file_hash}{source_path.suffix.lower()}"
    destination_path = output_dir / new_filename
    shutil.copy2(source_path, destination_path)
    
    # ハッシュエントリを更新
    with lock:
        processed_hashes[file_hash]["destination"] = str(destination_path)
        processed_hashes[file_hash]["filename"] = new_filename
    
    pair_info = {
        "sources": processed_hashes[file_hash]["sources"],
        "destination": str(destination_path),
        "filename": new_filename,
        "hash": file_hash,
    }
    
    return pair_info, False


def copy_images_with_hash(input_dir: Path, output_dir: Path, config: Dict[str, Any]) -> tuple[List[Dict[str, Any]], int]:
    image_extensions = get_image_extensions(config)
    pair_data = []
    duplicate_count = 0
    
    # スレッドセーフな共有データ構造（辞書に変更）
    processed_hashes = {}
    lock = threading.Lock()

    # 画像ファイルのリストを取得
    image_files = []
    for file_path in input_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            image_files.append(file_path)

    logger.info(f"見つかった画像ファイル数: {len(image_files)}")
    
    # CPUコア数の2倍のスレッドを使用（I/Oバウンドなので）
    max_workers = min(len(image_files), os.cpu_count() * 2)
    logger.info(f"並列処理を開始します (スレッド数: {max_workers})")

    with alive_bar(len(image_files), title="ファイルコピー中 (並列)") as bar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 全ファイルを並列処理
            futures = [
                executor.submit(process_single_file, source_path, output_dir, processed_hashes, lock)
                for source_path in image_files
            ]
            
            # 結果を収集
            for future in futures:
                try:
                    pair_info, is_duplicate = future.result()
                    
                    if is_duplicate:
                        duplicate_count += 1
                        bar.text(f"重複スキップ")
                    else:
                        pair_data.append(pair_info)
                        source_count = len(pair_info['sources'])
                        if source_count > 1:
                            bar.text(f"コピー完了: {source_count}個のファイル -> {pair_info['filename']}")
                        else:
                            bar.text(f"コピー完了: {pair_info['sources'][0].split('/')[-1]} -> {pair_info['filename']}")
                    
                    bar()
                except Exception as e:
                    logger.error(f"ファイル処理中にエラーが発生: {e}")
                    bar()

    return pair_data, duplicate_count




def main():
    base_dir = Path(__file__).parent
    config_path = base_dir / "config.toml"
    
    config = load_config(config_path)
    
    input_dir = base_dir / "input"
    output_dir = base_dir / "output"
    images_dir = output_dir / "images"
    pair_json_path = output_dir / "pair.json"

    logger.info("写真・動画ファイルのコピー処理を開始します")

    assert input_dir.exists(), f"入力ディレクトリが存在しません: {input_dir}"
    assert output_dir.exists(), f"出力ディレクトリが存在しません: {output_dir}"
    assert images_dir.exists(), f"画像出力ディレクトリが存在しません: {images_dir}"


    all_extensions = get_all_extensions(input_dir)
    logger.info(f"見つかった拡張子: {sorted(all_extensions)}")

    image_extensions = get_image_extensions(config)
    video_extensions = get_video_extensions(config)
    media_extensions = image_extensions | video_extensions

    unknown_extensions = all_extensions - media_extensions
    if unknown_extensions:
        logger.info(
            f"画像・動画として判定されなかった拡張子: {sorted(unknown_extensions)}"
        )
    else:
        logger.info("すべてのファイルが画像・動画として認識されました")

    logger.info("画像ファイルのコピー処理を開始します")
    pair_data, duplicate_count = copy_images_with_hash(input_dir, images_dir, config)

    with open(pair_json_path, "w", encoding="utf-8") as f:
        json.dump(pair_data, f, ensure_ascii=False, indent=2)

    logger.info(f"コピー完了: {len(pair_data)}個のファイル")
    logger.info(f"重複したためコピーされなかったファイル数: {duplicate_count}個")
    logger.info(f"pair.jsonに保存しました: {pair_json_path}")
    logger.info("処理が完了しました")

if __name__ == "__main__":
    main()