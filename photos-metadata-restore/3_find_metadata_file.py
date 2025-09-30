#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
画像ファイルに対応するメタデータファイルを検索するスクリプト
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from alive_progress import alive_bar
from loguru import logger


def load_pair_json(pair_file_path: Path) -> List[Dict[str, Any]]:
    """pair.jsonファイルを読み込む"""
    with open(pair_file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_metadata_file_for_image(
    original_source_path: Path,
) -> Optional[Dict[str, Any]]:
    """
    元の画像ファイルに対応するメタデータファイルを検索する

    Args:
        original_source_path: 元の画像ファイルのパス

    Returns:
        メタデータファイルの情報（見つからない場合はNone）
    """
    # 元のファイル名を取得s
    original_filename = original_source_path.name

    # メタデータファイルの候補パターン
    metadata_patterns = [
        f"{original_filename}.supplemental-metadata.json",
        f"{original_filename}.supplemental-met.json",
    ]

    # 元のファイルと同じディレクトリでメタデータファイルを検索
    original_dir = original_source_path.parent

    for pattern in metadata_patterns:
        metadata_file_path = original_dir / pattern
        if metadata_file_path.exists():
            return {
                "original_source": str(original_source_path),
                "metadata_file": str(metadata_file_path),
                "metadata_type": pattern.split(".")[
                    -2
                ],  # supplemental-metadata または supplemental-met
                "found": True,
                "file_exists": True,
            }

    # メタデータファイルが見つからない場合
    return {
        "original_source": str(original_source_path),
        "metadata_file": None,
        "metadata_type": None,
        "found": False,
        "file_exists": False,
    }


def process_all_images(pair_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    すべての画像ファイルに対してメタデータファイルを検索する

    Args:
        pair_data: pair.jsonから読み込んだデータ

    Returns:
        メタデータファイルの検索結果
    """
    metadata_results = {}
    total_files = len(pair_data)

    logger.info(f"{total_files}個の画像ファイルのメタデータファイルを検索中...")

    with alive_bar(
        total_files,
    ) as bar:
        for pair_info in pair_data:
            # 元のファイルパスを取得
            original_source = Path(pair_info["source"])
            hash_filename = pair_info["filename"]

            # メタデータファイルを検索
            metadata_info = find_metadata_file_for_image(original_source)
            metadata_results[hash_filename] = metadata_info
            
            bar()

    return metadata_results


def save_metadata_location_json(metadata_results: Dict[str, Any], output_path: Path):
    """メタデータファイルの検索結果をJSONファイルに保存する"""
    metadata_location_file = output_path / "supplemental_file_location.json"

    with open(metadata_location_file, "w", encoding="utf-8") as f:
        json.dump(metadata_results, f, ensure_ascii=False, indent=2)

    logger.info(
        f"メタデータファイル検索結果を保存しました: {metadata_location_file}"
    )


def main():
    """メイン関数"""
    # ベースディレクトリのパスを設定
    script_dir = Path(__file__).parent
    base_path = script_dir
    output_path = base_path / "output"
    pair_file_path = output_path / "pair.json"

    # バリデーション
    assert base_path.exists(), f"ディレクトリ '{base_path}' が存在しません"
    assert output_path.exists(), f"outputディレクトリが存在しません: {output_path}"
    assert pair_file_path.exists(), f"pair.jsonファイルが存在しません: {pair_file_path}"

    logger.info("メタデータファイル検索を開始します")

    # pair.jsonを読み込み
    pair_data = load_pair_json(pair_file_path)

    # メタデータファイルを検索
    metadata_results = process_all_images(pair_data)

    # 結果を保存
    save_metadata_location_json(metadata_results, output_path)

    logger.info("メタデータファイル検索が完了しました")


if __name__ == "__main__":
    main()
