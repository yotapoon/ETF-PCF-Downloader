import os
import requests
import pandas as pd
import zipfile
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# 設定
# このスクリプトがどこから実行されても正しくパスを解決するための設定
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

LOG_CSV = os.path.join(project_root, 'download_log.csv')
BASE_DIR = os.path.join(project_root, 'data', 'downloads')

for src in ['ice', 'ihs', 'solactive']:
    os.makedirs(os.path.join(BASE_DIR, src), exist_ok=True)

# ログ読み込み／初期化
if os.path.exists(LOG_CSV):
    log_df = pd.read_csv(LOG_CSV, parse_dates=['date']).set_index('date')
else:
    cols = [
        'flag_load_ice','flag_unzip_ice',
        'flag_load_ihs','flag_unzip_ihs',
        'flag_load_solactive','flag_unzip_solactive'
    ]
    log_df = pd.DataFrame(columns=cols)

# ダウンロードヘルパー
def try_download(url, path, check_zip=False):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        with open(path, 'wb') as f:
            f.write(r.content)
        # ZIP検証
        if check_zip:
            if not zipfile.is_zipfile(path):
                os.remove(path)
                return 0
        return 1
    except Exception:
        # 異常時はファイル削除の可能性を考慮
        if os.path.exists(path):
            os.remove(path)
        return 0

today = datetime.today().date()

# ICE: 過去14日分 (ZIP 形式の検証を有効化)
start = today - timedelta(days=10)
for d in pd.date_range(start, today):
    dt = d.date()
    ds = dt.strftime('%Y%m%d')
    if d not in log_df.index:
        log_df.loc[d] = 0
    if log_df.at[d, 'flag_load_ice'] == 1:
        continue
    url = f"https://inav.ice.com/pcf-download/all/all_pcf_{ds}.zip"
    out_path = os.path.join(BASE_DIR, 'ice', f"ice_{ds}.zip")
    flag = try_download(url, out_path, check_zip=True)
    print(f"Downloading ICE PCF for {ds}: {'Success' if flag else 'Failed'}")
    log_df.at[d, 'flag_load_ice'] = flag
    log_df.at[d, 'flag_unzip_ice'] = 0
    log_df.to_csv(LOG_CSV, index_label='date')


# IHS: 過去4ヶ月分
# start = today - relativedelta(months=4)
start = today - relativedelta(days=10)
for d in pd.date_range(start, today):
    dt = d.date()
    ds = dt.strftime('%Y%m%d')
    if d not in log_df.index:
        log_df.loc[d] = 0
    if log_df.at[d, 'flag_load_ihs'] == 1:
        continue
    url = f"https://api.ebs.ihsmarkit.com/inav/getfile?filename=all_pcf_{ds}.zip"
    out_path = os.path.join(BASE_DIR, 'ihs', f"ihs_{ds}.zip")
    flag = try_download(url, out_path)
    print(f"Downloading IHS PCF for {ds}: {'Success' if flag else 'Failed'}")
    log_df.at[d, 'flag_load_ihs'] = flag
    log_df.at[d, 'flag_unzip_ihs'] = 0
    log_df.to_csv(LOG_CSV, index_label='date')

# Solactive: 過去4年2ヶ月分
# start = today - relativedelta(years=4, months=2)
start = today - relativedelta(days=10)

for d in pd.date_range(start, today):
    dt = d.date()
    ds = dt.strftime('%Y-%m-%d')
    if d not in log_df.index:
        log_df.loc[d] = 0
    if log_df.at[d, 'flag_load_solactive'] == 1:
        continue
    url = f"https://www.solactive.com/downloads/etfservices/tse-pcf/bulk/{ds}.zip"
    out_path = os.path.join(BASE_DIR, 'solactive', f"solactive_{ds}.zip")
    flag = try_download(url, out_path)
    print(f"Downloading Solactive PCF for {ds}: {'Success' if flag else 'Failed'}")
    log_df.at[d, 'flag_load_solactive'] = flag
    log_df.at[d, 'flag_unzip_solactive'] = 0
    log_df.to_csv(LOG_CSV, index_label='date')



print('Done.')
