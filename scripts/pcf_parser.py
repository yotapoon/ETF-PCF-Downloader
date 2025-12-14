import pandas as pd
import logging
import io
import re

# --- 定義されたカラムリスト ---
# 元のCSVファイルに存在する可能性のあるカラム名のリスト
SOURCE_BASE_COLS = [
    'ETF Code', 'ETF Name', 'Fund Cash Component', 'Shares Outstanding',
    'Fund Date', 'Cash & Others', 'AUM'
]
SOURCE_HOLDINGS_COLS = [
    'Code', 'Name', 'ISIN', 'Isin', 'Exchange', 'Currency', 'Shares Amount',
    'Stock Price', 'Shares', 'Market Value', 'FX Rate',
    'FX Forward Delivery Date', 'Future multiplier'
]

def _clean_column_names(df):
    """DataFrameのカラム名を、定義済みマッピングに基づきスネークケースに変換する"""
    rename_map = {
        'ETF Code': 'etf_code',
        'ETF Name': 'etf_name',
        'Fund Cash Component': 'cash_component',
        'Shares Outstanding': 'shares_outstanding',
        'Fund Date': 'fund_date_in_file', # 元ファイルの日付は参照用に保持
        'Cash & Others': 'cash_and_others',
        'AUM': 'aum',
        'Code': 'local_code',
        'Name': 'name',
        'ISIN': 'isin',
        'Exchange': 'exchange',
        'Currency': 'currency',
        'Shares Amount': 'shares_amount',
        'Stock Price': 'stock_price',
        'Shares': 'shares',
        'Market Value': 'market_value',
        'FX Rate': 'fx_rate',
        'FX Forward Delivery Date': 'fx_forward_delivery_date',
        'Future multiplier': 'future_multiplier',
    }
    # DataFrameに存在するカラムのみをリネーム
    df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)
    return df

def find_header_row(lines, key_column, candidate_columns):
    """
    行のリストから、指定されたキーカラムと候補カラムの過半数が含まれる
    ヘッダー行のインデックスを見つける。
    """
    for i, line in enumerate(lines):
        cleaned_line = line.strip()
        columns = [col.strip() for col in cleaned_line.split(',')]
        if key_column in columns and sum(col in columns for col in candidate_columns) > len(candidate_columns) / 2:
            return i
    return None

def parse_csv_content(csv_content: str, fund_date):
    """
    1つのPCF CSVファイルの中身（文字列）を解析し、
    ETF基本情報と保有銘柄情報の2つのDataFrameを返す。
    この関数はデータクレンジングも実行する。
    """
    lines = csv_content.strip().splitlines()
    if not lines:
        return {'base_info': pd.DataFrame(), 'holdings': pd.DataFrame()}
    lines[0] = lines[0].lstrip('﻿')

    # 1. ETF基本情報の解析
    df_base_info = pd.DataFrame()
    base_header_index = find_header_row(lines, 'ETF Code', SOURCE_BASE_COLS)
    if base_header_index is not None:
        base_info_str = "\n".join(lines[base_header_index : base_header_index + 2])
        try:
            df_base_info = pd.read_csv(io.StringIO(base_info_str), sep=',', engine='python', dtype=str).dropna(how='all', axis=1)
            df_base_info = df_base_info.loc[:, ~df_base_info.columns.str.contains('^Unnamed')]
        except Exception as e:
            logging.warning(f"Could not parse base info: {e}")

    # 2. 保有銘柄情報の解析
    df_holdings = pd.DataFrame()
    holdings_header_index = find_header_row(lines, 'Code', SOURCE_HOLDINGS_COLS)
    if holdings_header_index is not None:
        holdings_info_str = "\n".join(lines[holdings_header_index:])
        try:
            df_holdings = pd.read_csv(io.StringIO(holdings_info_str), sep=',', engine='python', dtype=str).dropna(how='all', axis=1)
            df_holdings = df_holdings.loc[:, ~df_holdings.columns.str.contains('^Unnamed')]
            df_holdings = df_holdings.dropna(how='all')
        except Exception as e:
            logging.warning(f"Could not parse holdings info: {e}")

    # --- 3. データクレンジング ---
    if not df_base_info.empty:
        df_base_info = _clean_column_names(df_base_info)
        df_base_info['fund_date'] = fund_date
        num_cols = ['shares_outstanding', 'aum', 'cash_component', 'cash_and_others']
        for col in num_cols:
            if col in df_base_info.columns:
                df_base_info[col] = pd.to_numeric(df_base_info[col], errors='coerce')

    if not df_holdings.empty:
        # ISINカラムの統合（カラム名変更前に行う）
        if 'Isin' in df_holdings.columns:
            if 'ISIN' in df_holdings.columns:
                df_holdings['ISIN'] = df_holdings['ISIN'].fillna(df_holdings['Isin'])
                df_holdings.drop(columns=['Isin'], inplace=True)
            else:
                df_holdings.rename(columns={'Isin': 'ISIN'}, inplace=True)

        df_holdings = _clean_column_names(df_holdings)
        df_holdings['fund_date'] = fund_date

        if 'currency' in df_holdings.columns:
            df_holdings = df_holdings.dropna(subset=['currency'])

        # market_valueの計算
        shares_col = 'shares' if 'shares' in df_holdings.columns else 'shares_amount'
        if 'market_value' in df_holdings.columns and shares_col in df_holdings.columns and 'stock_price' in df_holdings.columns:
            num_cols_mv = [shares_col, 'stock_price', 'market_value']
            for col in num_cols_mv:
                df_holdings[col] = pd.to_numeric(df_holdings[col], errors='coerce')
            
            mask = df_holdings['market_value'].isnull()
            df_holdings.loc[mask, 'market_value'] = df_holdings.loc[mask, shares_col] * df_holdings.loc[mask, 'stock_price']

        # データ型変換
        num_cols = ['shares', 'shares_amount', 'stock_price', 'market_value', 'fx_rate', 'future_multiplier']
        for col in num_cols:
            if col in df_holdings.columns:
                df_holdings[col] = pd.to_numeric(df_holdings[col], errors='coerce')
        
        if 'fx_forward_delivery_date' in df_holdings.columns:
            df_holdings['fx_forward_delivery_date'] = pd.to_datetime(df_holdings['fx_forward_delivery_date'], errors='coerce').dt.date

    return {
        'base_info': df_base_info,
        'holdings': df_holdings
    }