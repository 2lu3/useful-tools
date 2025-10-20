#!/usr/bin/env python3
import hashlib
import os
from pathlib import Path
from typing import List, Tuple
import fitz  # PyMuPDF
from loguru import logger
from util.config import load_config
from alive_progress import alive_bar


def extract_images_from_pdf(pdf_path: Path, output_dir: Path) -> List[Tuple[str, str]]:
    """
    PDFから画像を抽出し、ハッシュ化したファイル名で保存する
    
    Returns:
        List[Tuple[str, str]]: (元の画像名, ハッシュ化されたファイル名) のリスト
    """
    doc = fitz.open(pdf_path)
    image_info = []
    
    # output/imageディレクトリ（0_init.shで初期化済み）
    image_dir = output_dir / "image"
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images()
        
        for img_index, img in enumerate(image_list):
            # 画像データを取得
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            
            # 画像が有効かチェック
            if pix.n - pix.alpha < 4:  # GRAY or RGB
                # 画像データを取得
                img_data = pix.tobytes("png")
                
                # ハッシュ化されたファイル名を生成
                img_hash = hashlib.md5(img_data).hexdigest()
                img_filename = f"{img_hash}.png"
                img_path = image_dir / img_filename
                
                # 画像を保存
                with open(img_path, "wb") as f:
                    f.write(img_data)
                
                # 元の画像名（ページ番号とインデックス）とハッシュ化されたファイル名を記録
                original_name = f"page_{page_num + 1}_img_{img_index + 1}"
                image_info.append((original_name, img_filename))
                
                logger.info(f"画像を抽出: {original_name} -> {img_filename}")
            
            pix = None  # メモリを解放
    
    doc.close()
    return image_info


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    PDFからテキストを抽出する
    """
    doc = fitz.open(pdf_path)
    text_content = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if text.strip():
            text_content.append(f"=== ページ {page_num + 1} ===\n{text}\n")
    
    doc.close()
    return "\n".join(text_content)


def embed_image_references(text: str, image_info: List[Tuple[str, str]]) -> str:
    """
    テキストに画像の参照情報を埋め込む
    """
    if not image_info:
        return text
    
    # 画像参照情報をテキストの最後に追加
    image_refs = "\n\n=== 画像参照 ===\n"
    for original_name, hashed_filename in image_info:
        image_refs += f"[画像: {original_name}] -> {hashed_filename}\n"
    
    return text + image_refs


def process_pdf_file(pdf_path: Path, output_dir: Path) -> None:
    """
    単一のPDFファイルを処理する
    """
    logger.info(f"PDFファイルを処理中: {pdf_path}")
    
    # テキストを抽出
    text_content = extract_text_from_pdf(pdf_path)
    
    # 画像を抽出
    image_info = extract_images_from_pdf(pdf_path, output_dir)
    
    # テキストに画像参照を埋め込む
    final_text = embed_image_references(text_content, image_info)
    
    # textualizedディレクトリに保存（0_init.shで初期化済み）
    textualized_dir = output_dir / "textualized"
    
    output_file = textualized_dir / f"{pdf_path.stem}.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_text)
    
    logger.info(f"テキスト化完了: {output_file}")
    logger.info(f"抽出した画像数: {len(image_info)}")


def find_pdf_files(input_dir: Path) -> List[Path]:
    """
    inputディレクトリからPDFファイルを検索する
    """
    pdf_files = list(input_dir.glob("*.pdf"))
    logger.info(f"見つかったPDFファイル数: {len(pdf_files)}")
    return pdf_files


def main():
    """
    メイン処理
    """
    # 設定を読み込み
    config = load_config()
    
    # パスを設定
    script_dir = Path(__file__).parent
    input_dir = script_dir / "input"
    output_dir = script_dir / "output"  # 0_init.shで初期化済み
    
    # PDFファイルを検索
    pdf_files = find_pdf_files(input_dir)
    
    if not pdf_files:
        logger.warning("処理するPDFファイルが見つかりませんでした。")
        return
    
    # 各PDFファイルを処理
    with alive_bar(len(pdf_files), title="PDFファイルを処理中") as bar:
        for pdf_file in pdf_files:
            try:
                process_pdf_file(pdf_file, output_dir)
            except Exception as e:
                logger.error(f"PDFファイルの処理中にエラーが発生しました: {pdf_file} - {e}")
                raise  # 開発方針に従い、エラーで異常終了
            bar()
    
    logger.info(f"処理完了: {len(pdf_files)}個のPDFファイルを処理しました。")


if __name__ == "__main__":
    main()
