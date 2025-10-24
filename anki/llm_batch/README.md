# LLM Batch

* inputディレクトリに配置されたテキスト・画像ファイルを並列してLLMに投げ、結果をoutputディレクトリに保存するツールです。

## 開発規定

* uv, black, alive-progressを使用する
* エラーハンドリングは行わず、問題が起きたらプログラムを異常終了させる
 * try-catchは使用しない
 * if文でのエラーチェックは行わず、assertを使う

## input/

可能な拡張子

* .txt
* .jpg
* .png

## output/

結果をtxtファイルとして保存する


## batcher.py

```bash
python batcher.py --prompt ./prompt/example.txt --model o3
```

* 入力ファイル名.txtとして保存する
* ThreadPoolExecutorで並列処理(max_wokrer=5)
