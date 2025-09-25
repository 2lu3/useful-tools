#!/usr/bin/env python3
"""
写真・動画ファイルのコピーとハッシュ化を行うスクリプト

入力ディレクトリから画像ファイルを検索し、ハッシュ値.拡張子の形式で
output/images/にコピーし、元ファイルとの対応関係をpair.jsonに保存する。
"""

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Set

from loguru import logger


def get_all_extensions(input_dir: Path) -> Set[str]:
    """
    入力ディレクトリ下にあるすべてのファイルの拡張子を列挙する

    Args:
        input_dir: 入力ディレクトリのパス

    Returns:
        拡張子のセット（小文字、ドット付き）
    """
    extensions = set()

    for file_path in input_dir.rglob("*"):
        if file_path.is_file():
            ext = file_path.suffix.lower()
            if ext:
                extensions.add(ext)

    return extensions


def get_image_extensions() -> Set[str]:
    """
    画像ファイルの拡張子を定義する

    Returns:
        画像拡張子のセット
    """
    return {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".tiff",
        ".tif",
        ".webp",
        ".svg",
        ".ico",
        ".heic",
        ".heif",
        ".raw",
        ".cr2",
        ".nef",
        ".arw",
        ".dng",
        ".orf",
        ".rw2",
        ".pef",
        ".srw",
    }


def get_video_extensions() -> Set[str]:
    """
    動画ファイルの拡張子を定義する

    Returns:
        動画拡張子のセット
    """
    return {
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
        ".mkv",
        ".m4v",
        ".3gp",
        ".ogv",
        ".ts",
        ".mts",
        ".m2ts",
        ".vob",
    }


def calculate_file_hash(file_path: Path) -> str:
    """
    ファイルのMD5ハッシュ値を計算する

    Args:
        file_path: ファイルのパス

    Returns:
        MD5ハッシュ値（16進数文字列）
    """
    hash_md5 = hashlib.md5()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)

    return hash_md5.hexdigest()


def copy_images_with_hash(input_dir: Path, output_dir: Path) -> List[Dict[str, Any]]:
    """
    画像ファイルをハッシュ値.拡張子の形式でコピーする

    Args:
        input_dir: 入力ディレクトリ
        output_dir: 出力ディレクトリ

    Returns:
        コピー情報のリスト
    """
    image_extensions = get_image_extensions()
    pair_data = []

    # 入力ディレクトリから画像ファイルを再帰的に検索
    image_files = []
    for file_path in input_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            image_files.append(file_path)

    logger.info(f"見つかった画像ファイル数: {len(image_files)}")

    for source_path in image_files:
        try:
            # ハッシュ値を計算
            file_hash = calculate_file_hash(source_path)

            # 新しいファイル名を作成（ハッシュ値.拡張子）
            new_filename = f"{file_hash}{source_path.suffix.lower()}"
            destination_path = output_dir / new_filename

            # ファイルをコピー
            shutil.copy2(source_path, destination_path)

            # ペア情報を記録
            pair_info = {
                "source": str(source_path),
                "destination": str(destination_path),
                "filename": new_filename,
                "hash": file_hash,
            }
            pair_data.append(pair_info)

            logger.debug(f"コピー完了: {source_path.name} -> {new_filename}")

        except Exception as e:
            logger.error(f"ファイルコピーエラー: {source_path} - {e}")

    return pair_data


def reset_tmp_directory(tmp_dir: Path) -> None:
    """
    tmpディレクトリをリセットする（削除して再作成）

    Args:
        tmp_dir: tmpディレクトリのパス
    """
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
        logger.info("tmpディレクトリを削除しました")

    tmp_dir.mkdir(parents=True, exist_ok=True)
    logger.info("tmpディレクトリを作成しました")


def main():
    """メイン処理"""
    # ディレクトリパスの設定
    base_dir = Path(__file__).parent
    input_dir = base_dir / "input"
    output_dir = base_dir / "output"
    images_dir = output_dir / "images"
    tmp_dir = base_dir / "tmp"
    pair_json_path = output_dir / "pair.json"

    # ログの設定
    logger.add("copy_files.log", rotation="10 MB", retention="7 days")

    logger.info("写真・動画ファイルのコピー処理を開始します")

    # 入力ディレクトリの存在確認
    if not input_dir.exists():
        logger.error(f"入力ディレクトリが存在しません: {input_dir}")
        return

    # tmpディレクトリのリセット
    reset_tmp_directory(tmp_dir)

    # 出力ディレクトリの作成
    images_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"出力ディレクトリを作成しました: {images_dir}")

    # すべての拡張子を列挙
    all_extensions = get_all_extensions(input_dir)
    logger.info(f"見つかった拡張子: {sorted(all_extensions)}")

    # 画像・動画の拡張子を定義
    image_extensions = get_image_extensions()
    video_extensions = get_video_extensions()
    media_extensions = image_extensions | video_extensions

    # 画像・動画として判定されなかった拡張子を表示
    unknown_extensions = all_extensions - media_extensions
    if unknown_extensions:
        logger.info(
            f"画像・動画として判定されなかった拡張子: {sorted(unknown_extensions)}"
        )
    else:
        logger.info("すべてのファイルが画像・動画として認識されました")

    # 画像ファイルのコピーとハッシュ化
    logger.info("画像ファイルのコピー処理を開始します")
    pair_data = copy_images_with_hash(input_dir, images_dir)

    # pair.jsonに保存
    with open(pair_json_path, "w", encoding="utf-8") as f:
        json.dump(pair_data, f, ensure_ascii=False, indent=2)

    logger.info(f"コピー完了: {len(pair_data)}個のファイル")
    logger.info(f"pair.jsonに保存しました: {pair_json_path}")
    logger.info("処理が完了しました")

if __name__ == "__main__":
    main()
