#!/usr/bin/env python3

from dataclasses import dataclass
from pathlib import Path
import pandas as pd
from util import ask_openai
import csv
from loguru import logger

@dataclass
class Disease:
    name: str
    start_page: int
    end_page: int

@dataclass
class Card:
    front: str
    back: str

def read_disease_page_index(csv_path: str) -> list[Disease]:

    # csv format:
    # name, page
    # Disease A, 1
    # Disease B, 3 
    # Disease C, 4

    # Exepected output:
    # [
    #     Disease(name='Disease A', start_page=1, end_page=2), # max(B's page - 1, A's page)
    #     Disease(name='Disease B', start_page=3, end_page=4), # max(C's page - 1, B's page)
    #     Disease(name='Disease C', start_page=4, end_page=5), # max(C's page - 1, C's page)
    # ] 

    # pandasを使ってCSVファイルを読み込み
    df = pd.read_csv(csv_path, encoding='utf-8')
    
    diseases = []
    
    for i, row in df.iterrows():
        name = row['疾患名'].strip()
        start_page = int(row['ページ数'])
        
        # 次の疾患のページを取得（最後の疾患の場合は適当な値）
        if i + 1 < len(df):
            next_page = int(df.iloc[i + 1]['ページ数'])
            end_page = next_page - 1
        else:
            # 最後の疾患の場合、start_page + 1 をend_pageとする
            end_page = start_page + 1
        
        # start_pageがend_pageより大きい場合は調整
        if start_page >= end_page:
            end_page = start_page + 1
            
        diseases.append(Disease(name=name, start_page=start_page, end_page=end_page))
    
    return diseases

def image2card(disease: Disease) -> Card:
    system_prompt = """多くの疾患もしくはトピックの核心を暗記を目的として、与えられた疾患に対する情報をフォーマットに従い記述して
疾患もしくはトピックに関連した画像を与えるので、その内容を抽出しまとめて
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
    user_text = f"疾患名: {disease.name}"
    image_paths = []
    for i in range(disease.start_page, disease.end_page):
        path = Path(f"tmp/explaination-{i:03d}.jpeg")
        if path.exists():
            image_paths.append(path)
        else:
            logger.warning(f"Image file not found: {path}")
            assert len(image_paths) > 0
            break
    
    if not image_paths:
        print(f"Error: No image files found for disease {disease.name}")
        return Card(front=disease.name, back="画像ファイルが見つかりませんでした")
    
    res = ask_openai(system_prompt, user_text, image_paths, model="o4-mini-2025-04-16")
    print(f"=== Response for {disease.name} ===")
    print(res)
    print("=== End Response ===")
    card = split_front_and_back(res)
    return card


def split_front_and_back(text: str) -> Card:
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
    return Card(front, back)


def initialize_csv():
    """CSVファイルを初期化する"""
    output_path = Path("output") / "cards.csv"
    output_path.parent.mkdir(exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)


def save_card(card: Card):
    """1件ずつCSVに追記する"""
    output_path = Path("output") / "cards.csv"
    with output_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([card.front, card.back])


def main():
    # プログラムの最初でCSVを初期化
    initialize_csv()
    
    diseases = read_disease_page_index("input/table.csv")

    for disease in diseases:
        card = image2card(disease)
        # 1件ずつCSVに追記
        save_card(card)

if __name__ == "__main__":
    main()

