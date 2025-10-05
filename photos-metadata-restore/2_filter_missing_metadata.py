#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path
import datetime
from alive_progress import alive_bar
from loguru import logger
from typing import Optional, List, Dict, Tuple
from utils.exif_utils import get_exif_data, get_exif_datetime, get_gps_data, GPSData, PhotoMetadata
import json
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
import shutil
from collections import defaultdict


def process_single_file(file_path: Path) -> PhotoMetadata:
    """単一ファイルのEXIFデータを取得"""
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


def load_pair_mapping(base_path: Path) -> Dict[Path, List[Path]]:
    """pair.jsonから対応関係を読み込む"""
    pair_file = base_path / "output" / "pair.json"
    assert pair_file.exists()
    
    with open(pair_file, 'r', encoding='utf-8') as f:
        pair_data = json.load(f)
    
    mapping = {}
    for item in pair_data:
        destination = Path(item['destination'])
        sources = [Path(source) for source in item['sources']]
        mapping[destination] = sources
    
    logger.info(f"pair.jsonから{len(mapping)}個の対応関係を読み込みました")
    return mapping


def get_all_source_metadata(pair_mapping: Dict[Path, List[Path]]) -> Dict[str, PhotoMetadata]:
    """pair.jsonから読み込んだ情報をもとに、元のファイルのmetadataをすべて取得する"""
    # すべての元ファイルを収集
    all_source_files = []
    for destination, sources in pair_mapping.items():
        all_source_files.extend(sources)
    
    logger.info(f"元ファイル総数: {len(all_source_files)}個")
    
    # 並列処理でメタデータを取得
    max_workers = multiprocessing.cpu_count() * 2
    source_metadata = {}
    
    with alive_bar(len(all_source_files), title="📸 元ファイル分析中 (並列)", bar='smooth', spinner='dots_waves') as bar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_single_file, file_path) for file_path in all_source_files]
            
            for future in futures:
                metadata = future.result()
                source_metadata[metadata.file_name] = metadata
                bar.text = f"🔍 分析中: {metadata.file_name[:50]}{'...' if len(metadata.file_name) > 50 else ''}"
                bar()
    
    return source_metadata


def merge_metadata_list(metadata_list: List[PhotoMetadata]) -> PhotoMetadata:
    """複数のメタデータを統合する"""
    if not metadata_list:
        raise ValueError("メタデータリストが空です")
    
    if len(metadata_list) == 1:
        return metadata_list[0]
    
    # 最初のメタデータをベースにする
    merged = metadata_list[0]
    
    # GPSデータの統合
    gps_data_list = [m.exif_gps for m in metadata_list if m.exif_gps is not None]
    if len(gps_data_list) > 1:
        # 複数のGPSデータがある場合、一致するかチェック
        first_gps = gps_data_list[0]
        for gps in gps_data_list[1:]:
            if (gps.latitude != first_gps.latitude or 
                gps.longitude != first_gps.longitude or 
                gps.altitude != first_gps.altitude):
                logger.error(f"GPSデータが一致しません:")
                logger.error(f"  ファイル1: {metadata_list[0].file_name} - {first_gps}")
                logger.error(f"  ファイル2: {[m.file_name for m in metadata_list if m.exif_gps == gps][0]} - {gps}")
                sys.exit(1)
        merged.exif_gps = first_gps
    elif len(gps_data_list) == 1:
        # GPSデータが1つだけある場合、それを使用
        merged.exif_gps = gps_data_list[0]
    
    # 日時データの統合
    datetime_list = [m.exif_datetime for m in metadata_list if m.exif_datetime is not None]
    if len(datetime_list) > 1:
        # 複数の日時データがある場合、一致するかチェック
        first_datetime = datetime_list[0]
        for dt in datetime_list[1:]:
            if dt != first_datetime:
                logger.error(f"日時データが一致しません:")
                logger.error(f"  ファイル1: {metadata_list[0].file_name} - {first_datetime}")
                logger.error(f"  ファイル2: {[m.file_name for m in metadata_list if m.exif_datetime == dt][0]} - {dt}")
                sys.exit(1)
        merged.exif_datetime = first_datetime
    elif len(datetime_list) == 1:
        # 日時データが1つだけある場合、それを使用
        merged.exif_datetime = datetime_list[0]
    
    return merged


def merge_all_metadata(pair_mapping: Dict[Path, List[Path]], source_metadata: Dict[str, PhotoMetadata]) -> List[PhotoMetadata]:
    """すべてのmetadataを統合する"""
    merged_metadata_list = []
    
    logger.info("メタデータ統合中...")
    with alive_bar(len(pair_mapping), title="🔄 メタデータ統合中", bar='smooth', spinner='dots_waves') as bar:
        for destination, sources in pair_mapping.items():
            # この出力ファイルに対応する元ファイルのメタデータを収集
            source_metadata_list = []
            for source in sources:
                source_name = source.name
                if source_name in source_metadata:
                    source_metadata_list.append(source_metadata[source_name])
                else:
                    logger.warning(f"メタデータが見つかりません: {source_name}")
            
            if source_metadata_list:
                # メタデータを統合
                merged_metadata = merge_metadata_list(source_metadata_list)
                # 出力ファイル名に変更
                merged_metadata.file_name = destination.name
                merged_metadata_list.append(merged_metadata)
                
                if len(source_metadata_list) > 1:
                    filename_short = destination.name[:40] + ('...' if len(destination.name) > 40 else '')
                    bar.text = f"🔄 統合完了: {len(source_metadata_list)}個のファイル -> {filename_short}"
                else:
                    filename_short = destination.name[:40] + ('...' if len(destination.name) > 40 else '')
                    bar.text = f"✅ 処理完了: {filename_short}"
            else:
                logger.error(f"メタデータが取得できませんでした: {destination}")
            
            bar()
    
    return merged_metadata_list


