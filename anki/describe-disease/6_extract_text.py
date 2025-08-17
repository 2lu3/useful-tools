#!/usr/bin/env python3

import csv
from pathlib import Path
from loguru import logger
from util import ask_openai, settings, find_image_file


def get_disease_page_ranges() -> list[dict]:
    """disease_page_range.csvから疾患ごとのページ範囲を取得する"""
    csv_path = Path("tmp/disease_page_range.csv")
    if not csv_path.exists():
        raise FileNotFoundError(f"Disease page range file not found: {csv_path}")
    
    # CSVを読み込み
    diseases = []
    with open(csv_path, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            diseases.append({
                'id': int(row['id']),
                'name': row['name'],
                'start': int(row['start']),
                'end': int(row['end'])
            })
    
    if not diseases:
        raise RuntimeError("No diseases found in disease_page_range.csv")
    
    logger.info(f"Found {len(diseases)} diseases")
    return diseases


def get_page_images(start_page: int, end_page: int) -> list[Path]:
    """指定されたページ範囲の画像ファイルを取得する"""
    images = []
    
    for page in range(start_page, end_page + 1):
        # find_image_file関数を使用して柔軟に画像パスを生成
        image_path = find_image_file(page)
        
        if image_path.exists():
            images.append(image_path)
            logger.debug(f"Found image: {image_path}")
        else:
            logger.warning(f"Image not found for page {page}: {image_path}")
    
    return images


def save_text_to_file(disease_id: int, text: str):
    """テキストをファイルに保存する"""
    # tmp/textディレクトリを作成
    text_dir = Path("tmp/text")
    text_dir.mkdir(parents=True, exist_ok=True)
    
    # IDを3桁で0埋めしたファイル名を生成
    output_path = text_dir / f"{disease_id:03d}.txt"
    
    with open(output_path, 'w', encoding='utf-8-sig') as f:
        f.write(text)
    
    logger.info(f"Saved text to {output_path}")
    return output_path


def main():
    try:
        # 疾患のページ範囲を取得
        diseases = get_disease_page_ranges()
        
        # 各疾患について処理
        for disease in diseases:
            disease_name = disease['name']
            start_page = disease['start']
            end_page = disease['end']
            
            logger.info(f"Processing disease: {disease_name} (pages {start_page}-{end_page})")
            
            # ページ範囲の画像を取得
            images = get_page_images(start_page, end_page)
            
            if not images:
                logger.warning(f"No images found for disease '{disease_name}' (pages {start_page}-{end_page})")
                continue
            
            # OpenAIに送信するプロンプト
            system_prompt = "画像には医学知識がノートとしてまとめられているので、与えられたトピックの観点で文章として記述して。画像の内容を忠実に記述し、画像に含まれていない知識は含めないで。ただし、画像には指定されたトピックとは関係ない情報が含まれているので、必要な情報のみを抽出して記述して。"
            user_text = f"「{disease_name}」の医学知識を画像から抽出してください。"
            
            try:
                # OpenAIに画像を送信してテキストを取得
                logger.info(f"Sending {len(images)} images to OpenAI for disease '{disease_name}'")
                text = ask_openai(system_prompt, user_text, images, model=settings.text_extraction_model)
                
                # テキストをファイルに保存
                save_text_to_file(disease['id'], text)
                
                logger.info(f"Successfully processed disease '{disease_name}'")
                
            except Exception as e:
                logger.error(f"Error processing disease '{disease_name}': {e}")
                continue
        
        logger.info("Text extraction completed")
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        raise


if __name__ == "__main__":
    main()
