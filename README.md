# ETF-PCF-Downloader

## 概要


このプロジェクトは、複数の指数提供会社（ICE, IHS Markit, Solactive）からETF（上場投資信託）の構成銘柄データ（PCF）を日次で自動収集し、データベースに蓄積するためのシステムです。

## 設定

本プロジェクトの設定は `config.py` と `.env` ファイルによって管理されます。

- **`config.py`**:
  プロジェクト全体で利用される設定（ファイルパス、URLなど）が定義されています。

- **`.env`**:
  サーバー名やデータベース接続情報など、環境に依存する機密情報を記述するためのファイルです。このファイルは `.gitignore` により、Gitの管理対象から除外されています。
  実行前に、このファイルを作成し、ご自身の環境に合わせて設定してください。

  **.env ファイルの例:**
  ```
  DB_SERVER="your_server_name"
  DB_NAME="ETF_PCFS"
  ```

## 主な機能

- **PCFファイルのダウンロード**: `scripts/download_pcfs.py` を実行することで、各指数提供会社から最新のPCF（Portfolio Composition File）のZIPファイルをダウンロードします。
- **PCFファイルの解析**: `scripts/parse_pcfs_by_date.py` は、指定された日付のダウンロード済みZIPファイルを解凍し、含まれるCSVファイルを解析して、ETFの基本情報と保有銘柄情報を集約した2つのCSVファイルとして出力します。

## ディレクトリ構成

```
.
├── .env
├── .gitignore
├── config.py
├── create_table.sql
├── download_log.csv
├── README.md
├── check/
├── data/
│   └── downloads/
│       ├── ice/
│       ├── ihs/
│       └── solactive/
└── scripts/
    ├── download_pcfs.bat
    ├── download_pcfs.py
    └── parse_pcfs_by_date.py
```

## 使い方

1.  **設定ファイルの準備**
    `.env` ファイルを作成し、ご自身の環境（データベースサーバー名など）に合わせて内容を編集します。詳細は「設定」セクションを参照してください。

2.  **ライブラリのインストール**
    必要なPythonライブラリをインストールします。
    ```bash
    pip install -r requirements.txt
    ```

3.  **PCFファイルのダウンロード**
    `scripts/download_pcfs.bat` を実行すると、`scripts/download_pcfs.py` が実行され、`data/downloads` ディレクトリにデータが保存されます。
    ```bash
    scripts\download_pcfs.bat
    ```

4.  **ダウンロードしたファイルの解析**
    `scripts/parse_pcfs_by_date.py` を日付を引数に指定して実行します。これにより、ダウンロードしたZIPファイルが解凍・解析され、`data` フォルダに集約されたCSVファイルが出力されます。
    ```bash
    python scripts/parse_pcfs_by_date.py YYYY-MM-DD
    ```
    例:
    ```bash
    python scripts/parse_pcfs_by_date.py 2025-12-04
    ```

5.  **データベースの準備**
    `create_table.sql` を使用して、任意のSQLデータベースにテーブルを作成します。

## 次のステップ

- 出力された`base_info_(日付).csv`と`holdings_(日付).csv`の内容を確認し、最適なデータベースのテーブル構造を検討する。
- 検討したDB構造に合うように、`parse_pcfs_by_date.py`のデータ整形処理を修正・拡張する。
- 整形したデータをデータベースに登録する処理を実装する。
