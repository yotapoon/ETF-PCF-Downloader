-- データベースを指定
USE [ETF_PCFS];
GO

----------------------------------------------------
-- 0. テーブルの削除 (存在する場合)
-- 依存関係を考慮し、参照しているテーブルから先に削除する
----------------------------------------------------
IF OBJECT_ID('dbo.holding_detail', 'U') IS NOT NULL
    DROP TABLE dbo.holding_detail;
GO
IF OBJECT_ID('dbo.history_fund_daily', 'U') IS NOT NULL
    DROP TABLE dbo.history_fund_daily;
GO
IF OBJECT_ID('dbo.master_fund', 'U') IS NOT NULL
    DROP TABLE dbo.master_fund;
GO
IF OBJECT_ID('dbo.master_stock', 'U') IS NOT NULL
    DROP TABLE dbo.master_stock;
GO

----------------------------------------------------
-- 1. MASTER テーブルの作成
----------------------------------------------------

-- ① ファンドマスタ (master_fund)
CREATE TABLE master_fund (
    etf_code VARCHAR(4) NOT NULL,
    etf_name NVARCHAR(200) NOT NULL,

    CONSTRAINT pk_master_fund PRIMARY KEY (etf_code)
);
GO

-- ② 銘柄マスタ (master_stock)
CREATE TABLE master_stock (
    stock_id INT IDENTITY(1,1) NOT NULL,
    isin VARCHAR(12) NULL,
    local_code VARCHAR(20) NULL,
    stock_name NVARCHAR(200) NULL,
    exchange VARCHAR(50) NULL,
    currency VARCHAR(10) NULL,

    CONSTRAINT pk_master_stock PRIMARY KEY (stock_id)
);
GO

-- isinがNULLでない場合に一意性を保証するFiltered Indexを作成
CREATE UNIQUE INDEX uq_master_stock_isin_notnull
ON master_stock(isin)
WHERE isin IS NOT NULL;
GO

----------------------------------------------------
-- 2. TRANSACTION/HISTORY テーブルの作成
----------------------------------------------------

-- ③ 日次ファンド情報テーブル (history_fund_daily)
CREATE TABLE history_fund_daily (
    fund_date DATE NOT NULL,
    etf_code VARCHAR(4) NOT NULL,
    cash_component DECIMAL(18,2) NULL,
    shares_outstanding DECIMAL(18,2) NULL,
	cash_and_others DECIMAL(18,2) NULL,
	aum DECIMAL(18,2) NULL,
    source VARCHAR(20) NULL,

    CONSTRAINT pk_history_fund_daily PRIMARY KEY (fund_date, etf_code),

    -- 外部キー: master_fundを参照
    CONSTRAINT fk_daily_master_fund FOREIGN KEY (etf_code)
        REFERENCES master_fund(etf_code)
);
GO

-- ④ PCF構成銘柄テーブル (holding_detail)
CREATE TABLE holding_detail (
    fund_date DATE NOT NULL,
    etf_code VARCHAR(4) NOT NULL,
    stock_id INT NOT NULL,
    shares_amount DECIMAL(18,4) NULL,
    stock_price DECIMAL(18,4) NULL,
    market_value DECIMAL(18, 4) NULL,
    fx_rate DECIMAL(18, 8) NULL,
    fx_forward_delivery_date DATE NULL,
    future_multiplier DECIMAL(18, 4) NULL,
    source VARCHAR(20) NULL,

    CONSTRAINT pk_holding_detail PRIMARY KEY (fund_date, etf_code, stock_id),

    -- 外部キー1: history_fund_dailyを参照
    CONSTRAINT fk_holding_daily FOREIGN KEY (fund_date, etf_code)
        REFERENCES history_fund_daily(fund_date, etf_code),

    -- 外部キー2: master_stockを参照
    CONSTRAINT fk_holding_stock FOREIGN KEY (stock_id)
        REFERENCES master_stock(stock_id)
);
GO