#!/usr/bin/env python3
import base64
import csv
import glob
import json
import os
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)  # 並列処理用のインポート
from pathlib import Path

import openai
from loguru import logger  # ロギングライブラリ


def encode_image_to_base64(image_path):
    """画像をbase64エンコードする"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def send_image_to_openai(image_path, prompt, api_key):
    """画像とプロンプトをOpenAI APIに送信する"""
    # 画像をbase64エンコード
    base64_image = encode_image_to_base64(image_path)

    # OpenAIクライアントを設定
    client = openai.OpenAI(api_key=api_key)

    try:
        response = client.responses.create(
                #model="o3",
            model="o3-pro",
            reasoning={"effort": "medium"},
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{base64_image}",
                        },
                    ],
                }
            ],
        )
        # Responses API では `output_text` に生成されたテキストが格納される
        return getattr(response, "output_text", None)
    except Exception as e:
        logger.error(f"API呼び出しエラー: {e}")
        return None


def send_text_to_openai(text_content, prompt, api_key):
    """テキストとプロンプトをOpenAI APIに送信する"""
    # OpenAIクライアントを設定
    client = openai.OpenAI(api_key=api_key)

    try:
        response = client.responses.create(
            model="o3",
            reasoning={"effort": "medium"},
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": f"{prompt}\n\n{text_content}"},
                    ],
                }
            ],
        )
        # Responses API では `output_text` に生成されたテキストが格納される
        return getattr(response, "output_text", None)
    except Exception as e:
        logger.error(f"API呼び出しエラー: {e}")
        return None


def send_csv_row_to_openai(csv_row, prompt, api_key):
    """CSVの行データとプロンプトをOpenAI APIに送信する"""
    # CSVの行を文字列に変換（改行文字を除去）
    csv_content = ", ".join([cell.strip() for cell in csv_row])
    
    # OpenAIクライアントを設定
    client = openai.OpenAI(api_key=api_key)

    try:
        response = client.responses.create(
            model="o3",
            reasoning={"effort": "medium"},
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": f"{prompt}\n\nCSVデータ: {csv_content}"},
                    ],
                }
            ],
        )
        # Responses API では `output_text` に生成されたテキストが格納される
        return getattr(response, "output_text", None)
    except Exception as e:
        logger.error(f"API呼び出しエラー: {e}")
        return None


def is_image_file(file_path):
    """ファイルが画像ファイルかどうかを判定する"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    return Path(file_path).suffix.lower() in image_extensions


def is_text_file(file_path):
    """ファイルがテキストファイルかどうかを判定する"""
    text_extensions = ['.txt', '.md']
    return Path(file_path).suffix.lower() in text_extensions


def is_csv_file(file_path):
    """ファイルがCSVファイルかどうかを判定する"""
    csv_extensions = ['.csv']
    return Path(file_path).suffix.lower() in csv_extensions


def read_text_file(file_path):
    """テキストファイルを読み込む"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"テキストファイル読み込みエラー: {e}")
        return None


def read_csv_file(file_path):
    """CSVファイルを読み込んで各行をリストで返す（コンマ区切り）"""
    try:
        rows = []
        with open(file_path, "r", encoding="utf-8-sig") as f:  # BOMを自動除去
            csv_reader = csv.reader(f, delimiter=',')
            for row in csv_reader:
                if row:  # 空行をスキップ
                    # 各セルの前後の空白と改行文字を除去
                    cleaned_row = [cell.strip().replace('\n', ' ').replace('\r', '') for cell in row]
                    rows.append(cleaned_row)
        return rows
    except Exception as e:
        logger.error(f"CSVファイル読み込みエラー: {e}")
        return None


def process_files_in_input_directory(prompt, api_key):
    """inputディレクトリ内の画像、テキスト、CSVファイルを処理する"""
    # サポートするファイル形式
    image_extensions = ["*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp", "*.webp"]
    text_extensions = ["*.txt", "*.md"]
    csv_extensions = ["*.csv"]

    # inputディレクトリのパス
    input_dir = Path("input")
    output_dir = Path("text")
    output_dir.mkdir(exist_ok=True)

    if not input_dir.exists():
        logger.error("inputディレクトリが存在しません。")
        return

    # ファイルを検索
    all_files = []
    
    # 画像ファイルを検索
    for ext in image_extensions:
        all_files.extend(glob.glob(str(input_dir / ext)))
        all_files.extend(glob.glob(str(input_dir / ext.upper())))
    
    # テキストファイルを検索
    for ext in text_extensions:
        all_files.extend(glob.glob(str(input_dir / ext)))
        all_files.extend(glob.glob(str(input_dir / ext.upper())))
    
    # CSVファイルを検索
    for ext in csv_extensions:
        all_files.extend(glob.glob(str(input_dir / ext)))
        all_files.extend(glob.glob(str(input_dir / ext.upper())))

    if not all_files:
        logger.error("inputディレクトリに処理可能なファイルが見つかりません。")
        return

    logger.info(f"見つかったファイル数: {len(all_files)}")

    # ThreadPoolExecutor を用いて並列にファイルを処理
    results = {}

    def worker(file_path):
        logger.info(f"処理中: {file_path}")
        
        if is_image_file(file_path):
            res = send_image_to_openai(file_path, prompt, api_key)
            return file_path, res
        elif is_text_file(file_path):
            text_content = read_text_file(file_path)
            if text_content is None:
                return file_path, None
            res = send_text_to_openai(text_content, prompt, api_key)
            return file_path, res
        elif is_csv_file(file_path):
            # CSVファイルの場合は各行を個別に処理
            csv_rows = read_csv_file(file_path)
            if csv_rows is None:
                return file_path, None
            
            csv_results = {}
            question_counter = 1
            
            for i, row in enumerate(csv_rows):
                logger.info(f"CSV行 {i+1} を処理中: {file_path}")
                
                # 各行をカンマで分割して各問題を個別に処理
                for question_text in row:
                    if question_text.strip():  # 空でない場合のみ処理
                        logger.info(f"問題 {question_counter} を処理中: {file_path}")
                        logger.debug(f"問題 {question_counter} の内容: {question_text}")
                        res = send_csv_row_to_openai([question_text], prompt, api_key)
                        if res:
                            csv_results[f"question_{question_counter}"] = res
                            # 各問題の結果を個別に保存
                            save_csv_result_to_file(file_path, question_counter, res, output_dir)
                            question_counter += 1
                        else:
                            logger.error(f"エラー: {file_path}の問題{question_counter}の処理に失敗しました")
                            question_counter += 1
            
            return file_path, csv_results
        else:
            logger.warning(f"サポートされていないファイル形式: {file_path}")
            return file_path, None

    max_workers = min(5, len(all_files))  # ワーカー数を制限
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(worker, file_path) for file_path in all_files]
        for future in as_completed(futures):
            file_path, res = future.result()
            if res:
                results[file_path] = res
                if not is_csv_file(file_path):  # CSVファイル以外は通常の保存処理
                    logger.info(f"結果を{file_path}に保存しました")
                    save_result_to_file(file_path, res, output_dir)
            else:
                logger.error(f"エラー: {file_path}の処理に失敗しました")

    return results


def save_result_to_file(file_path, result, output_dir):
    """ファイルごとにoutputディレクトリに同名の.txtファイルで保存"""
    file_name = Path(file_path).stem
    output_file = output_dir / f"{file_name}.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result)
    logger.info(f"結果を {output_file} に保存しました。")


def save_csv_result_to_file(csv_file_path, row_number, result, output_dir):
    """CSVの各行の結果を個別のファイルで保存"""
    csv_file_name = Path(csv_file_path).stem
    output_file = output_dir / f"{csv_file_name}_row{row_number:03d}.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result)
    logger.info(f"CSV行{row_number}の結果を {output_file} に保存しました。")


def main():
    # 設定
# - 一般には使われないような一部の専門用語にはふりがなを()でつけて

    prompt = """
