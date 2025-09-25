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
from PIL import Image
from PIL.ExifTags import TAGS
import datetime

def get_exif_data(image_path):
    """
    画像ファイルからEXIFデータを取得する
    
    Args:
        image_path (str): 画像ファイルのパス
        
    Returns:
        dict: EXIFデータの辞書
    """
    try:
        with Image.open(image_path) as image:
            exifdata = image.getexif()
            
            exif_dict = {}
            for tag_id in exifdata:
                tag = TAGS.get(tag_id, tag_id)
                data = exifdata.get(tag_id)
                exif_dict[tag] = data
                
            return exif_dict
    except Exception as e:
        print(f"EXIFデータの読み込みエラー ({image_path}): {e}")
        return {}

def has_datetime_property(exif_data):
    """
    EXIFデータに撮影日時の情報があるかチェックする
    
    Args:
        exif_data (dict): EXIFデータの辞書
        
    Returns:
        bool: 撮影日時情報がある場合はTrue
    """
    # 撮影日時に関連するEXIFタグ
    datetime_tags = [
        'DateTime',
        'DateTimeOriginal', 
        'DateTimeDigitized',
        'CreateDate',
        'ModifyDate'
    ]
    
    for tag in datetime_tags:
        if tag in exif_data and exif_data[tag]:
            return True
    
    return False

def get_file_creation_time(file_path):
    """
    ファイルの作成日時を取得する（EXIFデータがない場合の代替手段）
    
    Args:
        file_path (str): ファイルのパス
        
    Returns:
        datetime.datetime: ファイルの作成日時
    """
    try:
        stat = os.stat(file_path)
        return datetime.datetime.fromtimestamp(stat.st_ctime)
    except Exception as e:
        print(f"ファイル作成日時の取得エラー ({file_path}): {e}")
        return None

def find_takeout_directories(base_path):
    """takeoutで始まるディレクトリを検索する"""
    takeout_dirs = []
    for item in os.listdir(base_path):
        item_path = os.path.join(base_path, item)
        if os.path.isdir(item_path) and item.lower().startswith('takeout'):
            takeout_dirs.append(item_path)
    print(f"見つかったTakeoutディレクトリ: {len(takeout_dirs)}個")
    return takeout_dirs

def find_photo_files(directory):
    """指定されたディレクトリ内の写真ファイルを検索する"""
    photo_extensions = ['*.jpg', '*.jpeg', '*.JPG', '*.JPEG', '*.png', '*.PNG', 
                       '*.heic', '*.HEIC', '*.mp4', '*.MP4', '*.mov', '*.MOV']
    
    photo_files = []
    for extension in photo_extensions:
        pattern = os.path.join(directory, '**', extension)
        files = glob.glob(pattern, recursive=True)
        photo_files.extend(files)
    
    print(f"{os.path.basename(directory)}から{len(photo_files)}個の写真ファイルを発見")
    return photo_files

def load_pair_json(output_dir):
    """output/pair.jsonファイルを読み込む"""
    pair_file = Path(output_dir) / "pair.json"
    if not pair_file.exists():
        print(f"エラー: {pair_file} が存在しません")
        return None
    
    try:
        with open(pair_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"エラー: pair.jsonの読み込みに失敗しました: {e}")
        return None

def find_supplemental_metadata(source_path):
    """元ファイルパスから対応するsupplemental-metadata.jsonファイルを検索する"""
    source_path = Path(source_path)
    
    # 元ファイルと同じディレクトリにある.supplemental-metadata.jsonファイルを探す
    json_file = source_path.with_suffix(source_path.suffix + '.supplemental-metadata.json')
    
    if json_file.exists():
        return json_file
    
    # 見つからない場合はNoneを返す
    return None

