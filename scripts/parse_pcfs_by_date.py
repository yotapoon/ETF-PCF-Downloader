
import pandas as pd
import os
import logging
import argparse
import glob
from zipfile import ZipFile
from datetime import datetime
import io

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def find_header_row_and_data(file_content_lines, key_column):
    """
    ファイル内容（行のリスト）から、指定されたキーカラムを含むヘッダー行の
    行番号と、それ以降のデータ行を特定する。
    """
    header_row_index = -1
    for i, line in enumerate(file_content_lines):
        # BOMや空白文字を除去してから比較
        cleaned_line = line.strip()
        # カンマ区切りで列を評価
        columns = [col.strip() for col in cleaned_line.split(',')]
        if key_column in columns:
            header_row_index = i
            break
    
    if header_row_index != -1:
        # ヘッダー行以降のデータを取得
        data_lines = file_content_lines[header_row_index:]
        return header_row_index, data_lines
    
    return -1, []


def parse_pcf_file(csv_content, file_name_for_log=""):
    """
    1つのPCF CSVファイルの中身（文字列）を解析し、ETF基本情報と保有銘柄情報を抽出する。
    ファイルは2つのデータフレームを持つ可能性がある。
    """
    try:
        # --- 全エンコーディング共通の前処理 ---
        # 改行で分割して行のリストにする (splitlines()が最も堅牢)
        lines = csv_content.strip().splitlines()
        
        # BOM(Byte Order Mark)の除去
        if lines:
            lines[0] = lines[0].lstrip('\ufeff')

        # 1. ETF基本情報の検索と解析
        base_header_index, base_data_lines = find_header_row_and_data(lines, 'ETF Code')
        df_base_info = pd.DataFrame()
        
        if base_header_index != -1:
            # 基本情報はヘッダーの次の1行のみと仮定
            # pandasで読み込むために、ヘッダーとデータ1行を文字列に再結合
            base_info_str = "\n".join(base_data_lines[:2])
            df_base_info = pd.read_csv(
                io.StringIO(base_info_str),
                sep=',',
                engine='python'
            ).dropna(how='all', axis=1)

        # 2. 保有銘柄情報の検索と解析
        holdings_header_index, holdings_data_lines = find_header_row_and_data(lines, 'Code')
        df_holdings = pd.DataFrame()

        if holdings_header_index != -1:
            holdings_info_str = "\n".join(holdings_data_lines)
            df_holdings = pd.read_csv(
                io.StringIO(holdings_info_str),
                sep=',',
                engine='python',
            ).dropna(how='all', axis=1)
            # すべての列がNaNである行を削除
            df_holdings = df_holdings.dropna(how='all')


        if df_base_info.empty and df_holdings.empty:
            logging.warning(f"Could not parse any meaningful data from {file_name_for_log}")
            return None

        return {'base_info': df_base_info, 'holdings': df_holdings}

    except Exception as e:
        logging.error(f"Failed to parse file content for {file_name_for_log}: {e}")
        return None

def test_single_file_parsing():
    """
    単一のCSVファイルを使ってパース処理をテストする
    """
    logging.info("--- Running Test for Single File Parsing ---")
    test_file_path = os.path.join('data', '1306tsepcf_Dec042025.csv')

    if not os.path.exists(test_file_path):
        logging.error(f"Test file not found: {test_file_path}")
        return

    encodings_to_try = ['cp932', 'utf-8', 'sjis']
    parsed_data = None
    
    for enc in encodings_to_try:
        try:
            with open(test_file_path, 'r', encoding=enc) as f:
                content = f.read()
            
            parsed_data = parse_pcf_file(content, os.path.basename(test_file_path))
            if parsed_data and (not parsed_data.get('base_info', pd.DataFrame()).empty or not parsed_data.get('holdings', pd.DataFrame()).empty):
                logging.info(f"Successfully parsed with encoding: {enc}")
                break
        except Exception as e:
            logging.debug(f"Could not parse with encoding {enc}: {e}")
            continue
            
    if parsed_data:
        logging.info("--- ETF Base Info ---")
        print(parsed_data.get('base_info', pd.DataFrame()).to_string())
        
        logging.info("--- ETF Holdings (first 5 rows) ---")
        print(parsed_data.get('holdings', pd.DataFrame()).head().to_string())
    else:
        logging.error("Failed to parse the test file with all attempted encodings.")

    logging.info("--- Test Parsing Finished ---")


