#!/usr/bin/env python3
"""
メタデータファイルを検索するスクリプト
"""

import json
import os
from pathlib import Path
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_metadata_files(original_path):
    """元のファイルパスからメタデータファイルを検索"""
    original_path = Path(original_path)
    parent_dir = original_path.parent
    base_name = original_path.stem
    
    # 検索するメタデータファイルのパターン
    metadata_patterns = [
        f"{base_name}.json",
        f"{base_name}.supplemental-metadata.json",
        f"{base_name}.metadata.json",
        f"{base_name}.exif.json",
        f"{base_name}.sidecar.json"
    ]
    
    found_files = []
    
    # 同じディレクトリで検索
    for pattern in metadata_patterns:
        metadata_path = parent_dir / pattern
        if metadata_path.exists():
            found_files.append({
                "path": str(metadata_path),
                "type": "same_directory",
                "pattern": pattern
            })
    
    # 親ディレクトリで検索
    for pattern in metadata_patterns:
        metadata_path = parent_dir.parent / pattern
        if metadata_path.exists():
            found_files.append({
                "path": str(metadata_path),
                "type": "parent_directory", 
                "pattern": pattern
            })
    
    # 兄弟ディレクトリで検索（.jsonディレクトリなど）
    for sibling_dir in parent_dir.iterdir():
        if sibling_dir.is_dir() and sibling_dir.name.endswith('.json'):
            for pattern in metadata_patterns:
                metadata_path = sibling_dir / pattern
                if metadata_path.exists():
                    found_files.append({
                        "path": str(metadata_path),
                        "type": "sibling_directory",
                        "pattern": pattern
                    })
    
    return found_files

def analyze_metadata_file(metadata_path):
    """メタデータファイルの内容を分析"""
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # JSONとして解析を試行
        try:
            data = json.loads(content)
            return {
                "format": "json",
                "size": len(content),
                "keys": list(data.keys()) if isinstance(data, dict) else None
            }
        except json.JSONDecodeError:
            return {
                "format": "text",
                "size": len(content),
                "preview": content[:200] + "..." if len(content) > 200 else content
            }
    except Exception as e:
        return {
            "format": "error",
            "error": str(e)
        }

def main():
    output_dir = Path("/workspace/photos-metadata-restore/output")
    pair_file = output_dir / "pair.json"
    
    # pair.jsonの存在確認
    if not pair_file.exists():
        logger.error(f"pair.jsonが存在しません: {pair_file}")
        return
    
    # pair.jsonを読み込み
    with open(pair_file, 'r', encoding='utf-8') as f:
        pair_data = json.load(f)
    
    logger.info(f"処理対象のファイル数: {len(pair_data)}")
    
    # メタデータファイルを検索
    metadata_location = {}
    success_count = 0
    error_count = 0
    
    for i, item in enumerate(pair_data):
        try:
            print(f"検索中: {i+1}/{len(pair_data)} - {item.get('filename', 'unknown')}")
            filename = item["filename"]
            original_source = item["source"]
            
            # メタデータファイルを検索
            found_files = find_metadata_files(original_source)
            
            if found_files:
                # 最初に見つかったファイルを使用
                metadata_file = found_files[0]
                metadata_path = Path(metadata_file["path"])
                
                # メタデータファイルの分析
                analysis = analyze_metadata_file(metadata_path)
                
                metadata_location[filename] = {
                    "original_source": original_source,
                    "metadata_file": str(metadata_path),
                    "metadata_type": metadata_file["pattern"],
                    "found": True,
                    "file_exists": True,
                    "analysis": analysis
                }
            else:
                metadata_location[filename] = {
                    "original_source": original_source,
                    "metadata_file": None,
                    "metadata_type": None,
                    "found": False,
                    "file_exists": False
                }
            
            success_count += 1
            
        except Exception as e:
            logger.error(f"メタデータファイル検索エラー {item.get('filename', 'unknown')}: {e}")
            error_count += 1
    
    # metadata_location.jsonを保存
    location_file = output_dir / "metadata_location.json"
    with open(location_file, 'w', encoding='utf-8') as f:
        json.dump(metadata_location, f, ensure_ascii=False, indent=2)
    
    # 統計情報を表示
    found_count = sum(1 for data in metadata_location.values() if data.get("found"))
    
    logger.info(f"処理完了: 成功 {success_count}件, エラー {error_count}件")
    logger.info(f"メタデータファイル発見: {found_count}件")
    logger.info(f"metadata_location.jsonを保存しました: {location_file}")

if __name__ == "__main__":
    main()