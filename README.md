# JPX ETF PCFデータ処理ツール

JPX（日本取引所グループ）のウェブサイトからETFのPCF（ポートフォリオ構成ファイル）をダウンロードし、内容を解析してデータベースに登録するためのツールです。

## ファイル構成

```
.
├── .gitignore
├── config.py                # データベース接続情報などの設定ファイル
├── create_table.sql         # データベースのテーブル定義
├── download_log.csv         # データダウンロードの実行ログ
├── README.md                # このファイル
├── requirements.txt         # Pythonの依存パッケージリスト
├── data/
│   └── downloads/           # ダウンロードしたPCFのzipファイルを格納するディレクトリ
└── scripts/
    ├── download_pcfs.bat      # データダウンロードスクリプトを実行するバッファイル
    ├── download_pcfs.py       # JPXサイトからPCFデータをダウンロードするスクリプト
    ├── import_daily_pcf.py  # 日付を指定してPCFデータを解析し、DBに登録するスクリプト
    ├── pcf_parser.py          # 個別のPCFデータ（CSV）の解析処理を行うモジュール
    └── database_handler.py    # データベースへの接続とデータ登録を行うモジュール
```

## 実行手順

### 1. 準備

1.  `requirements.txt` をもとに、必要なPythonパッケージをインストールします。
    ```shell
    pip install -r requirements.txt
    ```
2.  `create_table.sql` を使用して、データベースにテーブルを作成します。
3.  `config.py` を開き、ご自身の環境に合わせてデータベース接続情報などを設定します。


### 2. PCFデータのダウンロード

`download_pcfs.bat` を実行すると、`scripts/download_pcfs.py` が起動し、PCFのzipファイルが `data/downloads/` ディレクトリにダウンロードされます。

```shell
download_pcfs.bat
```

### 3. データの解析とデータベースへの登録

`scripts/import_daily_pcf.py` を実行することで、ダウンロード済みのPCFデータが解析され、データベースに登録されます。
`--date`引数で処理したい日付を `YYYY-MM-DD` 形式で指定できます。引数を省略した場合は、実行した当日の日付が自動的に使用されます。

**例1：日付を指定して実行する場合（2023年1月1日）**
```shell
python scripts/import_daily_pcf.py --date 2023-01-01
```

**例2：当日のデータで実行する場合**
```shell
python scripts/import_daily_pcf.py
```

---