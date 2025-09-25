#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
写真ファイルの撮影日時プロパティをチェックし、撮影日時がないファイルをフィルタリングするスクリプト
"""

import os
import sys
import glob
import json
from pathlib import Path
import datetime
from alive_progress import alive_bar
from loguru import logger
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from utils.exif_utils import get_exif_data, get_exif_datetime, get_gps_data, GPSData


# 定数定義
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
ISO_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
MAX_FILENAME_DISPLAY_LENGTH = 30


@dataclass
class PhotoMetadata:
    """写真ファイルのメタデータを管理するdataclass"""
    file_path: Path
    file_name: str  # ファイル名（hash値）
    original_file_path: Optional[Path] = None  # 元のファイルのパス
    exif_datetime: Optional[datetime.datetime] = None
    file_creation_time: Optional[datetime.datetime] = None
    gps_data: Optional[GPSData] = None
    exif_data: Optional[Dict[str, Any]] = None
    
    @property
    def has_datetime(self) -> bool:
        """撮影日時情報があるかどうか"""
        return self.exif_datetime is not None
    
    @property
    def has_gps(self) -> bool:
        """GPS情報があるかどうか"""
        return self.gps_data is not None
    
    @property
    def has_metadata(self) -> bool:
        """何らかのメタデータがあるかどうか"""
        return self.has_datetime or self.has_gps
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換（JSON保存用）"""
        result = {
            'file_name': self.file_name,
            'file_path': str(self.file_path),
            'original_file_path': str(self.original_file_path) if self.original_file_path else None,
            'has_datetime': self.has_datetime,
            'has_gps': self.has_gps,
            'has_metadata': self.has_metadata
        }
        
        if self.exif_datetime:
            result['exif_datetime'] = _format_datetime_for_json(self.exif_datetime)
        
        if self.file_creation_time:
            result['file_creation_time'] = _format_datetime_for_json(self.file_creation_time)
        
        if self.gps_data:
            result['gps_data'] = asdict(self.gps_data)
        
        return result


def _format_filename_for_display(filename):
    """ファイル名を表示用にフォーマットする"""
    if len(filename) > MAX_FILENAME_DISPLAY_LENGTH:
        return f"{filename[:MAX_FILENAME_DISPLAY_LENGTH]}..."
    return filename


def _format_datetime_for_display(dt):
    """日時を表示用にフォーマットする"""
    if dt is None:
        return None
    return dt.strftime(DATETIME_FORMAT)


def _format_datetime_for_json(dt):
    """日時をJSON用にフォーマットする"""
    if dt is None:
        return None
    return dt.strftime(ISO_DATETIME_FORMAT)

def get_file_creation_time(file_path):
    """
    ファイルの作成日時を取得する（EXIFデータがない場合の代替手段）
    
    Args:
        file_path (str): ファイルのパス
        
    Returns:
        datetime.datetime: ファイルの作成日時
    """
    file_stat = os.stat(file_path)
    return datetime.datetime.fromtimestamp(file_stat.st_ctime)


def process_single_file(file_path: Path, original_file_path: Optional[Path] = None) -> PhotoMetadata:
    """単一ファイルのメタデータを処理する"""
    # 元のファイルが指定されている場合は、そちらのEXIFデータを取得
    source_file_path = original_file_path if original_file_path and original_file_path.exists() else file_path
    
    # EXIFデータを取得
    exif_data = get_exif_data(str(source_file_path))
    
    # 撮影日時を取得
    exif_datetime = None
    if exif_data is not None:
        exif_datetime = get_exif_datetime(exif_data)
    
    # ファイル作成日時は元のファイルから取得
    file_creation_time = get_file_creation_time(str(source_file_path))
    
    # GPS情報を取得
    gps_data = None
    if exif_data is not None:
        gps_data = get_gps_data(exif_data)
    
    return PhotoMetadata(
        file_path=file_path,
        file_name=file_path.name,
        original_file_path=original_file_path,
        exif_datetime=exif_datetime,
        file_creation_time=file_creation_time,
        gps_data=gps_data,
        exif_data=exif_data
    )

def load_pair_mapping(base_path):
    """pair.jsonファイルを読み込んで、output画像と元ファイルの対応関係を取得する"""
    pair_file = base_path / "output" / "pair.json"
    
    if not pair_file.exists():
        logger.error(f"pair.jsonファイルが見つかりません: {pair_file}")
        return {}
    
    with open(pair_file, 'r', encoding='utf-8') as f:
        pair_data = json.load(f)
    
    # destination -> source のマッピングを作成
    mapping = {}
    for item in pair_data:
        destination = Path(item['destination'])
        source = Path(item['source'])
        mapping[destination] = source
    
    logger.info(f"pair.jsonから{len(mapping)}個の対応関係を読み込みました")
    return mapping


