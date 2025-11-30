import pandas as pd
import os
import zipfile
import csv

def parse_ice_pcf(file_path: str):
    """
    ICEからダウンロードした特殊な形式のPCF CSVファイルをパースする。
    ファイルの区切り文字(カンマ or タブ)を自動検出する。

    Args:
        file_path (str): パース対象のCSVファイルへのパス。

    Returns:
        tuple: (fund_info_df, holdings_df)
               - fund_info_df: ETFの基本情報を含むDataFrame (1行)。
               - holdings_df: 保有銘柄の詳細情報を含むDataFrame。
               エラー時は (None, None) を返す。
    """
    delimiter = ','  # デフォルトはカンマ
    try:
        # --- 区切り文字の自動検出 ---
        with open(file_path, 'r', encoding='utf-8') as f:
            # 信頼性が高いと思われる4行目(保有銘柄のヘッダー)を読み込んで判別
            for _ in range(3):
                f.readline()
            sample_line = f.readline()
            dialect = csv.Sniffer().sniff(sample_line, delimiters=',\t') # Comma and Tab
            delimiter = dialect.delimiter
    except Exception:
        # 判別失敗時はデフォルトのカンマを使用
        pass

    try:
        # 1. ETF基本情報の読み込み
        fund_info_df = pd.read_csv(file_path, header=0, nrows=1, sep=delimiter)
        fund_info_df = fund_info_df.dropna(axis=1, how='all')

        # 2. 保有銘柄一覧の読み込み
        holdings_df = pd.read_csv(file_path, skiprows=3, sep=delimiter)
        holdings_df = holdings_df.dropna(subset=['ISIN'])

        # 3. データの結合
        fund_date = fund_info_df['Fund Date'].iloc[0]
        etf_code = fund_info_df['ETF Code'].iloc[0]

        holdings_df['Fund Date'] = fund_date
        holdings_df['ETF Code'] = etf_code

        return fund_info_df, holdings_df

    except KeyError as e:
        print(f"KeyError parsing file {file_path}: Column {e} not found.")
        print(f"Used delimiter: '{delimiter}'. Please check file format.")
        try:
            # デバッグ用に読み込んだ列情報を表示
            temp_df = pd.read_csv(file_path, skiprows=3, sep=delimiter, nrows=5)
            print(f"Available columns: {temp_df.columns.tolist()}")
        except Exception as debug_e:
            print(f"Could not read columns for debugging: {debug_e}")
        return None, None
    except Exception as e:
        print(f"An error occurred while parsing {file_path}: {e}")
        return None, None

def unzip_pcf_archive(zip_file_path: str):
    """
    ZIPアーカイブを解凍し、中のCSVファイルへのパスのリストを返す。

    Args:
        zip_file_path (str): 解凍するZIPファイルへのパス。

    Returns:
        list: 抽出された全CSVファイルへのフルパスのリスト。
    """
    try:
        # 解凍先のディレクトリ名をZIPファイル名から生成 (例: ice_20251128.zip -> ice_20251128/)
        extract_dir = os.path.splitext(zip_file_path)[0]
        
        if not os.path.exists(extract_dir):
            os.makedirs(extract_dir)
            print(f"Created directory: {extract_dir}")

        csv_files = []
        with zipfile.ZipFile(zip_file_path, 'r') as zf:
            print(f"Extracting {zip_file_path}...")
            zf.extractall(extract_dir)
            print("Extraction complete.")
            
            # 解凍されたファイルの中からCSVファイルを探す
            for file_name in zf.namelist():
                if file_name.lower().endswith('.csv'):
                    csv_files.append(os.path.join(extract_dir, file_name))
        
        return csv_files

    except FileNotFoundError:
        print(f"[Error] ZIP file not found: {zip_file_path}")
        return []
    except Exception as e:
        print(f"An error occurred during unzipping: {e}")
        return []

# このスクリプトが直接実行された場合のテスト用コード
if __name__ == '__main__':
    print("--- PCF Parser and Unzip Script ---")
    
    # ----------------------------------------------------------------
    # テスト対象のZIPファイルを指定
    # 注: このテストコードは、プロジェクトのルートディレクトリから `python scripts/parse_pcfs.py` として実行することを想定しています。
    sample_zip_file = os.path.join('data', 'downloads', 'ice', 'ice_20251128.zip')
    # ----------------------------------------------------------------
    
    print(f"\nテスト対象ZIPファイル: {sample_zip_file}")

    if not os.path.exists(sample_zip_file):
        print(f"\n[Warning] テスト用のZIPファイルが見つかりません: {sample_zip_file}")
        print("`data/downloads/ice/` に `ice_20251128.zip` が存在するか確認してください。")
        print("処理をスキップします。")
    else:
        # 1. ZIPファイルを解凍し、CSVファイルのリストを取得
        extracted_csv_files = unzip_pcf_archive(sample_zip_file)
        
        if extracted_csv_files:
            print(f"\n発見されたCSVファイル: {len(extracted_csv_files)}個")
            
            # 2. 最初のCSVファイルだけをサンプルとしてパース処理
            first_csv_path = extracted_csv_files[0]
            print(f"--- 最初のCSVファイルをパースします: {first_csv_path} ---")
            
            fund_info, holdings_info = parse_ice_pcf(first_csv_path)

            if fund_info is not None and holdings_info is not None:
                print("\n--- 抽出されたETF基本情報 ---")
                print(fund_info.to_string())
                
                print("\n--- 抽出された保有銘柄情報 (先頭5件) ---")
                print(holdings_info.head().to_string())
                
                print("\nパース処理のテストが正常に完了しました。")
        else:
            print("\nZIPファイル内でCSVファイルが見つかりませんでした。")