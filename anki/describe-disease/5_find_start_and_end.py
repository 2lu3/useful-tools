#!/usr/bin/env python3

import csv
from pathlib import Path
from loguru import logger
import pandas as pd


def get_explanation_pages() -> set[int]:
    """classification.csvから説明ページのみを取得する"""
    csv_path = Path("tmp/classification.csv")
    if not csv_path.exists():
        raise FileNotFoundError(f"Classification file not found: {csv_path}")
    
    # CSVを読み込み
    df = pd.read_csv(csv_path)
    
    # 説明ページのページ番号を取得（整数に変換）
    explanation_pages = set(int(page) for page in df[df['type'] == '説明']['page'].tolist())
    
    if not explanation_pages:
        raise RuntimeError("No explanation pages found in classification.csv")
    
    logger.info(f"Found {len(explanation_pages)} explanation pages")
    return explanation_pages


def get_disease_start_pages() -> list[dict]:
    """disease_page.csvから疾患ごとの説明開始ページを取得する"""
    csv_path = Path("tmp/disease_page.csv")
    if not csv_path.exists():
        raise FileNotFoundError(f"Disease page file not found: {csv_path}")
    
    # CSVを読み込み
    df = pd.read_csv(csv_path)
    
    # 疾患名と開始ページのリストを作成
    diseases = []
    for _, row in df.iterrows():
        diseases.append({
            'id': row['id'],
            'name': row['name'],
            'start': int(row['page'])  # ページ番号を整数に変換
        })
    
    if not diseases:
        raise RuntimeError("No diseases found in disease_page.csv")
    
    logger.info(f"Found {len(diseases)} diseases")
    return diseases


def verify_start_page_is_explanation(start_page: int, explanation_pages: set[int]) -> bool:
    """開始ページが説明ページかどうかを確認する"""
    return start_page in explanation_pages


def find_end_page(start_page: int, next_start_page: int, explanation_pages: set[int]) -> int:
    """終了ページを求める"""
    # ページ番号を整数に変換
    start_page = int(start_page)
    
    # 次の疾患の開始ページが存在する場合
    if next_start_page is not None:
        next_start_page = int(next_start_page)
        # max(次の疾患の開始ページ-1, 開始ページ)を計算
        max_possible_end = max(next_start_page - 1, start_page)
    else:
        # 最後の疾患の場合、十分大きな値を設定
        max_possible_end = 10000  # 適当な大きな値
    
    # 開始ページから順に調べて、説明ページ以外が存在するかチェック
    end_page = start_page
    
    for page in range(start_page + 1, max_possible_end + 1):
        if page not in explanation_pages:
            # 説明ページ以外が見つかった場合、その前のページを終了ページとする
            end_page = page - 1
            break
        end_page = page
    
    return end_page


def main():
    try:
        # 説明ページを取得
        explanation_pages = get_explanation_pages()
        
        # 疾患の開始ページを取得
        diseases = get_disease_start_pages()
        
        # 疾患ごとに開始ページと終了ページを計算
        disease_ranges = []
        
        for i, disease in enumerate(diseases):
            start_page = disease['start']
            disease_name = disease['name']
            
            logger.info(f"Processing disease: {disease_name} (start page: {start_page})")
            
            # 開始ページが説明ページかどうかを確認
            if not verify_start_page_is_explanation(start_page, explanation_pages):
                raise RuntimeError(f"Start page {start_page} for disease '{disease_name}' is not an explanation page")
            
            # 次の疾患の開始ページを取得（最後の疾患の場合はNone）
            next_start_page = None
            if i + 1 < len(diseases):
                next_start_page = diseases[i + 1]['start']
            
            # 終了ページを計算
            end_page = find_end_page(start_page, next_start_page, explanation_pages)
            
            # 結果をリストに追加
            disease_ranges.append({
                'id': disease['id'],
                'name': disease_name,
                'start': start_page,
                'end': end_page
            })
            
            logger.info(f"Disease '{disease_name}': pages {start_page}-{end_page}")
        
        # 結果をCSVファイルに保存
        output_path = Path("tmp/disease_page_range.csv")
        
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ['id', 'name', 'start', 'end']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for disease_range in disease_ranges:
                writer.writerow(disease_range)
        
        logger.info(f"Saved disease page ranges to {output_path}")
        logger.info(f"Processed {len(disease_ranges)} diseases")
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        raise


if __name__ == "__main__":
    main()
