#!/usr/bin/env python3
"""
画像・動画ファイルをinputディレクトリからoutputディレクトリに移動するスクリプト
alive-progressとloguruを使用してプログレス表示とログ出力を実装
"""

import os
import shutil
from pathlib import Path
from collections import defaultdict
from typing import Set, Dict, List, Tuple

from alive_progress import alive_bar
from loguru import logger


class MediaFileOrganizer:
    """画像・動画ファイルを整理するクラス"""
    
    # 画像ファイルの拡張子（大文字小文字を区別）
    IMAGE_EXTENSIONS: Set[str] = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp',
        '.heic', '.heif', '.raw', '.cr2', '.nef', '.arw', '.dng',
        '.JPG', '.JPEG', '.PNG', '.GIF', '.BMP', '.TIFF', '.TIF', '.WEBP',
        '.HEIC', '.HEIF', '.RAW', '.CR2', '.NEF', '.ARW', '.DNG',
        '.jp2', '.JP2'
    }
    
    # 動画ファイルの拡張子（大文字小文字を区別）
    VIDEO_EXTENSIONS: Set[str] = {
        '.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v',
        '.MP4', '.AVI', '.MOV', '.MKV', '.WMV', '.FLV', '.WEBM', '.M4V',
        '.mp', '.MP'
    }
    
    def __init__(self, input_dir: str, output_dir: str):
        """初期化
        
        Args:
            input_dir: 入力ディレクトリのパス
            output_dir: 出力ディレクトリのパス
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.media_extensions = self.IMAGE_EXTENSIONS | self.VIDEO_EXTENSIONS
        
        # ログの設定
        logger.add(
            "media_organizer.log",
            rotation="1 MB",
            retention="10 days",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
        
        # 統計情報
        self.stats = {
            'total_files': 0,
            'media_files': 0,
            'moved_files': 0,
            'skipped_files': 0,
            'error_files': 0
        }
        
        # 拡張子の統計
        self.extension_stats: Dict[str, int] = defaultdict(int)
        self.unknown_extensions: Set[str] = set()
        
    def is_media_file(self, file_path: Path) -> bool:
        """ファイルが画像・動画ファイルかどうかを判定
        
        Args:
            file_path: ファイルパス
            
        Returns:
            画像・動画ファイルの場合True
        """
        return file_path.suffix in self.media_extensions
    
    def get_all_files(self) -> List[Path]:
        """inputディレクトリ内のすべてのファイルを取得
        
        Returns:
            ファイルパスのリスト
        """
        logger.info(f"inputディレクトリを検索中: {self.input_dir}")
        all_files = []
        
        for file_path in self.input_dir.rglob('*'):
            if file_path.is_file():
                all_files.append(file_path)
                self.extension_stats[file_path.suffix.lower()] += 1
                
        logger.info(f"総ファイル数: {len(all_files)}")
        return all_files
    
    def move_media_files(self, files: List[Path]) -> None:
        """画像・動画ファイルをoutputディレクトリに移動
        
        Args:
            files: ファイルパスのリスト
        """
        self.stats['total_files'] = len(files)
        
        # メディアファイルをフィルタリング
        media_files = [f for f in files if self.is_media_file(f)]
        self.stats['media_files'] = len(media_files)
        
        # 未知の拡張子を収集
        for file_path in files:
            if not self.is_media_file(file_path) and file_path.suffix:
                self.unknown_extensions.add(file_path.suffix.lower())
        
        logger.info(f"メディアファイル数: {self.stats['media_files']}")
        logger.info(f"未知の拡張子数: {len(self.unknown_extensions)}")
        
        if not media_files:
            logger.warning("移動するメディアファイルが見つかりませんでした")
            return
        
        # outputディレクトリを作成
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # プログレスバーと共にファイルを移動
        with alive_bar(len(media_files), title="メディアファイルを移動中") as bar:
            for file_path in media_files:
                try:
                    # 移動先のパスを生成（元のディレクトリ構造を保持）
                    relative_path = file_path.relative_to(self.input_dir)
                    destination = self.output_dir / relative_path
                    
                    # 移動先ディレクトリを作成
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    
                    # ファイルが既に存在する場合はスキップ
                    if destination.exists():
                        logger.warning(f"ファイルが既に存在します: {destination}")
                        self.stats['skipped_files'] += 1
                    else:
                        # ファイルを移動
                        shutil.move(str(file_path), str(destination))
                        logger.debug(f"移動完了: {file_path} -> {destination}")
                        self.stats['moved_files'] += 1
                    
                except Exception as e:
                    logger.error(f"ファイル移動エラー: {file_path} - {e}")
                    self.stats['error_files'] += 1
                
                bar()
    
    def print_statistics(self) -> None:
        """統計情報を表示"""
        print("\n" + "="*60)
        print("📊 処理結果統計")
        print("="*60)
        print(f"総ファイル数: {self.stats['total_files']:,}")
        print(f"メディアファイル数: {self.stats['media_files']:,}")
        print(f"移動成功: {self.stats['moved_files']:,}")
        print(f"スキップ: {self.stats['skipped_files']:,}")
        print(f"エラー: {self.stats['error_files']:,}")
        
        print("\n" + "="*60)
        print("📁 検出された拡張子（上位20件）")
        print("="*60)
        sorted_extensions = sorted(
            self.extension_stats.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        for ext, count in sorted_extensions[:20]:
            media_type = "🖼️ 画像" if ext in [e.lower() for e in self.IMAGE_EXTENSIONS] else \
                        "🎬 動画" if ext in [e.lower() for e in self.VIDEO_EXTENSIONS] else \
                        "❓ その他"
            print(f"{ext:>10}: {count:>6,} 件 {media_type}")
        
        if self.unknown_extensions:
            print("\n" + "="*60)
            print("❓ 判定されなかった拡張子")
            print("="*60)
            for ext in sorted(self.unknown_extensions):
                print(f"  {ext}")
        
        print("\n" + "="*60)
        print("✅ 処理完了")
        print("="*60)


def main():
    """メイン処理"""
    input_dir = "/Users/hikarumuto/ghq/github.com/2lu3/useful-tools/photos-metadata-restore/output/input"
    output_dir = "/Users/hikarumuto/ghq/github.com/2lu3/useful-tools/photos-metadata-restore/output/output"
    
    # オーガナイザーを初期化
    organizer = MediaFileOrganizer(input_dir, output_dir)
    
    try:
        # すべてのファイルを取得
        all_files = organizer.get_all_files()
        
        if not all_files:
            logger.warning("inputディレクトリにファイルが見つかりませんでした")
            return
        
        # メディアファイルを移動
        organizer.move_media_files(all_files)
        
        # 統計情報を表示
        organizer.print_statistics()
        
    except Exception as e:
        logger.error(f"処理中にエラーが発生しました: {e}")
        raise


if __name__ == "__main__":
    main()
