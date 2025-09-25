#!/usr/bin/env python3
"""
画像ファイルのメタデータを調査するスクリプト
共通規格に従って実装
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
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PILが利用できません。基本的なファイル情報のみ取得します。")

def get_exif_data(image_path):
    """EXIFデータを取得"""
    if not PIL_AVAILABLE:
        return None
        
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()
        
        if exif_data is None:
            return None
        
        exif_dict = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            exif_dict[tag] = value
        
        return exif_dict
    except Exception as e:
        logger.error(f"EXIFデータ取得エラー {image_path}: {e}")
        return None

def get_datetime_from_exif(exif_data):
    """EXIFから日時情報を取得"""
    datetime_info = {}
    
    if not exif_data:
        return datetime_info
    
    # 日時関連のタグ
    datetime_tags = {
        'DateTime': 'exif_datetime',
        'DateTimeOriginal': 'exif_datetime_original', 
        'DateTimeDigitized': 'exif_datetime_digitized'
    }
    
    for tag, key in datetime_tags.items():
        if tag in exif_data:
            try:
                # EXIFの日時フォーマットをパース
                dt_str = exif_data[tag]
                if isinstance(dt_str, str):
                    # EXIF日時フォーマット: "YYYY:MM:DD HH:MM:SS"
                    dt = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                    datetime_info[key] = dt.isoformat()
            except Exception as e:
                logger.warning(f"日時パースエラー {tag}: {e}")
    
    return datetime_info

def get_location_from_exif(exif_data):
    """EXIFから位置情報を取得"""
    location_info = {}
    
    if not exif_data:
        return location_info
    
    # GPS情報の取得
    if 'GPSInfo' in exif_data:
        gps_info = exif_data['GPSInfo']
        gps_data = {}
        
        for tag_id, value in gps_info.items():
            tag = GPSTAGS.get(tag_id, tag_id)
            gps_data[tag] = value
        
        # 緯度・経度の計算
        if 'GPSLatitude' in gps_data and 'GPSLongitude' in gps_data:
            try:
                lat = convert_to_degrees(gps_data['GPSLatitude'])
                lon = convert_to_degrees(gps_data['GPSLongitude'])
                
                # 南緯・西経の場合は負の値にする
                if gps_data.get('GPSLatitudeRef') == 'S':
                    lat = -lat
                if gps_data.get('GPSLongitudeRef') == 'W':
                    lon = -lon
                
                location_info['latitude'] = lat
                location_info['longitude'] = lon
                location_info['exif_gps'] = True
                
                # 高度情報
                if 'GPSAltitude' in gps_data:
                    altitude = gps_data['GPSAltitude']
                    if isinstance(altitude, tuple):
                        altitude = altitude[0] / altitude[1]
                    location_info['altitude'] = altitude
                    
            except Exception as e:
                logger.warning(f"GPS座標計算エラー: {e}")
    
    return location_info

def convert_to_degrees(value):
    """GPS座標を度に変換"""
    if isinstance(value, tuple) and len(value) == 3:
        d, m, s = value
        return d + (m / 60.0) + (s / 3600.0)
    return value

def get_file_creation_time(file_path):
    """ファイルの作成日時を取得"""
    try:
        stat = os.stat(file_path)
        return datetime.fromtimestamp(stat.st_ctime).isoformat()
    except Exception as e:
        logger.warning(f"ファイル作成日時取得エラー {file_path}: {e}")
        return None

def analyze_image_metadata(image_path):
    """画像のメタデータを分析（共通規格に従う）"""
    result = {
        "datetime": {},
        "location": {},
        "has_datetime": False,
        "has_location": False,
        "metadata_sources": []
    }
    
    # EXIFデータの取得
    exif_data = get_exif_data(image_path)
    if exif_data:
        result["metadata_sources"].append("exif")
        
        # 日時情報
        datetime_info = get_datetime_from_exif(exif_data)
        result["datetime"].update(datetime_info)
        
        # 位置情報
        location_info = get_location_from_exif(exif_data)
        result["location"].update(location_info)
    
    # ファイル作成日時
    file_creation = get_file_creation_time(image_path)
    if file_creation:
        result["datetime"]["file_creation_time"] = file_creation
    
    # 日時情報の有無を判定
    result["has_datetime"] = bool(result["datetime"])
    
    # 位置情報の有無を判定
    result["has_location"] = bool(result["location"])
    
    return result

def main():
    input_dir = Path("/workspace/photos-metadata-restore/input")
    output_dir = Path("/workspace/photos-metadata-restore/output")
    images_dir = output_dir / "images"
    
    # 入力ディレクトリの存在確認
    if not input_dir.exists():
        logger.error(f"入力ディレクトリが存在しません: {input_dir}")
        return
    
    # 出力ディレクトリの存在確認
    if not images_dir.exists():
        logger.error(f"画像ディレクトリが存在しません: {images_dir}")
        return
    
    # 画像ファイルのリストを取得
    image_files = []
    for file_path in images_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.heic', '.heif'}:
            image_files.append(file_path)
    
    logger.info(f"分析対象の画像ファイル数: {len(image_files)}")
    
    # メタデータを分析
    metadata = {}
    success_count = 0
    error_count = 0
    
    for i, image_path in enumerate(image_files):
        try:
            print(f"分析中: {i+1}/{len(image_files)} - {image_path.name}")
            filename = image_path.name
            metadata[filename] = analyze_image_metadata(image_path)
            success_count += 1
            
        except Exception as e:
            logger.error(f"メタデータ分析エラー {image_path}: {e}")
            error_count += 1
    
    # metadata.jsonを保存（共通規格に従う）
    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    # 統計情報を表示
    datetime_count = sum(1 for data in metadata.values() if data.get("has_datetime"))
    location_count = sum(1 for data in metadata.values() if data.get("has_location"))
    
    logger.info(f"処理完了: 成功 {success_count}件, エラー {error_count}件")
    logger.info(f"日時情報あり: {datetime_count}件")
    logger.info(f"位置情報あり: {location_count}件")
    logger.info(f"metadata.jsonを保存しました: {metadata_file}")

if __name__ == "__main__":
    main()