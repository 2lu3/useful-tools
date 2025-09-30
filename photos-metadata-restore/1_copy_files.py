#!/usr/bin/env python3

import hashlib
import json
import os
import shutil
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


def copy_images_with_hash(input_dir: Path, output_dir: Path, config: Dict[str, Any]) -> tuple[List[Dict[str, Any]], int]:
    image_extensions = get_image_extensions(config)
    pair_data = []
    duplicate_count = 0
    processed_hashes = set()

    image_files = []
    for file_path in input_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            image_files.append(file_path)

    logger.info(f"見つかった画像ファイル数: {len(image_files)}")

    with alive_bar(len(image_files), title="ファイルコピー中") as bar:
        for source_path in image_files:
            file_hash = calculate_file_hash(source_path)

            new_filename = f"{file_hash}{source_path.suffix.lower()}"
            destination_path = output_dir / new_filename

            if file_hash in processed_hashes:
                duplicate_count += 1
                bar.text(f"重複スキップ: {source_path.name}")
                bar()
                continue

            shutil.copy2(source_path, destination_path)

            processed_hashes.add(file_hash)

            pair_info = {
                "source": str(source_path),
                "destination": str(destination_path),
                "filename": new_filename,
                "hash": file_hash,
            }
            pair_data.append(pair_info)

            bar.text(f"コピー完了: {source_path.name} -> {new_filename}")
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