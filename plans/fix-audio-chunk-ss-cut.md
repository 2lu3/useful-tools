# fix: audio-to-text チャンク分割を -ss/-t に変更

Issue: https://github.com/2lu3/useful-tools/issues/6

## Goal

25MB 超入力の分割で、末尾の破損 MP3 チャンクを作らないようにする。

## Root cause

`ffmpeg -f segment` + MP3 再エンコードで、計算チャンク数より多いほぼ空のファイルが生成され、OpenAI が拒否する。

## Approach

1. `build_split_command` / `segment` muxer を削除
2. 各チャンクを `ffmpeg -ss <start> -i <input> -t <duration> ... chunk_NNN.mp3` で個別生成
3. `-ss` は `-i` の前（コンテナシーク）に置く。長時間音声で各チャンクを高速に切り出せる。STT ではフレーム精度は不要
4. 最終チャンクは残り時間を `min(segment_sec, duration - start)` で計算
5. README の分割説明を「時間指定カット」に合わせて更新（必要なら）

## Steps

1. `split_audio_into_chunks` を個別カット実装に置換
2. ローカルで `data/2.m4a` の分割だけ再現し、チャンク数が期待どおり・全チャンクが再生可能であることを確認
3. （API キーがあれば）転写まで通す

## Out of scope

- モデル・言語・CLI フラグの変更
- data/ 配下の音声ファイルのコミット
