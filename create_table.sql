-- データベースを指定
USE [ETF_PCFS];
GO

----------------------------------------------------
-- 1. MASTER テーブルの作成
----------------------------------------------------

-- ① ファンドマスタ (MASTER_FUND)
CREATE TABLE MASTER_FUND (
    ETF_Code VARCHAR(20) NOT NULL,
    ETF_Name NVARCHAR(200) NOT NULL, 
    
    CONSTRAINT PK_MASTER_FUND PRIMARY KEY (ETF_Code)
);
GO

-- ② 銘柄マスタ (MASTER_STOCK)
CREATE TABLE MASTER_STOCK (
    ISIN VARCHAR(12) NOT NULL,
    Local_Code VARCHAR(20) NULL,
    Stock_Name NVARCHAR(200) NOT NULL, 
    Exchange VARCHAR(50) NULL,      
    Currency VARCHAR(10) NULL,      
    
    CONSTRAINT PK_MASTER_STOCK PRIMARY KEY (ISIN)
);
GO

----------------------------------------------------
-- 2. TRANSACTION/HISTORY テーブルの作成
----------------------------------------------------

-- ③ ファンド日次履歴テーブル (HISTORY_FUND_DAILY)
CREATE TABLE HISTORY_FUND_DAILY (
    Fund_Date DATE NOT NULL,
    ETF_Code VARCHAR(20) NOT NULL,
    Cash_Component DECIMAL(18,2) NULL, 
    Shares_Outstanding DECIMAL(18,2) NULL, 
    
    CONSTRAINT PK_HISTORY_FUND_DAILY PRIMARY KEY (Fund_Date, ETF_Code),
    
    -- 外部キー: MASTER_FUNDを参照
    CONSTRAINT FK_Daily_MASTER_FUND FOREIGN KEY (ETF_Code) 
        REFERENCES MASTER_FUND(ETF_Code)
);
GO

-- ④ PCF保有明細テーブル (HOLDING_DETAIL)
CREATE TABLE HOLDING_DETAIL (
    Fund_Date DATE NOT NULL,
    ETF_Code VARCHAR(20) NOT NULL,
    ISIN VARCHAR(12) NOT NULL,
    Shares_Amount DECIMAL(18,4) NULL,
    Stock_Price DECIMAL(18,4) NULL,
    
    CONSTRAINT PK_HOLDING_DETAIL PRIMARY KEY (Fund_Date, ETF_Code, ISIN),
    
    -- 外部キー1: HISTORY_FUND_DAILYを参照
    CONSTRAINT FK_Holding_Daily FOREIGN KEY (Fund_Date, ETF_Code) 
        REFERENCES HISTORY_FUND_DAILY(Fund_Date, ETF_Code),
        
    -- 外部キー2: MASTER_STOCKを参照
    CONSTRAINT FK_Holding_Stock FOREIGN KEY (ISIN) 
        REFERENCES MASTER_STOCK(ISIN)
);
GO

