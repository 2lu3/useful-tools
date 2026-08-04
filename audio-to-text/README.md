# audio-to-text

OpenAI Speech-to-Text API で音声ファイルをテキストに変換する CLI です。

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- `ffmpeg` / `ffprobe`（25MB 超の分割時に使用）
- 環境変数 `OPENAI_API_KEY`

## Setup

```bash
cd audio-to-text
uv sync
```

## Usage

```bash
uv run python transcribe.py -i input.mp3 -o output.txt
uv run python transcribe.py -i input.wav -o output.txt -m gpt-4o-transcribe
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `-i` / `--input` | Yes | — | 入力音声ファイル |
| `-o` / `--output` | Yes | — | 出力テキストファイル |
| `-m` / `--model` | No | `gpt-transcribe` | OpenAI STT モデル名 |

言語は日本語（`ja`）固定です。CLI での変更はできません。

対応フォーマット例: `mp3`, `mp4`, `mpeg`, `mpga`, `m4a`, `wav`, `webm` など（OpenAI API が受け付ける形式）。

入力が **25MB 超** の場合は、ffmpeg でモノラル MP3 チャンクに分割して順に転写し、結果を結合します。

## Models (performance & pricing guide)

料金は OpenAI 公式 Pricing（2026-08 時点）の目安です。変更されることがあるため、最新は [Pricing](https://developers.openai.com/api/docs/pricing) を確認してください。

| Model | Approx. price | Accuracy / notes | Best for |
|-------|---------------|------------------|----------|
| `gpt-transcribe` | **$0.0045 / min** | 現行のファイル転写向け推奨系。精度と価格のバランス | デフォルト |
| `gpt-4o-mini-transcribe` | **$0.003 / min** | コスト重視。多くの用途で十分な精度 | 大量処理 |
| `gpt-4o-transcribe` | **$0.006 / min** | mini より高精度寄り | 聞き取りづらい音声・品質優先 |
| `whisper-1` | 約 **$0.006 / min**（レガシー） | タイムスタンプ / SRT・VTT など旧機能向け。新規は非推奨寄り | 字幕・単語タイムスタンプが必要な場合 |

目安コスト例（60 分の音声）:

| Model | ~60 min cost |
|-------|--------------|
| `gpt-4o-mini-transcribe` | ~$0.18 |
| `gpt-transcribe` | ~$0.27 |
| `gpt-4o-transcribe` / `whisper-1` | ~$0.36 |

### 選び方

1. まずは `gpt-transcribe`（デフォルト）
2. コストを抑えたいなら `gpt-4o-mini-transcribe`
3. さらに精度が欲しければ `gpt-4o-transcribe`
4. 単語タイムスタンプや SRT/VTT が必要なら `whisper-1`

リアルタイム配信向けの `gpt-live-transcribe` はこのツールの対象外です（ファイル転写のみ）。
