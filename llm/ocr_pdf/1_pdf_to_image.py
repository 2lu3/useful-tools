#!/usr/bin/env python3
"""
PDFファイルを画像に変換するスクリプト
inputディレクトリのPDFファイルを1枚ずつ画像に変換してoutput/image/に保存する
"""

import os
import glob
from pathlib import Path
from pdf2image import convert_from_path
import tomllib
from loguru import logger
from alive_progress import alive_bar


def load_config():
    """config.tomlから設定を読み込む"""
    with open("config.toml", "rb") as f:
        return tomllib.load(f)


def check_pdf_files():
    """inputディレクトリのPDFファイル数を確認"""
    pdf_files = glob.glob("input/*.pdf")
    assert len(pdf_files) == 1, f"PDFファイルは1つである必要があります。現在: {len(pdf_files)}個"
    return pdf_files[0]


def convert_pdf_to_images(pdf_path, output_dir, max_pages=None):
    """PDFを画像に変換して保存（1ページずつ処理）"""
    import gc
    
    # ファイル名のベース部分を取得（拡張子なし）
    base_name = Path(pdf_path).stem
    
    # PDFの総ページ数を取得（メモリを使わずに）
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        logger.info(f"PDF総ページ数: {total_pages}")
        
        # 最大ページ数が設定されている場合は制限
        if max_pages is not None:
            total_pages = min(total_pages, max_pages)
            logger.info(f"最大ページ数制限: {max_pages}ページまで処理")
        
        # ページ数の桁数を計算
        digit_count = len(str(total_pages))
        
        # 1ページずつ処理
        with alive_bar(total_pages, title="PDF変換中") as bar:
            for page_num in range(1, total_pages + 1):
                try:
                    logger.info(f"ページ {page_num}/{total_pages} を処理中...")
                    
                    # 1ページだけを画像に変換
                    images = convert_from_path(
                        pdf_path,
                        first_page=page_num,
                        last_page=page_num,
                        dpi=200,  # DPIを下げてメモリ使用量を削減
                        fmt='jpeg',
                        thread_count=1  # スレッド数を制限
                    )
                    
                    if images:  # 画像が正常に取得できた場合
                        image = images[0]  # 1ページなので最初の要素
                        filename = f"{base_name}_{page_num:0{digit_count}}.jpg"
                        output_path = output_dir / filename
                        image.save(output_path, "JPEG", quality=85)
                        logger.info(f"保存完了: {output_path}")
                        
                        # メモリを即座に解放
                        del image, images
                        gc.collect()
                    else:
                        logger.warning(f"ページ {page_num} の画像取得に失敗")
                    
                    bar()
                    
                except Exception as e:
                    logger.error(f"ページ {page_num} の処理でエラー: {e}")
                    bar()
                    continue
                    
    except Exception as e:
        logger.error(f"PDF読み込みエラー: {e}")
        raise


def main():
    """メイン処理"""
    # 設定を読み込み
    config = load_config()
    
    # PDFファイルの存在確認
    pdf_path = check_pdf_files()
    logger.info(f"処理対象PDF: {pdf_path}")
    
    # 出力ディレクトリの確認・作成
    output_dir = Path("output/image")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 最大ページ数を設定から取得
    max_pages = config.get("pdf", {}).get("process_pages")
    if max_pages:
        logger.info(f"最大処理ページ数: {max_pages}")
    
    # PDFを画像に変換
    convert_pdf_to_images(pdf_path, output_dir, max_pages)
    
    logger.success("変換完了")


if __name__ == "__main__":
    main()
