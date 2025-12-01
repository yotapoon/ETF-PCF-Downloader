import os
import glob
import zipfile
import pandas as pd
import shutil
import logging

# ロギング設定: INFOレベル以上のメッセージをコンソールに出力
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def analyze_csv_structure(csv_path):
    """
    1つのCSVファイルの構造を解析し、ヘッダー情報をリストとして返します。
    複数のエンコーディングを試行します。

    Args:
        csv_path (str): 解析対象のCSVファイルへのパス。

    Returns:
        list: 抽出された構造情報のリスト。各要素は [path, filename, type, header] の形式。
    """
    structures = []
    filename = os.path.basename(csv_path)
    # 試行するエンコーディングのリスト
    encodings_to_try = ['cp932', 'utf-8', 'shift_jis']

    def read_headers(file_path, header_row, encoding_list):
        """指定された行をヘッダーとして読み込み、カラム名を返す"""
        for encoding in encoding_list:
            try:
                # nrows=0 を指定すると、データ部を読み込まずヘッダーのみを取得できる
                df = pd.read_csv(file_path, header=header_row, nrows=0, encoding=encoding, on_bad_lines='skip')
                return df.columns
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue # エンコーディングが違う場合は次のものを試す
            except Exception as e:
                # その他の予期せぬエラー
                logging.warning(f"Could not read header from {filename} with encoding {encoding} at row {header_row + 1}. Error: {e}")
                return None
        logging.warning(f"Failed to read header from {filename} at row {header_row + 1} with any of the specified encodings.")
        return None

    # ETF基本情報のヘッダーを読み込む (2行目想定 -> header=1)
    etf_info_headers = read_headers(csv_path, 1, encodings_to_try)
    if etf_info_headers is not None:
        for col in etf_info_headers:
            col_str = str(col).strip()
            # 空のカラムや 'Unnamed:' で始まる自動生成されたカラム名は除外
            if col_str and 'Unnamed:' not in col_str:
                structures.append([csv_path, filename, 'etf_info', col_str])

    # 保有銘柄一覧のヘッダーを読み込む (4行目想定 -> header=3)
    holdings_headers = read_headers(csv_path, 3, encodings_to_try)
    if holdings_headers is not None:
        for col in holdings_headers:
            col_str = str(col).strip()
            if col_str and 'Unnamed:' not in col_str:
                structures.append([csv_path, filename, 'holdings', col_str])

    return structures

def main():
    """
    メイン処理。
    - data/downloads内の全zipファイルを処理対象とします。
    - zipを解凍し、含まれる全CSVのヘッダー構造を解析します。
    - 結果を`data/csv_structure.csv`に出力します。
    - 処理後、解凍したファイル・ディレクトリは削除します。
    """
    logging.info("--- PCF Parser and Structure Analyzer ---")

    download_dir = 'data/downloads'
    output_csv_path = 'data/csv_structure.csv'
    all_structures = []

    # data/downloads 以下のすべての.zipファイルを再帰的に検索
    zip_files = glob.glob(os.path.join(download_dir, '**/*.zip'), recursive=True)
    if not zip_files:
        logging.info("No zip files found in '%s'.", download_dir)
        return

    logging.info(f"Found {len(zip_files)} zip files to process.")

    for zip_path in zip_files:
        # zipファイル名から拡張子を除いた名前を解凍先ディレクトリ名とする
        extract_dir = zip_path.rsplit('.', 1)[0]
        logging.info(f"Processing {zip_path}...")

        try:
            # zipファイルを解凍
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            logging.info(f"Extracted to {extract_dir}")

            # 解凍後のCSVファイルを再帰的に探索
            csv_files = glob.glob(os.path.join(extract_dir, '**/*.csv'), recursive=True)
            logging.info(f"Found {len(csv_files)} CSV files in extracted directory.")

            # 各CSVの構造を解析
            for csv_file in csv_files:
                structures = analyze_csv_structure(csv_file)
                if structures:
                    all_structures.extend(structures)
                else:
                    logging.warning(f"Could not extract any header from {csv_file}")

        except Exception as e:
            logging.error(f"Failed to process {zip_path}: {e}", exc_info=True)
        finally:
            # 処理後に解凍したディレクトリをクリーンアップ
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
                logging.info(f"Cleaned up directory: {extract_dir}")

    if not all_structures:
        logging.warning("No CSV header information could be extracted from any file.")
        return

    # 結果をDataFrameに変換してCSVに出力
    try:
        structure_df = pd.DataFrame(all_structures, columns=['path', 'filename', 'type', 'header'])
        # Excelで文字化けしないように'utf-8-sig'を指定
        structure_df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
        logging.info(f"Analysis complete. Structure information saved to {output_csv_path}")
    except Exception as e:
        logging.error(f"Failed to save the output CSV file: {e}")

if __name__ == "__main__":
    main()