def parse_by_date(target_date_str):
    """
    指定された日付のPCFファイルをすべて解析し、結果を連結して2つのCSVファイルとして保存する
    """
    logging.info(f"--- Running Parsing for Date: {target_date_str} ---")
    
    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
    except ValueError:
        logging.error("Invalid date format. Please use YYYY-MM-DD.")
        return

    # 各プロバイダーのファイル名のパターンを作成
    date_formats = {
        'solactive': target_date.strftime('%Y-%m-%d'),
        'ice': target_date.strftime('%Y%m%d'),
        'ihs': target_date.strftime('%Y%m%d')
    }

    # ダウンロードディレクトリのパス
    base_download_path = os.path.join('data', 'downloads')
    
    # 検索するzipファイルのパターンリスト
    zip_patterns = [
        os.path.join(base_download_path, 'solactive', f'solactive_{date_formats["solactive"]}.zip'),
        os.path.join(base_download_path, 'ice', f'ice_{date_formats["ice"]}.zip'),
        os.path.join(base_download_path, 'ihs', f'ihs_{date_formats["ihs"]}.zip')
    ]

    found_files = []
    for pattern in zip_patterns:
        found_files.extend(glob.glob(pattern))

    if not found_files:
        logging.warning(f"No zip files found for date {target_date_str}")
        return

    logging.info(f"Found {len(found_files)} zip file(s) to process.")

    # エンコーディングの試行リスト
    encodings_to_try = ['cp932', 'utf-8', 'sjis']

    # パース結果を保存するディレクトリ
    output_dir = 'data'
    os.makedirs(output_dir, exist_ok=True)

    all_base_infos = []
    all_holdings_infos = []

    # 各zipファイルを処理
    for zip_path in found_files:
        logging.info(f"Processing zip file: {zip_path}")
        # zipファイルのパスからsourceを取得 (例: .../data/downloads/ice/...) -> 'ice'
        source = os.path.basename(os.path.dirname(zip_path))

        try:
            with ZipFile(zip_path, 'r') as zf:
                csv_files = [f for f in zf.namelist() if f.lower().endswith('.csv')]
                for csv_file_name in csv_files:
                    logging.info(f"  Parsing CSV: {csv_file_name}")
                    
                    parsed_data = None
                    content = None
                    
                    # zip内のファイルを読み込み、最適なエンコーディングを見つける
                    with zf.open(csv_file_name) as csv_file:
                        file_bytes = csv_file.read()
                        
                    for enc in encodings_to_try:
                        try:
                            content = file_bytes.decode(enc)
                            parsed_data = parse_pcf_file(content, csv_file_name)
                            if parsed_data and (not parsed_data.get('base_info', pd.DataFrame()).empty or not parsed_data.get('holdings', pd.DataFrame()).empty):
                                logging.info(f"    Successfully parsed with encoding: {enc}")
                                break
                            else:
                                parsed_data = None
                        except UnicodeDecodeError:
                            logging.debug(f"    Failed to decode with {enc}")
                            continue
                        except Exception as e:
                            logging.debug(f"    Error during parsing with {enc}: {e}")
                            continue
                    
                    # パース成功後の処理
                    if parsed_data:
                        df_base = parsed_data.get('base_info')
                        df_holdings = parsed_data.get('holdings')

                        if df_base is not None and not df_base.empty:
                            df_base['source'] = source
                            all_base_infos.append(df_base)
                        
                        if df_holdings is not None and not df_holdings.empty:
                            # 保有銘柄にもETFコードとsourceを追加して関連付け
                            if df_base is not None and not df_base.empty and 'ETF Code' in df_base.columns:
                                df_holdings['ETF Code'] = df_base['ETF Code'].iloc[0]
                            df_holdings['source'] = source
                            all_holdings_infos.append(df_holdings)
                    else:
                        logging.warning(f"  Could not parse {csv_file_name} with any of the attempted encodings.")

        except Exception as e:
            logging.error(f"Failed to process zip file {zip_path}: {e}")

    # すべてのパース結果を連結して保存
    if all_base_infos:
        final_base_df = pd.concat(all_base_infos, ignore_index=True)
        base_output_path = os.path.join(output_dir, f"base_info_{target_date_str}.csv")
        final_base_df.to_csv(base_output_path, index=False, encoding='utf-8-sig')
        logging.info(f"Aggregated base info saved to {base_output_path}")

    if all_holdings_infos:
        final_holdings_df = pd.concat(all_holdings_infos, ignore_index=True)
        holdings_output_path = os.path.join(output_dir, f"holdings_{target_date_str}.csv")
        final_holdings_df.to_csv(holdings_output_path, index=False, encoding='utf-8-sig')
        logging.info(f"Aggregated holdings info saved to {holdings_output_path}")

    logging.info(f"--- Parsing for Date: {target_date_str} Finished ---")



if __name__ == '__main__':
    # コマンドライン引数の設定
    parser = argparse.ArgumentParser(description="Parse ETF PCF files for a specific date.")
    parser.add_argument(
        "date",
        nargs='?', # 引数を任意に
        default=None, # デフォルト値をNoneに
        type=str,
        help="The date to process files for, in YYYY-MM-DD format. If not provided, a single file test will run."
    )
    args = parser.parse_args()

    # 日付が指定されている場合は日付ごとの処理、そうでなければ単一ファイルテストを実行
    if args.date:
        parse_by_date(args.date)
    else:
        test_single_file_parsing()
