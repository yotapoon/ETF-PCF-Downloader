import logging
from datetime import datetime
import pandas as pd
import time

# 既存の処理スクリプトから、日付指定で処理を実行する関数をインポート
try:
    from import_daily_pcf import parse_by_date
except ImportError:
    logging.error("Failed to import 'parse_by_date' from 'import_daily_pcf'. Make sure the script is in the same directory.")
    # このスクリプトが 'scripts' ディレクトリにあることを前提としているため、
    # 必要に応じてsys.pathを調整するなどの対応が必要になる場合があります。
    # ここでは、同一ディレクトリにあると仮定して進めます。
    exit(1)


# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def batch_import():
    """
    指定された期間の平日について、日次PCFデータのインポート処理を実行する。
    """
    # 開始日と終了日を設定
    start_date = "2025-7-11" # iceはここから
    # start_date = "2021-06-21" # solactiveはここから
    # start_date = "2025-3-21" # ihsはここから
    end_date = datetime.now().strftime('%Y-%m-%d')

    logging.info(f"Starting batch import from {start_date} to {end_date}.")

    # 指定された期間内の平日（月曜日から金曜日）の日付リストを生成
    # 日本の祝日は考慮しない
    date_range = pd.bdate_range(start=start_date, end=end_date)

    if date_range.empty:
        logging.warning("No business days found in the specified date range.")
        return

    total_days = len(date_range)
    logging.info(f"Found {total_days} business days to process.")

    # 各平日について処理を実行
    for i, business_day in enumerate(date_range):
        date_str = business_day.strftime('%Y-%m-%d')
        logging.info(f"--- Processing day {i+1}/{total_days}: {date_str} ---")

        try:
            # 既存のETL処理関数を呼び出す
            parse_by_date(date_str)
            logging.info(f"Successfully finished processing for {date_str}.")
        except Exception as e:
            # 特定の日の処理でエラーが発生しても、全体を停止させずに次に進む
            logging.error(f"An error occurred while processing date {date_str}: {e}", exc_info=True)

        # サーバー等への負荷を考慮して、1秒待機
        time.sleep(1)

    logging.info("Batch import process finished.")

if __name__ == "__main__":
    batch_import()
