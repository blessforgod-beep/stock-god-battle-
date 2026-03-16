
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
import base64
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 🚀 股神帶你飛 v3.1 - 支援手動上傳 CSV 資料
# ============================================================

st.set_page_config(
    page_title="🚀 股神帶你飛 - 三強對決 v3.1",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定義 CSS
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
    .upload-box {
        background-color: #e3f2fd;
        border: 2px dashed #2196f3;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        margin: 10px 0;
    }
    .data-source-badge {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
        margin: 5px 0;
    }
    .badge-finmind { background-color: #4caf50; color: white; }
    .badge-twse { background-color: #ff9800; color: white; }
    .badge-csv { background-color: #2196f3; color: white; }
    .badge-error { background-color: #f44336; color: white; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 資料管理器（支援 API + 手動上傳 CSV）
# ============================================================
class DataManager:
    """資料管理器 - 支援 API、快取、手動上傳 CSV"""

    def __init__(self, api_token=None):
        self.api_token = api_token
        self.cache_dir = Path(".cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.data_source = "FinMind" if api_token else "TWSE"
        self.manual_data = {}  # 儲存手動上傳的資料 {stock_no: df}

    def upload_csv_data(self, stock_no, uploaded_file):
        """
        處理手動上傳的 CSV 檔案
        支援格式：台股常用的日成交資訊 CSV
        """
        try:
            # 讀取 CSV
            df = pd.read_csv(uploaded_file)

            # 欄位名稱對照（支援常見的中文/英文名稱）
            column_mapping = {
                # 中文欄位名
                '日期': 'Date',
                '成交日期': 'Date',
                '開盤價': 'Open',
                '最高價': 'High',
                '最低價': 'Low',
                '收盤價': 'Close',
                '成交股數': 'Volume',
                '成交量': 'Volume',
                # 英文欄位名
                'date': 'Date',
                'Date': 'Date',
                'open': 'Open',
                'Open': 'Open',
                'high': 'High',
                'High': 'High',
                'low': 'Low',
                'Low': 'Low',
                'close': 'Close',
                'Close': 'Close',
                'volume': 'Volume',
                'Volume': 'Volume',
                'vol': 'Volume'
            }

            # 重新命名欄位
            df = df.rename(columns=column_mapping)

            # 檢查必要欄位
            required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            missing_cols = [col for col in required_cols if col not in df.columns]

            if missing_cols:
                return False, f"缺少必要欄位: {', '.join(missing_cols)}\n\n目前欄位: {list(df.columns)}"

            # 處理日期格式
            df['Date'] = pd.to_datetime(df['Date'])

            # 確保數值欄位為數字
            numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # 移除無效資料
            df = df.dropna()
            df = df.sort_values('Date').reset_index(drop=True)

            # 儲存到手動資料庫
            self.manual_data[stock_no] = df

            # 儲存快取
            cache_file = self.cache_dir / f"{stock_no}_manual.pkl"
            cache_data = {
                'df': df,
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'source': 'CSV_UPLOAD',
                'rows': len(df)
            }
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)

            return True, f"成功載入 {len(df)} 筆資料（來源：手動上傳 CSV）"

        except Exception as e:
            return False, f"CSV 處理錯誤: {str(e)}"

    def get_csv_template(self):
        """產生 CSV 範本供使用者下載"""
        template_data = {
            'Date': ['2024-01-02', '2024-01-03', '2024-01-04'],
            'Open': [550.0, 555.0, 558.0],
            'High': [555.0, 560.0, 562.0],
            'Low': [548.0, 553.0, 556.0],
            'Close': [553.0, 558.0, 560.0],
            'Volume': [15000000, 18000000, 16000000]
        }
        df_template = pd.DataFrame(template_data)
        return df_template

    def fetch_stock_data(self, stock_no, years=3, force_update=False, use_manual=False):
        """
        抓取股票資料（優先使用手動上傳，其次 API）
        """
        # 如果有手動上傳的資料，優先使用
        if use_manual and stock_no in self.manual_data:
            df = self.manual_data[stock_no]
            return df, datetime.now().strftime('%Y-%m-%d %H:%M'), 'CSV_UPLOAD'

        # 檢查快取
        cache_file = self.cache_dir / f"{stock_no}_manual.pkl"
        if cache_file.exists() and not force_update:
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
                if cache_data.get('source') == 'CSV_UPLOAD':
                    self.manual_data[stock_no] = cache_data['df']
                    return cache_data['df'], cache_data['last_update'], 'CSV_UPLOAD'

        # 使用 API 抓取
        # ... (原有 API 抓取邏輯)
        return None, None, 'ERROR'

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
        self.data_source = None

    def set_strategy(self, stock_no, strategy_config, data_manager, use_manual=False):
        """設定交易策略（支援手動上傳資料）"""
        self.selected_stock = stock_no
        self.strategy_config = strategy_config

        # 抓取資料（優先手動上傳）
        df, last_update, source = data_manager.fetch_stock_data(
            stock_no, 
            years=strategy_config.get('years', 3),
            use_manual=use_manual
        )

        if df is not None and len(df) > 0:
            self.stock_data = StrategyEngine.calculate_indicators(df)
            self.last_update = last_update
            self.data_source = source
            self.reset()
            return True, f"成功載入 {len(df)} 筆資料（來源：{source}，更新於 {last_update}）"
        else:
            return False, "無法載入資料，請檢查股票代碼或上傳 CSV"

    def trade_step(self, idx=None):
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

        # 生成訊號
        result = StrategyEngine.generate_signal(self.stock_data, self.strategy_config, idx)
        signal = result[0] if isinstance(result, tuple) else result
        reasons = result[1] if isinstance(result, tuple) else []

        # 執行交易
        trade_type = None
        if signal == 1 and self.position == 0:
            shares = 1000
            cost = price * shares
            if self.capital >= cost:
                self.position = shares
                self.cost_basis = price
                self.capital -= cost
                trade_type = 'BUY'

        elif signal == -1 and self.position > 0:
            revenue = price * self.position
            profit = (price - self.cost_basis) * self.position
            self.capital += revenue
            trade_type = 'SELL'

            self.trades.append({
                'date': row['Date'],
                'type': trade_type,
                'price': price,
                'shares': self.position,
                'profit': profit,
                'return_pct': (price - self.cost_basis) / self.cost_basis * 100,
                'reason': ', '.join(reasons),
                'capital': self.capital
            })
            self.position = 0
            self.cost_basis = 0

        # 計算總資產
        total_value = self.capital + (self.position * price if self.position > 0 else 0)
        self.daily_values.append({
            'date': row['Date'],
            'price': price,
            'capital': self.capital,
            'position': self.position,
            'total_value': total_value,
            'signal': signal,
            'trade_type': trade_type
        })

        self.current_idx = idx + 1
        return True

    def run_simulation(self, steps=1):
        """執行多步模擬"""
        for _ in range(steps):
            if not self.trade_step():
                break

    def get_performance(self):
        """取得績效報告"""
        if not self.daily_values:
            return None

        final_value = self.daily_values[-1]['total_value']
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100

        if self.trades:
            sell_trades = [t for t in self.trades if t['type'] == 'SELL']
            wins = len([t for t in sell_trades if t['profit'] > 0])
            win_rate = wins / len(sell_trades) * 100 if sell_trades else 0
        else:
            win_rate = 0

        return {
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'trades_count': len([t for t in self.trades if t['type'] == 'SELL']),
            'win_rate': win_rate,
            'active': self.active,
            'current_idx': self.current_idx,
            'total_days': len(self.stock_data) if self.stock_data is not None else 0,
            'last_update': self.last_update,
            'data_source': self.data_source
        }

# ============================================================
# 初始化
# ============================================================
def init_session():
    """初始化所有股神角色與資料管理器"""
    if 'data_manager' not in st.session_state:
        api_token = st.secrets.get("FINMIND_API_TOKEN", None) if "FINMIND_API_TOKEN" in st.secrets else None
        st.session_state.data_manager = DataManager(api_token=api_token)

    if 'gods' not in st.session_state:
        st.session_state.gods = {
            'god_a': StockGod('A', '🔥 短線快攻手', 1000000),
            'god_b': StockGod('B', '⚡ 技術分析大師', 1000000),
            'god_c': StockGod('C', '🧘 波段操作之神', 1000000)
        }
    if 'simulation_running' not in st.session_state:
        st.session_state.simulation_running = False

# ============================================================
# CSV 上傳區塊（側邊欄）
# ============================================================
def csv_upload_section():
    """CSV 手動上傳區塊"""
    st.sidebar.markdown("---")
    st.sidebar.subheader("📁 手動上傳資料")

    with st.sidebar.expander("上傳台股 CSV 資料", expanded=False):
        st.markdown("""
        **支援格式：**
        - 日期、開盤價、最高價、最低價、收盤價、成交量
        - 日期格式：YYYY-MM-DD 或 YYYY/MM/DD
        """)

        # 下載範本
        template_df = DataManager().get_csv_template()
        csv_template = template_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 下載 CSV 範本",
            data=csv_template,
            file_name='stock_template.csv',
            mime='text/csv',
            use_container_width=True
        )

        # 上傳檔案
        uploaded_file = st.file_uploader(
            "選擇 CSV 檔案",
            type=['csv'],
            help="上傳台股日成交資訊 CSV"
        )

        if uploaded_file is not None:
            stock_no = st.text_input(
                "股票代碼",
                value="2330",
                help="請輸入股票代碼（如：2330）"
            )

            if st.button("📤 上傳並解析資料", use_container_width=True):
                with st.spinner("處理中..."):
                    dm = st.session_state.data_manager
                    success, msg = dm.upload_csv_data(stock_no, uploaded_file)

                    if success:
                        st.success(msg)
                        st.info(f"已將 {stock_no} 資料存入系統，可在策略設定中選擇「使用手動上傳資料」")
                    else:
                        st.error(msg)
                        st.info("💡 提示：請確認 CSV 格式正確，或下載範本參考")

# ============================================================
# 側邊欄控制
# ============================================================
def sidebar_controls():
    st.sidebar.title("🎮 控制台")

    # CSV 上傳功能
    csv_upload_section()

    # 資料來源顯示
    dm = st.session_state.data_manager
    api_token = st.secrets.get("FINMIND_API_TOKEN", None) if "FINMIND_API_TOKEN" in st.secrets else None

    if api_token:
        source_badge = '<span class="data-source-badge badge-finmind">✅ FinMind API</span>'
    else:
        source_badge = '<span class="data-source-badge badge-twse">⚠️ TWSE 公開資料</span>'

    # 檢查是否有手動上傳資料
    manual_count = len(dm.manual_data)
    if manual_count > 0:
        source_badge += f'<br><span class="data-source-badge badge-csv">📁 手動上傳: {manual_count} 檔</span>'

    st.sidebar.markdown(f"""
    <div style="margin: 10px 0;">
        <strong>資料來源</strong><br>
        {source_badge}
    </div>
    """, unsafe_allow_html=True)

    # 股票選擇
    stock_options = ["2330", "2317", "2454", "2382", "2308"]  # 預設熱門股
    # 加入手動上傳的股票
    stock_options.extend(list(dm.manual_data.keys()))
    stock_options = list(dict.fromkeys(stock_options))  # 移除重複

    selected_stock = st.sidebar.selectbox(
        "選擇標的股票",
        options=stock_options,
        format_func=lambda x: f"{x} {dm.manual_data.get(x, {}).get('stock_name', '')}" if x in dm.manual_data else x,
        index=0
    )

    st.sidebar.markdown("---")

    # 全局操作
    col1, col2 = st.sidebar.columns(2)
    if col1.button("▶️ 開始對決", use_container_width=True):
        st.session_state.simulation_running = True
    if col2.button("⏸️ 暫停", use_container_width=True):
        st.session_state.simulation_running = False

    if st.sidebar.button("🔄 重置所有角色", use_container_width=True, type="secondary"):
        for god in st.session_state.gods.values():
            god.reset()
        st.session_state.simulation_running = False
        st.rerun()

    return selected_stock

# ============================================================
# 策略配置頁面（新增手動上傳選項）
# ============================================================
def strategy_config_page(god_id, god_name, selected_stock):
    """個別股神策略配置"""
    god = st.session_state.gods[god_id]
    dm = st.session_state.data_manager

    st.subheader(f"{god_name} 策略設定")

    # 顯示目前資料狀態
    if god.stock_data is not None:
        perf = god.get_performance()
        source_icon = "📁" if perf['data_source'] == 'CSV_UPLOAD' else "✅"
        st.markdown(f"""
        <div style="background-color: #e8f5e9; padding: 10px; border-radius: 5px; margin: 10px 0;">
            {source_icon} 已載入 {god.selected_stock} 資料<br>
            📅 更新時間：{perf['last_update']}<br>
            📊 資料筆數：{perf['total_days']} 天<br>
            🏷️ 來源：{perf['data_source']}
        </div>
        """, unsafe_allow_html=True)

    # 策略模板
    presets = {
        '短線MA交叉': {'use_ma': True, 'ma_short': 5, 'ma_long': 10, 'min_conditions': 1},
        'KD極值逆勢': {'use_kd': True, 'kd_buy': 20, 'kd_sell': 80, 'min_conditions': 1},
        'RSI超買超賣': {'use_rsi': True, 'rsi_buy': 30, 'rsi_sell': 70, 'min_conditions': 1},
        'MACD趨勢': {'use_macd': True, 'min_conditions': 1},
        '多指標綜合': {'use_ma': True, 'use_kd': True, 'use_rsi': True, 'min_conditions': 2}
    }

    col1, col2 = st.columns(2)

    with col1:
        preset = st.selectbox("快速選擇策略模板", list(presets.keys()), key=f"preset_{god_id}")

        config = presets[preset].copy()
        config['years'] = st.slider("歷史資料年數", 1, 5, 3, key=f"years_{god_id}")
        config['initial_capital'] = st.number_input("初始資金", 100000, 10000000, 1000000, step=100000, key=f"capital_{god_id}")

    with col2:
        st.markdown("#### 啟用指標")
        config['use_ma'] = st.checkbox("MA移動平均", value=config.get('use_ma', False), key=f"use_ma_{god_id}")
        config['use_kd'] = st.checkbox("KD隨機指標", value=config.get('use_kd', False), key=f"use_kd_{god_id}")
        config['use_rsi'] = st.checkbox("RSI相對強弱", value=config.get('use_rsi', False), key=f"use_rsi_{god_id}")
        config['use_macd'] = st.checkbox("MACD異同平均", value=config.get('use_macd', False), key=f"use_macd_{god_id}")
        config['use_bb'] = st.checkbox("布林通道", value=config.get('use_bb', False), key=f"use_bb_{god_id}")

        config['min_conditions'] = st.slider("需滿足條件數", 1, 3, config.get('min_conditions', 1), key=f"min_con_{god_id}")

    # 資料來源選擇（新增手動上傳選項）
    use_manual = False
    if selected_stock in dm.manual_data:
        use_manual = st.checkbox(
            f"📁 使用手動上傳的 {selected_stock} 資料", 
            value=True,
            key=f"use_manual_{god_id}",
            help="優先使用您上傳的 CSV 資料，而非 API 抓取"
        )

    # 套用設定
    if st.button("💾 套用策略並載入資料", key=f"apply_{god_id}", use_container_width=True):
        with st.spinner(f"正在載入 {selected_stock} 資料..."):
            god.initial_capital = config['initial_capital']
            success, msg = god.set_strategy(selected_stock, config, dm, use_manual=use_manual)

            if success:
                st.success(msg)
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(msg)
                if not use_manual and selected_stock not in dm.manual_data:
                    st.info("💡 提示：您可以在側邊欄「手動上傳資料」上傳 CSV 檔案")

    # 個別重置
    if st.button("🔄 重置此角色", key=f"reset_{god_id}", type="secondary"):
        god.reset()
        st.rerun()

    return config

# ============================================================
# 績效顯示元件
# ============================================================
def display_god_card(god_id, god_name, col):
    """顯示股神卡片"""
    god = st.session_state.gods[god_id]
    perf = god.get_performance()

    with col:
        st.markdown(f"""
        <div class="god-card">
            <div style="font-size: 1.5rem; font-weight: bold;">{god_name}</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">{god.selected_stock if god.selected_stock else '未選股'}</div>
        </div>
        """, unsafe_allow_html=True)

        if perf:
            ret_color = "#00ff88" if perf['total_return'] >= 0 else "#ff4757"
            status = "🟢 交易中" if perf['active'] else "🔴 已結束"

            # 資料來源標籤
            if perf['data_source'] == 'CSV_UPLOAD':
                source_tag = "📁 手動上傳"
            elif perf['data_source'] == 'FinMind':
                source_tag = "✅ FinMind"
            else:
                source_tag = "⚠️ 其他"

            st.markdown(f"""
            <div style="margin: 10px 0;">
                <div style="display: flex; justify-content: space-between; margin: 5px 0;">
                    <span>狀態:</span> <strong>{status}</strong>
                </div>
                <div style="display: flex; justify-content: space-between; margin: 5px 0;">
                    <span>總資產:</span> <strong>${perf['final_value']:,.0f}</strong>
                </div>
                <div style="display: flex; justify-content: space-between; margin: 5px 0;">
                    <span>總報酬:</span> <span style="color: {ret_color}; font-weight: bold;">{perf['total_return']:+.2f}%</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin: 5px 0;">
                    <span>交易次數:</span> <strong>{perf['trades_count']}</strong>
                </div>
                <div style="display: flex; justify-content: space-between; margin: 5px 0;">
                    <span>勝率:</span> <strong>{perf['win_rate']:.1f}%</strong>
                </div>
                <div style="display: flex; justify-content: space-between; margin: 5px 0; font-size: 0.8rem; color: #666;">
                    <span>資料來源:</span> <span>{source_tag}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin: 5px 0; font-size: 0.8rem; color: #666;">
                    <span>更新時間:</span> <span>{perf['last_update']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("📋 交易記錄"):
                if god.trades:
                    trades_df = pd.DataFrame(god.trades)
                    trades_df['date'] = pd.to_datetime(trades_df['date']).dt.strftime('%m/%d')
                    st.dataframe(trades_df[['date', 'type', 'price', 'profit', 'return_pct']].style.format({
                        'price': '{:.1f}',
                        'profit': '{:,.0f}',
                        'return_pct': '{:.2f}%'
                    }), use_container_width=True, height=200)
                else:
                    st.info("尚無交易記錄")

# ============================================================
# 主視覺化圖表
# ============================================================
def plot_comparison():
    """繪製三股神對比圖"""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=('資金曲線比較', '報酬率比較'),
        row_heights=[0.7, 0.3]
    )

    colors = {'god_a': '#FF6B6B', 'god_b': '#4ECDC4', 'god_c': '#45B7D1'}
    names = {'god_a': '短線快攻手', 'god_b': '技術分析大師', 'god_c': '波段操作之神'}

    for god_id, god in st.session_state.gods.items():
        if god.daily_values:
            df = pd.DataFrame(god.daily_values)

            fig.add_trace(go.Scatter(
                x=df['date'], y=df['total_value'],
                mode='lines',
                name=names[god_id],
                line=dict(color=colors[god_id], width=2),
            ), row=1, col=1)

            init_cap = god.initial_capital
            df['cum_return'] = (df['total_value'] - init_cap) / init_cap * 100

            fig.add_trace(go.Scatter(
                x=df['date'], y=df['cum_return'],
                mode='lines',
                name=names[god_id],
                line=dict(color=colors[god_id], width=2),
                showlegend=False,
            ), row=2, col=1)

    fig.update_layout(
        height=600,
        template='plotly_white',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    fig.update_yaxes(title_text="資產價值", row=1, col=1)
    fig.update_yaxes(title_text="報酬率 %", row=2, col=1)

    return fig

# ============================================================
# 主程式
# ============================================================
def main():
    init_session()

    st.markdown("<h1 style='text-align: center; color: #FF6B6B;'>🚀 股神帶你飛 - 三強對決 v3.1</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>支援手動上傳 CSV 資料版本</p>", unsafe_allow_html=True)

    # 說明資訊
    with st.expander("📖 使用說明（點擊展開）", expanded=False):
        st.markdown("""
        ### 🎯 三種資料來源方式

        1. **FinMind API**（推薦）：穩定、完整歷史資料
           - 在 Secrets 設定 `FINMIND_API_TOKEN`

        2. **TWSE 公開資料**（備援）：免設定，但較不穩定
           - 自動使用，無需設定

        3. **手動上傳 CSV**（新增）：使用自己的資料檔案
           - 在側邊欄「手動上傳資料」上傳
           - 支援格式：日期、開盤價、最高價、最低價、收盤價、成交量

        ### 📁 CSV 格式範例
        ```
        Date,Open,High,Low,Close,Volume
        2024-01-02,550.0,555.0,548.0,553.0,15000000
        2024-01-03,555.0,560.0,553.0,558.0,18000000
        ```
        """)

    selected_stock = sidebar_controls()

    tabs = st.tabs(["🏆 對決戰場", "⚙️ 短線快攻手設定", "⚙️ 技術分析大師設定", "⚙️ 波段操作之神設定"])

    # Tab 0: 對決戰場
    with tabs[0]:
        st.markdown("### 實時對決狀態")

        if st.session_state.simulation_running:
            progress_placeholder = st.empty()

            while st.session_state.simulation_running:
                all_finished = True
                status_text = []

                for god_id, god in st.session_state.gods.items():
                    if god.active:
                        all_finished = False
                        god.run_simulation(steps=5)
                        perf = god.get_performance()
                        if perf:
                            status_text.append(f"{god.name}: Day {perf['current_idx']}/{perf['total_days']}")

                progress_placeholder.text(" | ".join(status_text))

                if all_finished:
                    st.session_state.simulation_running = False
                    st.balloons()
                    st.success("🎉 對決結束！")
                    time.sleep(2)
                    st.rerun()
                else:
                    time.sleep(0.1)

        cols = st.columns(3)
        display_god_card('god_a', '🔥 短線快攻手', cols[0])
        display_god_card('god_b', '⚡ 技術分析大師', cols[1])
        display_god_card('god_c', '🧘 波段操作之神', cols[2])

        st.markdown("---")
        st.subheader("📊 對決走勢圖")

        has_data = any(len(god.daily_values) > 0 for god in st.session_state.gods.values())

        if has_data:
            fig = plot_comparison()
            st.plotly_chart(fig, use_container_width=True, height=600)
        else:
            st.info("👆 請先在「設定」頁面為每位股神配置策略，然後點擊「開始對決」")

        if not st.session_state.simulation_running:
            performances = []
            for god_id, god in st.session_state.gods.items():
                perf = god.get_performance()
                if perf:
                    performances.append((god_id, god.name, perf['total_return'], perf['final_value']))

            if performances:
                performances.sort(key=lambda x: x[2], reverse=True)
                st.markdown("### 🏅 最終排名")
                for i, (gid, name, ret, val) in enumerate(performances, 1):
                    medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
                    st.markdown(f"{medal} **{name}**: {ret:+.2f}% (總資產 ${val:,.0f})")

    # Tab 1-3: 策略設定
    god_configs = [
        ('god_a', '🔥 短線快攻手'),
        ('god_b', '⚡ 技術分析大師'),
        ('god_c', '🧘 波段操作之神')
    ]

    for i, (god_id, god_name) in enumerate(god_configs, 1):
        with tabs[i]:
            strategy_config_page(god_id, god_name, selected_stock)

    st.markdown("---")
    st.caption("📌 支援資料來源：FinMind API / TWSE / 手動上傳 CSV | 本程式僅供教學參考")

if __name__ == "__main__":
    main()
