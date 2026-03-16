import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import hashlib
import pickle
import os
from pathlib import Path
import io
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 🚀 股神帶你飛 v3.2 - 手機緊急修正版（支援 CSV 貼上）
# ============================================================

st.set_page_config(
    page_title="🚀 股神帶你飛 - 三強對決 v3.2",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定義 CSS（保留動畫效果 + 新增 CSV 輸入區樣式）
st.markdown("""
<style>
    .god-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
    }
    .god-card:hover {
        transform: translateY(-5px);
    }
    .trading-animation {
        background: linear-gradient(90deg, #00c9ff 0%, #92fe9d 100%);
        height: 4px;
        border-radius: 2px;
        animation: trading-pulse 1s ease-in-out infinite;
    }
    @keyframes trading-pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    .data-info {
        background-color: #f0f2f6;
        border-left: 4px solid #00b894;
        padding: 10px;
        margin: 10px 0;
        border-radius: 5px;
        font-size: 0.9rem;
    }
    .csv-box {
        background-color: #e3f2fd;
        border: 2px dashed #2196f3;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .phone-notice {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 資料管理（新增 CSV 貼上支援）
# ============================================================
class DataManager:
    """資料管理器 - 支援 FinMind API、本地快取與 CSV 貼上"""

    def __init__(self, api_token=None):
        self.api_token = api_token
        self.cache_dir = Path(".cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.data_source = "FinMind" if api_token else "TWSE"
        self.csv_data = None  # 儲存貼上的 CSV 資料

    def set_csv_data(self, csv_text):
        """解析用戶貼上的 CSV 文字"""
        try:
            # 智能檢測分隔符
            if '\t' in csv_text:
                df = pd.read_csv(io.StringIO(csv_text), sep='\t')
            else:
                df = pd.read_csv(io.StringIO(csv_text))
            
            # 標準化欄位名稱（處理大小寫與中文）
            df.columns = [col.strip() for col in df.columns]
            column_mapping = {}
            
            # 自動對應常見欄位名稱
            for col in df.columns:
                col_upper = col.upper()
                if col_upper in ['DATE', '日期', 'DAY']:
                    column_mapping[col] = 'Date'
                elif col_upper in ['OPEN', '開盤', '開盤價']:
                    column_mapping[col] = 'Open'
                elif col_upper in ['HIGH', '最高', '最高價']:
                    column_mapping[col] = 'High'
                elif col_upper in ['LOW', '最低', '最低價']:
                    column_mapping[col] = 'Low'
                elif col_upper in ['CLOSE', '收盤', '收盤價', 'PRICE']:
                    column_mapping[col] = 'Close'
                elif col_upper in ['VOLUME', '成交量', 'VOL', '量']:
                    column_mapping[col] = 'Volume'
            
            if column_mapping:
                df = df.rename(columns=column_mapping)
            
            # 確保必要欄位存在
            required_cols = ['Date', 'Open', 'High', 'Low', 'Close']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                return False, f"缺少必要欄位: {', '.join(missing_cols)}。請確保 CSV 包含 Date, Open, High, Low, Close 欄位。"
            
            # 資料型態轉換
            df['Date'] = pd.to_datetime(df['Date'])
            for col in ['Open', 'High', 'Low', 'Close']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            if 'Volume' in df.columns:
                df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce').fillna(0)
            else:
                df['Volume'] = 0
            
            # 移除無效資料
            df = df.dropna(subset=required_cols)
            df = df.sort_values('Date').reset_index(drop=True)
            
            self.csv_data = df
            return True, f"✅ 成功載入 {len(df)} 筆資料（{df['Date'].min().date()} 至 {df['Date'].max().date()}）"
            
        except Exception as e:
            return False, f"❌ CSV 解析錯誤: {str(e)}"

    def get_stock_list(self):
        """取得股票清單（優先使用快取）"""
        cache_file = self.cache_dir / "stock_list.pkl"

        if cache_file.exists():
            cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if (datetime.now() - cache_time).days < 7:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)

        if self.api_token:
            stocks = self._fetch_finmind_stock_list()
        else:
            stocks = self._fetch_twse_stock_list()

        if stocks:
            with open(cache_file, 'wb') as f:
                pickle.dump(stocks, f)

        return stocks

    def _fetch_finmind_stock_list(self):
        """使用 FinMind API 抓取股票清單"""
        try:
            url = "https://api.finmindtrade.com/api/v4/data"
            params = {
                "dataset": "TaiwanStockInfo",
                "token": self.api_token
            }
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data.get('status') == 200 and 'data' in data:
                stocks = {}
                for item in data['data']:
                    stocks[item['stock_id']] = item['stock_name']
                return stocks
        except Exception as e:
            st.error(f"FinMind API 錯誤: {e}")
        return None

    def _fetch_twse_stock_list(self):
        """備援：使用 TWSE API"""
        try:
            url = "https://www.twse.com.tw/exchangeReport/STOCK_ALL?response=json"
            response = requests.get(url, timeout=10)
            data = response.json()

            if data.get('stat') == 'OK':
                stocks = {}
                for item in data['data'][:200]:
                    code = item[0].strip()
                    name = item[1].strip()
                    stocks[code] = name
                return stocks
        except:
            pass

        # 預設熱門股票
        return {
            "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2382": "廣達",
            "2308": "台達電", "2881": "富邦金", "2891": "中信金", "2002": "中鋼",
            "1303": "南亞", "2412": "中華電", "2882": "國泰金", "3008": "大立光",
            "1216": "統一", "1301": "台塑", "2892": "第一金", "5880": "合庫金",
            "2884": "玉山金", "2885": "元大金", "2886": "兆豐金", "1101": "台泥",
            "2327": "國巨", "2303": "聯電", "2880": "華南金", "2357": "華碩",
            "2887": "台新金", "2890": "永豐金", "2912": "統一超", "9904": "寶成",
            "2207": "和泰車", "3045": "台灣大", "1402": "遠東新", "1326": "台化"
        }

    def fetch_stock_data(self, stock_no, years=3, force_update=False, use_csv=False):
        """
        抓取股票資料（支援 CSV 模式）
        use_csv: True 則使用貼上的 CSV 資料
        """
        # 如果使用 CSV 模式且已有資料，直接回傳
        if use_csv and self.csv_data is not None:
            return self.csv_data, "CSV匯入"
        
        # 原有的 API 抓取邏輯
        cache_file = self.cache_dir / f"{stock_no}_data.pkl"

        if not force_update and cache_file.exists():
            cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            cache_age = (datetime.now() - cache_time).days

            if cache_age < 1:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                return cached_data['df'], cached_data['last_update']

            if cache_age < 30:
                return self._update_existing_data(stock_no, pickle.load(open(cache_file, 'rb')), cache_file)

        return self._fetch_full_history(stock_no, years, cache_file)

    def _fetch_full_history(self, stock_no, years, cache_file):
        """抓取完整歷史資料"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years*365)

        if self.api_token:
            df = self._fetch_finmind_history(stock_no, start_date, end_date)
        else:
            df = self._fetch_twse_history(stock_no, start_date, end_date)

        if df is not None and len(df) > 0:
            cache_data = {
                'df': df,
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'source': self.data_source
            }
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            return df, cache_data['last_update']

        return None, None

    def _update_existing_data(self, stock_no, cached_data, cache_file):
        """更新現有資料"""
        df_existing = cached_data['df']
        last_date = pd.to_datetime(df_existing['Date'].max())
        start_date = last_date + timedelta(days=1)
        end_date = datetime.now()

        if self.api_token:
            df_new = self._fetch_finmind_history(stock_no, start_date, end_date)
        else:
            df_new = self._fetch_twse_history(stock_no, start_date, end_date)

        if df_new is not None and len(df_new) > 0:
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined = df_combined.drop_duplicates(subset=['Date'], keep='last')
            df_combined = df_combined.sort_values('Date').reset_index(drop=True)

            cache_data = {
                'df': df_combined,
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'source': self.data_source
            }
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)

            return df_combined, cache_data['last_update']

        return df_existing, cached_data['last_update']

    def _fetch_finmind_history(self, stock_no, start_date, end_date):
        """使用 FinMind API 抓取歷史股價"""
        try:
            url = "https://api.finmindtrade.com/api/v4/data"
            params = {
                "dataset": "TaiwanStockPrice",
                "data_id": stock_no,
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": end_date.strftime('%Y-%m-%d'),
                "token": self.api_token
            }

            response = requests.get(url, params=params, timeout=15)
            data = response.json()

            if data.get('status') == 200 and 'data' in data:
                df = pd.DataFrame(data['data'])
                if len(df) > 0:
                    df = df.rename(columns={
                        'date': 'Date',
                        'open': 'Open',
                        'max': 'High',
                        'min': 'Low',
                        'close': 'Close',
                        'Trading_Volume': 'Volume'
                    })
                    df['Date'] = pd.to_datetime(df['Date'])
                    df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                    return df
        except Exception as e:
            st.warning(f"FinMind 抓取失敗: {e}")
        return None

    def _fetch_twse_history(self, stock_no, start_date, end_date):
        """備援：使用 TWSE API"""
        all_data = []
        months = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month

        for i in range(months + 1):
            query_date = end_date - timedelta(days=i*30)
            date_str = query_date.strftime('%Y%m01')

            url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={stock_no}"

            try:
                response = requests.get(url, timeout=10)
                data = response.json()

                if data.get('stat') == 'OK' and 'data' in data:
                    for row in data['data']:
                        date_parts = row[0].split('/')
                        year = int(date_parts[0]) + 1911
                        date_str_fmt = f"{year}-{date_parts[1]}-{date_parts[2]}"
                        all_data.append({
                            'Date': pd.to_datetime(date_str_fmt),
                            'Open': float(row[3].replace(',', '')),
                            'High': float(row[4].replace(',', '')),
                            'Low': float(row[5].replace(',', '')),
                            'Close': float(row[6].replace(',', '')),
                            'Volume': int(row[1].replace(',', ''))
                        })
            except:
                continue

        if all_data:
            df = pd.DataFrame(all_data).sort_values('Date').reset_index(drop=True)
            return df
        return None

# ============================================================
# 策略引擎（保持原有邏輯）
# ============================================================
class StrategyEngine:
    """策略計算引擎"""

    @staticmethod
    def calculate_indicators(df):
        """計算技術指標"""
        df = df.copy()
        close = df['Close']
        high = df['High']
        low = df['Low']

        # 移動平均
        df['MA5'] = close.rolling(5).mean()
        df['MA10'] = close.rolling(10).mean()
        df['MA20'] = close.rolling(20).mean()
        df['MA60'] = close.rolling(60).mean()

        # KD
        low_min = low.rolling(9).min()
        high_max = high.rolling(9).max()
        df['K'] = 100 * (close - low_min) / (high_max - low_min)
        df['D'] = df['K'].rolling(3).mean()

        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + gain / loss))

        # MACD
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

        # 布林通道
        df['BB_Middle'] = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)

        return df

    @staticmethod
    def generate_signal(df, strategy_config, idx):
        """根據策略配置生成交易訊號"""
        if idx < 60:
            return 0, []

        row = df.iloc[idx]
        prev = df.iloc[idx-1] if idx > 0 else row

        signal = 0
        buy_conditions = []
        sell_conditions = []

        # MA策略
        if strategy_config.get('use_ma', False):
            ma_short = strategy_config.get('ma_short', 5)
            ma_long = strategy_config.get('ma_long', 20)

            golden_cross = row[f'MA{ma_short}'] > row[f'MA{ma_long}'] and prev[f'MA{ma_short}'] <= prev[f'MA{ma_long}']
            death_cross = row[f'MA{ma_short}'] < row[f'MA{ma_long}'] and prev[f'MA{ma_short}'] >= prev[f'MA{ma_long}']

            if golden_cross:
                buy_conditions.append('MA黃金交叉')
            if death_cross:
                sell_conditions.append('MA死亡交叉')

        # KD策略
        if strategy_config.get('use_kd', False):
            k_buy = strategy_config.get('kd_buy', 30)
            k_sell = strategy_config.get('kd_sell', 70)

            if row['K'] < k_buy and row['K'] > row['D']:
                buy_conditions.append(f'KD超賣({row["K"]:.1f})')
            if row['K'] > k_sell and row['K'] < row['D']:
                sell_conditions.append(f'KD超買({row["K"]:.1f})')

        # RSI策略
        if strategy_config.get('use_rsi', False):
            rsi_buy = strategy_config.get('rsi_buy', 30)
            rsi_sell = strategy_config.get('rsi_sell', 70)

            if row['RSI'] < rsi_buy:
                buy_conditions.append(f'RSI超賣({row["RSI"]:.1f})')
            if row['RSI'] > rsi_sell:
                sell_conditions.append(f'RSI超買({row["RSI"]:.1f})')

        # MACD策略
        if strategy_config.get('use_macd', False):
            macd_golden = row['MACD'] > row['MACD_Signal'] and prev['MACD'] <= prev['MACD_Signal']
            macd_death = row['MACD'] < row['MACD_Signal'] and prev['MACD'] >= prev['MACD_Signal']

            if macd_golden:
                buy_conditions.append('MACD金叉')
            if macd_death:
                sell_conditions.append('MACD死叉')

        # 布林通道策略
        if strategy_config.get('use_bb', False):
            if row['Close'] < row['BB_Lower']:
                buy_conditions.append('觸及下軌')
            if row['Close'] > row['BB_Upper']:
                sell_conditions.append('觸及上軌')

        # 綜合判斷
        min_conditions = strategy_config.get('min_conditions', 1)

        if len(buy_conditions) >= min_conditions:
            signal = 1
        elif len(sell_conditions) >= min_conditions:
            signal = -1

        return signal, buy_conditions + sell_conditions

