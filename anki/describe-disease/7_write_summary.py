#!/usr/bin/env python3

import csv
from pathlib import Path
from loguru import logger
from util import ask_openai
from alive_progress import alive_bar


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


def create_summary_from_text(disease_name: str, text: str) -> str:
    """テキストから疾患の要約を作成する"""
    system_prompt = """指定された疾患/トピックに関して、与えられたテキストの情報のみを情報源として、以下の形式に従って医学知識を記述してください。
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
    
    response = ask_openai(system_prompt, user_text, [], model="o3")
    if not response:
        raise RuntimeError(f"Empty response from OpenAI for disease '{disease_name}'")
    
    logger.debug(f"Generated summary for disease '{disease_name}': {len(response)} characters")
    return response


def save_summary_to_file(disease_id: int, summary: str):
    """要約をファイルに保存する"""
    output_dir = Path("tmp/summary")
    output_dir.mkdir(exist_ok=True)
    
    output_path = output_dir / f"{disease_id:03d}.txt"
    
    with open(output_path, 'w', encoding='utf-8-sig') as f:
        f.write(summary)
    
    logger.info(f"Saved summary for disease ID {disease_id} to {output_path}")


def main():
    # 疾患のページ範囲を取得
    diseases = get_disease_page_ranges()
    
    # 各疾患について要約を作成
    with alive_bar(len(diseases), title="Creating summaries") as bar:
        for disease in diseases:
            disease_name = disease['name']
            disease_id = disease['id']
            
            
            # テキストファイルを読み込み
            text = get_disease_text(disease_id)
            
            # 要約を作成
            summary = create_summary_from_text(disease_name, text)
            
            # 要約をファイルに保存
            save_summary_to_file(disease_id, summary)
            
            bar()
    
    logger.info("Summary creation completed successfully")


if __name__ == "__main__":
    main()