def find_image_files(output_path):
    """output/images以下のファイルを検索する"""
    images_directory = output_path / "images"
    discovered_photo_files = []
    for file_path in images_directory.rglob('*'):
        if file_path.is_file():
            discovered_photo_files.append(file_path)
    
    logger.info(f"output/imagesディレクトリから{len(discovered_photo_files)}個のファイルを発見しました")
    assert discovered_photo_files, f"ファイルが見つかりませんでした: {images_directory}"
    return discovered_photo_files

def process_all_files(all_photo_files, pair_mapping):
    """すべてのファイルを処理する"""
    metadata_list = []
    # 4つのカテゴリに分類
    files_with_datetime_and_gps = []  # 撮影情報&GPSあり
    files_with_datetime_only = []    # 撮影情報のみ
    files_with_gps_only = []         # GPSのみ
    files_without_metadata = []      # 両方なし
    total_file_count = len(all_photo_files)
    
    logger.info(f"outputディレクトリ内の写真ファイルをスキャン中...")
    logger.info("=" * 60)
    
    # 各ファイルを処理（alive-progressを使用）
    with alive_bar(total_file_count, title="📸 ファイル分析中", bar='smooth', spinner='dots_waves') as bar:
        for file_path in all_photo_files:
            bar.text = f"🔍 分析中: {_format_filename_for_display(file_path.name)}"
            
            # 元のファイルのパスを取得
            original_file_path = pair_mapping.get(file_path)
            
            metadata = process_single_file(file_path, original_file_path)
            metadata_list.append(metadata)
            
            # 4つのカテゴリに分類
            if metadata.has_datetime and metadata.has_gps:
                files_with_datetime_and_gps.append(metadata.file_path)
            elif metadata.has_datetime and not metadata.has_gps:
                files_with_datetime_only.append(metadata.file_path)
            elif not metadata.has_datetime and metadata.has_gps:
                files_with_gps_only.append(metadata.file_path)
            else:
                files_without_metadata.append(metadata.file_path)
            
            # プログレスバーのテキストを更新
            metadata_status_parts = []
            if metadata.has_datetime:
                metadata_status_parts.append("📅日時")
            if metadata.has_gps:
                metadata_status_parts.append("📍GPS")
            
            if metadata_status_parts:
                bar.text = f"✅ {','.join(metadata_status_parts)}: {_format_filename_for_display(metadata.file_name)}"
            else:
                bar.text = f"⚠️  メタデータなし: {_format_filename_for_display(metadata.file_name)}"
            
            bar()
    
    return metadata_list, files_with_datetime_and_gps, files_with_datetime_only, files_with_gps_only, files_without_metadata


def print_summary(metadata_list, files_with_datetime_and_gps, files_with_datetime_only, files_with_gps_only, files_without_metadata, total_files, base_path):
    """調査結果のサマリーを出力する"""
    _print_summary_to_console(files_with_datetime_and_gps, files_with_datetime_only, files_with_gps_only, files_without_metadata, total_files)
    _create_metadata_json(base_path, metadata_list)
    _save_results_to_file(files_with_datetime_and_gps, files_with_datetime_only, files_with_gps_only, files_without_metadata, total_files, base_path)


def _print_summary_to_console(files_with_datetime_and_gps, files_with_datetime_only, files_with_gps_only, files_without_metadata, total_files):
    """コンソールに調査結果のサマリーを出力する"""
    logger.info("\n" + "=" * 60)
    logger.info("📊 調査結果まとめ")
    logger.info("=" * 60)
    logger.info(f"📁 総ファイル数: {total_files}")
    logger.info(f"📅📍 撮影情報&GPSあり: {len(files_with_datetime_and_gps)}")
    logger.info(f"📅 撮影情報のみ: {len(files_with_datetime_only)}")
    logger.info(f"📍 GPSのみ: {len(files_with_gps_only)}")
    logger.info(f"❌ 両方なし: {len(files_without_metadata)}")

    # 各カテゴリの詳細表示
    if files_without_metadata:
        logger.info(f"\n❌ メタデータなしのファイル ({len(files_without_metadata)}件):")
        logger.info("-" * 40)
        for i, file_path in enumerate(files_without_metadata, 1):
            logger.info(f"{i:3d}. {file_path.name}")
    
    if files_with_gps_only:
        logger.info(f"\n📍 GPSのみのファイル ({len(files_with_gps_only)}件):")
        logger.info("-" * 40)
        for i, file_path in enumerate(files_with_gps_only, 1):
            logger.info(f"{i:3d}. {file_path.name}")
    
    if files_with_datetime_only:
        logger.info(f"\n📅 撮影情報のみのファイル ({len(files_with_datetime_only)}件):")
        logger.info("-" * 40)
        for i, file_path in enumerate(files_with_datetime_only, 1):
            logger.info(f"{i:3d}. {file_path.name}")
    
    if files_with_datetime_and_gps:
        logger.info(f"\n📅📍 撮影情報&GPSありのファイル ({len(files_with_datetime_and_gps)}件):")
        logger.info("-" * 40)
        for i, file_path in enumerate(files_with_datetime_and_gps, 1):
            logger.info(f"{i:3d}. {file_path.name}")


