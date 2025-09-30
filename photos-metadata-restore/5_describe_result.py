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


def format_gps_info(gps: Optional[GPSData]) -> str:
    """GPS情報をフォーマットする"""
    if gps is None:
        return "なし"
    lat_str = f"{gps.latitude:.6f}"
    lon_str = f"{gps.longitude:.6f}"
    alt_str = f"{gps.altitude:.1f}m" if gps.altitude is not None else "不明"
    return f"緯度: {lat_str}, 経度: {lon_str}, 高度: {alt_str}"


def format_datetime(dt: Optional[datetime]) -> str:
    """日時をフォーマットする"""
    if dt is None:
        return "なし"
    return dt.strftime("%Y年%m月%d日 %H:%M")


def generate_report(categories: Dict[str, List[Dict]], total_files: int, image_video_files: int) -> str:
    """レポートを生成する（Markdown形式）"""
    
    report_lines = []
    report_lines.append("# 写真・動画メタデータ比較レポート")
    report_lines.append("")
    report_lines.append(f"**生成日時:** {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
    report_lines.append("")
    
    # 統計情報
    report_lines.append("## 統計情報")
    report_lines.append("")
    report_lines.append(f"- **総ファイル数:** {total_files}")
    report_lines.append(f"- **画像・動画ファイル数:** {image_video_files}")
    report_lines.append("")
    
    # 2x4表形式の統計
    report_lines.append("## 2x4分類表")
    report_lines.append("")
    report_lines.append("| 項目 | 両方一致 | ファイルのみ | supplementalのみ | 両方なし |")
    report_lines.append("|------|----------|-------------|------------------|----------|")
    
    # 各行の統計を計算
    row_stats = {}
    for row_prefix in ["GPSあり", "日時あり"]:
        row_stats[row_prefix] = {
            "両方一致": len(categories.get(f"{row_prefix}_両方一致", [])),
            "ファイルのみ": len(categories.get(f"{row_prefix}_ファイルのみ", [])),
            "supplementalのみ": len(categories.get(f"{row_prefix}_supplementalのみ", [])),
            "両方なし": len(categories.get(f"{row_prefix}_両方なし", []))
        }
    
    # 表の各行を出力
    for row_name, stats in row_stats.items():
        report_lines.append(f"| {row_name} | {stats['両方一致']} | {stats['ファイルのみ']} | {stats['supplementalのみ']} | {stats['両方なし']} |")
    
    report_lines.append("")
    
    # 分類別の詳細統計
    report_lines.append("## 分類別詳細統計")
    report_lines.append("")
    for category, files in categories.items():
        count = len(files)
        if count > 0:
            report_lines.append(f"- **{category}:** {count}ファイル")
    report_lines.append("")
    
    # 各分類の詳細
    for category, files in categories.items():
        if not files:
            continue
            
        report_lines.append(f"## {category}")
        report_lines.append("")
        report_lines.append(f"**件数:** {len(files)}ファイル")
        report_lines.append("")
        
        # 画像・動画ファイルのみを対象とする
        media_files = [f for f in files if f['file_type'] in ['画像', '動画']]
        
        if not media_files:
            report_lines.append("該当する画像・動画ファイルはありません。")
            report_lines.append("")
            continue
        
        for i, file_info in enumerate(media_files, 1):
            report_lines.append(f"### ファイル{i}")
            report_lines.append("")
            report_lines.append(f"**元ファイル名:** {file_info['original_filename']}")
            report_lines.append("")
            report_lines.append(f"**ファイルタイプ:** {file_info['file_type']}")
            report_lines.append("")
            
            # 2列比較表示
            report_lines.append("| 項目 | Photoメタデータ | Supplementalメタデータ |")
            report_lines.append("|------|-----------------|------------------------|")
            
            # GPS情報
            photo_gps = format_gps_info(file_info['photo'].exif_gps)
            supp_gps = format_gps_info(file_info['supplemental'].exif_gps if file_info['supplemental'] else None)
            report_lines.append(f"| GPS情報 | {photo_gps} | {supp_gps} |")
            
            # 日時情報
            photo_dt = format_datetime(file_info['photo'].exif_datetime)
            supp_dt = format_datetime(file_info['supplemental'].exif_datetime if file_info['supplemental'] else None)
            report_lines.append(f"| 撮影日時 | {photo_dt} | {supp_dt} |")
            
            report_lines.append("")
    
    return "\n".join(report_lines)


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
    
    # メタデータを比較
    print("メタデータを比較中...")
    categories, total_files, image_video_files = compare_metadata(
        photo_metadata, supplemental_metadata, hash_to_pair, image_extensions, video_extensions
    )
    
    # レポートを生成
    print("レポートを生成中...")
    report = generate_report(categories, total_files, image_video_files)
    
    # レポートを保存
    output_path = "output/metadata_comparison_report.md"
    os.makedirs("output", exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"レポートを {output_path} に保存しました。")
    
    # 簡易統計を表示
    print("\n【2x4 Classification Table】")
    print()
    
    # ヘッダー行
    print(f"{'Item':<8} {'Both Match':<10} {'Media Only':<12} {'Supplemental Only':<18} {'Both None':<10}")
    print("-" * 60)
    
    # 各行の統計を計算して表示
    for row_prefix in ["GPSあり", "日時あり"]:
        stats = {
            "両方一致": len(categories.get(f"{row_prefix}_両方一致", [])),
            "ファイルのみ": len(categories.get(f"{row_prefix}_ファイルのみ", [])),
            "supplementalのみ": len(categories.get(f"{row_prefix}_supplementalのみ", [])),
            "両方なし": len(categories.get(f"{row_prefix}_両方なし", []))
        }
        display_name = row_prefix.replace("GPSあり", "GPS").replace("日時あり", "DateTime")
        print(f"{display_name:<8} {stats['両方一致']:<10} {stats['ファイルのみ']:<12} {stats['supplementalのみ']:<18} {stats['両方なし']:<10}")
    
    print()
    print(f"Total files: {total_files}")
    print(f"Media files: {image_video_files}")


if __name__ == "__main__":
    main()
