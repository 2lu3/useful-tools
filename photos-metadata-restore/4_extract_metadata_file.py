#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
見つかったメタデータファイルを読み込んでPhotoMetadataに格納し、
pickleファイルとして保存するスクリプト
"""

import datetime
import json
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional

from alive_progress import alive_bar
from loguru import logger

from utils.exif_utils import PhotoMetadata, GPSData


def load_metadata_location_json(metadata_location_file: Path) -> Dict[str, Any]:
    """supplemental_file_location.jsonファイルを読み込む"""
    with open(metadata_location_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_supplemental_metadata(metadata_file_path: Path) -> Optional[Dict[str, Any]]:
    """supplemental-metadata.jsonファイルを読み込む"""
    with open(metadata_file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_google_photos_timestamp(timestamp_str: str) -> Optional[datetime.datetime]:
    """Google Photosのタイムスタンプ文字列をパースする"""
    # "2018/11/12 3:42:35 UTC" 形式をパース
    if "UTC" in timestamp_str:
        timestamp_str = timestamp_str.replace("UTC", "").strip()
        dt = datetime.datetime.strptime(timestamp_str, "%Y/%m/%d %H:%M:%S")
        # UTCをJSTに変換（+9時間）
        return dt + datetime.timedelta(hours=9)
    return None


def extract_datetime_from_supplemental_metadata(
    supplemental_data: Dict[str, Any],
) -> Optional[datetime.datetime]:
    """supplemental-metadataから撮影日時を抽出する"""
    # photoTakenTimeのみを使用（撮影日時）
    if "photoTakenTime" in supplemental_data:
        photo_taken_time = supplemental_data["photoTakenTime"]
        if "formatted" in photo_taken_time:
            return parse_google_photos_timestamp(photo_taken_time["formatted"])

    return None


def extract_gps_from_supplemental_metadata(
    supplemental_data: Dict[str, Any],
) -> Optional[GPSData]:
    """supplemental-metadataからGPS情報を抽出する"""
    if "geoData" not in supplemental_data:
        return None

    geo_data = supplemental_data["geoData"]
    latitude = geo_data["latitude"]
    longitude = geo_data["longitude"]
    altitude = geo_data["altitude"]

    # 緯度・経度が0.0の場合は無効とみなす
    if latitude == 0.0 and longitude == 0.0:
        return None

    return GPSData(latitude=latitude, longitude=longitude, altitude=altitude)


def process_single_metadata_file(
    filename: str, metadata_location_info: Dict[str, Any]
) -> PhotoMetadata:
    """単一のメタデータファイルを処理してPhotoMetadataを作成する"""
    # 元のファイル名を取得（hashから元のファイル名を推測）
    original_filename = filename

    # supplemental-metadataファイルから情報を取得
    exif_datetime = None
    exif_gps = None

    if metadata_location_info.get("found", False):
        metadata_file_path = Path(metadata_location_info["metadata_file"])
        supplemental_data = load_supplemental_metadata(metadata_file_path)

        if supplemental_data:
            # 日時情報を抽出
            exif_datetime = extract_datetime_from_supplemental_metadata(supplemental_data)

            # GPS情報を抽出
            exif_gps = extract_gps_from_supplemental_metadata(supplemental_data)

    return PhotoMetadata(
        file_name=original_filename,
        exif_datetime=exif_datetime,
        exif_gps=exif_gps,
    )


def process_all_metadata_files(
    metadata_location: Dict[str, Any]
) -> List[PhotoMetadata]:
    """すべてのメタデータファイルを処理してPhotoMetadataのリストを作成する"""
    metadata_list = []
    total_files = len(metadata_location)

    logger.info(f"{total_files}個のメタデータファイルを処理中...")

    with alive_bar(total_files) as bar:
        for filename, metadata_location_info in metadata_location.items():
            metadata = process_single_metadata_file(filename, metadata_location_info)
            metadata_list.append(metadata)
            bar()

    return metadata_list


def save_metadata_to_pickle(metadata_list: List[PhotoMetadata], output_path: Path):
    """PhotoMetadataのリストをpickleファイルとして保存する"""
    metadata_pickle_file = output_path / "supplemental_metadata.pkl"

    with open(metadata_pickle_file, "wb") as f:
        pickle.dump(metadata_list, f)

    logger.info(f"メタデータをpickleファイルに保存しました: {metadata_pickle_file}")




def main():
    """メイン関数"""
    # ベースディレクトリのパスを設定
    script_dir = Path(__file__).parent
    base_path = script_dir
    output_path = base_path / "output"
    metadata_location_file = output_path / "supplemental_file_location.json"

    # バリデーション
    assert base_path.exists(), f"ディレクトリ '{base_path}' が存在しません"
    assert output_path.exists(), f"outputディレクトリが存在しません: {output_path}"
    assert (
        metadata_location_file.exists()
    ), f"supplemental_file_location.jsonファイルが存在しません: {metadata_location_file}"

    logger.info("メタデータ抽出を開始します")

    # supplemental_file_location.jsonを読み込み
    metadata_location = load_metadata_location_json(metadata_location_file)

    # すべてのメタデータファイルを処理
    metadata_list = process_all_metadata_files(metadata_location)

    # pickleファイルに保存
    save_metadata_to_pickle(metadata_list, output_path)


    logger.info("メタデータ抽出が完了しました")


if __name__ == "__main__":
    main()