def _create_metadata_json(base_path, metadata_list):
    """メタデータ情報をJSONファイルに保存する"""
    metadata_file = base_path / "output" / "metadata.json"
    metadata_dict = _collect_all_metadata(metadata_list)
    
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata_dict, f, ensure_ascii=False, indent=2)
    
    logger.info(f"💾 メタデータ情報を保存しました: {metadata_file}")


def _collect_all_metadata(metadata_list):
    """すべての画像ファイルのメタデータを収集する"""
    metadata_dict = {}
    
    for metadata in metadata_list:
        metadata_dict[metadata.file_name] = metadata.to_dict()
    
    return metadata_dict


def _save_results_to_file(files_with_datetime_and_gps, files_with_datetime_only, files_with_gps_only, files_without_metadata, total_files, base_path):
    """結果をファイルに保存する"""
    result_file = base_path / "output" / "filter_results.txt"
    
    with open(result_file, 'w', encoding='utf-8') as f:
        # ヘッダー
        f.write("写真ファイルフィルタリング結果\n")
        f.write("=" * 50 + "\n")
        f.write(f"スキャン日時: {_format_datetime_for_display(datetime.datetime.now())}\n")
        f.write(f"総ファイル数: {total_files}\n")
        f.write(f"📅📍 撮影情報&GPSあり: {len(files_with_datetime_and_gps)}\n")
        f.write(f"📅 撮影情報のみ: {len(files_with_datetime_only)}\n")
        f.write(f"📍 GPSのみ: {len(files_with_gps_only)}\n")
        f.write(f"❌ 両方なし: {len(files_without_metadata)}\n\n")
        
        # 各カテゴリの詳細
        if files_without_metadata:
            f.write("❌ メタデータなしのファイル:\n")
            f.write("-" * 30 + "\n")
            for i, file_path in enumerate(files_without_metadata, 1):
                f.write(f"{i:3d}. {file_path.name}\n")
                f.write(f"     パス: {file_path}\n")
                f.write(f"     サイズ: {file_path.stat().st_size} bytes\n")
                creation_time = get_file_creation_time(str(file_path))
                if creation_time:
                    f.write(f"     ファイル作成日時: {_format_datetime_for_display(creation_time)}\n")
                f.write("\n")
        
        if files_with_gps_only:
            f.write("📍 GPSのみのファイル:\n")
            f.write("-" * 30 + "\n")
            for i, file_path in enumerate(files_with_gps_only, 1):
                f.write(f"{i:3d}. {file_path.name}\n")
                f.write(f"     パス: {file_path}\n")
                f.write(f"     サイズ: {file_path.stat().st_size} bytes\n")
                creation_time = get_file_creation_time(str(file_path))
                if creation_time:
                    f.write(f"     ファイル作成日時: {_format_datetime_for_display(creation_time)}\n")
                f.write("\n")
        
        if files_with_datetime_only:
            f.write("📅 撮影情報のみのファイル:\n")
            f.write("-" * 30 + "\n")
            for i, file_path in enumerate(files_with_datetime_only, 1):
                f.write(f"{i:3d}. {file_path.name}\n")
                f.write(f"     パス: {file_path}\n")
                f.write(f"     サイズ: {file_path.stat().st_size} bytes\n")
                creation_time = get_file_creation_time(str(file_path))
                if creation_time:
                    f.write(f"     ファイル作成日時: {_format_datetime_for_display(creation_time)}\n")
                f.write("\n")
        
        if files_with_datetime_and_gps:
            f.write("📅📍 撮影情報&GPSありのファイル:\n")
            f.write("-" * 30 + "\n")
            for i, file_path in enumerate(files_with_datetime_and_gps, 1):
                f.write(f"{i:3d}. {file_path.name}\n")
                f.write(f"     パス: {file_path}\n")
                f.write(f"     サイズ: {file_path.stat().st_size} bytes\n")
                creation_time = get_file_creation_time(str(file_path))
                if creation_time:
                    f.write(f"     ファイル作成日時: {_format_datetime_for_display(creation_time)}\n")
                f.write("\n")
    
    logger.info(f"💾 結果をファイルに保存しました: {result_file}")

def main():
    """メイン関数"""
    # ベースディレクトリのパスを設定
    script_dir = Path(__file__).parent
    base_path = script_dir
    output_path = base_path / "output"
    
    # バリデーション
    assert base_path.exists(), f"ディレクトリ '{base_path}' が存在しません"
    assert output_path.exists(), f"outputディレクトリが存在しません: {output_path}"
    
    # pair mappingを読み込み
    pair_mapping = load_pair_mapping(base_path)
    
    # ファイルを検索
    all_photo_files = find_image_files(output_path)
    
    # ファイルを処理
    metadata_list, files_with_datetime_and_gps, files_with_datetime_only, files_with_gps_only, files_without_metadata = process_all_files(all_photo_files, pair_mapping)
    
    # 結果を出力
    print_summary(metadata_list, files_with_datetime_and_gps, files_with_datetime_only, files_with_gps_only, files_without_metadata, len(all_photo_files), base_path)

if __name__ == "__main__":
    main()
