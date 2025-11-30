# ETF-PCF-Downloader

## 概要

このプロジェクトは、複数の指数提供会社（ICE, IHS Markit, Solactive）からETF（上場投資信託）の構成銘柄データ（PCF）を日次で自動収集し、データベースに蓄積するためのシステムです。

## 主な機能

- 複数のソースから日次のPCFデータをダウンロードします。
- ログファイルを用いてダウンロード履歴を管理し、重複取得を防ぎます。
- ダウンロードしたデータを格納するためのSQLデータベーススキーマを提供します。

## ディレクトリ構成

```
.
├── .gitignore
├── create_table.sql       # データベースのテーブル作成用SQL
├── download_log.csv       # データダウンロードの実行ログ
├── download_pcfs.bat      # ダウンロードスクリプトの実行用バッチファイル
├── download_pcfs.py       # データダウンロード用Pythonスクリプト
└── downloads/             # ダウンロードしたzipファイルの保存先
    ├── ice/
    ├── ihs/
    └── solactive/
```

## 使い方

1.  必要なPythonライブラリをインストールします。
    ```bash
    pip install requests pandas
    ```
2.  `download_pcfs.bat` を実行します。
    ```bash
    ./download_pcfs.bat
    ```
    これにより `download_pcfs.py` が実行され、`downloads` ディレクトリにデータが保存されます。

3.  `create_table.sql` を使用して、任意のSQLデータベースにテーブルを作成します。

## 次のステップ

- `downloads` ディリトリ内のzipファイルを解凍する機能の実装。
- 解凍したデータを解析し、データベースに登録する処理の実装。
