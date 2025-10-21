# Past Exam to Anki

## 開発方針

* ログ出力はloguruを使う
* パッケージ追加はuvを使う
* なにか問題が起きたときに絶対に把握したいので、プログラムを異常終了させて
  * try-catchは基本いらない。そのままエラー出せばいい
  * 前提条件はif→logger.errorより、assertで簡潔にしたい


## ディレクトリ構成

* input/
  * テキスト：txt
    * 1問1ファイル
    * 複数問1ファイル
  * pdf：pdf
    * 複数問1ファイル
  * 画像：png, jpg
    * 1問1ファイル
* output/
  * anki.csv
    * 生成物
  * image/
    * pdf中に含まれる画像素材
    * ファイル名はハッシュ化されている
  * textualized/
    * pdf, 画像をテキスト化したものをtxt形式で保存する
  * single_problem/
    * テキストもしくはtextualizedデータには複数問題が記載されている場合があり、その場合は分割して1問1ファイルで保存する
  * normalized/
    * llmによる修正を受けたあとの問題
  * tmp
    * 処理中に一時保存する


## スクリプト

### 1_csv_to_text.py

### 2_pdf_to_text.py

### 3_image_to_text.py

