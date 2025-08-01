import os
import base64
from pathlib import Path

import openai
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
    before_sleep=before_log(logger, logging.WARNING),
)


@retry_openai
def ask_openai(
    system_prompt: str,
    user_text: str,
    image_paths: list[Path],
    temperature: float = 0.5,
    model: str = "gpt-4o",
) -> str:
    openai.api_key = os.environ["OPENAI_API_KEY"]

    # 1) まず user メッセージの content リストを組み立てる
    
    content: list[dict[str, Any]] = [{"type": "text", "text": user_text}]
    for path in image_paths:
        with path.open("rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/{path.suffix[1:]};base64,{b64}",
                    # 必要なら detail を low / high / auto で指定
                    "detail": "auto",
                }
            }
        )

    # 2) ChatCompletion 呼び出し
    if "4o" in model:
        response = openai.chat.completions.create(
            model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
    )
    else:
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
        )
    return response.choices[0].message.content.strip()
