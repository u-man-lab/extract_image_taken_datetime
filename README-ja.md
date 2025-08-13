# extract_image_taken_datetime

* NOTE: See [`README.md`](./README.md) for English README.

## 概要
このリポジトリは、[ExifTool](https://exiftool.org/)を使用してファイル（写真、動画）から「撮影日時」を抽出するためのツールを提供します。
メインのスクリプトは：

- **1. [`extract_image_taken_datetime.py`](#1-extract_image_taken_datetimepy)** — CSVファイルからファイルパスを読み込み、ExifToolを使用して最も適切な「撮影日時」を取得し、CSVに出力します。

また、補助スクリプトも同時に提供しています。：

- **2. [`read_exiftool_values_of_files.py`](#2-read_exiftool_values_of_filespy)** — ファイルのメタデータタグを確認するのに役立ちます。
メインスクリプトを実行する前に、ファイルにどのようなメタデータタグが存在し、撮影日時として利用できるかを確認したい場合に便利です。なお、メインスクリプトのYAML設定ファイルにおいては、撮影日時として利用できるタグの優先順位が事前設定されています。

両方のスクリプトは、`configs/`ディレクトリ内のYAML設定ファイルから設定を読み込み、入力CSVファイルが`data/`ディレクトリ内に存在することを前提としています。結果のCSVファイルは`results/`ディレクトリに書き込まれます。

---

## ライセンス & 開発者

- **ライセンス**: このリポジトリ内の[`LICENSE`](./LICENSE)を参照してください。
- **開発者**: U-MAN Lab. ([https://u-man-lab.com/](https://u-man-lab.com/))

---

## 1. `extract_image_taken_datetime.py`

### 1.1. 概要

[`extract_image_taken_datetime.py`](./extract_image_taken_datetime.py) は、CSVファイルからファイルパスの一覧を読み込み、ExifToolを使用して最適な「撮影日時」を決定します。  
「撮影日時」とみなせるメタデータタグ一覧をYAML設定ファイルに指定する必要がありますが、実験的に求められた11のメタデータタグがデフォルトでYAMLファイルに記載されています。自分の保有する写真・動画ファイルについて、撮影日時とみなせるメタデータタグを確認したい場合は、まず[`read_exiftool_values_of_files.py`](#2-read_exiftool_values_of_filespy)を実行してください。

スクリプトはCSVに以下の列を追加します：

- ExifToolが返す日時関連のタグ名
- ExifToolが返す日時の生データ
- ISO-8601拡張形式に変換した日時
- ローカルのUNIXタイムスタンプに変換した日時

---

### 1.2. インストールと使用方法

#### (1) Pythonのインストール

Pythonを[公式サイト](https://www.python.org/downloads/)を参照してインストールしてください。  
開発者が検証したバージョンより古い場合、スクリプトが正常に動作しない可能性があります。[`.python-version`](./.python-version)を参照してください。

#### (2) ExifToolのインストール

ExifToolがインストールされ、PATHを通すなどして"exiftool"コマンドにより実行可能である必要があります。  
ダウンロードとインストールの手順: [https://exiftool.org/install.html](https://exiftool.org/install.html)  
開発者が検証したバージョン「13.33」より古い場合、スクリプトが正常に動作しない可能性があります。

インストールされていることの確認:
```bash
exiftool -ver
# 例: 13.33
```

#### (3) リポジトリをクローンする

```bash
git clone https://github.com/u-man-lab/extract_image_taken_datetime.git
# gitコマンドを利用できない場合は、別の方法でスクリプトファイルとYAML設定ファイルを環境に配置してください。
cd ./extract_image_taken_datetime
```

#### (4) Python依存関係をインストールする

```bash
pip install --upgrade pip
pip install -r ./requirements.txt
```

#### (5) 設定ファイルを編集する

設定ファイル[`configs/extract_image_taken_datetime.yaml`](./configs/extract_image_taken_datetime.yaml)を開き、ファイル内のコメントに従って値を編集します。

#### (6) スクリプトを実行する

```bash
python ./extract_image_taken_datetime.py ./configs/extract_image_taken_datetime.yaml
```

---

### 1.3. 期待される出力

成功した場合、標準エラー出力(stderr)に次のようなログが出力されます:

```
2025-08-11 10:01:23,476 [INFO] __main__: "extract_image_taken_datetime.py" start!
2025-08-11 10:01:23,522 [INFO] __main__: Reading CSV file "data/file_paths_list.csv"...
2025-08-11 10:01:23,873 [INFO] __main__: Scanning profiles of the files...
2025-08-11 10:01:42,014 [INFO] __main__: ExifTool processing... [0/36031 valid files]
：
2025-08-11 10:35:42,436 [INFO] __main__: ExifTool processing... [35630/36031 valid files]
2025-08-11 10:36:07,480 [INFO] __main__: ExifTool processing has been completed. [36031/36031 valid files]
2025-08-11 10:36:09,023 [INFO] __main__: Searching image taken datetime data...
2025-08-11 10:36:27,048 [INFO] __main__: Adding new columns...
2025-08-11 10:36:28,748 [INFO] __main__: Writing CSV file "results/file_paths_list_with_image_taken_datetime.csv"...
2025-08-11 10:36:30,185 [INFO] __main__: "extract_image_taken_datetime.py" done!
```

生成されるCSVは次のような形式になります：

```
file_paths,datetime_tag_by_exiftool,datetime_by_exiftool,datetime_aware_iso8601_extended,datetime_local_unix
/path/IMG_0395.PNG,File:FileModifyDate,2012-12-05 22:46:41+09:00,2012-12-05T22:46:41.000000+09:00,1354715201.000000
/path/IMG_0401.PNG,File:FileModifyDate,2012-12-05 22:48:28+09:00,2012-12-05T22:48:28.000000+09:00,1354715308.000000
:
```

---

### 1.4. よくあるエラー

詳細については、スクリプトのソースコードを参照してください。よくあるエラーには以下のものが含まれます:

- **ExifToolがインストールされていない**
  ```
  2025-08-13 09:50:58,593 [CRITICAL] __main__: "exiftool" is necessary, but not installed on this pc.
  2025-08-13 09:50:58,653 [CRITICAL] __main__: See https://exiftool.org/index.html.
  ```
- **スクリプトに引数を渡していない**
  ```
  2025-08-13 09:46:05,471 [ERROR] __main__: This script needs a config file path as an arg.
  ```
- **設定ファイルの値がおかしい**
  ```
  2025-08-13 09:47:40,930 [ERROR] __main__: Failed to parse the config file.: "configs\extract_image_taken_datetime.yaml"
  Traceback (most recent call last):
  :
  ```

---

## 2. `read_exiftool_values_of_files.py`

### 2.1. 概要

[`read_exiftool_values_of_files.py`](./read_exiftool_values_of_files.py)は、CSVファイルからファイルのパス一覧を読み込み、各ファイルのメタデータをExifTool形式で取得します。  
本スクリプトは、ファイルが保有するメタデータタグを一覧で確認するための補助ツールです。特に、メインスクリプト（[`extract_image_taken_datetime.py`](#1-extract_image_taken_datetimepy)）を使用する前に、撮影日時関連のタグとしてどのようなものが存在するのかを確認したい場合に便利です。

2つのモードをサポートしています：
1. **All tags mode** — YAML設定ファイルで`PROCESS` > `TARGET_EXIFTOOL_TAGS`が指定されていない場合、結果のCSVにすべてのExifToolタグが表示されますが、すべての値はマスクされます（CSVのサイズが過大になるのを防ぐため）。
2. **Specific tags mode** — YAML設定ファイルに`PROCESS` > `TARGET_EXIFTOOL_TAGS`を指定すると、結果のCSVファイルに指定したExifToolタグと実際の値が表示されます。

---

### 2.2. 使い方

実施する前に、以下の準備が完了していることを確認してください：

- Pythonのインストール
- ExifToolのインストール
- リポジトリをクローンする
- Python依存関係をインストールする

（詳細は[1章](#1-extract_image_taken_datetimepy)を参照してください。）

#### (1) 設定ファイルを編集する

設定ファイル[`configs/read_exiftool_values_of_files.yaml`](./configs/read_exiftool_values_of_files.yaml)を開き、ファイル内のコメントに従って値を編集してください。

#### (2) スクリプトを実行する

```bash
python ./read_exiftool_values_of_files.py ./configs/read_exiftool_values_of_files.yaml
```

---

### 2.3. 期待される出力

成功した場合、標準エラー出力(stderr)に次のようなログが出力されます:

```
2025-08-11 14:44:11,870 [INFO] __main__: "read_exiftool_values_of_files.py" start!
2025-08-11 14:44:11,913 [INFO] __main__: Running in "specific tags mode".: Showing all values.
2025-08-11 14:44:11,914 [INFO] extract_image_taken_datetime: Reading CSV file "data/file_paths_list.csv"...
2025-08-11 14:44:12,307 [INFO] __main__: Scanning profiles of the files...
2025-08-11 14:44:31,246 [INFO] extract_image_taken_datetime: ExifTool processing... [0/36031 valid files]
:
2025-08-11 15:46:32,408 [INFO] extract_image_taken_datetime: ExifTool processing... [35817/36031 valid files]
2025-08-11 15:46:56,540 [INFO] extract_image_taken_datetime: ExifTool processing has been completed. [36031/36031 valid files]
2025-08-11 15:46:59,015 [INFO] __main__: Merging profiles data to source CSV data...
2025-08-11 15:47:03,275 [INFO] __main__: Writing CSV file "results/file_paths_list_with_exif_tool_tags.csv"...
2025-08-11 15:47:08,354 [INFO] __main__: "read_exiftool_values_of_files.py" done!
```

生成されるCSVファイルは次のような形式になります：

* **All tags mode** (値がマスクされます):
  ```
  file_paths,SourceFile,File:FilePermissions,...,MakerNotes:ColorTemperatureSet
  /path/IMG_0395.PNG,*,*,...,
  /path/IMG_0401.PNG,*,*,...,
  :
  ```

* **Specific tags mode** (生データが表示されます):
  ```
  file_paths,SourceFile,File:FileModifyDate,...,QuickTime:EncodingTime
  /path/IMG_0395.PNG,/path/IMG_0395.PNG,2012:12:05 22:46:41+09:00,...,
  /path/IMG_0401.PNG,/path/IMG_0401.PNG,2012:12:05 22:48:28+09:00,...,
  :
  ```

---

### 2.4. よくあるエラー

詳細については、スクリプトのソースコードを参照してください。よくあるエラーは、[`extract_image_taken_datetime.py`](#1-extract_image_taken_datetimepy)と同様です。
