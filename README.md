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

- 複数のソースから日次のPCFデータをダウンロードします。
- ログファイルを用いてダウンロード履歴を管理し、重複取得を防ぎます。
- ダウンロードしたデータを格納するためのSQLデータベーススキーマを提供します。

## ディレクトリ構成

```
.
├── .env
├── .gitignore
├── config.py
├── create_table.sql
├── download_log.csv
├── README.md
├── data/
│   └── downloads/
│       ├── ice/
│       ├── ihs/
│       └── solactive/
└── scripts/
    ├── download_pcfs.bat
    ├── download_pcfs.py
    └── parse_pcfs.py
```

## 使い方

1.  **設定ファイルの準備**
    `.env` ファイルを作成し、ご自身の環境（データベースサーバー名など）に合わせて内容を編集します。詳細は「設定」セクションを参照してください。

2.  **ライブラリのインストール**
    必要なPythonライブラリをインストールします。`.env`ファイルを読み込むために `python-dotenv` が追加されています。
    ```bash
    pip install requests pandas python-dotenv
    ```

3.  **実行**
    プロジェクトのルートディレクトリから、以下のコマンドでバッチファイルを実行します。
    ```bash
    scripts\download_pcfs.bat
    ```
    これにより `scripts/download_pcfs.py` が実行され、`data/downloads` ディレクトリにデータが保存されます。

4.  **データベースの準備**
    `create_table.sql` を使用して、任意のSQLデータベースにテーブルを作成します。

## 次のステップ

- `data/downloads` ディレクトリ内のzipファイルを解凍する機能の実装。
- 解凍したデータを解析し、データベースに登録する処理の実装。
