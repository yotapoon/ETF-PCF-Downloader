import pandas as pd
import os
import logging
import argparse
import glob
from zipfile import ZipFile
from datetime import datetime, timedelta
import io

# 外部のモジュールをインポート
from pcf_parser import parse_csv_content
import database_handler

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_previous_business_day(date: datetime) -> datetime.date:
    """
    指定されたdatetimeオブジェクトから、前営業日を計算して返す。
    土日の場合は金曜日を返す簡単な実装。祝日は未考慮。
    """
    offset = max(1, (date.weekday() + 6) % 7 - 3)
    business_date = date.date() - timedelta(days=offset)
    logging.info(f"Source date: {date.strftime('%Y-%m-%d')}, Calculated business date: {business_date}")
    return business_date

def parse_by_date(target_date_str: str):
    """
    指定された日付のPCFファイルをすべて解析し、クレンジング、DB保存まで行うETL処理。
    """
    logging.info(f"--- Running ETL Process for Date: {target_date_str} ---")
    
    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
    except ValueError:
        logging.error("Invalid date format. Please use YYYY-MM-DD.")
        return

    # 1. 取引日を計算
    business_date = get_previous_business_day(target_date)

    # 2. 対象となるzipファイルを検索
    date_formats = {
        'solactive': target_date.strftime('%Y-%m-%d'),
        'ice': target_date.strftime('%Y%m%d'),
        'ihs': target_date.strftime('%Y%m%d')
    }
    base_download_path = os.path.join('data', 'downloads')
    zip_patterns = [
        os.path.join(base_download_path, 'solactive', f'*{date_formats["solactive"]}*.zip'),
        os.path.join(base_download_path, 'ice', f'*{date_formats["ice"]}*.zip'),
        os.path.join(base_download_path, 'ihs', f'*{date_formats["ihs"]}*.zip')
    ]

    found_files = []
    for pattern in zip_patterns:
        found_files.extend(glob.glob(pattern))

    if not found_files:
        logging.warning(f"No zip files found for date {target_date_str}")
        return

    logging.info(f"Found {len(found_files)} zip file(s) to process.")

    all_base_infos = []
    all_holdings_infos = []
    encodings_to_try = ['cp932', 'utf-8', 'sjis']

    # 3. 各zipファイルを処理
    for zip_path in found_files:
        logging.info(f"Processing zip file: {zip_path}")
        source = os.path.basename(os.path.dirname(zip_path))

        try:
            with ZipFile(zip_path, 'r') as zf:
                csv_files = [f for f in zf.namelist() if f.lower().endswith('.csv')]
                for csv_file_name in csv_files:
                    logging.info(f"  Parsing CSV: {csv_file_name}")
                    
                    content = None
                    with zf.open(csv_file_name) as csv_file:
                        file_bytes = csv_file.read()
                    
                    for enc in encodings_to_try:
                        try:
                            content = file_bytes.decode(enc)
                            break
                        except UnicodeDecodeError:
                            continue
                    
                    if content is None:
                        logging.warning(f"    Could not decode {csv_file_name} with any attempted encodings.")
                        continue

                    # 4. 中央パーサーで解析とクレンジングを実行
                    parsed_data = parse_csv_content(content, business_date)
                    
                    if parsed_data:
                        df_base = parsed_data.get('base_info')
                        df_holdings = parsed_data.get('holdings')

                        if df_base is not None and not df_base.empty:
                            df_base['source'] = source
                            all_base_infos.append(df_base)
                        
                        if df_holdings is not None and not df_holdings.empty:
                            if df_base is not None and not df_base.empty and 'etf_code' in df_base.columns:
                                df_holdings['etf_code'] = df_base['etf_code'].iloc[0]
                            df_holdings['source'] = source
                            all_holdings_infos.append(df_holdings)
        except Exception as e:
            logging.error(f"Failed to process zip file {zip_path}: {e}")

    # 5. 集約したデータをDBに保存
    final_base_df = pd.DataFrame()
    if all_base_infos:
        final_base_df = pd.concat(all_base_infos, ignore_index=True)
        logging.info(f"Aggregated {len(final_base_df)} rows for Base Info.")

    final_holdings_df = pd.DataFrame()
    if all_holdings_infos:
        final_holdings_df = pd.concat(all_holdings_infos, ignore_index=True)
        logging.info(f"Aggregated {len(final_holdings_df)} rows for Holdings Info.")

    # データベースハンドラを呼び出して保存
    database_handler.save_dataframes(final_base_df, final_holdings_df, target_date_str)

    logging.info(f"--- ETL Process for Date: {target_date_str} Finished ---")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run ETL process for ETF PCF files for a specific date.")
    parser.add_argument(
        "--date",
        type=str,
        default=datetime.now().strftime('%Y-%m-%d'),
        help="The date to process files for, in YYYY-MM-DD format. Defaults to the current date."
    )
    args = parser.parse_args()
    parse_by_date(args.date)
