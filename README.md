# extract_image_taken_datetime

## Overview

This repository provides tools for extracting "image taken" datetime from files (photos, videos) using [ExifTool](https://exiftool.org/).  
The main script is:

- **1. [`extract_image_taken_datetime.py`](#1-extract_image_taken_datetimepy)** — Reads a CSV containing file paths, queries ExifTool for the most relevant "image taken" datetime, and outputs a CSV with multiple datetime formats.

An auxiliary script is also included:

- **2. [`read_exiftool_values_of_files.py`](#2-read_exiftool_values_of_filespy)** — Helps investigate the metadata tags available for your files.  
  This can be useful if you wish to understand which datetime-related tags are present in your files before running the main script.  
  The main script already has a preconfigured tag priority order (See the configuration YAML).

Both scripts read their settings from YAML config files in the `configs/` directory and expect the input CSV of file paths to be located in the `data/` directory. Results are written to the `results/` directory.

---

## License & Developer

- **License**: See [`LICENSE`](./LICENSE) in this repository.
- **Developer**: U-MAN Lab. ([https://u-man-lab.com/](https://u-man-lab.com/))

---

## 1. `extract_image_taken_datetime.py`

### 1.1. Description

[`extract_image_taken_datetime.py`](./extract_image_taken_datetime.py) reads a list of file paths from a CSV file and determines the most relevant "image taken" datetime using ExifTool.  
It uses a list of datetime-related tags, ordered by priority. A preconfigured tag priority order is already in the configuration YAML. If you want to explore available tags in your files, use [`read_exiftool_values_of_files.py`](#2-read_exiftool_values_of_filespy) first.

The script appends the following columns to the CSV:

- The datetime tag name returned by ExifTool
- The raw datetime value by ExifTool
- An ISO-8601 extended format datetime
- A local UNIX timestamp

---

### 1.2. Installation & Usage

#### (1) Install Python

Install Python from the [official Python website](https://www.python.org/downloads/).  
The scripts may not work properly if the version is lower than the verified one. Refer to the [`.python-version`](./.python-version).

#### (2) Install ExifTool

ExifTool must be installed and available in your system PATH.  
Download and installation instructions: [https://exiftool.org/install.html](https://exiftool.org/install.html).  
The scripts may not work properly if the version is lower than the verified version "13.33".

Verify installation:
```bash
exiftool -ver
# e.g. 13.33
```

#### (3) Clone the repository

```bash
git clone https://github.com/u-man-lab/extract_image_taken_datetime.git
cd ./extract_image_taken_datetime
```

#### (4) Install Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### (5) Edit the configuration file

Open the configuration file [`configs/extract_image_taken_datetime.yaml`](./configs/extract_image_taken_datetime.yaml) and edit the values according to the comments in the file.

#### (6) Run the script

```bash
python ./extract_image_taken_datetime.py ./configs/extract_image_taken_datetime.yaml
```

---

### 1.3. Expected Output

On success, stderr will include logs similar to:

```
2025-08-11 10:01:23,476 [INFO] __main__: "extract_image_taken_datetime.py" start!
2025-08-11 10:01:23,522 [INFO] __main__: Reading file "data/file_paths_list.csv"...
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

The resulting CSV will be like:

```
file_paths,datetime_tag_by_exiftool,datetime_by_exiftool,datetime_aware_iso8601_extended,datetime_local_unix
/path/IMG_0395.PNG,File:FileModifyDate,2012-12-05 22:46:41+09:00,2012-12-05T22:46:41.000000+09:00,1354715201.000000
/path/IMG_0401.PNG,File:FileModifyDate,2012-12-05 22:48:28+09:00,2012-12-05T22:48:28.000000+09:00,1354715308.000000
:
```

---

### 1.4. Common Errors

For full details, see the script source. Common errors include:

- **ExifTool is not installed**
  ```
  2025-08-13 09:50:58,593 [CRITICAL] __main__: "exiftool" is necessary, but not installed on this pc.
  2025-08-13 09:50:58,653 [CRITICAL] __main__: See https://exiftool.org/index.html.
  ```
- **Missing config path argument**
  ```
  2025-08-13 09:46:05,471 [ERROR] __main__: This script needs a config file path as an arg.
  ```
- **Invalid or missing config field**
  ```
  2025-08-13 09:47:40,930 [ERROR] __main__: Failed to parse the config file.: "configs\extract_image_taken_datetime.yaml"
  Traceback (most recent call last):
  :
  ```

---

## 2. `read_exiftool_values_of_files.py`

### 2.1. Description

[`read_exiftool_values_of_files.py`](./read_exiftool_values_of_files.py) scans a list of file paths from a CSV and retrieves ExifTool metadata for each file.  
It is primarily an auxiliary tool to help determine which tags are present in your files. This is especially useful if you want to see what datetime-related tags exist before using the main script ([`extract_image_taken_datetime.py`](#1-extract_image_taken_datetimepy)).

It supports two modes:
1. **All tags mode** — Without `PROCESS` > `TARGET_EXIFTOOL_TAGS` in the configuration YAML, you can see all ExifTool tags in the result CSV, but all of the values are masked (to prevent too large CSV size.)
2. **Specific tags mode** — With `PROCESS` > `TARGET_EXIFTOOL_TAGS` in the configuration YAML, you can see specific ExifTool tags and the actual values in the result CSV.

---

### 2.2. Usage

Before running, ensure you have already:

- Installed Python
- Installed ExifTool
- Cloned the repository
- Installed dependencies

(See [Chapter 1](#1-extract_image_taken_datetimepy) for setup details.)

#### (1) Edit the configuration file

Open the configuration file [`configs/read_exiftool_values_of_files.yaml`](./configs/read_exiftool_values_of_files.yaml) and edit the values according to the comments in the file.

#### (2) Run the script

```bash
python ./read_exiftool_values_of_files.py ./configs/read_exiftool_values_of_files.yaml
```

---

### 2.3. Expected Output

Example stderr log (specific tags mode):

```
2025-08-11 14:44:11,870 [INFO] __main__: "read_exiftool_values_of_files.py" start!
2025-08-11 14:44:11,913 [INFO] __main__: Running in specific tags mode.: Showing all values.
2025-08-11 14:44:11,914 [INFO] extract_image_taken_datetime: Reading file "data/file_paths_list.csv"...
2025-08-11 14:44:12,307 [INFO] __main__: Scanning profiles of the files...
2025-08-11 14:44:31,246 [INFO] extract_image_taken_datetime: ExifTool processing... [0/36031 valid files]
:
2025-08-11 15:46:32,408 [INFO] extract_image_taken_datetime: ExifTool processing... [35817/36031 valid files]
2025-08-11 15:46:56,540 [INFO] extract_image_taken_datetime: ExifTool processing has been completed. [36031/36031 valid files]
2025-08-11 15:46:59,015 [INFO] __main__: Merging profiles data to source CSV data...
2025-08-11 15:47:03,275 [INFO] __main__: Writing CSV file "results/file_paths_list_with_all_exif_tool_tags_specific_.csv"...
2025-08-11 15:47:08,354 [INFO] __main__: "read_exiftool_values_of_files.py" done!
```

The resulting CSV will be like:

* **All tags mode** (masked values):
  ```
  file_paths,SourceFile,File:FilePermissions,...,MakerNotes:ColorTemperatureSet
  /path/IMG_0395.PNG,*,*,...,
  /path/IMG_0401.PNG,*,*,...,
  :
  ```

* **Specific tags mode** (actual values):
  ```
  file_paths,datetime_tag_by_exiftool,datetime_by_exiftool,datetime_aware_iso8601_extended,datetime_local_unix
  /path/IMG_0395.PNG,File:FileModifyDate,2012-12-05 22:46:41+09:00,2012-12-05T22:46:41.000000+09:00,1354715201.000000
  /path/IMG_0401.PNG,File:FileModifyDate,2012-12-05 22:48:28+09:00,2012-12-05T22:48:28.000000+09:00,1354715308.000000
  :
  ```

---

### 2.4. Common Errors

For full details, see the script source.
