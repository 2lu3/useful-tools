#!/usr/bin/env python3
"""
画像からAnki用CSVを作成するツール

inputディレクトリのjpg/png画像を読み込み、OpenAI APIでトピック名称を抽出し、
Anki用のCSVファイルを生成します。画像はハッシュ化されたファイル名でoutputディレクトリに保存されます。
"""

import os
import hashlib
import csv
import base64
from pathlib import Path
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger
from openai import OpenAI
from alive_progress import alive_bar


class ImageToAnkiConverter:
    def __init__(self, openai_api_key: str = None):
        """
        初期化
        
        Args:
            openai_api_key: OpenAI APIキー（Noneの場合は環境変数OPENAI_API_KEYを使用）
        """
        self.client = OpenAI(api_key=openai_api_key)
        self.input_dir = Path("input")
        self.output_dir = Path("output")
        self.image_dir = self.output_dir / "image"
        self.csv_file = self.output_dir / "anki_cards.csv"
        self.max_workers = 5
        
        # 出力ディレクトリを作成
        self.output_dir.mkdir(exist_ok=True)
        self.image_dir.mkdir(exist_ok=True)
        
        logger.info(f"入力ディレクトリ: {self.input_dir.absolute()}")
        logger.info(f"出力ディレクトリ: {self.output_dir.absolute()}")
        logger.info(f"画像ディレクトリ: {self.image_dir.absolute()}")

    def get_image_files(self) -> List[Path]:
        """
        inputディレクトリからjpg/png画像ファイルを取得
        
        Returns:
            画像ファイルのパスのリスト
        """
        image_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
        image_files = []
        
        if not self.input_dir.exists():
            logger.warning(f"入力ディレクトリが存在しません: {self.input_dir}")
            return image_files
            
        for file_path in self.input_dir.iterdir():
            if file_path.is_file() and file_path.suffix in image_extensions:
                image_files.append(file_path)
                
        logger.info(f"見つかった画像ファイル数: {len(image_files)}")
        return image_files

    def encode_image(self, image_path: Path) -> str:
        """
        画像をbase64エンコード
        
        Args:
            image_path: 画像ファイルのパス
            
        Returns:
            base64エンコードされた画像データ
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def get_topic_name(self, image_path: Path) -> str:
        """
        OpenAI APIを使用して画像からトピック名称を抽出
        
        Args:
            image_path: 画像ファイルのパス
            
        Returns:
            抽出されたトピック名称
        """
        try:
            base64_image = self.encode_image(image_path)
            
            response = self.client.chat.completions.create(
                model="gpt-4.1-2025-04-14",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "この画像は医学部で使われているテキストのスクリーンショットです。画像はある特定のトピックについて記載されています。そのトピックはタイトルとして記載されています。タイトルを探し、そのトピックの名称のみを答えてください。名称以外は一切出力しないでください。"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=100
            )
            
            topic_name = response.choices[0].message.content.strip()
            logger.info(f"画像 {image_path.name} のトピック: {topic_name}")
            return topic_name
            
        except Exception as e:
            logger.error(f"画像 {image_path.name} の処理中にエラーが発生: {e}")
            return f"エラー: {image_path.stem}"

    def get_image_hash(self, image_path: Path) -> str:
        """
        画像ファイルのハッシュ値を計算
        
        Args:
            image_path: 画像ファイルのパス
            
        Returns:
            ハッシュ値（16進数文字列）
        """
        with open(image_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        return file_hash

    def copy_image_with_hash(self, image_path: Path) -> str:
        """
        画像をハッシュ化されたファイル名でoutputディレクトリにコピー
        
        Args:
            image_path: 元の画像ファイルのパス
            
        Returns:
            新しいファイル名
        """
        # ハッシュ値を計算
        file_hash = self.get_image_hash(image_path)
        
        # 元の拡張子を保持
        extension = image_path.suffix.lower()
        new_filename = f"{file_hash}{extension}"
        new_path = self.image_dir / new_filename
        
        # ファイルをコピー
        import shutil
        shutil.copy2(image_path, new_path)
        
        logger.info(f"画像をコピー: {image_path.name} -> {new_filename}")
        return new_filename

    def create_anki_csv(self, cards_data: List[Tuple[str, str]]) -> None:
        """
        Anki用のCSVファイルを作成
        
        Args:
            cards_data: (問題, 画像ファイル名)のタプルのリスト
        """
        with open(self.csv_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # ヘッダー行はなし
            
            # データ行
            for question, image_filename in cards_data:# Ankiの画像表示形式: <img src="image/filename">
                answer = f'<img src="{image_filename}">'
                writer.writerow([question, answer])
                
        logger.info(f"Anki用CSVファイルを作成: {self.csv_file}")

    def process_single_image(self, image_path: Path) -> Tuple[str, str]:
        """
        単一の画像を処理
        
        Args:
            image_path: 画像ファイルのパス
            
        Returns:
            (トピック名称, 画像ファイル名)のタプル
        """
        logger.info(f"処理中: {image_path.name}")
        
        try:
            # トピック名称を抽出
            topic_name = self.get_topic_name(image_path)
            
            # 画像をハッシュ化されたファイル名でコピー
            image_filename = self.copy_image_with_hash(image_path)
            
            logger.info(f"完了: {image_path.name} -> {topic_name}")
            return (topic_name, image_filename)
            
        except Exception as e:
            logger.error(f"画像 {image_path.name} の処理に失敗: {e}")
            return None

    def process_images(self) -> None:
        """
        画像ファイルを処理してAnki用CSVを作成（並列処理）
        """
        # 画像ファイルを取得
        image_files = self.get_image_files()
        
        if not image_files:
            logger.warning("処理する画像ファイルが見つかりませんでした")
            return
            
        cards_data = []
        
        # alive_progressでプログレスバーを表示
        with alive_bar(len(image_files), title="画像処理中") as bar:
            # ThreadPoolExecutorを使用して並列処理
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 各画像の処理を並列実行
                future_to_image = {
                    executor.submit(self.process_single_image, image_path): image_path 
                    for image_path in image_files
                }
                
                # 完了したタスクから結果を取得
                for future in as_completed(future_to_image):
                    image_path = future_to_image[future]
                    try:
                        result = future.result()
                        if result:
                            cards_data.append(result)
                    except Exception as e:
                        logger.error(f"画像 {image_path.name} の処理で予期しないエラー: {e}")
                    
                    # プログレスバーを更新
                    bar()
        
        # CSVファイルを作成
        if cards_data:
            self.create_anki_csv(cards_data)
            logger.info(f"完了: {len(cards_data)}枚のカードを作成しました")
        else:
            logger.warning("作成されたカードがありません")


def main():
    """メイン関数"""
    import os
    
    # OpenAI APIキーを取得
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY環境変数が設定されていません")
        return
    
    # コンバーターを作成して実行
    converter = ImageToAnkiConverter(api_key)
    converter.process_images()


if __name__ == "__main__":
    main()
