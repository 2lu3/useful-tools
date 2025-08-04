#!/usr/bin/env python3

import csv
from pathlib import Path
from loguru import logger


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


def get_disease_images(disease_id: int, start_page: int, end_page: int) -> list[str]:
    """疾患のページ範囲に対応する画像のハッシュ値を取得する"""
    # hashed_images.csvから画像情報を読み込み
    csv_path = Path("tmp/hashed_images.csv")
    if not csv_path.exists():
        logger.warning(f"Hashed images file not found: {csv_path}")
        return []
    
    images = []
    with open(csv_path, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            page = int(row['page'])
            if start_page <= page <= end_page:
                images.append(row['hash'])
    
    logger.debug(f"Found {len(images)} images for disease ID {disease_id} (pages {start_page}-{end_page})")
    return images


def get_disease_summary(disease_id: int) -> str:
    """疾患IDに対応する要約ファイルを読み込む"""
    summary_path = Path(f"tmp/summary/{disease_id:03d}.txt")
    if not summary_path.exists():
        raise FileNotFoundError(f"Summary file not found: {summary_path}")
    
    with open(summary_path, 'r', encoding='utf-8-sig') as f:
        summary = f.read().strip()
    
    if not summary:
        raise RuntimeError(f"Summary file is empty: {summary_path}")
    
    logger.debug(f"Loaded summary for disease ID {disease_id}: {len(summary)} characters")
    return summary


def create_card_from_summary(disease_name: str, summary: str, images: list[str]) -> dict:
    """要約からAnkiカードを作成する"""
    logger.debug(f"Creating card for disease '{disease_name}': {len(summary)} characters")
    return split_front_and_back(summary, images)


def split_front_and_back(text: str, images: list[str]) -> dict:
    """テキストをfrontとbackに分割し、backに画像を追加する"""
    # "説明" で分割し、前後をfront/backに
    if "説明" in text:
        parts = text.split("説明", 1)
        front = parts[0].strip()
        back = "説明\n" + parts[1].strip()
    else:
        # "説明"が見つからない場合は、最初の改行で分割
        lines = text.split('\n')
        if len(lines) >= 2:
            front = lines[0].strip()
            back = '\n'.join(lines[1:]).strip()
        else:
            # 改行がない場合は、テキスト全体をbackに
            front = "疾患情報"
            back = text.strip()
    
    # backに画像を追加
    if images:
        image_html = "\n\n画像:\n"
        for image_hash in images:
            image_html += f'<img src="{image_hash}.jpeg">\n'
        back += image_html
    
    return {
        'front': front,
        'back': back
    }


def save_cards_to_csv(cards: list[dict]):
    """カードをCSVファイルに保存する"""
    output_path = Path("output/cards.csv")
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['front', 'back']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter='\t')
        
        #writer.writeheader()
        for card in cards:
            writer.writerow(card)
    
    logger.info(f"Saved {len(cards)} cards to {output_path}")


def main():
    try:
        # 疾患のページ範囲を取得
        diseases = get_disease_page_ranges()
        
        # 各疾患についてカードを作成
        cards = []
        
        for disease in diseases:
            disease_name = disease['name']
            disease_id = disease['id']
            start_page = disease['start']
            end_page = disease['end']
            
            logger.info(f"Processing disease: {disease_name} (ID: {disease_id}, pages: {start_page}-{end_page})")
            
            try:
                # 要約ファイルを読み込み
                summary = get_disease_summary(disease_id)
                
                # 疾患の画像を取得
                images = get_disease_images(disease_id, start_page, end_page)
                
                # カードを作成
                card = create_card_from_summary(disease_name, summary, images)
                cards.append(card)
                
                logger.info(f"Successfully created card for disease '{disease_name}' with {len(images)} images")
                
            except Exception as e:
                logger.error(f"Error processing disease '{disease_name}': {e}")
                continue
        
        if not cards:
            raise RuntimeError("No cards were created successfully")
        
        # カードをCSVファイルに保存
        save_cards_to_csv(cards)
        
        logger.info("Anki database creation completed successfully")
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        raise


if __name__ == "__main__":
    main()