過去問暗記でAnkiアプリに入れるデータを作成したいので、問題・解答・解説・正誤訂正を記載して

全体

- 文字の大きさはすべて同じにして、太字や大文字は使わないで
- 解答・解説に医学的に誤りがある場合は正しい知識で置き換えて、その旨を正誤訂正に記載して
- 一般には使われない専門用語は、最後に専門用語と読み方の一覧を記載して

問題について

- 問題番号が与えられている場合は、一番最初に記載して
- 誤字脱字等があれば適切に修正して
- 誤字脱字以外は与えられた文章もしくは画像を改変しないで

解答について

- 問題が選択肢式の場合
    - 問題の選択肢の番号(a,b,cや1,2,3など)だけを列挙し、選択肢の内容は解答に含めないで
    - 選択肢の内容が真実の場合は、✅️を行の最初につけて
        - 誤っているものを選べという問題なら、誤っていない(=真実)選択肢に✅️をつけて
    - 選択肢の番号ごとに背景知識を簡潔に1行で説明して
    - 選択肢の番号の順番を入れ替えないで
- 問題が記述式の場合
    - 模範解答を記載して

解説について

- 問題を解くうえで身につけておくべき背景知識を体系的に記載して
- 例えば、問題でGERDの症状が問われていた場合、GERDの疾患自体の説明をして
- 必要なら「・」を用いた箇条書きや→を使用して

以下に例を示す。ただし、()は説明なので、実際の出力には入れないこと。

問題10(←問題番号が与えられている場合に書く) 正しい選択肢を選べ(←与えられている問題文。今回は選択肢式)

1. XOはOXに使われている
2. XXではOOの症状がある
3. XXではOXOが治療薬として使われている

解答
1: XXが使われている。XOが使われているのはOOのような場合。
2: ✅️ OOは重要な所見の一つ（←真実を述べている選択肢なので✅️がある）
3: OOの説明。OOはOYが特徴である。XXではBが使われている。

解説

- OO疾患はXXの低下によってOXが引き起こされる病気で、AやB、Cという症状もある。
- 鑑別疾患としてXOがあるが、OOとはこのような違いがある

正誤訂正

- 解答では1番が正解で根拠としてOOが記載されていたが、OOはXXという理由で誤り
- 解答ではOXと記述されていたが、OXはOOという理由で誤り

専門用語

- 幽門狭窄症(ゆうもんきょうさくしょう)

"""  # プロンプトを変更してください
    api_key = os.getenv("OPENAI_API_KEY")  # 環境変数からAPIキーを取得

    if not api_key:
        logger.error("OPENAI_API_KEY環境変数が設定されていません。")
        logger.info("export OPENAI_API_KEY='your_api_key_here' で設定してください。")
        return

    # ファイル処理を実行
    results = process_files_in_input_directory(prompt, api_key)

    if results:
        logger.info(f"\n処理完了: {len(results)}個のファイルを処理しました。")


if __name__ == "__main__":
    main()
