#!/usr/bin/env python3
import base64
import openai
from .config import load_config, get_api_key


def encode_image_to_base64(image_path):
    """画像をbase64エンコードする"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def ask_llm(prompt, image_paths=None, text_content=None):
    """プロンプトとコンテンツ（画像・テキスト）をLLM APIに送信する統合関数"""
    # configを読み込み
    config = load_config()
    llm_config = config["llm"]
    
    # OpenAI使用フラグをチェック
    if llm_config["use_openai"]:
        return _ask_openai(prompt, image_paths, text_content, config)
    else:
        return _ask_lm_studio(prompt, image_paths, text_content, config)


def _ask_openai(prompt, image_paths=None, text_content=None, config=None):
    """OpenAI APIに送信"""
    if config is None:
        config = load_config()
    
    # APIキーを取得
    api_key = get_api_key()
    client = openai.OpenAI(api_key=api_key)
    
    # モデル設定を取得
    model = config["llm"]["model"]
    reasoning_effort = config["llm"]["reasoning_effort"]
    
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
        reasoning={"effort": reasoning_effort},
        input=[
            {
                "role": "user",
                "content": content,
            }
        ],
    )
    return getattr(response, "output_text", None)


def _ask_lm_studio(prompt, image_paths=None, text_content=None, config=None):
    """LM Studio APIに送信"""
    if config is None:
        config = load_config()
    
    # LM Studio設定を取得
    endpoint_url = config["llm"]["endpoint_url"]
    model = config["llm"]["model"]
    
    # エンドポイントURLからベースURLを取得
    client = openai.OpenAI(
        api_key="lm-studio",  # LM StudioはAPIキーを要求するが、実際には使用しない
        base_url=endpoint_url
    )
    
    # コンテンツの構築（LM Studio用）
    messages = []
    
    # テキストコンテンツを統合
    full_prompt = prompt
    if text_content:
        full_prompt = f"{prompt}\n\n{text_content}"
    
    # 画像がある場合はマルチモーダル対応
    if image_paths:
        content = [{"type": "text", "text": full_prompt}]
        
        # 画像を追加
        for image_path in image_paths:
            image_path_str = str(image_path)
            base64_image = encode_image_to_base64(image_path_str)
            content.append({
                "type": "image_url",
                "image_url": f"data:image/jpeg;base64,{base64_image}",
            })
        
        messages.append({
            "role": "user",
            "content": content
        })
    else:
        # テキストのみの場合
        messages.append({
            "role": "user",
            "content": full_prompt
        })
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=4000,
        temperature=0.7
    )
    
    return response.choices[0].message.content