# ============================================================
# 股神角色類別
# ============================================================
class StockGod:
    """股神角色 - 獨立的交易者"""

    def __init__(self, god_id, name, initial_capital=1000000):
        self.god_id = god_id
        self.name = name
        self.initial_capital = initial_capital
        self.reset()

    def reset(self):
        """重置角色狀態"""
        self.capital = self.initial_capital
        self.position = 0
        self.cost_basis = 0
        self.trades = []
        self.daily_values = []
        self.current_idx = 0
        self.active = True
        self.strategy_config = {}
        self.selected_stock = None
        self.stock_data = None
        self.last_update = None
        self.is_trading = False

    def set_strategy(self, stock_no, strategy_config, data_manager, use_csv=False):
        """設定交易策略"""
        self.selected_stock = stock_no
        self.strategy_config = strategy_config

        # 抓取資料（支援 CSV 模式）
        years = strategy_config.get('years', 3)
        df, last_update = data_manager.fetch_stock_data(stock_no, years=years, use_csv=use_csv)

        if df is not None and len(df) > 0:
            self.stock_data = StrategyEngine.calculate_indicators(df)
            self.last_update = last_update
            self.reset()
            return True, f"成功載入 {len(df)} 筆資料（更新於 {last_update}）"
        else:
            return False, "無法抓取資料，請檢查股票代碼或 CSV 格式"

    def trade_step(self, idx=None, animation_placeholder=None):
        """執行一步交易"""
        if not self.active or self.stock_data is None:
            return False

        if idx is None:
            idx = self.current_idx

        if idx >= len(self.stock_data):
            self.active = False
            return False

        row = self.stock_data.iloc[idx]
        price = row['Close']

        # 檢查破產
        if self.capital < price * 1000 and self.position == 0:
            self.active = False
            return False

        # 顯示交易動畫
        if animation_placeholder:
            self.is_trading = True
            animation_placeholder.markdown(f"""
            <div style="background: linear-gradient(90deg, #00c9ff 0%, #92fe9d 100%); 
                        height: 4px; border-radius: 2px; 
                        animation: trading-pulse 0.5s ease-in-out;">
            </div>
            <small>📊 {self.name} 分析中... Day {idx+1}/{len(self.stock_data)}</small>
            """, unsafe_allow_html=True)
            time.sleep(0.05)

        # 生成訊號
        result = StrategyEngine.generate_signal(self.stock_data, self.strategy_config, idx)
        signal = result[0] if isinstance(result, tuple) else result
        reasons = result[1] if isinstance(result, tuple) 
