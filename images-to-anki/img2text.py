import os
import glob
import base64
import openai
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed  # 並列処理用のインポート
from loguru import logger  # ロギングライブラリ

def encode_image_to_base64(image_path):
    """画像をbase64エンコードする"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def send_to_openai(image_path, prompt, api_key):
    """画像とプロンプトをOpenAI APIに送信する"""
    # 画像をbase64エンコード
    base64_image = encode_image_to_base64(image_path)
    
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
                        {
                            "type": "input_text",
                            "text": prompt
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    ]
                }
            ]
        )
        # Responses API では `output_text` に生成されたテキストが格納される
        return getattr(response, "output_text", None)
    except Exception as e:
        logger.error(f"API呼び出しエラー: {e}")
        return None

def process_images_in_input_directory(prompt, api_key):
    """inputディレクトリ内の画像を処理する"""
    # サポートする画像形式
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.webp']
    
    # inputディレクトリのパス
    input_dir = Path("input")
    output_dir = Path("text")
    output_dir.mkdir(exist_ok=True)
    
    if not input_dir.exists():
        logger.error("inputディレクトリが存在しません。")
        return
    
    # 画像ファイルを検索
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(str(input_dir / ext)))
        image_files.extend(glob.glob(str(input_dir / ext.upper())))
    
    if not image_files:
        logger.error("inputディレクトリに画像ファイルが見つかりません。")
        return
    
    logger.info(f"見つかった画像ファイル数: {len(image_files)}")
    
    # ThreadPoolExecutor を用いて並列に画像を処理
    results = {}

    def worker(img_path):
        logger.info(f"処理中: {img_path}")
        res = send_to_openai(img_path, prompt, api_key)
        return img_path, res

    max_workers = min(100, len(image_files))  # ワーカー数を制限
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(worker, img) for img in image_files]
        for future in as_completed(futures):
            img_path, res = future.result()
            if res:
                results[img_path] = res
                logger.info(f"結果を{img_path}に保存しました")
                save_result_to_file(img_path, res, output_dir)
            else:
                logger.error(f"エラー: {img_path}の処理に失敗しました")
    
    return results

def save_result_to_file(image_path, result, output_dir):
    """画像ごとにoutputディレクトリに同名の.txtファイルで保存"""
    image_name = Path(image_path).stem
    output_file = output_dir / f"{image_name}.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result)
    logger.info(f"結果を {output_file} に保存しました。")

def main():
    # 設定
    prompt = """
過去問暗記でAnkiアプリに入れるデータを作成したいので、問題・解答・解説を記載して

全体

- 文字の大きさはすべて同じにして、太字や大文字は使わないで

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

- その問題の理解の助けになる解説を体系的に記述して
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
"""  # プロンプトを変更してください
    api_key = os.getenv("OPENAI_API_KEY")  # 環境変数からAPIキーを取得

    if not api_key:
        logger.error("OPENAI_API_KEY環境変数が設定されていません。")
        logger.info("export OPENAI_API_KEY='your_api_key_here' で設定してください。")
        return
    
    # 画像処理を実行
    results = process_images_in_input_directory(prompt, api_key)
    
    if results:
        logger.info(f"\n処理完了: {len(results)}個の画像を処理しました。")

if __name__ == "__main__":
    main()
