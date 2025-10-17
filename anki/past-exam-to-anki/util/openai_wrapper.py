#!/usr/bin/env python3
import base64
import openai
from .config import load_config, get_api_key


def encode_image_to_base64(image_path):
    """画像をbase64エンコードする"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def send_to_openai(prompt, image_paths=None, text_content=None):
    """プロンプトとコンテンツ（画像・テキスト）をOpenAI APIに送信する統合関数"""
    # APIキーとconfigを読み込み
    api_key = get_api_key()
    config = load_config()
    
    client = openai.OpenAI(api_key=api_key)
    
    # 共通モデルを使用
    model = config["openai"]["model"]
    
    # コンテンツの構築
    content = [{"type": "input_text", "text": prompt}]
    
    # 画像を追加
    if image_paths:
        for image_path in image_paths:
            # Pathオブジェクトを文字列に変換
            image_path_str = str(image_path)
            base64_image = encode_image_to_base64(image_path_str)
            content.append({
                "type": "input_image",
                "image_url": f"data:image/jpeg;base64,{base64_image}",
            })
    
    # テキストコンテンツを追加
    if text_content:
        content[0]["text"] = f"{prompt}\n\n{text_content}"
    
    response = client.responses.create(
        model=model,
        reasoning={"effort": config["openai"]["reasoning_effort"]},
        input=[
            {
                "role": "user",
                "content": content,
            }
        ],
    )
    return getattr(response, "output_text", None)
