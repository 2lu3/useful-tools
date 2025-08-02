#!/usr/bin/env python3

import csv
from pathlib import Path
from loguru import logger
from util import ask_openai
import pandas as pd


def get_toc_pages() -> list[Path]:
    """classification.csvから目次のページを取得する"""
    csv_path = Path("tmp/classification.csv")
    if not csv_path.exists():
        raise FileNotFoundError(f"Classification file not found: {csv_path}")
    
    # CSVを読み込み
    df = pd.read_csv(csv_path)
    
    toc_pages = df[df['type'] == '目次']['page'].tolist()
    
    if not toc_pages:
        raise RuntimeError("No TOC pages found in classification.csv")
    
    # 対応する画像ファイルのパスを取得
    image_paths = []
    missing_images = []
    
    for page_num in toc_pages:
        image_path = Path(f"tmp/image/{page_num:03d}.jpeg")
        if image_path.exists():
            image_paths.append(image_path)
        else:
            missing_images.append(image_path)
    
    if missing_images:
        raise FileNotFoundError(f"Missing image files: {missing_images}")
    
    return image_paths


def extract_toc_info(image_path: Path) -> str:
    """画像から目次の情報を抽出する"""
    prompt = """画像には目次の情報が入っています。
目次の情報を抽出してcsvにして。
期待する形式を下に示す
name, page
Disease A, 1
Disease B, 3 
Disease C, 4"""

    try:
        response = ask_openai(prompt, "", [image_path], model="o3")
        if not response:
            raise RuntimeError(f"Empty response from OpenAI for {image_path}")
        return response
    except Exception as e:
        raise RuntimeError(f"Error extracting TOC info from {image_path}: {e}")


def parse_csv_response(response: str) -> list[dict]:
    """OpenAIの応答からCSVデータをパースする"""
    lines = response.strip().split('\n')
    results = []
    invalid_lines = []
    
    for line in lines:
        if "name" in line and "page" in line:
            continue
        if ',' in line:
            parts = [part.strip() for part in line.split(',')]
            if len(parts) >= 2:
                try:
                    # ページ番号を整数に変換
                    page_num = int(parts[1])
                    results.append({
                        'name': parts[0],
                        'page': page_num
                    })
                except ValueError:
                    invalid_lines.append(line)
    
    if invalid_lines:
        logger.warning(f"Invalid lines in response: {invalid_lines}")
    
    if not results:
        raise RuntimeError("No valid disease entries found in OpenAI response")
    
    return results


def main():
    try:
        # 目次のページを取得
        toc_images = get_toc_pages()
        
        logger.info(f"Found {len(toc_images)} TOC pages")
        
        # すべての目次ページから情報を抽出
        all_diseases = []
        
        for image_path in toc_images:
            logger.info(f"Processing TOC page: {image_path}")
            
            # 目次情報を抽出
            response = extract_toc_info(image_path)
            
            # CSVレスポンスをパース
            diseases = parse_csv_response(response)
            all_diseases.extend(diseases)
            
            logger.info(f"Extracted {len(diseases)} diseases from {image_path}")
        
        if not all_diseases:
            raise RuntimeError("No diseases extracted from any TOC pages")
        
        # 結果をCSVファイルに保存
        output_path = Path("tmp/disease_page.csv")
        
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ['id', 'name', 'page']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for i, disease in enumerate(all_diseases):
                disease_with_id = {
                    'id': i,
                    'name': disease['name'],
                    'page': disease['page']
                }
                writer.writerow(disease_with_id)
        
        logger.info(f"Extracted {len(all_diseases)} diseases and saved to {output_path}")
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        raise


if __name__ == "__main__":
    main()