def get_json_datetime(json_file):
    """supplemental-metadata.jsonファイルから撮影日時を取得する"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # photoTakenTimeを優先的に取得
        if 'photoTakenTime' in data and data['photoTakenTime']:
            timestamp = data['photoTakenTime'].get('timestamp')
            if timestamp:
                return datetime.datetime.fromtimestamp(int(timestamp))
        
        # photoTakenTimeがない場合はcreationTimeを使用
        if 'creationTime' in data and data['creationTime']:
            timestamp = data['creationTime'].get('timestamp')
            if timestamp:
                return datetime.datetime.fromtimestamp(int(timestamp))
        
        return None
    except Exception as e:
        print(f"JSONファイルの読み込みエラー ({json_file}): {e}")
        return None

def filter_photos_without_datetime(base_path):
    """
    outputディレクトリ内の写真ファイルをチェックし、撮影日時プロパティがないファイルを特定する
    pair.jsonを参考にして対応するJSONファイルもリストアップする
    
    Args:
        base_path (str): ベースディレクトリのパス
    """
    base_path = Path(base_path)
    output_path = base_path / "output"
    
    if not base_path.exists():
        print(f"エラー: ディレクトリ '{base_path}' が存在しません")
        return
    
    if not output_path.exists():
        print(f"エラー: outputディレクトリが存在しません")
        return
    
    # pair.jsonを読み込み
    file_pairs = load_pair_json(output_path)
    if not file_pairs:
        return
    
    # outputディレクトリ内の写真ファイルを検索
    photo_extensions = {'.jpg', '.jpeg', '.JPG', '.JPEG', '.heic', '.HEIC', '.png', '.PNG', '.tiff', '.TIFF', '.mp4', '.MP4', '.mov', '.MOV'}
    
    all_photo_files = []
    for file_path in output_path.rglob('*'):
        if file_path.is_file() and file_path.suffix in photo_extensions:
            all_photo_files.append(file_path)
    
    print(f"outputディレクトリから{len(all_photo_files)}個の写真ファイルを発見しました")
    
    if not all_photo_files:
        print("写真ファイルが見つかりませんでした")
        return
    
    files_without_datetime = []
    files_with_datetime = []
    json_files_found = []
    total_files = len(all_photo_files)
    
    print(f"outputディレクトリ内の写真ファイルをスキャン中...")
    print("-" * 60)
    
    # 各写真ファイルをチェック
    for i, file_path in enumerate(all_photo_files, 1):
        print(f"チェック中 ({i}/{total_files}): {file_path.name}")
        
        # EXIFデータを取得
        exif_data = get_exif_data(str(file_path))
        
        if has_datetime_property(exif_data):
            files_with_datetime.append(file_path)
            print(f"  ✓ 撮影日時情報あり")
        else:
            # ファイル作成日時を取得して表示
            creation_time = get_file_creation_time(str(file_path))
            if creation_time:
                print(f"  ✗ 撮影日時情報なし (ファイル作成日時: {creation_time.strftime('%Y-%m-%d %H:%M:%S')})")
            else:
                print(f"  ✗ 撮影日時情報なし")
            
            files_without_datetime.append(file_path)
            
            # pair.jsonから元ファイルパスを取得
            original_source = None
            for pair in file_pairs:
                if str(pair['destination']) == str(file_path.resolve()):
                    original_source = pair['source']
                    break
            
            if original_source:
                # 対応するsupplemental-metadata.jsonファイルを検索
                json_file = find_supplemental_metadata(original_source)
                if json_file:
                    json_datetime = get_json_datetime(json_file)
                    if json_datetime:
                        print(f"  📄 対応するJSONファイル発見: {json_file.name}")
                        print(f"     JSON撮影日時: {json_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                        json_files_found.append({
                            'output_file': str(file_path),
                            'original_source': original_source,
                            'json_file': str(json_file),
                            'json_datetime': json_datetime
                        })
                    else:
                        print(f"  📄 対応するJSONファイル発見: {json_file.name} (日付情報なし)")
                        json_files_found.append({
                            'output_file': str(file_path),
                            'original_source': original_source,
                            'json_file': str(json_file),
                            'json_datetime': None
                        })
                else:
                    print(f"  ❌ 対応するJSONファイルが見つかりません")
            else:
                print(f"  ❌ pair.jsonから元ファイルパスが見つかりません")
    
    # 結果を表示
    print("\n" + "=" * 60)
    print("フィルタリング結果")
    print("=" * 60)
    print(f"総ファイル数: {total_files}")
    print(f"撮影日時情報あり: {len(files_with_datetime)}")
    print(f"撮影日時情報なし: {len(files_without_datetime)}")
    print(f"対応するJSONファイル発見: {len(json_files_found)}")
    
    if files_without_datetime:
        print(f"\n撮影日時情報がないファイル ({len(files_without_datetime)}件):")
        print("-" * 40)
        for i, file_path in enumerate(files_without_datetime, 1):
            print(f"{i:3d}. {file_path.name}")
    
    if json_files_found:
        print(f"\n対応するJSONファイルが見つかったファイル ({len(json_files_found)}件):")
        print("-" * 50)
        for i, json_info in enumerate(json_files_found, 1):
            print(f"{i:3d}. {Path(json_info['output_file']).name}")
            print(f"     JSONファイル: {Path(json_info['json_file']).name}")
            if json_info['json_datetime']:
                print(f"     JSON撮影日時: {json_info['json_datetime'].strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"     JSON撮影日時: なし")
            print()
    
    # 結果をファイルに保存
    result_file = base_path / "filter_results.txt"
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write("写真ファイルフィルタリング結果\n")
        f.write("=" * 50 + "\n")
        f.write(f"スキャン日時: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"総ファイル数: {total_files}\n")
        f.write(f"撮影日時情報あり: {len(files_with_datetime)}\n")
        f.write(f"撮影日時情報なし: {len(files_without_datetime)}\n")
        f.write(f"対応するJSONファイル発見: {len(json_files_found)}\n\n")
        
        if files_without_datetime:
            f.write("撮影日時情報がないファイル:\n")
            f.write("-" * 30 + "\n")
            for i, file_path in enumerate(files_without_datetime, 1):
                f.write(f"{i:3d}. {file_path.name}\n")
                f.write(f"     パス: {file_path}\n")
                f.write(f"     サイズ: {file_path.stat().st_size} bytes\n")
                creation_time = get_file_creation_time(str(file_path))
                if creation_time:
                    f.write(f"     ファイル作成日時: {creation_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("\n")
        
        if json_files_found:
            f.write("\n対応するJSONファイルが見つかったファイル:\n")
            f.write("-" * 40 + "\n")
            for i, json_info in enumerate(json_files_found, 1):
                f.write(f"{i:3d}. {Path(json_info['output_file']).name}\n")
                f.write(f"     JSONファイル: {Path(json_info['json_file']).name}\n")
                f.write(f"     元ファイル: {json_info['original_source']}\n")
                if json_info['json_datetime']:
                    f.write(f"     JSON撮影日時: {json_info['json_datetime'].strftime('%Y-%m-%d %H:%M:%S')}\n")
                else:
                    f.write(f"     JSON撮影日時: なし\n")
                f.write("\n")
    
    print(f"\n結果をファイルに保存しました: {result_file}")

def main():
    """メイン関数"""
    # ベースディレクトリのパスを設定
    script_dir = Path(__file__).parent
    
    print("写真ファイルフィルタリングスクリプト")
    print("=" * 50)
    print(f"対象ディレクトリ: {script_dir}")
    
    # 必要なライブラリのチェック
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
    except ImportError:
        print("エラー: Pillowライブラリがインストールされていません")
        print("以下のコマンドでインストールしてください:")
        print("pip install Pillow")
        sys.exit(1)
    
    # フィルタリング実行
    filter_photos_without_datetime(str(script_dir))

if __name__ == "__main__":
    main()
