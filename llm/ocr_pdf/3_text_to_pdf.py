#!/usr/bin/env python3
"""
テキストファイルとPDFファイルから検索可能なPDFを作成するスクリプト
output/text/内のテキストファイルとinput/内のPDFファイルを読み込み、
PDFページを切り出してテキストを検索可能なテキストレイヤーとして追加したPDFを作成し、
output/pdf/に保存する
"""

import glob
import tomllib
from pathlib import Path
from typing import List, Optional

from natsort import natsorted
from alive_progress import alive_bar
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color


def load_config():
    """config.tomlから設定を読み込む"""
    with open("config.toml", "rb") as f:
        return tomllib.load(f)


def get_input_pdf_path() -> Path:
    """inputディレクトリのPDFファイルを取得"""
    pdf_files = glob.glob("input/*.pdf")
    assert len(pdf_files) == 1, f"PDFファイルは1つである必要があります。現在: {len(pdf_files)}個"
    return Path(pdf_files[0])


def extract_pdf_page(pdf_path: Path, page_number: int) -> bytes:
    """PDFから指定したページを切り出してバイトデータとして返す"""
    with open(pdf_path, 'rb') as file:
        reader = PdfReader(file)
        writer = PdfWriter()
        
        # 指定したページを追加（0ベースインデックス）
        writer.add_page(reader.pages[page_number - 1])
        
        # バイトデータとして出力
        import io
        output_stream = io.BytesIO()
        writer.write(output_stream)
        return output_stream.getvalue()


def get_text_files() -> List[Path]:
    """output/text/内のテキストファイルを取得（番号順にソート）"""
    text_dir = Path("output/text")
    assert text_dir.exists(), "output/text/ディレクトリが存在しません"
    
    text_files = glob.glob(str(text_dir / "*.txt"))
    # ファイル名で自然順ソート
    text_files = natsorted(text_files)
    return [Path(f) for f in text_files]


def get_page_number_from_text_file(text_path: Path) -> int:
    """テキストファイル名からページ番号を取得"""
    stem = text_path.stem
    # ファイル名の最後の数字を抽出（例: spreads_1 -> 1）
    import re
    match = re.search(r'_(\d+)$', stem)
    if match:
        return int(match.group(1))
    else:
        raise ValueError(f"テキストファイル名からページ番号を取得できません: {text_path.name}")


def read_text_file(text_path: Path) -> str:
    """テキストファイルを読み込む"""
    with open(text_path, "r", encoding="utf-8") as f:
        return f.read()


