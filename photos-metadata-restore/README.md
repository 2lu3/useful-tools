# 写真・動画メタデータ復元ツール

Google PhotosのTakeoutデータから写真・動画ファイルのメタデータ（撮影日時、GPS情報）を復元するツールです。

## ディレクトリ構成

### outputディレクトリ
処理結果を格納するディレクトリです。各スクリプトの実行により以下のファイルが作成されます。

```
output/
├── images/                          # ハッシュ化された画像ファイル（1_copy_files.pyで作成）
│   ├── 41c8060f1dc3a729542902458907ca43.jpg
│   ├── b8cad2c5da5d3a9f4773d01ccca0958e.jpg
│   └── ...
├── pair.json                        # 元ファイルとハッシュファイルの対応表（1_copy_files.pyで作成）
├── photo_metadata.pkl               # EXIFメタデータのpickleファイル（2_filter_missing_metadata.pyで作成）
├── supplemental_file_location.json # メタデータファイルの場所情報（3_find_metadata_file.pyで作成）
└── supplemental_metadata.pkl       # supplemental-metadataから抽出したメタデータのpickleファイル（4_extract_metadata_file.pyで作成）
```

#### outputディレクトリに格納されるファイル

1. **images/ディレクトリ** (`1_copy_files.py`で作成)
   - MD5ハッシュ値でリネームされた画像ファイル
   - 重複ファイルは除外される
   - 元のファイル名は`pair.json`で管理
   - ファイル名例: `41c8060f1dc3a729542902458907ca43.jpg`

2. **pair.json** (`1_copy_files.py`で作成)
   - 元ファイルとハッシュファイルの対応関係
   - 各エントリには以下の情報が含まれる：
     - `source`: 元ファイルのパス
     - `destination`: ハッシュファイルのパス
     - `filename`: ハッシュファイル名
     - `hash`: MD5ハッシュ値

3. **photo_metadata.pkl** (`2_filter_missing_metadata.py`で作成)
   - 各画像ファイルのEXIFメタデータを格納したpickleファイル
   - `PhotoMetadata`オブジェクトのリストが格納される
   - EXIFデータから抽出された撮影日時、GPS情報を含む

4. **supplemental_file_location.json** (`3_find_metadata_file.py`で作成)
   - 各画像ファイルに対応するメタデータファイルの場所情報
   - supplemental-metadata.jsonファイルの検索結果
   - 各エントリには以下の情報が含まれる：
     - `original_source`: 元のファイルパス
     - `metadata_file`: メタデータファイルのパス
     - `metadata_type`: メタデータの種類
     - `found`: メタデータファイルが見つかったかどうか
     - `file_exists`: メタデータファイルが存在するかどうか

5. **supplemental_metadata.pkl** (`4_extract_metadata_file.py`で作成)
   - supplemental-metadata.jsonから抽出したメタデータを格納したpickleファイル
   - `PhotoMetadata`オブジェクトのリストが格納される
   - supplemental-metadataから抽出された撮影日時、GPS情報を含む

## 処理フロー

1. **1_copy_files.py**: 画像ファイルをハッシュ化してコピー
2. **2_filter_missing_metadata.py**: EXIFメタデータを分析・保存
3. **3_find_metadata_file.py**: 対応するメタデータファイルを検索
4. **4_extract_metadata_file.py**: supplemental-metadataファイルから情報を抽出

## 設定ファイル

### config.toml
ファイルタイプの設定ファイルです。

```toml
[file_types]
# 画像ファイルの拡張子
image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".heic", ".raw", ...]

# 動画ファイルの拡張子  
video_extensions = [".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mkv", ...]
```

## ユーティリティ

### utils/exif_utils.py
EXIFデータ処理に関するユーティリティ関数を提供します。

- `GPSData`: GPS情報を管理するデータクラス
- `PhotoMetadata`: 写真メタデータを管理するデータクラス
- `get_exif_data()`: ExifToolを使ってEXIFデータを取得
- `get_exif_datetime()`: EXIFデータから撮影日時を抽出
- `get_gps_data()`: EXIFデータからGPS情報を抽出
