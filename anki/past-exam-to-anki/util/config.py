#!/usr/bin/env python3
import os
import toml
from pathlib import Path


def load_config():
    """config.tomlファイルを読み込む"""
    # プロジェクトルートディレクトリを取得
    project_root = Path(__file__).parent.parent
    config_path = project_root / "config.toml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = toml.load(f)
    
    return config


def get_api_key():
    """環境変数からOpenAI APIキーを取得する"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY環境変数が設定されていません")
    return api_key
