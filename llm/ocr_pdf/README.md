# LLM Batch

* inputディレクトリに配置されたテキスト・画像ファイルを並列してLLMに投げ、結果をoutputディレクトリに保存するツールです。

## 開発規定

* uv, black, alive-progressを使用する
* エラーハンドリングは行わず、問題が起きたらプログラムを異常終了させる
 * try-catchは使用しない
 * if文でのエラーチェックは行わず、assertを使う
* config.tomlに設定されている値を使って
  * ただし、config.tomlに追記はしないで

## input/

可能な拡張子

* .txt
* .jpg
* .png

## output/

* image/
* text/
* log/
* pdf/
