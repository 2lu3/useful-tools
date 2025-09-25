#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
メタデータを復元して画像ファイルに書き込むスクリプト
"""

import datetime
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import exiftool
from alive_progress import alive_bar
from loguru import logger

from utils.exif_utils import GPSData


@dataclass
class RestoreResult:
    """復元結果を管理するdataclass"""

    filename: str
    success: bool
    restored_datetime: bool = False
    restored_gps: bool = False
    conflicts: List[str] = None
    missing_info: List[str] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.conflicts is None:
            self.conflicts = []
        if self.missing_info is None:
            self.missing_info = []


def load_json_files(
    output_path: Path,
) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]:
    """必要なJSONファイルを読み込む"""
    metadata_file = output_path / "metadata.json"
    metadata_location_file = output_path / "metadata_location.json"
    pair_file = output_path / "pair.json"

    # ファイルの存在確認
    assert metadata_file.exists(), f"metadata.jsonが見つかりません: {metadata_file}"
    assert (
        metadata_location_file.exists()
    ), f"metadata_location.jsonが見つかりません: {metadata_location_file}"
    assert pair_file.exists(), f"pair.jsonが見つかりません: {pair_file}"

    # JSONファイルを読み込み
    with open(metadata_file, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    with open(metadata_location_file, "r", encoding="utf-8") as f:
        metadata_location = json.load(f)

    with open(pair_file, "r", encoding="utf-8") as f:
        pair_data = json.load(f)

    logger.info(f"📖 JSONファイルを読み込みました")
    logger.info(f"  - metadata.json: {len(metadata)}件")
    logger.info(f"  - metadata_location.json: {len(metadata_location)}件")
    logger.info(f"  - pair.json: {len(pair_data)}件")

    return metadata, metadata_location, pair_data


def load_supplemental_metadata(metadata_file_path: Path) -> Optional[Dict[str, Any]]:
    """supplemental-metadata.jsonファイルを読み込む"""
    try:
        with open(metadata_file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(
            f"メタデータファイルの読み込みに失敗: {metadata_file_path} - {e}"
        )
        return None


def parse_google_photos_timestamp(timestamp_str: str) -> Optional[datetime.datetime]:
    """Google Photosのタイムスタンプ文字列をパースする"""
    try:
        # "2018/11/12 3:42:35 UTC" 形式をパース
        if "UTC" in timestamp_str:
            timestamp_str = timestamp_str.replace("UTC", "").strip()
            dt = datetime.datetime.strptime(timestamp_str, "%Y/%m/%d %H:%M:%S")
            # UTCをJSTに変換（+9時間）
            return dt + datetime.timedelta(hours=9)
        return None
    except Exception as e:
        logger.warning(f"タイムスタンプのパースに失敗: {timestamp_str} - {e}")
        return None


def extract_datetime_from_supplemental_metadata(
    supplemental_data: Dict[str, Any],
) -> Optional[datetime.datetime]:
    """supplemental-metadataから撮影日時を抽出する"""
    # photoTakenTimeを優先
    if "photoTakenTime" in supplemental_data:
        photo_taken_time = supplemental_data["photoTakenTime"]
        if "formatted" in photo_taken_time:
            return parse_google_photos_timestamp(photo_taken_time["formatted"])

    # creationTimeをフォールバック
    if "creationTime" in supplemental_data:
        creation_time = supplemental_data["creationTime"]
        if "formatted" in creation_time:
            return parse_google_photos_timestamp(creation_time["formatted"])

    return None


def extract_gps_from_supplemental_metadata(
    supplemental_data: Dict[str, Any],
) -> Optional[GPSData]:
    """supplemental-metadataからGPS情報を抽出する"""
    if "geoData" not in supplemental_data:
        return None

    geo_data = supplemental_data["geoData"]
    latitude = geo_data.get("latitude", 0.0)
    longitude = geo_data.get("longitude", 0.0)
    altitude = geo_data.get("altitude", None)

    # 緯度・経度が0.0の場合は無効とみなす
    if latitude == 0.0 and longitude == 0.0:
        return None

    return GPSData(latitude=latitude, longitude=longitude, altitude=altitude)


def compare_datetime(
    existing_dt: Optional[str], new_dt: Optional[datetime.datetime]
) -> bool:
    """既存の日時と新しい日時を比較する"""
    if existing_dt is None and new_dt is None:
        return True
    if existing_dt is None or new_dt is None:
        return False

    try:
        existing_datetime = datetime.datetime.fromisoformat(
            existing_dt.replace("T", " ")
        )
        # 1分以内の差は同じとみなす
        time_diff = abs((existing_datetime - new_dt).total_seconds())
        return time_diff <= 60
    except Exception:
        return False


def compare_gps(
    existing_gps: Optional[Dict[str, Any]], new_gps: Optional[GPSData]
) -> bool:
    """既存のGPS情報と新しいGPS情報を比較する"""
    if existing_gps is None and new_gps is None:
        return True
    if existing_gps is None or new_gps is None:
        return False

    try:
        existing_lat = existing_gps.get("latitude", 0.0)
        existing_lon = existing_gps.get("longitude", 0.0)
        new_lat = new_gps.latitude
        new_lon = new_gps.longitude

        # 0.0001度以内の差は同じとみなす（約10m以内）
        lat_diff = abs(existing_lat - new_lat)
        lon_diff = abs(existing_lon - new_lon)
        return lat_diff <= 0.0001 and lon_diff <= 0.0001
    except Exception:
        return False


def write_exif_data(
    image_path: Path,
    datetime_to_write: Optional[datetime.datetime],
    gps_to_write: Optional[GPSData],
) -> bool:
    """画像ファイルにEXIFデータを書き込む"""
    try:
        with exiftool.ExifTool() as et:
            # 日時データの書き込み
            if datetime_to_write:
                datetime_str = datetime_to_write.strftime("%Y:%m:%d %H:%M:%S")
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
    except Exception as e:
        logger.error(f"EXIFデータの書き込みに失敗: {image_path} - {e}")
        return False


def _decimal_to_dms(decimal_deg: float) -> Tuple[int, int, float]:
    """10進数度を度分秒に変換する"""
    degrees = int(abs(decimal_deg))
    minutes_float = (abs(decimal_deg) - degrees) * 60
    minutes = int(minutes_float)
    seconds = (minutes_float - minutes) * 60
    return degrees, minutes, seconds


def restore_metadata_for_image(
    filename: str,
    image_metadata: Dict[str, Any],
    metadata_location_info: Dict[str, Any],
    output_path: Path,
) -> RestoreResult:
    """単一画像のメタデータ復元を実行する"""
    result = RestoreResult(filename=filename, success=False)

    try:
        image_path = output_path / "images" / filename

        # ファイルの存在確認
        if not image_path.exists():
            result.error_message = f"画像ファイルが存在しません: {image_path}"
            return result

        # supplemental-metadataファイルから情報を取得
        supplemental_data = None
        if metadata_location_info.get("found", False):
            metadata_file_path = Path(metadata_location_info["metadata_file"])
            supplemental_data = load_supplemental_metadata(metadata_file_path)

        # 復元する情報を決定
        datetime_to_restore = None
        gps_to_restore = None

        # 日時情報の復元
        if supplemental_data:
            supplemental_datetime = extract_datetime_from_supplemental_metadata(
                supplemental_data
            )
            existing_datetime = image_metadata.get("exif_datetime")

            if supplemental_datetime:
                if existing_datetime and not compare_datetime(
                    existing_datetime, supplemental_datetime
                ):
                    result.conflicts.append(
                        f"日時が異なります: EXIF={existing_datetime}, メタデータ={supplemental_datetime}"
                    )
                else:
                    datetime_to_restore = supplemental_datetime
                    result.restored_datetime = True
            elif not existing_datetime:
                result.missing_info.append("日時情報が不足しています")
        elif not image_metadata.get("exif_datetime"):
            result.missing_info.append("日時情報が不足しています")

        # GPS情報の復元
        if supplemental_data:
            supplemental_gps = extract_gps_from_supplemental_metadata(supplemental_data)
            existing_gps = image_metadata.get("gps_data")

            if supplemental_gps:
                if existing_gps and not compare_gps(existing_gps, supplemental_gps):
                    result.conflicts.append(
                        f"GPS情報が異なります: EXIF={existing_gps}, メタデータ={supplemental_gps}"
                    )
                else:
                    gps_to_restore = supplemental_gps
                    result.restored_gps = True
            elif not existing_gps:
                result.missing_info.append("GPS情報が不足しています")
        elif not image_metadata.get("gps_data"):
            result.missing_info.append("GPS情報が不足しています")

        # EXIFデータを書き込み
        if datetime_to_restore or gps_to_restore:
            success = write_exif_data(image_path, datetime_to_restore, gps_to_restore)
            if success:
                result.success = True
            else:
                result.error_message = "EXIFデータの書き込みに失敗しました"
        else:
            # 復元する情報がない場合は成功とする
            result.success = True

    except Exception as e:
        result.error_message = f"予期しないエラー: {e}"
        logger.error(f"メタデータ復元中にエラー: {filename} - {e}")

    return result


def process_all_images(
    metadata: Dict[str, Any], metadata_location: Dict[str, Any], output_path: Path
) -> List[RestoreResult]:
    """すべての画像ファイルのメタデータ復元を実行する"""
    results = []
    total_files = len(metadata)

    logger.info(f"🔧 {total_files}個の画像ファイルのメタデータ復元を開始します...")

    with alive_bar(
        total_files, title="📸 メタデータ復元中", bar="smooth", spinner="dots_waves"
    ) as bar:
        for filename, image_metadata in metadata.items():
            bar.text = f"🔧 復元中: {filename}"

            metadata_location_info = metadata_location.get(filename, {})
            result = restore_metadata_for_image(
                filename, image_metadata, metadata_location_info, output_path
            )
            results.append(result)

            # プログレスバーのテキストを更新
            if result.success:
                restored_items = []
                if result.restored_datetime:
                    restored_items.append("📅日時")
                if result.restored_gps:
                    restored_items.append("📍GPS")

                if restored_items:
                    bar.text = f"✅ 復元完了: {','.join(restored_items)} - {filename}"
                else:
                    bar.text = f"ℹ️  復元不要: {filename}"
            else:
                bar.text = f"❌ 復元失敗: {filename}"

            bar()

    return results


def generate_summary_report(results: List[RestoreResult], output_path: Path):
    """復元結果のサマリーレポートを生成する"""
    total_files = len(results)
    successful_restorations = sum(1 for r in results if r.success)
    failed_restorations = total_files - successful_restorations

    # 復元された情報の統計
    datetime_restored = sum(1 for r in results if r.restored_datetime)
    gps_restored = sum(1 for r in results if r.restored_gps)

    # コンフリクトと不足情報の統計
    files_with_conflicts = sum(1 for r in results if r.conflicts)
    files_with_missing_info = sum(1 for r in results if r.missing_info)

    # コンソールにサマリーを表示
    logger.info("\n" + "=" * 60)
    logger.info("📊 メタデータ復元結果")
    logger.info("=" * 60)
    logger.info(f"📁 総ファイル数: {total_files}")
    logger.info(f"✅ 復元成功: {successful_restorations}")
    logger.info(f"❌ 復元失敗: {failed_restorations}")
    logger.info(f"📅 日時復元: {datetime_restored}")
    logger.info(f"📍 GPS復元: {gps_restored}")
    logger.info(f"⚠️  コンフリクトあり: {files_with_conflicts}")
    logger.info(f"❓ 情報不足: {files_with_missing_info}")

    # result.txtファイルを生成
    result_file = output_path / "result.txt"
    with open(result_file, "w", encoding="utf-8") as f:
        f.write("メタデータ復元結果\n")
        f.write("=" * 50 + "\n")
        f.write(f"実行日時: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"総ファイル数: {total_files}\n")
        f.write(f"復元成功: {successful_restorations}\n")
        f.write(f"復元失敗: {failed_restorations}\n")
        f.write(f"日時復元: {datetime_restored}\n")
        f.write(f"GPS復元: {gps_restored}\n")
        f.write(f"コンフリクトあり: {files_with_conflicts}\n")
        f.write(f"情報不足: {files_with_missing_info}\n\n")

        # コンフリクトがあるファイルの詳細
        if files_with_conflicts > 0:
            f.write("⚠️ コンフリクトがあるファイル:\n")
            f.write("-" * 40 + "\n")
            for result in results:
                if result.conflicts:
                    f.write(f"ファイル: {result.filename}\n")
                    for conflict in result.conflicts:
                        f.write(f"  - {conflict}\n")
                    f.write("\n")

        # 情報が不足しているファイルの詳細
        if files_with_missing_info > 0:
            f.write("❓ 情報が不足しているファイル:\n")
            f.write("-" * 40 + "\n")
            for result in results:
                if result.missing_info:
                    f.write(f"ファイル: {result.filename}\n")
                    for missing in result.missing_info:
                        f.write(f"  - {missing}\n")
                    f.write("\n")

        # 復元に失敗したファイルの詳細
        if failed_restorations > 0:
            f.write("❌ 復元に失敗したファイル:\n")
            f.write("-" * 40 + "\n")
            for result in results:
                if not result.success:
                    f.write(f"ファイル: {result.filename}\n")
                    if result.error_message:
                        f.write(f"  エラー: {result.error_message}\n")
                    f.write("\n")

    logger.info(f"💾 詳細結果を保存しました: {result_file}")


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

    # JSONファイルを読み込み
    metadata, metadata_location, pair_data = load_json_files(output_path)

    # すべての画像ファイルのメタデータ復元を実行
    results = process_all_images(metadata, metadata_location, output_path)

    # サマリーレポートを生成
    generate_summary_report(results, output_path)

    logger.info("✅ メタデータ復元が完了しました")


if __name__ == "__main__":
    main()
