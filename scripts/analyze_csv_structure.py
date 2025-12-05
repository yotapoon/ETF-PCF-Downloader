import os
import glob
import zipfile
import pandas as pd
import shutil
import logging
import re
from datetime import datetime
import csv

path = r"C:\Users\yota-\Desktop\study\data\JPX\ETF保有銘柄\data\1306tsepcf_Dec042025.csv"


# ロギング設定: INFOレベル以上のメッセージをコンソールに出力
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_date_from_filename(filename):
    """ファイル名から日付を抽出し、datetimeオブジェクトを返す"""
    # YYYYMMDD形式のパターン
    match = re.search(r'(\d{8})', filename)
    if match:
        return datetime.strptime(match.group(1), '%Y%m%d')
    # YYYY-MM-DD形式のパターン
    match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    if match:
        return datetime.strptime(match.group(1), '%Y-%m-%d')
    return None

def parse_csv(csv_path, encoding='cp932'):
    """
    指定されたCSVファイルの先頭10行を、列数を30に固定して読み込み、DataFrameを返す。
    区切り文字は自動で判別する。
    """
    try:
        # 固定する列数を定義し、列名を生成 (例: col_1, col_2, ...)
        num_cols = 30
        col_names = [f'col_{i+1}' for i in range(num_cols)]

        # namesオプションで列数を固定して読み込む
        df = pd.read_csv(
            csv_path,
            header=None,
            names=col_names,
            nrows=10,
            encoding=encoding,
            engine='python',
            sep=None,
            on_bad_lines='warn', # 不正な行は警告を出してスキップ
            dtype={0: str} # 1列目を文字列として読み込む
        )
        return df
    except Exception as e:
        print(f"Error parsing file {csv_path} with encoding {encoding}: {e}")
        return None

def main():
    """
    メイン関数
    """
    print("--- PCF Parser and Unzip Script ---")

    # ダウンロードディレクトリを設定
    download_dir = 'data/downloads'

    # data/csv_structure.csvが既に存在する場合は削除
    output_csv_path = 'data/csv_structure.csv'
    if os.path.exists(output_csv_path):
        os.remove(output_csv_path)

    # ベンダーごとに処理
    results = []
    if not os.path.isdir(download_dir):
        print(f"Error: Download directory not found at '{download_dir}'")
        return

    for vendor in os.listdir(download_dir):
        vendor_path = os.path.join(download_dir, vendor)
        if os.path.isdir(vendor_path):
            # 日付の形式がベンダーごとに異なる可能性があるため、ファイル名から日付を抽出してソート
            zip_files = sorted([f for f in os.listdir(vendor_path) if f.endswith('.zip')])
            if not zip_files:
                continue

            # 最新と最古のZIPファイルを選択
            target_zip_files = []
            if len(zip_files) > 0:
                target_zip_files.append(zip_files[0]) # 最古
            if len(zip_files) > 1:
                target_zip_files.append(zip_files[-1]) # 最新

            for zip_filename in set(target_zip_files): # 重複を避ける
                zip_filepath = os.path.join(vendor_path, zip_filename)
                extract_dir = os.path.join(vendor_path, os.path.splitext(zip_filename)[0])

                # ZIPファイルを解凍
                if os.path.exists(extract_dir):
                    shutil.rmtree(extract_dir)
                os.makedirs(extract_dir, exist_ok=True)
                print(f"Extracting {zip_filepath}...")
                try:
                    with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)
                    print("Extraction complete.")
                except zipfile.BadZipFile:
                    print(f"Error: {zip_filepath} is not a valid zip file. Skipping.")
                    continue


                # 解凍したディレクトリ内のCSVファイルを処理
                for root, _, files in os.walk(extract_dir):
                    for file in files:
                        if file.lower().endswith('.csv'):
                            csv_path = os.path.join(root, file)
                            
                            # 複数のエンコーディングを試す
                            encodings_to_try = ['cp932', 'utf-8', 'sjis']
                            df_parsed = None
                            for enc in encodings_to_try:
                                # parse_csvはDataFrameを返す（またはNone）
                                df_parsed = parse_csv(csv_path, encoding=enc)
                                if df_parsed is not None and not df_parsed.empty:
                                    break
                            
                            if df_parsed is None or df_parsed.empty:
                                print(f"Could not parse or file is empty: {csv_path}")
                                continue

                            # DataFrameを転置
                            df_transposed = df_parsed.transpose()

                            # カラム名を 'row_1', 'row_2', ... に設定
                            df_transposed.columns = [f'row_{i+1}' for i in range(df_transposed.shape[1])]

                            # パスとファイル名を追加
                            df_transposed['path'] = csv_path
                            df_transposed['file_name'] = file
                            
                            results.append(df_transposed)

                # 解凍したファイルとディレクトリを削除
                shutil.rmtree(extract_dir)
                print(f"Cleaned up {extract_dir}")


    # 結果をCSVファイルに出力
    if results:
        df_output = pd.concat(results, ignore_index=True)
        
        # カラムの順序を整理
        # 'path' と 'file_name' 以外のカラム（row_...）を取得
        row_cols = [col for col in df_output.columns if col.startswith('row_')]
        # row_X カラムを数値でソート
        if row_cols:
            row_cols.sort(key=lambda x: int(x.split('_')[1]))
        
        # 最終的なカラム順序
        cols = ['path', 'file_name'] + row_cols
        # 存在しないカラムが指定されるのを防ぐ
        cols = [col for col in cols if col in df_output.columns]
        df_output = df_output[cols]

        df_output.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
        print(f"--- Structure analysis complete. Output saved to {output_csv_path} ---")
    else:
        print("--- No CSV files found or processed. ---")

if __name__ == '__main__':
    main()
