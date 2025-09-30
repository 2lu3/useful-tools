# ToDo

## general instruction

- ログにはloguruを使用して
- ファイルが完成したらblackとisortでフォーマットして
- パッケージの追加/削除にはuv add/removeを使用して(pipではなく)
- 複数のファイルを連続して処理するときは、loguruで記載するよりalive-progressで進捗を表示し、すべての処理が終わったらエラーや注意すべき情報をloguruで表示して

## 共通規格

### pair.json

```json
[
  {
    "source": "/path/to/original/file.jpg",
    "destination": "/path/to/output/images/hash.jpg",
    "filename": "hash.jpg",
    "hash": "md5hashvalue"
  }
]
```

### metadata.json

```json
{
  "hash.jpg": {
    "datetime": {
      "exif_datetime": "2023-01-01T12:00:00",
      "exif_datetime_original": "2023-01-01T12:00:00",
      "exif_datetime_digitized": "2023-01-01T12:00:00",
      "file_creation_time": "2023-01-01T12:00:00",
      "json_datetime": "2023-01-01T12:00:00"
    },
    "location": {
      "latitude": 35.6762,
      "longitude": 139.6503,
      "altitude": 10.5,
      "exif_gps": true,
      "json_location": true
    },
    "has_datetime": true,
    "has_location": true,
    "metadata_sources": ["exif", "json"]
  }
}
```

### supplemental_file_location.json

```json
{
  "hash.jpg": {
    "original_source": "/path/to/original/file.jpg",
    "metadata_file": "/path/to/metadata/file.supplemental-metadata.json",
    "metadata_type": "supplemental-metadata",
    "found": true,
    "file_exists": true
  }
}
```


## 1_copy_files.py

- [ ] 元のファイルの内容を把握して。今後、このファイルを以下の指示にしたがって改変する
- [ ] 入力ディレクトリは複数のtakeoutディレクトリではなくinputディレクトリだけにして(このあと、inputディレクトリを再帰的に検索する)
- [ ] 入力ディレクトリ下にあるすべてのファイルの拡張子を列挙する関数を作成して
- [ ] 事前に、画像と動画の拡張子をすべて列挙し、画像・動画として判定されなかった拡張子をすべてinfoログで表示して
- [ ] tmpディレクトリを作成する(すでにあるなら削除して作成することでリセット)
- [ ] すべての画像のファイル名をハッシュ値.拡張子に変換してoutput/images/にコピーして保管して
  - [ ] 階層構造は作らず、すべてimages直下に保存して
- [ ] コピー元とコピー先のパスの対応をoutput/pair.jsonに保存して

## 2_filter_missing_metadata.py

- [ ] 元のファイルを参考にしつつ改変して
- [ ] 1_copy_filesの入力・出力場所に準拠して
- [ ] output/imagesのすべての画像に対して、以下の情報があるかどうかを調査して
  - [ ] 撮影日時
  - [ ] 撮影座標
- [ ] output/metadata.json に写真のファイル名と上の情報を保存して。情報がない場合は欠落していることがわかるようにnullとかjson的にベストプラクティスに従って


## 3_find_metadata_file.py

- [ ] output/images下の画像の元の場所は output/pair.jsonに保管されているので、その情報を読み元の画像の場所を把握して
- [ ] metadataがjson等の形式で保存されているはずなので、どのようなルールでその画像の情報が保存されているかを調査して。これはプログラムに書かずにllmが把握して
  - [ ] 例えば、同じディレクトリで同じファイル名.jsonとなっているとかルールがあるはず
- [ ] 上で発見したルールに従い、すべての画像ファイルに対して対応するmetadataファイルを調べ、 output/supplemental_file_location.json に保存して

## 4_restore_metadata.py

- [ ] output/supplemental_file_location.json, output/metada.json, output/pair.jsonを利用し、可能な限り 2_filter_missing_metadata.py で指定したプロパティを復元して
- [ ] レストアできたら、output/imagesの画像のプロパティにその情報を埋め込んで
- [ ] もし、metadata.jsonに保存されている画像に埋め込まれていたプロパティと、メタデータのファイルに記載されている場合のプロパティが異なる場合は、一旦保持しておいて
- [ ] もし、情報が足りない場合は一旦保持しておいて
- [ ] 最後に、成功した数、失敗した数をログで表示して
- [ ] output/result.txtに異なる場合と足りない場合それぞれ情報を記載して
  - [ ] ファイルのパス、ファイル名、わかっている情報、わかっていない情報、をわかりやすく記載して