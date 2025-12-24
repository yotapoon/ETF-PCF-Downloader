import pandas as pd
import logging
from pandas.io import sql as pd_sql
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.types import NVARCHAR
import sys
import os

# プロジェクトのルートディレクトリをsys.pathに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

# グローバルなengineインスタンスを定義
engine = None

def get_db_engine():
    """
    SQLAlchemyのengineをシングルトンとして取得・管理する
    """
    global engine
    if engine is None:
        try:
            logging.info("Initializing database engine.")
            engine = create_engine(config.CONNECTION_STRING, fast_executemany=True)
            # 接続テスト
            with engine.connect() as connection:
                logging.info("Database connection successful.")
        except Exception as e:
            logging.error(f"Failed to create database engine: {e}")
            engine = None
            raise
    return engine

def save_dataframes(base_info_df: pd.DataFrame, holdings_df: pd.DataFrame, date: str):
    """
    基本情報と保有銘柄のDataFrameをデータベースに保存するメイン関数
    """
    if base_info_df.empty and holdings_df.empty:
        logging.info("No data to save.")
        return

    try:
        db_engine = get_db_engine()
        with db_engine.connect() as connection:
            # トランザクションを開始
            with connection.begin() as transaction:
                try:
                    if not base_info_df.empty:
                        _save_fund_data(connection, base_info_df)
                    
                    if not holdings_df.empty:
                        # date引数を渡すように変更
                        _save_holdings_data(connection, holdings_df, date)
                    
                    logging.info("Data successfully saved to database.")
                except Exception as e:
                    logging.error(f"Error during database transaction: {e}")
                    # トランザクションは自動的にロールバックされる
                    raise

    except Exception as e:
        logging.error(f"Failed to save dataframes to database: {e}")
        # 必要に応じてさらなるエラーハンドリングをここに記述

def _save_fund_data(connection, df: pd.DataFrame):
    """
    ファンドのマスターデータと日次データを保存する
    """
    # 1. master_fund のUPSERT
    if 'etf_code' in df.columns and 'etf_name' in df.columns:
        fund_master_df = df[['etf_code', 'etf_name']].dropna().drop_duplicates(subset=['etf_code'])
        _upsert(connection, 'master_fund', fund_master_df, ['etf_code'])

    # 2. history_fund_daily のINSERT
    history_cols = ['fund_date', 'etf_code', 'cash_component', 'shares_outstanding', 'cash_and_others', 'aum', 'source']
    existing_cols = [col for col in history_cols if col in df.columns]
    fund_history_df = df[existing_cols].copy()

    for col in history_cols:
        if col not in fund_history_df.columns:
            fund_history_df[col] = None
    
    fund_history_df = fund_history_df[history_cols]
    fund_history_df.drop_duplicates(inplace=True)
    
    if not fund_history_df.empty:
        try:
            fund_history_df.to_sql('history_fund_daily', connection, if_exists='append', index=False)
            logging.info(f"Inserted {len(fund_history_df)} rows into history_fund_daily.")
        except IntegrityError:
            logging.warning("Some daily fund data might already exist. Skipping duplicates.")


