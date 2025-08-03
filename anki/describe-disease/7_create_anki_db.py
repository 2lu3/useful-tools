#!/usr/bin/env python3

import csv
from pathlib import Path
from loguru import logger
from util import ask_openai


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


def get_disease_text(disease_id: int) -> str:
    """疾患IDに対応するテキストファイルを読み込む"""
    text_path = Path(f"tmp/text/{disease_id:03d}.txt")
    if not text_path.exists():
        raise FileNotFoundError(f"Text file not found: {text_path}")
    
    with open(text_path, 'r', encoding='utf-8-sig') as f:
        text = f.read().strip()
    
    if not text:
        raise RuntimeError(f"Text file is empty: {text_path}")
    
    logger.debug(f"Loaded text for disease ID {disease_id}: {len(text)} characters")
    return text


def create_card_from_text(disease_name: str, text: str) -> dict:
    """テキストからAnkiカードを作成する"""
    system_prompt = """指定された疾患/トピックに関して、与えられたテキストの情報のみを情報源として、以下の形式で医学知識を記述してください。
ただし、[]内は指示を記載しているだけなので出力には含めないで
例として、GERDが与えられたとします

GERD (胃食道逆流症)

説明
1. 一言でいうと[簡潔に文章でその疾患の本質を説明する]
下部食道括約筋(LES)がゆるみ、胃酸が逆流する疾患

2. 機序[このセクションは因果関係スタイルで説明する]
LES圧の低下
→胃酸逆流
→酸性環境
↓
食道粘膜炎
→Barret食道(粘膜が円柱上皮に置換される)
↓
食道腺癌

3. 典型患者像[覚えるべき観点を疫学的に明らかに有意なもののみ記載して]
・肥満
・高脂肪食
・Ca拮抗薬・亜硝酸薬(高血圧治療)

4. キーワード[関連する疾患などを列挙する]
・NERD(非びらん性食道逆流症)
粘膜障害あり→GERD,なし→NERD[必要なら簡単な説明をする]

・食道裂孔ヘルニア
・妊婦
・前屈
・臥位
"""

    user_text = f"疾患/トピック: {disease_name}\n\nテキスト内容:\n{text}"
    
    try:
        response = ask_openai(system_prompt, user_text, [], model="o4-mini")
        if not response:
            raise RuntimeError(f"Empty response from OpenAI for disease '{disease_name}'")
        
        logger.debug(f"Generated card for disease '{disease_name}': {len(response)} characters")
        return split_front_and_back(response)
        
    except Exception as e:
        raise RuntimeError(f"Error creating card for disease '{disease_name}': {e}")


def split_front_and_back(text: str) -> dict:
    """テキストをfrontとbackに分割する"""
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
            
            logger.info(f"Processing disease: {disease_name} (ID: {disease_id})")
            
            try:
                # テキストファイルを読み込み
                text = get_disease_text(disease_id)
                
                # カードを作成
                card = create_card_from_text(disease_name, text)
                cards.append(card)
                
                logger.info(f"Successfully created card for disease '{disease_name}'")
                
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

