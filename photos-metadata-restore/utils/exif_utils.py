#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXIFデータ処理に関するユーティリティ関数
"""

import datetime
import exiftool
from dataclasses import dataclass
from typing import Optional


# 定数定義
EXIF_DATETIME_FORMAT = '%Y:%m:%d %H:%M:%S'


@dataclass
class GPSData:
    """GPS情報を管理するdataclass"""
    latitude: float
    longitude: float
    altitude: Optional[float] = None


@dataclass
class PhotoMetadata:
    file_name: str
    exif_datetime: Optional[datetime.datetime] = None
    exif_gps: Optional[GPSData] = None
    
    @property
    def has_datetime(self) -> bool:
        return self.exif_datetime is not None
    
    @property
    def has_gps(self) -> bool:
        return self.exif_gps is not None
    
    @property
    def has_metadata(self) -> bool:
        return self.has_datetime or self.has_gps


def get_exif_data(image_path):
    """
    ExifToolを使って画像ファイルからEXIFデータを取得する
    
    Args:
        image_path (str): 画像ファイルのパス
        
    Returns:
        dict: EXIFデータの辞書、取得できない場合はNone
    """
    with exiftool.ExifTool() as et:
        metadata = et.execute_json(str(image_path))
        if metadata and len(metadata) > 0:
            return metadata[0]  # execute_jsonはリストを返すので最初の要素を取得
        return None


def get_exif_datetime(exif_data):
    """
    EXIFデータから撮影日時を取得する
    
    Args:
        exif_data (dict): EXIFデータの辞書
        
    Returns:
        datetime.datetime: 撮影日時、見つからない場合はNone
    """
    # ExifToolのタグ名で日時フィールドを探す
    datetime_fields = [
        'EXIF:DateTime',
        'EXIF:DateTimeOriginal', 
        'EXIF:DateTimeDigitized',
        'EXIF:CreateDate',
        'EXIF:ModifyDate',
        'File:FileModifyDate',
        'File:FileAccessDate',
        'File:FileInodeChangeDate'
    ]
    
    for datetime_field in datetime_fields:
        if datetime_field in exif_data and exif_data[datetime_field]:
            datetime_string = str(exif_data[datetime_field])
            # ExifToolの日時フォーマットをパース
            if 'T' in datetime_string:
                # ISO形式: "YYYY-MM-DDTHH:MM:SS" または "YYYY-MM-DDTHH:MM:SS+XX:XX"
                if '+' in datetime_string:
                    datetime_string = datetime_string.split('+')[0]
                return datetime.datetime.fromisoformat(datetime_string.replace('T', ' '))
            elif ':' in datetime_string and len(datetime_string) >= 19:
                # EXIF形式: "YYYY:MM:DD HH:MM:SS"
                return datetime.datetime.strptime(datetime_string[:19], EXIF_DATETIME_FORMAT)
    
    return None


def get_gps_data(exif_data):
    """
    EXIFデータからGPS情報を取得する（ExifTool形式）
    
    Args:
        exif_data (dict): EXIFデータの辞書
        
    Returns:
        GPSData: GPS情報のオブジェクト、見つからない場合はNone
    """
    latitude = None
    longitude = None
    altitude = None
    
    # ExifToolのGPSタグから緯度を取得
    latitude_tags = [
        'EXIF:GPSLatitude',
        'Composite:GPSLatitude'
    ]
    
    latitude_ref_tags = [
        'EXIF:GPSLatitudeRef',
        'Composite:GPSLatitudeRef'
    ]
    
    # 経度タグ
    longitude_tags = [
        'EXIF:GPSLongitude', 
        'Composite:GPSLongitude'
    ]
    
    longitude_ref_tags = [
        'EXIF:GPSLongitudeRef',
        'Composite:GPSLongitudeRef'
    ]
    
    # 高度タグ
    altitude_tags = [
        'EXIF:GPSAltitude',
        'Composite:GPSAltitude'
    ]
    
    # 緯度を取得
    for lat_tag, lat_ref_tag in zip(latitude_tags, latitude_ref_tags):
        if lat_tag in exif_data and lat_ref_tag in exif_data:
            lat_str = str(exif_data[lat_tag])
            lat_ref = str(exif_data[lat_ref_tag])
            latitude = _parse_gps_coordinate(lat_str, lat_ref)
            break
    
    # 経度を取得
    for lon_tag, lon_ref_tag in zip(longitude_tags, longitude_ref_tags):
        if lon_tag in exif_data and lon_ref_tag in exif_data:
            lon_str = str(exif_data[lon_tag])
            lon_ref = str(exif_data[lon_ref_tag])
            longitude = _parse_gps_coordinate(lon_str, lon_ref)
            break
    
    # 高度を取得
    for alt_tag in altitude_tags:
        if alt_tag in exif_data:
            alt_str = str(exif_data[alt_tag])
            # 高度は通常 "XX m above sea level" のような形式
            if 'm above sea level' in alt_str:
                alt_value = float(alt_str.replace(' m above sea level', ''))
            else:
                alt_value = float(alt_str)
            altitude = alt_value
            break
    
    # 緯度と経度の両方がある場合のみGPSDataオブジェクトを作成
    if latitude is not None and longitude is not None:
        return GPSData(latitude=latitude, longitude=longitude, altitude=altitude)
    
    return None


def _parse_gps_coordinate(coord_str, direction):
    """ExifTool形式のGPS座標文字列を10進数に変換する"""
    # ExifToolの形式: "XX deg XX' XX.XX\""
    coord_str = coord_str.strip()
    
    # 度分秒を抽出
    if 'deg' in coord_str and "'" in coord_str:
        # 例: "35 deg 40' 12.34\""
        parts = coord_str.split('deg')
        degrees = float(parts[0].strip())
        
        minute_part = parts[1].strip()
        if "'" in minute_part:
            minute_sec_parts = minute_part.split("'")
            minutes = float(minute_sec_parts[0].strip())
            
            if len(minute_sec_parts) > 1 and '"' in minute_sec_parts[1]:
                seconds = float(minute_sec_parts[1].replace('"', '').strip())
            else:
                seconds = 0.0
        else:
            minutes = 0.0
            seconds = 0.0
    else:
        # 単純な数値形式の場合
        degrees = float(coord_str)
        minutes = 0.0
        seconds = 0.0
    
    # 10進数に変換
    decimal = degrees + minutes / 60.0 + seconds / 3600.0
    
    # 方向に応じて符号を決定
    return -decimal if direction in ['S', 'W'] else decimal