def filter_inconsistent_metadata(metadata_list: List[PhotoMetadata]) -> List[PhotoMetadata]:
    """日付やGPSが一致しないものをフィルタリングする"""
    logger.info("🔍 一貫性チェックとフィルタリングを開始します...")
    
    # 日時でグループ化
    datetime_groups = defaultdict(list)
    files_without_datetime = []
    
    with alive_bar(len(metadata_list), title="📊 日時グループ化中", bar='smooth', spinner='dots_waves') as bar:
        for metadata in metadata_list:
            if metadata.exif_datetime:
                datetime_groups[metadata.exif_datetime].append(metadata)
            else:
                files_without_datetime.append(metadata)
            bar.text = f"📊 グループ化中: {metadata.file_name[:40]}{'...' if len(metadata.file_name) > 40 else ''}"
            bar()
    
    logger.info(f"日時グループ数: {len(datetime_groups)}")
    logger.info(f"日時なしファイル数: {len(files_without_datetime)}")
    
    # 各日時グループ内でGPSデータの一貫性をチェック
    consistent_metadata = []
    inconsistent_files = []
    
    total_groups = len(datetime_groups)
    with alive_bar(total_groups, title="🔍 GPS一貫性チェック中", bar='smooth', spinner='dots_waves') as bar:
        for datetime_obj, group in datetime_groups.items():
            if len(group) > 1:
                # 同じ日時に複数のファイルがある場合、GPSデータをチェック
                gps_data_list = [m.exif_gps for m in group if m.exif_gps is not None]
                
                if len(gps_data_list) > 1:
                    # 複数のGPSデータがある場合、一致するかチェック
                    first_gps = gps_data_list[0]
                    is_consistent = True
                    
                    for gps in gps_data_list[1:]:
                        if (gps.latitude != first_gps.latitude or 
                            gps.longitude != first_gps.longitude or 
                            gps.altitude != first_gps.altitude):
                            is_consistent = False
                            break
                    
                    if is_consistent:
                        # GPSデータが一致する場合は1つのメタデータを保持
                        consistent_metadata.append(group[0])
                        bar.text = f"✅ GPS一致: {group[0].file_name[:30]}{'...' if len(group[0].file_name) > 30 else ''}"
                    else:
                        # GPSデータが一致しない場合はすべて除外
                        inconsistent_files.extend(group)
                        logger.warning(f"日時 {datetime_obj} でGPSデータが一致しません: {len(group)}個のファイルを除外")
                        bar.text = f"⚠️ GPS不一致: {len(group)}個のファイルを除外"
                else:
                    # GPSデータが1つまたは0個の場合は保持
                    consistent_metadata.append(group[0])
                    bar.text = f"✅ 単一GPS: {group[0].file_name[:30]}{'...' if len(group[0].file_name) > 30 else ''}"
            else:
                # 単一ファイルの場合は保持
                consistent_metadata.append(group[0])
                bar.text = f"✅ 単一ファイル: {group[0].file_name[:30]}{'...' if len(group[0].file_name) > 30 else ''}"
            
            bar()
    
    # 日時なしファイルも除外
    inconsistent_files.extend(files_without_datetime)
    logger.info(f"日時なしファイルを除外: {len(files_without_datetime)}個")
    
    logger.info(f"一貫性のあるメタデータ: {len(consistent_metadata)}個")
    logger.info(f"除外されたファイル: {len(inconsistent_files)}個")
    
    return consistent_metadata


def save_filtered_metadata(metadata_list: List[PhotoMetadata], base_path: Path) -> None:
    """フィルタリングされた画像のメタデータを保存する"""
    import pickle
    
    metadata_file = base_path / "output" / "photo_metadata.pkl"
    
    with open(metadata_file, 'wb') as f:
        pickle.dump(metadata_list, f)
    
    logger.info(f"💾 フィルタリングされたメタデータを保存しました: {metadata_file}")
    logger.info(f"保存されたメタデータ数: {len(metadata_list)}個")


def main():
    """メイン関数 - シンプルな4ステップで処理"""
    script_dir = Path(__file__).parent
    base_path = script_dir
    output_path = base_path / "output"
    
    assert base_path.exists(), f"ディレクトリ '{base_path}' が存在しません"
    assert output_path.exists(), f"outputディレクトリが存在しません: {output_path}"
    
    # 1. pair.jsonから読み込んだ情報をもとに、元のファイルのmetadataをすべて取得する
    logger.info("🚀 === ステップ1: 元ファイルのメタデータ取得 ===")
    pair_mapping = load_pair_mapping(base_path)
    source_metadata = get_all_source_metadata(pair_mapping)
    
    # 2. すべてのmetadataを統合する
    logger.info("🔄 === ステップ2: メタデータ統合 ===")
    merged_metadata = merge_all_metadata(pair_mapping, source_metadata)
    
    # 3. 日付やGPSが一致しないものをフィルタリングする
    logger.info("🔍 === ステップ3: 一貫性チェックとフィルタリング ===")
    filtered_metadata = filter_inconsistent_metadata(merged_metadata)
    
    # 4. フィルタリングされた画像のメタデータを保存する
    logger.info("💾 === ステップ4: フィルタリングされたメタデータ保存 ===")
    save_filtered_metadata(filtered_metadata, base_path)
    
    logger.info("🎉 ✅ 全ての処理が完了しました！")

if __name__ == "__main__":
    main()