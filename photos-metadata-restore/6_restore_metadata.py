#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
メタデータを復元して画像ファイルに書き込むスクリプト
"""

import datetime
import json
import os
import pickle
import multiprocessing
from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

import exiftool
from alive_progress import alive_bar
from loguru import logger

from utils.exif_utils import GPSData, PhotoMetadata




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


def write_exif_data(
    image_path: Path,
    datetime_to_write: Optional[datetime.datetime],
    gps_to_write: Optional[GPSData],
) -> bool:
    """画像ファイルにEXIFデータを書き込む"""
    with exiftool.ExifTool() as et:
            # 日時データの書き込み
            if datetime_to_write:
                datetime_str = datetime_to_write.strftime("%Y:%m:%d %H:%M:%S")
                # EXIFデータの書き込み
                et.execute(
                    f"-EXIF:DateTime={datetime_str}",
                    f"-EXIF:DateTimeOriginal={datetime_str}",
                    f"-EXIF:DateTimeDigitized={datetime_str}",
                    str(image_path),
                )

            # GPSデータの書き込み
            if gps_to_write:
                # 緯度・経度を度分秒形式に変換
                lat_deg, lat_min, lat_sec = _decimal_to_dms(gps_to_write.latitude)
                lon_deg, lon_min, lon_sec = _decimal_to_dms(gps_to_write.longitude)

                lat_ref = "N" if gps_to_write.latitude >= 0 else "S"
                lon_ref = "E" if gps_to_write.longitude >= 0 else "W"

                et.execute(
                    f"-EXIF:GPSLatitude={lat_deg}deg {lat_min}' {lat_sec:.2f}\"",
                    f"-EXIF:GPSLatitudeRef={lat_ref}",
                    f"-EXIF:GPSLongitude={lon_deg}deg {lon_min}' {lon_sec:.2f}\"",
                    f"-EXIF:GPSLongitudeRef={lon_ref}",
                    str(image_path),
                )

                # 高度の書き込み
                if gps_to_write.altitude is not None:
                    et.execute(
                        f"-EXIF:GPSAltitude={gps_to_write.altitude}",
                        f"-EXIF:GPSAltitudeRef=0",  # 0 = above sea level
                        str(image_path),
                    )

    return True


def _decimal_to_dms(decimal_deg: float) -> Tuple[int, int, float]:
    """10進数度を度分秒に変換する"""
    degrees = int(abs(decimal_deg))
    minutes_float = (abs(decimal_deg) - degrees) * 60
    minutes = int(minutes_float)
    seconds = (minutes_float - minutes) * 60
    return degrees, minutes, seconds


def restore_metadata_for_image(
    filename: str,
    photo_data: PhotoMetadata,
    supplemental_data: Optional[PhotoMetadata],
    output_path: Path,
) -> None:
    """単一画像のメタデータ復元を実行する"""
    image_path = output_path / "images" / filename

    
    # 日時情報の復元（photoデータを優先、なければsupplementalデータを使用）
    if photo_data.exif_datetime is not None and photo_data.exif_gps is not None:
        # 両方存在するのでスキップ
        return
    # 復元する情報を決定
    datetime_to_restore = None
    gps_to_restore = None
    
    if photo_data.exif_datetime is None:
        datetime_to_restore = supplemental_data.exif_datetime
    
    if photo_data.exif_gps is None:
        gps_to_restore = supplemental_data.exif_gps
   
    # EXIFデータを書き込み
    if datetime_to_restore or gps_to_restore:
        write_exif_data(image_path, datetime_to_restore, gps_to_restore)

    # 日時情報がない写真は隔離する
    if datetime_to_restore is None:
        shutil.move(image_path, output_path / "images" / "no_datetime" / filename)
        return


def process_single_image(args):
    """単一画像の処理（並列処理用）"""
    filename, photo_data, supplemental_data, output_path = args
    restore_metadata_for_image(filename, photo_data, supplemental_data, output_path)
    return filename


def process_all_images(
    photo_metadata: List[PhotoMetadata], 
    supplemental_metadata: List[PhotoMetadata], 
    output_path: Path,
    max_workers: Optional[int] = None
) -> None:
    """すべての画像ファイルのメタデータ復元を実行する（並列処理）"""
    # ハッシュでインデックス化
    photo_dict = {m.file_name: m for m in photo_metadata}
    supplemental_dict = {m.file_name: m for m in supplemental_metadata}
    
    total_files = len(photo_dict)
    
    if max_workers is None:
        max_workers = multiprocessing.cpu_count() * 2  # I/OバウンドなのでCPUコア数の2倍

    logger.info(f"🔧 {total_files}個の画像ファイルのメタデータ復元を開始します... (並列処理: {max_workers}スレッド)")

    # 並列処理用の引数を準備
    args_list = []
    for filename, photo_data in photo_dict.items():
        supplemental_data = supplemental_dict.get(filename)
        args_list.append((filename, photo_data, supplemental_data, output_path))

    with alive_bar(
        total_files, title="📸 メタデータ復元中 (並列)", bar="smooth", spinner="dots_waves"
    ) as bar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 並列処理を実行
            futures = [executor.submit(process_single_image, args) for args in args_list]
            
            for future in futures:
                filename = future.result()
                bar.text = f"✅ 復元完了: {filename}"
                bar()


def generate_summary_report(output_path: Path):
    """復元結果のサマリーレポートを生成する"""
    logger.info("\n" + "=" * 60)
    logger.info("📊 メタデータ復元完了")
    logger.info("=" * 60)
    logger.info("✅ すべてのファイルのメタデータ復元が完了しました")


def main():
    """メイン関数"""
    # ベースディレクトリのパスを設定
    script_dir = Path(__file__).parent
    base_path = script_dir
    output_path = base_path / "output"

    # バリデーション
    assert base_path.exists(), f"ディレクトリ '{base_path}' が存在しません"
    assert output_path.exists(), f"outputディレクトリが存在しません: {output_path}"

    logger.info("🚀 メタデータ復元を開始します")

    # メタデータファイルを読み込み
    photo_metadata, supplemental_metadata = load_metadata()
    
    logger.info(f"📖 メタデータを読み込みました")
    logger.info(f"  - photo_metadata: {len(photo_metadata)}件")
    logger.info(f"  - supplemental_metadata: {len(supplemental_metadata)}件")

    # すべての画像ファイルのメタデータ復元を実行
    process_all_images(photo_metadata, supplemental_metadata, output_path)

    # サマリーレポートを生成
    generate_summary_report(output_path)

    logger.info("✅ メタデータ復元が完了しました")


if __name__ == "__main__":
    main()
