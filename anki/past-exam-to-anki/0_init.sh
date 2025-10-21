#!/bin/bash

# Past Exam to Anki - ディレクトリ初期化スクリプト
# ReadMe.mdに記載されたディレクトリ構造を作成します

echo "ディレクトリ構造を初期化しています..."

rm -rf output/*

# outputディレクトリを作成
mkdir -p output

# output配下のディレクトリを作成
mkdir -p output/image
mkdir -p output/textualized
mkdir -p output/single_problem
mkdir -p output/normalized
mkdir -p output/tmp

echo "以下のディレクトリ構造を作成しました:"
echo "output/"
echo "├── image/          # pdf中に含まれる画像素材（ファイル名はハッシュ化）"
echo "├── textualized/    # pdf, 画像をテキスト化したものをtxt形式で保存"
echo "├── single_problem/ # 複数問題を分割して1問1ファイルで保存"
echo "├── normalized/     # llmによる修正を受けたあとの問題"
echo "└── tmp/           # 処理中に一時保存する"

echo "初期化完了！"
