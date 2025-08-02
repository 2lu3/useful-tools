import os
import base64
from pathlib import Path

import openai
from openai import OpenAI
from tenacity import (
    retry,
    retry_if_exception,
    wait_exponential,
    stop_after_attempt,
    before_log,
)
from loguru import logger
import logging
from typing import Any


client = OpenAI()


def is_rate_limit_error(e: BaseException) -> bool:
    # openai-python 1.x
    if isinstance(e, openai.RateLimitError):
        return True
    # 将来バージョンで APIStatusError が来ても 429 だけ拾う
    return (
        isinstance(e, openai.APIStatusError) and getattr(e, "status_code", None) == 429
    )


retry_openai = retry(
    reraise=True,
    retry=retry_if_exception(is_rate_limit_error),  # ← 判定関数
    wait=wait_exponential(multiplier=2, min=30, max=60),
    stop=stop_after_attempt(6),
    before_sleep=before_log(logger, logging.WARNING),  # type: ignore
)


@retry_openai
def ask_openai(system_prompt: str, user_text: str, images: list[Path], model: str):
    content: list[dict] = [{"type": "input_text", "text": user_text}]

    for path in images:
        with path.open("rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")

        content.append(
            {
                "type": "input_image",
                "image_url": f"data:image/{path.suffix[1:]};base64,{b64}",
            }
        )

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},  # type: ignore
        ],
    )

    # レスポンスからテキストを抽出
    if response.output and len(response.output) > 1:
        # 2番目の要素（ResponseOutputMessage）からテキストを取得
        message = response.output[1]
        if hasattr(message, 'content') and message.content:
            # contentの最初の要素からテキストを取得
            text_item = message.content[0]
            if hasattr(text_item, 'text'):
                return text_item.text.strip()
    
    # フォールバック
    return "No response"