def _save_holdings_data(connection, df: pd.DataFrame, date: str):
    """
    保有銘柄のマスターデータと詳細データを保存する。
    ISINの有無で処理を分岐し、すべての銘柄を正しく登録・参照する。
    """
    if df.empty:
        logging.info("No holdings data to save.")
        return

    # 1. master_stockに登録するための元データ準備
    master_stock_cols = ['isin', 'local_code', 'name', 'exchange', 'currency']
    existing_cols = [col for col in master_stock_cols if col in df.columns]
    stock_master_df = df[existing_cols].copy()
    for col in master_stock_cols:
        if col not in stock_master_df.columns:
            stock_master_df[col] = None
    stock_master_df = stock_master_df.rename(columns={'name': 'stock_name'})

    stock_master_df.drop_duplicates(subset=['isin'], inplace=True, ignore_index=True)
    stock_master_df.drop_duplicates(subset=['local_code', 'exchange'], inplace=True, ignore_index=True)

    # 2. ISINの有無でグループ分けしてUPSERT
    df_with_isin = stock_master_df[stock_master_df['isin'].notna()].copy()
    df_without_isin = stock_master_df[stock_master_df['isin'].isna()].copy()

    if not df_with_isin.empty:
        _upsert(connection, 'master_stock', df_with_isin, ['isin'])
    if not df_without_isin.empty:
        df_without_isin.dropna(subset=['local_code', 'exchange'], inplace=True)
        if not df_without_isin.empty:
            _upsert(connection, 'master_stock', df_without_isin, ['local_code', 'exchange'])

    # 3. master_stockからstock_idを取得
    # ISINを持つ銘柄のIDを取得
    isin_map_df = pd.DataFrame()
    all_isins = df['isin'].dropna().unique().tolist()
    if all_isins:
        isins_df = pd.DataFrame(all_isins, columns=['isin'])
        temp_isin_table = '#temp_isin_list'
        _safe_to_temp_sql(isins_df, temp_isin_table, connection)
        query_isin = text(f"""
            SELECT T1.stock_id, T1.isin FROM master_stock AS T1
            INNER JOIN {temp_isin_table} AS T2 ON T1.isin = T2.isin
        """)
        isin_map_df = pd.read_sql_query(query_isin, connection)

    # ISINを持たない銘柄のIDを取得
    local_code_map_df = pd.DataFrame()
    df_for_local_code_lookup = df[df['isin'].isnull() & df['local_code'].notna() & df['exchange'].notna()]
    if not df_for_local_code_lookup.empty:
        local_codes_df = df_for_local_code_lookup[['local_code', 'exchange']].drop_duplicates()
        temp_local_code_table = '#temp_local_code_list'
        _safe_to_temp_sql(local_codes_df, temp_local_code_table, connection)
        query_local_code = text(f"""
            SELECT T1.stock_id, T1.local_code, T1.exchange FROM master_stock AS T1
            INNER JOIN {temp_local_code_table} AS T2 ON T1.local_code = T2.local_code AND T1.exchange = T2.exchange
        """)
        local_code_map_df = pd.read_sql_query(query_local_code, connection)

    # 4. holding_detail の準備 (stock_idをマージ)
    df_with_stock_id = df.copy()
    if not isin_map_df.empty:
        df_with_stock_id = pd.merge(df_with_stock_id, isin_map_df, on='isin', how='left')

    if 'stock_id' not in df_with_stock_id.columns:
        df_with_stock_id['stock_id'] = None

    if not local_code_map_df.empty:
        df_with_stock_id = pd.merge(
            df_with_stock_id,
            local_code_map_df,
            on=['local_code', 'exchange'],
            how='left',
            suffixes=('', '_from_local')
        )
        df_with_stock_id['stock_id'] = df_with_stock_id['stock_id'].fillna(df_with_stock_id['stock_id_from_local'])
        df_with_stock_id.drop(columns=['stock_id_from_local'], inplace=True)

    # 5. stock_idが取得できなかったデータは警告を出す
    missing_stock_ids = df_with_stock_id[df_with_stock_id['stock_id'].isnull()]
    if not missing_stock_ids.empty:
        skipped_samples = missing_stock_ids[['etf_code', 'isin', 'name', 'local_code']].head(5).to_string(index=False)
        logging.warning(f"Could not find stock_id for {len(missing_stock_ids)} holding rows after all attempts. These rows will be skipped.")
        logging.warning(f"Skipped sample rows:\n{skipped_samples}")

    # stock_idが存在する行のみを抽出し、コピーを作成してSettingWithCopyWarningを回避
    holding_detail_df = df_with_stock_id[df_with_stock_id['stock_id'].notna()].copy()
    if not holding_detail_df.empty:
        holding_detail_df['stock_id'] = holding_detail_df['stock_id'].astype(int)

    # 6. holding_detail のINSERT
    cols = ['fund_date', 'etf_code', 'stock_id', 'shares_amount', 'stock_price', 'market_value', 'fx_rate', 'fx_forward_delivery_date', 'future_multiplier', 'source']
    
    final_cols = [c for c in cols if c in holding_detail_df.columns]
    final_holding_df = holding_detail_df[final_cols].copy()
    
    final_holding_df.drop_duplicates(inplace=True)

    if not final_holding_df.empty:
        try:
            final_holding_df.to_sql('holding_detail', connection, if_exists='append', index=False)
            logging.info(f"Inserted {len(final_holding_df)} rows into holding_detail.")
        except IntegrityError:
            logging.warning("Some holding detail data might already exist. Skipping duplicates.")

def _safe_to_temp_sql(df: pd.DataFrame, table_name: str, connection, dtype_map: dict = None):
    """
    DataFrameをSQL Serverの一時テーブルに安全に書き込むヘルパー関数。
    pandas.to_sqlのif_exists='replace'が引き起こすリフレクションエラーを回避する。
    """
    if not table_name.startswith('#'):
        raise ValueError("Temporary table name must start with '#'")

    # `tempdb`でオブジェクトIDを確認するのは、一時テーブルを扱う際の堅牢な方法
    connection.execute(text(f"IF OBJECT_ID('tempdb..{table_name}') IS NOT NULL DROP TABLE {table_name}"))

    # DataFrameを一時テーブルにロード（if_existsはデフォルトの'fail'のまま）
    df.to_sql(table_name, connection, index=False, dtype=dtype_map)

def _upsert(connection, table_name, df, key_cols):
    """
    MERGE文を使ってDataFrameのデータをテーブルにUPSERTする汎用関数
    """
    if df.empty:
        return

    temp_table_name = f"#{table_name}_temp"

    # DataFrameの文字列型カラムの型を明示的に指定
    dtype_map = {}
    for col in df.columns:
        if df[col].dtype == 'object' and df[col].notna().any():
            max_len = int(df[col].str.len().max())
            dtype_map[col] = NVARCHAR(max_len if max_len > 0 else 1)

    # MERGE文を先に構築
    update_cols = [col for col in df.columns if col not in key_cols]
    merge_sql = f"""
    MERGE {table_name} AS target
    USING {temp_table_name} AS source
    ON ({' AND '.join([f'target.{key} = source.{key}' for key in key_cols])})
    WHEN MATCHED THEN
        UPDATE SET {', '.join([f'target.{col} = source.{col}' for col in update_cols])}
    WHEN NOT MATCHED THEN
        INSERT ({', '.join(df.columns)})
        VALUES ({', '.join([f'source.{col}' for col in df.columns])});
    """

    try:
        # 新しいヘルパー関数で安全に一時テーブルへ書き込む
        _safe_to_temp_sql(df, temp_table_name, connection, dtype_map=dtype_map)

        # MERGE実行
        connection.execute(text(merge_sql))
        logging.info(f"Upserted {len(df)} rows into {table_name}.")

    except Exception as e:
        logging.error(f"Error during upsert to {table_name}: {e}")
        raise
