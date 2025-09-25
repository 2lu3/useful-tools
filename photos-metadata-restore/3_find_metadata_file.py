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
    # 元のファイル名を取得
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

    logger.info(f"🔍 {total_files}個の画像ファイルのメタデータファイルを検索中...")

    with alive_bar(
        total_files,
        title="📁 メタデータファイル検索中",
        bar="smooth",
        spinner="dots_waves",
    ) as bar:
        for i, pair_info in enumerate(pair_data):
            # 元のファイルパスを取得
            original_source = Path(pair_info["source"])
            hash_filename = pair_info["filename"]

            bar.text = f"🔍 検索中: {hash_filename}"

            # メタデータファイルを検索
            metadata_info = find_metadata_file_for_image(original_source)
            metadata_results[hash_filename] = metadata_info

            # プログレスバーのテキストを更新
            if metadata_info["found"]:
                bar.text = (
                    f"✅ 発見: {hash_filename} -> {metadata_info['metadata_type']}"
                )
            else:
                bar.text = f"❌ 未発見: {hash_filename}"

            bar()

    return metadata_results


def save_metadata_location_json(metadata_results: Dict[str, Any], output_path: Path):
    """メタデータファイルの検索結果をJSONファイルに保存する"""
    metadata_location_file = output_path / "metadata_location.json"

    with open(metadata_location_file, "w", encoding="utf-8") as f:
        json.dump(metadata_results, f, ensure_ascii=False, indent=2)

    logger.info(
        f"💾 メタデータファイル検索結果を保存しました: {metadata_location_file}"
    )


def print_summary(metadata_results: Dict[str, Any]):
    """検索結果のサマリーを表示する"""
    total_files = len(metadata_results)
    found_files = sum(1 for result in metadata_results.values() if result["found"])
    not_found_files = total_files - found_files

    # メタデータタイプ別の集計
    metadata_type_counts = {}
    for result in metadata_results.values():
        if result["found"]:
            metadata_type = result["metadata_type"]
            metadata_type_counts[metadata_type] = (
                metadata_type_counts.get(metadata_type, 0) + 1
            )

    logger.info("\n" + "=" * 60)
    logger.info("📊 メタデータファイル検索結果")
    logger.info("=" * 60)
    logger.info(f"📁 総ファイル数: {total_files}")
    logger.info(f"✅ メタデータファイル発見: {found_files}")
    logger.info(f"❌ メタデータファイル未発見: {not_found_files}")

    if metadata_type_counts:
        logger.info("\n📋 メタデータタイプ別集計:")
        for metadata_type, count in metadata_type_counts.items():
            logger.info(f"  - {metadata_type}: {count}件")

    # 未発見ファイルの詳細表示（最初の10件のみ）
    not_found_list = [
        filename for filename, result in metadata_results.items() if not result["found"]
    ]
    if not_found_list:
        logger.info(f"\n❌ メタデータファイル未発見のファイル (最初の10件):")
        logger.info("-" * 40)
        for i, filename in enumerate(not_found_list[:10], 1):
            logger.info(f"{i:3d}. {filename}")

        if len(not_found_list) > 10:
            logger.info(f"    ... 他 {len(not_found_list) - 10}件")


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

    logger.info("🚀 メタデータファイル検索を開始します")

    # pair.jsonを読み込み
    logger.info(f"📖 pair.jsonを読み込み中: {pair_file_path}")
    pair_data = load_pair_json(pair_file_path)
    logger.info(f"📊 {len(pair_data)}個の画像ファイルの情報を読み込みました")

    # メタデータファイルを検索
    metadata_results = process_all_images(pair_data)

    # 結果を保存
    save_metadata_location_json(metadata_results, output_path)

    # サマリーを表示
    print_summary(metadata_results)

    logger.info("✅ メタデータファイル検索が完了しました")


if __name__ == "__main__":
    main()
