import pandas as pd
import os
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 定義されたカラムリスト ---
# ETF基本情報の候補カラム
ETF_BASE_INFO_COLS = [
    'ETF Code', 'ETF Name', 'Fund Cash Component', 'Shares Outstanding',
    'Fund Date', 'Cash & Others', 'AUM'
]
# 保有銘柄情報の候補カラム
ETF_HOLDINGS_COLS = [
    'Code', 'Name', 'ISIN', 'Exchange', 'Currency', 'Shares Amount',
    'Stock Price', 'Shares', 'Market Value', 'FX Rate',
    'FX Forward Delivery Date', 'Future multiplier'
]

def find_header_row(csv_path, key_column, candidate_columns, encoding='cp932'):
    """
    指定されたキーカラムと候補カラムの過半数が含まれる行（ヘッダー行）の行番号を見つける。
    行をカンマで分割して、フィールドとしてカラム名が存在するかをチェックする。
    """
    try:
        with open(csv_path, 'r', encoding=encoding) as f:
            for i, line in enumerate(f):
                # 行をカンマで分割し、各要素の空白を除去
                columns = [col.strip() for col in line.split(',')]
                # キーカラムが存在し、かつ候補カラムの過半数が存在するかチェック
                if key_column in columns and sum(col in columns for col in candidate_columns) > len(candidate_columns) / 2:
                    return i
        return None
    except Exception as e:
        logging.error(f"Error reading file {csv_path} to find header: {e}")
        return None

def parse_pcf_file(csv_path, encoding='cp932'):
    """
    1つのPCF CSVファイルを解析し、ETF基本情報と保有銘柄情報を抽出する
    """
    logging.info(f"Parsing file: {csv_path}")

    # 1. ETF基本情報のヘッダー行を探す
    base_info_header_row = find_header_row(csv_path, 'ETF Code', ETF_BASE_INFO_COLS, encoding)
    if base_info_header_row is None:
        logging.warning(f"'ETF Code' not found in {csv_path}. Skipping ETF base info.")
        return None

    # 2. ETF基本情報を読み込む (ヘッダーの次の1行)
    try:
        df_base_info = pd.read_csv(
            csv_path,
            header=base_info_header_row,
            nrows=1,
            encoding=encoding,
            engine='python',
            sep=',',  # 区切り文字をカンマに明示
            on_bad_lines='skip' # 不正な行はスキップ
        )
        # 余分なUnnamed列を削除
        df_base_info = df_base_info.loc[:, ~df_base_info.columns.str.contains('^Unnamed')]
        # 必要なカラムのみに絞り込む
        df_base_info = df_base_info[[col for col in ETF_BASE_INFO_COLS if col in df_base_info.columns]]

    except Exception as e:
        logging.error(f"Failed to parse ETF base info from {csv_path}: {e}")
        return None

    # 3. 保有銘柄情報のヘッダー行を探す (基本情報ヘッダーより後)
    holdings_header_row = find_header_row(csv_path, 'Code', ETF_HOLDINGS_COLS, encoding)
    if holdings_header_row is None:
        logging.warning(f"'Code' not found in {csv_path}. Skipping ETF holdings.")
        return {'base_info': df_base_info, 'holdings': pd.DataFrame()}

    # 4. 保有銘柄情報を読み込む
    try:
        df_holdings = pd.read_csv(
            csv_path,
            header=holdings_header_row,
            encoding=encoding,
            engine='python',
            sep=',', # 区切り文字をカンマに明示
            on_bad_lines='skip' # 不正な行はスキップ
        )
        # 余分なUnnamed列を削除
        df_holdings = df_holdings.loc[:, ~df_holdings.columns.str.contains('^Unnamed')]
        # 必要なカラムのみに絞り込む
        df_holdings = df_holdings[[col for col in ETF_HOLDINGS_COLS if col in df_holdings.columns]]
        # すべての列がNaNである行を削除
        df_holdings = df_holdings.dropna(how='all')

    except Exception as e:
        logging.error(f"Failed to parse ETF holdings from {csv_path}: {e}")
        return {'base_info': df_base_info, 'holdings': pd.DataFrame()}
    
    return {
        'base_info': df_base_info,
        'holdings': df_holdings
    }

def test_parsing():
    """
    特定の日付のファイルを使ってパース処理をテストする
    """
    logging.info("--- Running Test Parsing ---")
    
    # テスト対象のファイルパス
    test_file = os.path.join('data', '1306tsepcf_Dec042025.csv')

    if not os.path.exists(test_file):
        logging.error(f"Test file not found: {test_file}")
        # 仮のテストファイルを作成する
        logging.info("Creating a dummy test file for demonstration.")
        dummy_data = [
            ["Fund Date,12/04/2025,ETF Code,1306,ETF Name,TOPIX Core30 ETF,,,Shares Outstanding,100000,AUM,500000000,Cash & Others,12345.67"],
            [], # empty line
            ["Code,Name,ISIN,Exchange,Shares,Stock Price,Market Value,Currency"],
            ["7203,Toyota Motor,JP3633400001,TSE,500,9000,4500000,JPY"],
            ["9984,Softbank Group,JP3436100006,TSE,300,7000,2100000,JPY"],
        ]
        
        # ディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        
        with open(test_file, 'w', newline='', encoding='cp932') as f:
            for row in dummy_data:
                f.write(','.join(map(str, row)) + '\n')
                
    # 複数のエンコーディングを試す
    encodings_to_try = ['cp932', 'utf-8', 'sjis']
    parsed_data = None
    for enc in encodings_to_try:
        try:
            parsed_data = parse_pcf_file(test_file, encoding=enc)
            if parsed_data and not parsed_data['base_info'].empty:
                logging.info(f"Successfully parsed with encoding: {enc}")
                break
        except Exception:
            continue
            
    if parsed_data:
        logging.info("\n--- ETF Base Info ---")
        print(parsed_data['base_info'].to_string())
        
        logging.info("\n--- ETF Holdings (first 5 rows) ---")
        print(parsed_data['holdings'].head().to_string())
    else:
        logging.error("Failed to parse the test file with all attempted encodings.")

    logging.info("--- Test Parsing Finished ---")

if __name__ == '__main__':
    test_parsing()
