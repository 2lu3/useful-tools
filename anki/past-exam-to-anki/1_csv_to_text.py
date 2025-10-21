#!/usr/bin/env python3
import glob
from pathlib import Path
from loguru import logger
import pandas as pd
from util.config import load_config
from typing import Literal
from dataclasses import dataclass


@dataclass
class CsvFile:
    path: Path
    type: Literal["csv"]


def search_csv_files(input_dir: Path) -> list[CsvFile]:
    """inputディレクトリからCSVファイルを検索する"""
    config = load_config()
    results = []
    
    # CSVファイルの拡張子を取得
    csv_extensions = config["file_extensions"]["csv"]
    
    for ext in csv_extensions:
        globbed_files = glob.glob(str(input_dir / ext))
        files = [CsvFile(path=Path(path), type="csv") for path in globbed_files]
        results.extend(files)
    
    logger.info(f"見つかったCSVファイル数: {len(results)}")
    return results


def csv_to_text_files(csv_files: list[CsvFile], output_dir: Path):
    """CSVファイルの各セルを1問題としてtxtファイルに保存"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for csv_file in csv_files:
        logger.info(f"処理中: {csv_file.path}")
        
        # CSVファイルを読み込み
        df = pd.read_csv(csv_file.path, encoding="utf-8-sig", dtype=str, na_filter=False, header=None)
        
        # 有効なセル（空でないセル）をカウント
        valid_cells = []
        for row_idx, row in df.iterrows():
            for col_idx, cell in enumerate(row):
                if pd.notna(cell) and str(cell).strip():
                    valid_cells.append((row_idx, col_idx, str(cell).strip()))
        
        total_cells = len(valid_cells)
        logger.info(f"有効なセル数: {total_cells}")
        
        # ファイル名の桁数を決定（問題数に応じて）
        if total_cells == 0:
            logger.warning(f"有効なセルが見つかりません: {csv_file.path}")
            continue
            
        # 桁数を計算（数値の桁数を直接計算）
        digit_width = len(str(total_cells))
        
        # 各セルをtxtファイルとして保存
        for i, (row_idx, col_idx, cell_content) in enumerate(valid_cells):
            # ファイル名を生成（例：filename_0001.txt, filename_0002.txt）
            file_name = f"{csv_file.path.stem}_{i+1:0{digit_width}d}.txt"
            output_file = output_dir / file_name
            
            # セルの内容をクリーンアップ（改行を空白に置換）
            cleaned_content = cell_content.replace("\n", " ").replace("\r", "")
            
            # ファイルに保存
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(cleaned_content)
            
            logger.debug(f"保存: {output_file}")
        
        logger.info(f"完了: {csv_file.path} -> {total_cells}個のtxtファイルを作成")


def main():
    """メイン処理"""
    # 設定ファイルを読み込み
    config = load_config()
    
    # 入力ディレクトリと出力ディレクトリを設定
    input_dir = Path(__file__).parent / "input"
    output_dir = Path(__file__).parent / "output" / "single_problem"
    
    # CSVファイルを検索
    csv_files = search_csv_files(input_dir)
    
    if not csv_files:
        logger.warning("CSVファイルが見つかりませんでした。")
        return
    
    # CSVファイルをtxtファイルに変換
    csv_to_text_files(csv_files, output_dir)
    
    logger.info(f"\n処理完了: {len(csv_files)}個のCSVファイルを処理しました。")


if __name__ == "__main__":
    main()
