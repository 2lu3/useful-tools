#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Takeoutフォルダー内の写真ファイルをoutputディレクトリに整理するスクリプト
"""

import os
import shutil
import glob
import hashlib
import argparse
import json
from pathlib import Path
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_output_directory(output_path):
    """outputディレクトリを作成する"""
    os.makedirs(output_path, exist_ok=True)
    logger.info(f"Outputディレクトリを作成しました: {output_path}")
    return True

def find_takeout_directories(base_path):
    """takeoutで始まるディレクトリを検索する"""
    takeout_dirs = []
    for item in os.listdir(base_path):
        item_path = os.path.join(base_path, item)
        if os.path.isdir(item_path) and item.lower().startswith('takeout'):
            takeout_dirs.append(item_path)
    logger.info(f"見つかったTakeoutディレクトリ: {len(takeout_dirs)}個")
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
    
    logger.info(f"{os.path.basename(directory)}から{len(photo_files)}個の写真ファイルを発見")
    return photo_files

def calculate_file_hash(file_path):
    """ファイルのMD5ハッシュを計算する"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def copy_photo_file(source_file, output_dir, file_counter):
    """写真ファイルをoutputディレクトリにコピーする"""
    # ファイルのハッシュを計算
    source_hash = calculate_file_hash(source_file)
    
    # 拡張子を取得
    _, ext = os.path.splitext(source_file)
    if not ext:
        ext = '.jpg'  # 拡張子がない場合はデフォルトで.jpg
    
    # ハッシュベースのファイル名を生成
    new_filename = f"{source_hash}{ext}"
    destination = os.path.join(output_dir, new_filename)
    
    # ファイルが既に存在する場合はスキップ
    if os.path.exists(destination):
        logger.debug(f"同じハッシュのファイルをスキップ: {os.path.basename(source_file)} -> {new_filename}")
        return "skipped", None
    
    # ファイルをコピー
    shutil.copy2(source_file, destination)
    logger.debug(f"コピー完了: {os.path.basename(source_file)} -> {new_filename}")
    
    # ファイルパスの対応情報を返す
    return "success", {
        "source": str(Path(source_file).resolve()),
        "destination": str(Path(destination).resolve()),
        "filename": new_filename,
        "hash": source_hash
    }

def organize_photos(base_path, output_dir_name="output"):
    """メイン処理：takeoutフォルダー内の写真を整理する"""
    base_path = Path(base_path).resolve()
    output_path = base_path / output_dir_name
    
    logger.info(f"写真整理を開始します...")
    logger.info(f"ベースパス: {base_path}")
    logger.info(f"出力先: {output_path}")
    logger.info(f"モード: コピー")
    
    # outputディレクトリを作成
    if not create_output_directory(output_path):
        return False
    
    # takeoutディレクトリを検索
    takeout_dirs = find_takeout_directories(base_path)
    if not takeout_dirs:
        logger.warning("Takeoutディレクトリが見つかりませんでした")
        return False
    
    # 全写真ファイルを収集
    all_photo_files = []
    for takeout_dir in takeout_dirs:
        photo_files = find_photo_files(takeout_dir)
        all_photo_files.extend(photo_files)
    
    logger.info(f"合計{len(all_photo_files)}個の写真ファイルを発見しました")
    
    if not all_photo_files:
        logger.warning("写真ファイルが見つかりませんでした")
        return False
    
    # ファイルをコピー
    success_count = 0
    failed_count = 0
    skipped_count = 0
    file_pairs = []  # ファイルパスの対応を保存
    
    for i, photo_file in enumerate(all_photo_files, 1):
        result, pair_info = copy_photo_file(photo_file, output_path, i)
        if result == "success":
            success_count += 1
            if pair_info:
                file_pairs.append(pair_info)
        elif result == "skipped":
            skipped_count += 1
        else:  # "failed"
            failed_count += 1
        
        # 進捗表示
        if i % 100 == 0 or i == len(all_photo_files):
            logger.info(f"進捗: {i}/{len(all_photo_files)} ({i/len(all_photo_files)*100:.1f}%)")
    
    # ファイルパスの対応をJSONファイルに保存
    pair_file = output_path / "pair.json"
    with open(pair_file, 'w', encoding='utf-8') as f:
        json.dump(file_pairs, f, ensure_ascii=False, indent=2)
    logger.info(f"ファイルパス対応情報を保存しました: {pair_file}")
    
    # 結果表示
    logger.info(f"写真整理が完了しました！")
    logger.info(f"処理成功: {success_count}個")
    logger.info(f"重複スキップ: {skipped_count}個")
    if failed_count > 0:
        logger.warning(f"処理失敗: {failed_count}個")
    
    return True

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='Takeoutフォルダー内の写真ファイルを整理します')
    parser.add_argument('--output', default='output', 
                       help='出力ディレクトリ名 (デフォルト: output)')
    parser.add_argument('--path', default=None,
                       help='処理するベースパス (デフォルト: スクリプトのあるディレクトリ)')
    
    args = parser.parse_args()
    
    # ベースパスを決定
    if args.path:
        base_path = Path(args.path).resolve()
    else:
        base_path = Path(__file__).parent.resolve()
    
    organize_photos(base_path, args.output)

if __name__ == "__main__":
    main()
