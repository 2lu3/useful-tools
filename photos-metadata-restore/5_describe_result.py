#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
メタデータ分析結果のレポート生成スクリプト

Google PhotosのTakeoutデータから抽出したメタデータを分析し、
GPS情報と撮影日時の有無によってファイルを分類してレポートを生成します。
"""

import pickle
import json
import os
import shutil
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import toml

from utils.exif_utils import PhotoMetadata, GPSData


def load_metadata() -> Tuple[List[PhotoMetadata], List[PhotoMetadata]]:
    """メタデータファイルを読み込む"""
    with open("output/photo_metadata.pkl", 'rb') as f:
        photo_metadata = pickle.load(f)
    
    with open("output/supplemental_metadata.pkl", 'rb') as f:
        supplemental_metadata = pickle.load(f)
    
    return photo_metadata, supplemental_metadata


def load_pair_data() -> Dict[str, Dict]:
    """pair.jsonファイルを読み込む"""
    with open("output/pair.json", 'r', encoding='utf-8') as f:
        pair_data = json.load(f)
    
    # ハッシュ値でインデックス化
    hash_to_pair = {}
    for pair in pair_data:
        hash_to_pair[pair['hash']] = pair
    
    return hash_to_pair


def load_file_types() -> Tuple[List[str], List[str]]:
    """設定ファイルからファイルタイプを読み込む"""
    config = toml.load("config.toml")
    return config['file_types']['image_extensions'], config['file_types']['video_extensions']


def get_file_type(filename: str, image_extensions: List[str], video_extensions: List[str]) -> str:
    """ファイル名からファイルタイプを判定する"""
    ext = Path(filename).suffix.lower()
    if ext in image_extensions:
        return "画像"
    elif ext in video_extensions:
        return "動画"
    else:
        return "その他"


def compare_metadata(photo_metadata: List[PhotoMetadata], supplemental_metadata: List[PhotoMetadata], 
                    hash_to_pair: Dict[str, Dict], image_extensions: List[str], video_extensions: List[str]) -> Dict[str, List[Dict]]:
    """photoメタデータとsupplementalメタデータを比較する"""
    
    # ハッシュでインデックス化
    photo_dict = {m.file_name: m for m in photo_metadata}
    supplemental_dict = {m.file_name: m for m in supplemental_metadata}
    
    # 2x4の分類: 行はGPSと日時の有無、列はファイル自体とsupplementalの一致状況
    categories = {
        # GPSあり
        "GPSあり_両方一致": [],      # 両方のファイルでGPSが一致
        "GPSあり_ファイルのみ": [],   # ファイル自体のみにGPSがある
        "GPSあり_supplementalのみ": [], # supplementalのみにGPSがある
        "GPSあり_両方なし": [],      # 両方ともGPSがない
        
        # 日時あり
        "日時あり_両方一致": [],      # 両方のファイルで日時が一致
        "日時あり_ファイルのみ": [],   # ファイル自体のみに日時がある
        "日時あり_supplementalのみ": [], # supplementalのみに日時がある
        "日時あり_両方なし": []       # 両方とも日時がない
    }
    
    total_files = 0
    image_video_files = 0
    
    for hash_filename in photo_dict.keys():
        total_files += 1
        
        # ファイルタイプを判定
        file_type = get_file_type(hash_filename, image_extensions, video_extensions)
        if file_type in ["画像", "動画"]:
            image_video_files += 1
        
        # 元ファイル名を取得
        hash_value = hash_filename.split('.')[0]
        original_filename = "不明"
        if hash_value in hash_to_pair:
            original_filename = os.path.basename(hash_to_pair[hash_value]['source'])
        
        photo_data = photo_dict[hash_filename]
        supplemental_data = supplemental_dict.get(hash_filename)
        
        # ファイル情報を構築
        file_info = {
            "hash_filename": hash_filename,
            "original_filename": original_filename,
            "file_type": file_type,
            "photo": photo_data,
            "supplemental": supplemental_data
        }
        
        # 比較
        photo_has_gps = photo_data.exif_gps is not None
        photo_has_datetime = photo_data.exif_datetime is not None
        
        if supplemental_data is None:
            # supplementalデータがない場合
            if photo_has_gps:
                categories["GPSあり_ファイルのみ"].append(file_info)
            if photo_has_datetime:
                categories["日時あり_ファイルのみ"].append(file_info)
        else:
            # 両方のデータがある場合
            supp_has_gps = supplemental_data.exif_gps is not None
            supp_has_datetime = supplemental_data.exif_datetime is not None
            
            gps_match = _compare_gps(photo_data.exif_gps, supplemental_data.exif_gps)
            datetime_match = _compare_datetime(photo_data.exif_datetime, supplemental_data.exif_datetime)
            
            # GPSの分類
            if photo_has_gps and supp_has_gps:
                if gps_match:
                    categories["GPSあり_両方一致"].append(file_info)
                else:
                    categories["GPSあり_両方なし"].append(file_info)
            elif photo_has_gps:
                categories["GPSあり_ファイルのみ"].append(file_info)
            elif supp_has_gps:
                categories["GPSあり_supplementalのみ"].append(file_info)
            else:
                categories["GPSあり_両方なし"].append(file_info)
            
            # 日時の分類
            if photo_has_datetime and supp_has_datetime:
                if datetime_match:
                    categories["日時あり_両方一致"].append(file_info)
                else:
                    categories["日時あり_両方なし"].append(file_info)
            elif photo_has_datetime:
                categories["日時あり_ファイルのみ"].append(file_info)
            elif supp_has_datetime:
                categories["日時あり_supplementalのみ"].append(file_info)
            else:
                categories["日時あり_両方なし"].append(file_info)
    
    return categories, total_files, image_video_files


def _compare_gps(gps1: Optional[GPSData], gps2: Optional[GPSData]) -> bool:
    """GPS情報を比較する"""
    if gps1 is None and gps2 is None:
        return True
    if gps1 is None or gps2 is None:
        return False
    
    # 小数点以下6桁で比較（約0.1mの精度）
    lat_diff = abs(gps1.latitude - gps2.latitude)
    lon_diff = abs(gps1.longitude - gps2.longitude)
    
    return lat_diff < 0.000001 and lon_diff < 0.000001


def _compare_datetime(dt1: Optional[datetime], dt2: Optional[datetime]) -> bool:
    """日時を比較する"""
    if dt1 is None and dt2 is None:
        return True
    if dt1 is None or dt2 is None:
        return False
    
    return dt1 == dt2


def copy_unknown_datetime_files(photo_metadata: List[PhotoMetadata], supplemental_metadata: List[PhotoMetadata], 
                               hash_to_pair: Dict[str, Dict], image_extensions: List[str], video_extensions: List[str]) -> None:
    """日時不明のファイルをoutput/日時不明ディレクトリにコピーする"""
    
    # ハッシュでインデックス化
    photo_dict = {m.file_name: m for m in photo_metadata}
    supplemental_dict = {m.file_name: m for m in supplemental_metadata}
    
    # 出力ディレクトリを作成
    unknown_datetime_dir = Path("output/日時不明")
    unknown_datetime_dir.mkdir(exist_ok=True)
    
    copied_count = 0
    
    print("\n【日時不明ファイルのコピー処理】")
    print("=" * 50)
    
    for hash_filename in photo_dict.keys():
        photo_data = photo_dict[hash_filename]
        supplemental_data = supplemental_dict.get(hash_filename)
        file_type = get_file_type(hash_filename, image_extensions, video_extensions)
        
        # 画像・動画ファイルのみを対象
        if file_type in ['画像', '動画']:
            photo_has_datetime = photo_data.exif_datetime is not None
            supp_has_datetime = supplemental_data.exif_datetime is not None if supplemental_data else False
            
            # 両方とも日時がない場合
            if not photo_has_datetime and not supp_has_datetime:
                # 元ファイルのパスを取得
                hash_value = hash_filename.split('.')[0]
                if hash_value in hash_to_pair:
                    source_path = Path(hash_to_pair[hash_value]['source'])
                    if source_path.exists():
                        # コピー先のパス
                        dest_path = unknown_datetime_dir / hash_filename
                        
                        try:
                            shutil.copy2(source_path, dest_path)
                            copied_count += 1
                            print(f"コピー完了: {source_path.name} -> {hash_filename}")
                        except Exception as e:
                            print(f"コピーエラー: {source_path.name} - {e}")
                    else:
                        print(f"元ファイルが見つかりません: {source_path}")
                else:
                    print(f"ペア情報が見つかりません: {hash_filename}")
    
    print(f"\nコピー完了: {copied_count}個のファイルをoutput/日時不明/にコピーしました")






def main():
    """メイン処理"""
    print("メタデータ比較分析を開始します...")
    
    # データを読み込み
    print("メタデータを読み込み中...")
    photo_metadata, supplemental_metadata = load_metadata()
    
    print("ペアデータを読み込み中...")
    hash_to_pair = load_pair_data()
    
    print("設定ファイルを読み込み中...")
    image_extensions, video_extensions = load_file_types()
    
    # メタデータを直接カウント
    print("メタデータを分析中...")
    
    # ハッシュでインデックス化
    photo_dict = {m.file_name: m for m in photo_metadata}
    supplemental_dict = {m.file_name: m for m in supplemental_metadata}
    
    total_files = len(photo_dict)
    image_video_files = 0
    
    # 画像・動画ファイル数をカウント
    for hash_filename in photo_dict.keys():
        file_type = get_file_type(hash_filename, image_extensions, video_extensions)
        if file_type in ["画像", "動画"]:
            image_video_files += 1
    
    
    # 簡易統計を表示
    print("\n【2x4 Classification Table】")
    print()
    
    # ヘッダー行
    print(f"{'Item':<8} {'Both Match':<10} {'Media Only':<12} {'Supplemental Only':<18} {'Both None':<10}")
    print("-" * 60)
    
    # GPSの統計を直接計算
    gps_both_match = 0
    gps_media_only = 0
    gps_supplemental_only = 0
    gps_both_none = 0
    
    for hash_filename in photo_dict.keys():
        photo_data = photo_dict[hash_filename]
        supplemental_data = supplemental_dict.get(hash_filename)
        
        photo_has_gps = photo_data.exif_gps is not None
        supp_has_gps = supplemental_data.exif_gps is not None if supplemental_data else False
        
        if photo_has_gps and supp_has_gps:
            gps_match = _compare_gps(photo_data.exif_gps, supplemental_data.exif_gps)
            if gps_match:
                gps_both_match += 1
            else:
                gps_both_none += 1
        elif photo_has_gps:
            gps_media_only += 1
        elif supp_has_gps:
            gps_supplemental_only += 1
        else:
            gps_both_none += 1
    
    # DateTimeの統計を直接計算
    datetime_both_match = 0
    datetime_media_only = 0
    datetime_supplemental_only = 0
    datetime_both_none = 0
    
    for hash_filename in photo_dict.keys():
        photo_data = photo_dict[hash_filename]
        supplemental_data = supplemental_dict.get(hash_filename)
        
        photo_has_datetime = photo_data.exif_datetime is not None
        supp_has_datetime = supplemental_data.exif_datetime is not None if supplemental_data else False
        
        if photo_has_datetime and supp_has_datetime:
            datetime_match = _compare_datetime(photo_data.exif_datetime, supplemental_data.exif_datetime)
            if datetime_match:
                datetime_both_match += 1
            else:
                datetime_both_none += 1
        elif photo_has_datetime:
            datetime_media_only += 1
        elif supp_has_datetime:
            datetime_supplemental_only += 1
        else:
            datetime_both_none += 1
    
    print(f"{'GPS':<8} {gps_both_match:<10} {gps_media_only:<12} {gps_supplemental_only:<18} {gps_both_none:<10}")
    print(f"{'DateTime':<8} {datetime_both_match:<10} {datetime_media_only:<12} {datetime_supplemental_only:<18} {datetime_both_none:<10}")
    
    print()
    print(f"Total files: {total_files}")
    print(f"Media files: {image_video_files}")
    
    # 3種類の2x2表を表示
    
    # 1. Photoデータのみの場合
    print("\n【Photo Data Only】")
    print()
    photo_gps_has_datetime_has = 0
    photo_gps_has_datetime_none = 0
    photo_gps_none_datetime_has = 0
    photo_gps_none_datetime_none = 0
    
    for hash_filename in photo_dict.keys():
        photo_data = photo_dict[hash_filename]
        file_type = get_file_type(hash_filename, image_extensions, video_extensions)
        
        if file_type in ['画像', '動画']:
            photo_has_gps = photo_data.exif_gps is not None
            photo_has_datetime = photo_data.exif_datetime is not None
            
            if photo_has_gps and photo_has_datetime:
                photo_gps_has_datetime_has += 1
            elif photo_has_gps and not photo_has_datetime:
                photo_gps_has_datetime_none += 1
            elif not photo_has_gps and photo_has_datetime:
                photo_gps_none_datetime_has += 1
            else:
                photo_gps_none_datetime_none += 1
    
    print(f"{'':<12} {'DateTimeあり':<12} {'DateTimeなし':<12}")
    print("-" * 40)
    print(f"{'GPSあり':<12} {photo_gps_has_datetime_has:<12} {photo_gps_has_datetime_none:<12}")
    print(f"{'GPSなし':<12} {photo_gps_none_datetime_has:<12} {photo_gps_none_datetime_none:<12}")
    
    # 2. Supplementalだけの場合
    print("\n【Supplemental Data Only】")
    print()
    supp_gps_has_datetime_has = 0
    supp_gps_has_datetime_none = 0
    supp_gps_none_datetime_has = 0
    supp_gps_none_datetime_none = 0
    
    for hash_filename in photo_dict.keys():
        photo_data = photo_dict[hash_filename]
        supplemental_data = supplemental_dict.get(hash_filename)
        file_type = get_file_type(hash_filename, image_extensions, video_extensions)
        
        if file_type in ['画像', '動画'] and supplemental_data is not None:
            supp_has_gps = supplemental_data.exif_gps is not None
            supp_has_datetime = supplemental_data.exif_datetime is not None
            
            if supp_has_gps and supp_has_datetime:
                supp_gps_has_datetime_has += 1
            elif supp_has_gps and not supp_has_datetime:
                supp_gps_has_datetime_none += 1
            elif not supp_has_gps and supp_has_datetime:
                supp_gps_none_datetime_has += 1
            else:
                supp_gps_none_datetime_none += 1
    
    print(f"{'':<12} {'DateTimeあり':<12} {'DateTimeなし':<12}")
    print("-" * 40)
    print(f"{'GPSあり':<12} {supp_gps_has_datetime_has:<12} {supp_gps_has_datetime_none:<12}")
    print(f"{'GPSなし':<12} {supp_gps_none_datetime_has:<12} {supp_gps_none_datetime_none:<12}")
    
    # 3. 両方のどっちかがあればよい場合
    print("\n【Either Photo or Supplemental】")
    print()
    either_gps_has_datetime_has = 0
    either_gps_has_datetime_none = 0
    either_gps_none_datetime_has = 0
    either_gps_none_datetime_none = 0
    
    for hash_filename in photo_dict.keys():
        photo_data = photo_dict[hash_filename]
        supplemental_data = supplemental_dict.get(hash_filename)
        file_type = get_file_type(hash_filename, image_extensions, video_extensions)
        
        if file_type in ['画像', '動画']:
            photo_has_gps = photo_data.exif_gps is not None
            photo_has_datetime = photo_data.exif_datetime is not None
            supp_has_gps = supplemental_data.exif_gps is not None if supplemental_data else False
            supp_has_datetime = supplemental_data.exif_datetime is not None if supplemental_data else False
            
            # どちらかがあればよい
            has_gps = photo_has_gps or supp_has_gps
            has_datetime = photo_has_datetime or supp_has_datetime
            
            if has_gps and has_datetime:
                either_gps_has_datetime_has += 1
            elif has_gps and not has_datetime:
                either_gps_has_datetime_none += 1
            elif not has_gps and has_datetime:
                either_gps_none_datetime_has += 1
            else:
                either_gps_none_datetime_none += 1
    
    print(f"{'':<12} {'DateTimeあり':<12} {'DateTimeなし':<12}")
    print("-" * 40)
    print(f"{'GPSあり':<12} {either_gps_has_datetime_has:<12} {either_gps_has_datetime_none:<12}")
    print(f"{'GPSなし':<12} {either_gps_none_datetime_has:<12} {either_gps_none_datetime_none:<12}")
    
    # 日時もGPSもないファイルの上位10個を表示
    print("\n【Top 10 files with no datetime and no GPS in both files】")
    print()
    
    no_metadata_files = []
    for hash_filename in photo_dict.keys():
        photo_data = photo_dict[hash_filename]
        supplemental_data = supplemental_dict.get(hash_filename)
        file_type = get_file_type(hash_filename, image_extensions, video_extensions)
        
        if file_type in ['画像', '動画']:
            photo_has_gps = photo_data.exif_gps is not None
            photo_has_datetime = photo_data.exif_datetime is not None
            supp_has_gps = supplemental_data.exif_gps is not None if supplemental_data else False
            supp_has_datetime = supplemental_data.exif_datetime is not None if supplemental_data else False
            
            # 両方ともGPSとDateTimeがない場合
            if not photo_has_gps and not photo_has_datetime and not supp_has_gps and not supp_has_datetime:
                no_metadata_files.append({
                    'hash_filename': hash_filename,
                    'file_type': file_type
                })
    
    # 上位10個を表示
    top_10 = no_metadata_files[:10]
    if top_10:
        print(f"{'Rank':<4} {'Output Path':<60} {'File Type':<8}")
        print("-" * 80)
        for i, file_info in enumerate(top_10, 1):
            output_path = f"output/images/{file_info['hash_filename']}"
            print(f"{i:<4} {output_path:<60} {file_info['file_type']:<8}")
    else:
        print("No files found with missing datetime and GPS in both files.")
    
    # 日時不明ファイルのコピー処理
    print("\n" + "=" * 60)
    print("日時不明ファイルのコピー処理を開始します...")
    copy_unknown_datetime_files(photo_metadata, supplemental_metadata, hash_to_pair, image_extensions, video_extensions)


if __name__ == "__main__":
    main()
