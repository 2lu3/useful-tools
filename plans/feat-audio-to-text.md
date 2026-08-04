# feat: audio-to-text CLI

Issue: https://github.com/2lu3/useful-tools/issues/5

## Goal

OpenAI Speech-to-Text API で音声 → テキスト変換する CLI を `audio-to-text/` に追加する。

## CLI

```bash
uv run python transcribe.py -i input.mp3 -o output.txt
uv run python transcribe.py -i input.wav -o output.txt -m gpt-4o-transcribe
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `-i` / `--input` | Yes | — | 入力音声ファイル |
| `-o` / `--output` | Yes | — | 出力テキストファイル |
| `-m` / `--model` | No | `gpt-transcribe` | OpenAI STT モデル名 |

## Design decisions

- API キー: `OPENAI_API_KEY`
- 言語は日本語（`ja`）固定（CLI オプションなし）
- デフォルトモデル: `gpt-transcribe`
- アップロード上限 25MB を超える場合は ffmpeg で時間分割し、順に文字起こしして結合
- 安全マージンとしてチャンク上限は 20MB 相当の長さで分割
- パッケージ管理は uv、依存は `openai`

## Files

- `audio-to-text/pyproject.toml`
- `audio-to-text/transcribe.py`
- `audio-to-text/README.md`（モデル性能・料金目安を含む）

## Steps

1. uv プロジェクト初期化と依存追加
2. CLI + 転写 + チャンク分割の実装
3. README 作成
4. ローカルで import / help 確認