def create_text_overlay_page(text: str, page_width: float, page_height: float) -> bytes:
    """テキストレイヤーのみのPDFページを作成"""
    import io
    
    # メモリ上でPDFを作成
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    
    # テキストを検索可能なテキストレイヤーとして追加
    c.setFillColor(Color(0, 0, 0, alpha=0.8))  # 黒色で80%の不透明度
    c.setStrokeColor(Color(0, 0, 0, alpha=0.8))
    
    # テキストを1行ずつ配置
    lines = text.split('\n')
    font_size = 12  # 見やすいサイズに変更
    line_height = 14
    
    # 日本語フォントを使用（NotoSansCJKまたはシステムフォント）
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
        font_name = 'HeiseiKakuGo-W5'
    except:
        # フォールバック: システムの日本語フォント
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            # macOSの場合の日本語フォント
            pdfmetrics.registerFont(TTFont('NotoSansCJK', '/System/Library/Fonts/Hiragino Sans GB.ttc'))
            font_name = 'NotoSansCJK'
        except:
            # 最終フォールバック: Helvetica（日本語は表示されないが検索は可能）
            font_name = 'Helvetica'
    
    # テキストを固定位置(100, 100)に配置（左揃え・上揃え）
    text_x = 100  # 左から100ポイント
    text_y = page_height - 100  # 上から100ポイント（PDF座標系は下が0なので逆算）
    for i, line in enumerate(lines):
        if text_y < 0:  # ページの下部を超えたら終了
            break
        
        # テキストを長くする場合は繰り返して配置（検索性向上のため）
        c.setFont(font_name, font_size)
        text_object = c.beginText(text_x, text_y)
        
        # 日本語テキストの処理（文字単位で分割）
        chars = list(line)
        current_line = ""
        for char in chars:
            test_line = current_line + char
            # 行の幅をチェック（固定サイズで計算）
            char_width = font_size * 0.5  # 固定の文字幅（日本語文字想定）
            line_width = c.stringWidth(current_line, font_name, font_size) + char_width
            
            if line_width < page_width - text_x - 4:
                current_line = test_line
            else:
                if current_line:
                    text_object.textLine(current_line)
                current_line = char
        
        if current_line:
            text_object.textLine(current_line)
        
        c.drawText(text_object)
        text_y -= line_height  # 上から下に向かって配置するため減算
    
    # PDFを保存
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def add_page_to_pdf(writer: PdfWriter, text: str, pdf_page_data: bytes) -> None:
    """PDFWriterにページを追加（PDFページデータを直接使用）"""
    import io
    
    # PDFページデータからページを読み込み
    page_reader = PdfReader(io.BytesIO(pdf_page_data))
    page = page_reader.pages[0]
    
    # ページサイズを取得
    page_width = float(page.mediabox.width)
    page_height = float(page.mediabox.height)
    
    print(f"ページサイズ: {page_width} x {page_height}")
    print(f"テキスト内容（最初の100文字）: {text[:100]}...")
    
    # テキストレイヤーを追加するための新しいページを作成
    text_page_data = create_text_overlay_page(text, page_width, page_height)
    text_reader = PdfReader(io.BytesIO(text_page_data))
    text_page = text_reader.pages[0]
    
    print(f"テキストページ作成完了: {len(text_page_data)} bytes")
    
    # テキストページを元のページにマージ（ページを追加する前に実行）
    page.merge_page(text_page)
    
    print("テキストレイヤーのマージ完了")
    
    # マージしたページをWriterに追加
    writer.add_page(page)


def process_text_and_pdf_page(text_path: Path, pdf_path: Path) -> tuple[str, bytes]:
    """テキストファイルと対応するPDFページのペアを処理"""
    # テキストファイル名からページ番号を取得
    page_number = get_page_number_from_text_file(text_path)
    
    # テキストを読み込む
    text = read_text_file(text_path)
    
    # PDFから指定したページを切り出し
    pdf_page_data = extract_pdf_page(pdf_path, page_number)
    
    return text, pdf_page_data


def main():
    """メイン処理"""
    # 設定を読み込み
    config = load_config()
    
    # テキストファイル取得
    text_files = get_text_files()
    assert len(text_files) > 0, "処理するテキストファイルが見つかりません"
    
    # 入力PDFファイルを取得
    pdf_path = get_input_pdf_path()
    
    # 最大ページ数を設定から取得
    max_pages = config.get("pdf", {}).get("process_pages")
    if max_pages:
        print(f"最大処理ページ数: {max_pages}")
        # テキストファイル数を最大ページ数で制限
        text_files = text_files[:max_pages]
    
    print(f"見つかったテキストファイル: {len(text_files)}個")
    print(f"処理対象PDF: {pdf_path}")
    
    # 出力ファイルパス生成
    output_path = Path("output/pdf") / "combined.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # PDFWriterを使用してPDFファイルを作成
    writer = PdfWriter()
    
    # 順次処理でテキストとPDFページのペアを処理（番号順を保証）
    with alive_bar(len(text_files), title="PDFを作成中") as bar:
        for text_path in text_files:
            try:
                text, pdf_page_data = process_text_and_pdf_page(text_path, pdf_path)
                add_page_to_pdf(writer, text, pdf_page_data)
                print(f"完了: {text_path.name} -> PDFに追加")
            except Exception as e:
                print(f"エラー: {text_path.name} - {e}")
            finally:
                bar()
    
    # PDFを保存
    with open(output_path, 'wb') as output_file:
        writer.write(output_file)
    
    print(f"すべてのPDFページとテキストを結合したPDFが作成されました: {output_path}")


if __name__ == "__main__":
    main()
