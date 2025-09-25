#!/usr/bin/env python3
"""
メタデータを復元するスクリプト
"""

import json
import os
from pathlib import Path
from datetime import datetime
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# PILの代替として、基本的な画像処理のみ実装
try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    import piexif
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL/piexifが利用できません。メタデータの復元は制限されます。")

def load_json_file(file_path):
    """JSONファイルを読み込み"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"JSONファイル読み込みエラー {file_path}: {e}")
        return None

def parse_datetime_string(dt_str):
    """日時文字列をパース"""
    if not dt_str:
        return None
    
    # ISO形式の日時をパース
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except ValueError:
        # EXIF形式の日時をパース
        try:
            return datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
        except ValueError:
            logger.warning(f"日時パースエラー: {dt_str}")
            return None

def create_gps_ifd(latitude, longitude, altitude=None):
    """GPS情報のIFDを作成"""
    def deg_to_dms(deg):
        d = int(deg)
        m = int((deg - d) * 60)
        s = (deg - d - m/60) * 3600
        return (d, 1), (m, 1), (int(s * 100), 100)
    
    lat_dms = deg_to_dms(abs(latitude))
    lon_dms = deg_to_dms(abs(longitude))
    
    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: 'S' if latitude < 0 else 'N',
        piexif.GPSIFD.GPSLatitude: lat_dms,
        piexif.GPSIFD.GPSLongitudeRef: 'W' if longitude < 0 else 'E',
        piexif.GPSIFD.GPSLongitude: lon_dms,
    }
    
    if altitude is not None:
        gps_ifd[piexif.GPSIFD.GPSAltitude] = (int(altitude * 100), 100)
        gps_ifd[piexif.GPSIFD.GPSAltitudeRef] = 0  # 0 = above sea level
    
    return gps_ifd

def restore_metadata_to_image(image_path, metadata_info, pair_info, location_info):
    """画像にメタデータを復元"""
    if not PIL_AVAILABLE:
        return {
            "datetime_restored": False,
            "location_restored": False,
            "success": False,
            "reason": "PIL/piexifが利用できません"
        }
        
    try:
        # 画像を開く
        image = Image.open(image_path)
        
        # 既存のEXIFデータを取得
        exif_dict = piexif.load(image.info.get('exif', b'')) if image.info.get('exif') else {'0th': {}, 'Exif': {}, 'GPS': {}, '1st': {}, 'thumbnail': None}
        
        # 日時情報の復元
        datetime_restored = False
        if metadata_info.get("datetime"):
            datetime_data = metadata_info["datetime"]
            
            # 最適な日時を選択
            best_datetime = None
            for key in ['exif_datetime_original', 'exif_datetime', 'json_datetime', 'file_creation_time']:
                if key in datetime_data and datetime_data[key]:
                    best_datetime = parse_datetime_string(datetime_data[key])
                    if best_datetime:
                        break
            
            if best_datetime:
                # EXIF日時フォーマットに変換
                exif_datetime = best_datetime.strftime("%Y:%m:%d %H:%M:%S")
                exif_dict['0th'][piexif.ImageIFD.DateTime] = exif_datetime
                exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = exif_datetime
                exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = exif_datetime
                datetime_restored = True
        
        # 位置情報の復元
        location_restored = False
        if metadata_info.get("location") and metadata_info["location"].get("latitude") and metadata_info["location"].get("longitude"):
            lat = metadata_info["location"]["latitude"]
            lon = metadata_info["location"]["longitude"]
            alt = metadata_info["location"].get("altitude")
            
            gps_ifd = create_gps_ifd(lat, lon, alt)
            exif_dict['GPS'] = gps_ifd
            location_restored = True
        
        # メタデータファイルからの追加情報
        if location_info.get("found") and location_info.get("metadata_file"):
            metadata_file_path = Path(location_info["metadata_file"])
            if metadata_file_path.exists():
                try:
                    with open(metadata_file_path, 'r', encoding='utf-8') as f:
                        external_metadata = json.load(f)
                    
                    # 外部メタデータから追加の日時情報を取得
                    if not datetime_restored and isinstance(external_metadata, dict):
                        for key, value in external_metadata.items():
                            if 'datetime' in key.lower() and isinstance(value, str):
                                dt = parse_datetime_string(value)
                                if dt:
                                    exif_datetime = dt.strftime("%Y:%m:%d %H:%M:%S")
                                    exif_dict['0th'][piexif.ImageIFD.DateTime] = exif_datetime
                                    exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = exif_datetime
                                    datetime_restored = True
                                    break
                    
                    # 外部メタデータから追加の位置情報を取得
                    if not location_restored and isinstance(external_metadata, dict):
                        if 'latitude' in external_metadata and 'longitude' in external_metadata:
                            lat = external_metadata['latitude']
                            lon = external_metadata['longitude']
                            alt = external_metadata.get('altitude')
                            
                            gps_ifd = create_gps_ifd(lat, lon, alt)
                            exif_dict['GPS'] = gps_ifd
                            location_restored = True
                            
                except Exception as e:
                    logger.warning(f"外部メタデータ読み込みエラー {metadata_file_path}: {e}")
        
        # EXIFデータを画像に埋め込み
        if datetime_restored or location_restored:
            exif_bytes = piexif.dump(exif_dict)
            
            # 画像を保存（EXIFデータ付き）
            if image.mode in ('RGBA', 'LA'):
                image = image.convert('RGB')
            
            image.save(image_path, exif=exif_bytes, quality=95)
            
            return {
                "datetime_restored": datetime_restored,
                "location_restored": location_restored,
                "success": True
            }
        else:
            return {
                "datetime_restored": False,
                "location_restored": False,
                "success": False,
                "reason": "復元可能なメタデータなし"
            }
            
    except Exception as e:
        logger.error(f"メタデータ復元エラー {image_path}: {e}")
        return {
            "datetime_restored": False,
            "location_restored": False,
            "success": False,
            "reason": f"エラー: {str(e)}"
        }

def main():
    output_dir = Path("/workspace/photos-metadata-restore/output")
    images_dir = output_dir / "images"
    
    # 必要なファイルの存在確認
    pair_file = output_dir / "pair.json"
    metadata_file = output_dir / "metadata.json"
    location_file = output_dir / "metadata_location.json"
    
    for file_path in [pair_file, metadata_file, location_file]:
        if not file_path.exists():
            logger.error(f"必要なファイルが存在しません: {file_path}")
            return
    
    # データを読み込み
    pair_data = load_json_file(pair_file)
    metadata_data = load_json_file(metadata_file)
    location_data = load_json_file(location_file)
    
    if not all([pair_data, metadata_data, location_data]):
        logger.error("データの読み込みに失敗しました")
        return
    
    logger.info(f"処理対象の画像ファイル数: {len(pair_data)}")
    
    # メタデータを復元
    results = []
    success_count = 0
    error_count = 0
    datetime_restored_count = 0
    location_restored_count = 0
    
    for i, item in enumerate(pair_data):
        try:
            print(f"復元中: {i+1}/{len(pair_data)} - {item.get('filename', 'unknown')}")
            filename = item["filename"]
            image_path = images_dir / filename
            
            if not image_path.exists():
                logger.warning(f"画像ファイルが存在しません: {image_path}")
                error_count += 1
                continue
            
            # メタデータ情報を取得
            metadata_info = metadata_data.get(filename, {})
            location_info = location_data.get(filename, {})
            
            # メタデータを復元
            result = restore_metadata_to_image(image_path, metadata_info, item, location_info)
            result["filename"] = filename
            result["image_path"] = str(image_path)
            results.append(result)
            
            if result["success"]:
                success_count += 1
                if result["datetime_restored"]:
                    datetime_restored_count += 1
                if result["location_restored"]:
                    location_restored_count += 1
            else:
                error_count += 1
            
        except Exception as e:
            logger.error(f"処理エラー {item.get('filename', 'unknown')}: {e}")
            error_count += 1
    
    # 結果を保存
    result_file = output_dir / "result.txt"
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write("メタデータ復元結果\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"総処理数: {len(pair_data)}\n")
        f.write(f"成功: {success_count}\n")
        f.write(f"エラー: {error_count}\n")
        f.write(f"日時復元: {datetime_restored_count}\n")
        f.write(f"位置復元: {location_restored_count}\n\n")
        
        # 失敗したファイルの詳細
        failed_files = [r for r in results if not r["success"]]
        if failed_files:
            f.write("失敗したファイル:\n")
            f.write("-" * 30 + "\n")
            for result in failed_files:
                f.write(f"ファイル: {result['filename']}\n")
                f.write(f"理由: {result.get('reason', '不明')}\n")
                f.write(f"パス: {result['image_path']}\n\n")
        
        # 部分的な復元
        partial_restored = [r for r in results if r["success"] and (not r["datetime_restored"] or not r["location_restored"])]
        if partial_restored:
            f.write("部分的な復元（情報が不足）:\n")
            f.write("-" * 30 + "\n")
            for result in partial_restored:
                f.write(f"ファイル: {result['filename']}\n")
                f.write(f"日時復元: {result['datetime_restored']}\n")
                f.write(f"位置復元: {result['location_restored']}\n")
                f.write(f"パス: {result['image_path']}\n\n")
    
    # 統計情報を表示
    logger.info(f"処理完了:")
    logger.info(f"  総処理数: {len(pair_data)}")
    logger.info(f"  成功: {success_count}")
    logger.info(f"  エラー: {error_count}")
    logger.info(f"  日時復元: {datetime_restored_count}")
    logger.info(f"  位置復元: {location_restored_count}")
    logger.info(f"結果ファイルを保存しました: {result_file}")

if __name__ == "__main__":
    main()