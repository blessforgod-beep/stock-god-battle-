
import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 🚀 股神帶你飛 - 多角色量化對決平台 (Streamlit Cloud 優化版)
# 支援3位股神、自定義策略、持續模擬交易
# ============================================================

# 頁面設定
st.set_page_config(
    page_title="🚀 股神帶你飛 - 三強對決",
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
    }
    .god-title {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .metric-row {
        display: flex;
        justify-content: space-between;
        margin: 5px 0;
    }
    .profit-positive { color: #00ff88; font-weight: bold; }
    .profit-negative { color: #ff4757; font-weight: bold; }
    .strategy-box {
        background-color: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 15px;
        margin: 10px 0;
        border-radius: 5px;
    }
    .trade-log {
        max-height: 300px;
        overflow-y: auto;
        font-size: 0.85rem;
    }
    .winner-banner {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        font-size: 1.2rem;
        font-weight: bold;
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 數據抓取模組 (TWSE 台灣證交所免費 API)
# ============================================================
class TaiwanStockData:
    """台股數據抓取器"""

    @staticmethod
    @st.cache_data(ttl=3600)  # 快取1小時
    def fetch_stock_list():
        """抓取上市股票清單"""
        try:
            url = "https://www.twse.com.tw/exchangeReport/STOCK_ALL?response=json"
            response = requests.get(url, timeout=10)
            data = response.json()
            if data['stat'] == 'OK':
                stocks = {}
                for item in data['data']:
                    code = item[0].strip()
                    name = item[1].strip()
                    stocks[code] = name
                return stocks
        except:
            pass
        # 備援：熱門股票清單
        return {
            "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2382": "廣達",
            "2308": "台達電", "2881": "富邦金", "2891": "中信金", "2002": "中鋼",
            "1303": "南亞", "2412": "中華電", "2882": "國泰金", "3008": "大立光",
            "1216": "統一", "1301": "台塑", "2892": "第一金", "5880": "合庫金",
            "2884": "玉山金", "2885": "元大金", "2886": "兆豐金", "1101": "台泥"
        }

    @staticmethod
    @st.cache_data(ttl=1800)  # 快取30分鐘
    def fetch_ohlc(stock_no, months=3):
        """抓取K線數據"""
        all_data = []
        end_date = datetime.now()

        for i in range(months):
            query_date = end_date - timedelta(days=i*30)
            date_str = query_date.strftime('%Y%m01')
            url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={stock_no}"

            try:
                response = requests.get(url, timeout=10)
                data = response.json()
                if data['stat'] == 'OK' and 'data' in data:
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
# 策略引擎 (安全參數化策略，非代碼執行)
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

        # ATR (真實波幅)
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        df['ATR'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14).mean()

        return df

    @staticmethod
    def generate_signal(df, strategy_config, idx):
        """
        根據策略配置生成交易訊號
        strategy_config: 策略參數字典
        idx: 當前索引
        """
        if idx < 60:  # 確保有足夠數據
            return 0

        row = df.iloc[idx]
        prev = df.iloc[idx-1] if idx > 0 else row

        signal = 0
        buy_conditions = []
        sell_conditions = []

        # 1. MA策略
        if strategy_config.get('use_ma', False):
            ma_short = strategy_config.get('ma_short', 5)
            ma_long = strategy_config.get('ma_long', 20)

            golden_cross = row[f'MA{ma_short}'] > row[f'MA{ma_long}'] and prev[f'MA{ma_short}'] <= prev[f'MA{ma_long}']
            death_cross = row[f'MA{ma_short}'] < row[f'MA{ma_long}'] and prev[f'MA{ma_short}'] >= prev[f'MA{ma_long}']

            if golden_cross:
                buy_conditions.append('MA黃金交叉')
            if death_cross:
                sell_conditions.append('MA死亡交叉')

        # 2. KD策略
        if strategy_config.get('use_kd', False):
            k_buy = strategy_config.get('kd_buy', 30)
            k_sell = strategy_config.get('kd_sell', 70)

            if row['K'] < k_buy and row['K'] > row['D']:
                buy_conditions.append(f'KD超賣({row["K"]:.1f})')
            if row['K'] > k_sell and row['K'] < row['D']:
                sell_conditions.append(f'KD超買({row["K"]:.1f})')

        # 3. RSI策略
        if strategy_config.get('use_rsi', False):
            rsi_buy = strategy_config.get('rsi_buy', 30)
            rsi_sell = strategy_config.get('rsi_sell', 70)

            if row['RSI'] < rsi_buy:
                buy_conditions.append(f'RSI超賣({row["RSI"]:.1f})')
            if row['RSI'] > rsi_sell:
                sell_conditions.append(f'RSI超買({row["RSI"]:.1f})')

        # 4. MACD策略
        if strategy_config.get('use_macd', False):
            macd_golden = row['MACD'] > row['MACD_Signal'] and prev['MACD'] <= prev['MACD_Signal']
            macd_death = row['MACD'] < row['MACD_Signal'] and prev['MACD'] >= prev['MACD_Signal']

            if macd_golden:
                buy_conditions.append('MACD金叉')
            if macd_death:
                sell_conditions.append('MACD死叉')

        # 5. 布林通道策略
        if strategy_config.get('use_bb', False):
            if row['Close'] < row['BB_Lower']:
                buy_conditions.append('觸及下軌')
            if row['Close'] > row['BB_Upper']:
                sell_conditions.append('觸及上軌')

        # 綜合判斷 (需滿足至少2個條件才交易，避免雜訊)
        min_conditions = strategy_config.get('min_conditions', 1)

        if len(buy_conditions) >= min_conditions:
            signal = 1  # 買入
        elif len(sell_conditions) >= min_conditions:
            signal = -1  # 賣出

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
        self.position = 0  # 持股數
        self.cost_basis = 0  # 持倉成本
        self.trades = []  # 交易記錄
        self.daily_values = []  # 每日資產價值
        self.current_idx = 0  # 當前交易進度
        self.active = True  # 是否仍在交易
        self.strategy_config = {}  # 策略配置
        self.selected_stock = None  # 選中的股票
        self.stock_data = None  # 股票數據

    def set_strategy(self, stock_no, strategy_config):
        """設定交易策略"""
        self.selected_stock = stock_no
        self.strategy_config = strategy_config
        # 抓取數據
        self.stock_data = TaiwanStockData.fetch_ohlc(stock_no, months=strategy_config.get('months', 3))
        if self.stock_data is not None:
            self.stock_data = StrategyEngine.calculate_indicators(self.stock_data)
        self.reset()

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

        # 檢查是否破產（買不起1000股）
        if self.capital < price * 1000 and self.position == 0:
            self.active = False
            return False

        # 生成訊號
        result = StrategyEngine.generate_signal(self.stock_data, self.strategy_config, idx)
        signal = result[0] if isinstance(result, tuple) else result
        reasons = result[1] if isinstance(result, tuple) else []

        # 執行交易
        trade_type = None
        if signal == 1 and self.position == 0:  # 買入
            shares = 1000  # 台股最小單位
            cost = price * shares
            if self.capital >= cost:
                self.position = shares
                self.cost_basis = price
                self.capital -= cost
                trade_type = 'BUY'

        elif signal == -1 and self.position > 0:  # 賣出
            revenue = price * self.position
            profit = (price - self.cost_basis) * self.position
            self.capital += revenue
            trade_type = 'SELL'

            # 記錄交易
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

        # 計算勝率
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
            'total_days': len(self.stock_data) if self.stock_data is not None else 0
        }

# ============================================================
# 初始化 Session State
# ============================================================
def init_session():
    """初始化所有股神角色"""
    if 'gods' not in st.session_state:
        st.session_state.gods = {
            'god_a': StockGod('A', '🔥 短線快攻手', 1000000),
            'god_b': StockGod('B', '⚡ 技術分析大師', 1000000),
            'god_c': StockGod('C', '🧘 波段操作之神', 1000000)
        }
    if 'simulation_running' not in st.session_state:
        st.session_state.simulation_running = False
    if 'current_day' not in st.session_state:
        st.session_state.current_day = 0

# ============================================================
# 側邊欄 - 全局控制
# ============================================================
def sidebar_controls():
    st.sidebar.title("🎮 控制台")

    # 股票選擇
    stock_list = TaiwanStockData.fetch_stock_list()
    selected_stock = st.sidebar.selectbox(
        "選擇標的股票",
        options=list(stock_list.keys()),
        format_func=lambda x: f"{x} {stock_list.get(x, '')}",
        index=0 if "2330" in stock_list else 0
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
        st.session_state.current_day = 0
        st.rerun()

    return selected_stock

# ============================================================
# 策略配置頁面
# ============================================================
def strategy_config_page(god_id, god_name, selected_stock):
    """個別股神策略配置"""
    god = st.session_state.gods[god_id]

    st.subheader(f"{god_name} 策略設定")

    # 預設策略模板
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
        config['months'] = st.slider("回測月份", 1, 12, 3, key=f"months_{god_id}")
        config['initial_capital'] = st.number_input("初始資金", 100000, 10000000, 1000000, step=100000, key=f"capital_{god_id}")

    with col2:
        st.markdown("#### 啟用指標")
        config['use_ma'] = st.checkbox("MA移動平均", value=config.get('use_ma', False), key=f"use_ma_{god_id}")
        config['use_kd'] = st.checkbox("KD隨機指標", value=config.get('use_kd', False), key=f"use_kd_{god_id}")
        config['use_rsi'] = st.checkbox("RSI相對強弱", value=config.get('use_rsi', False), key=f"use_rsi_{god_id}")
        config['use_macd'] = st.checkbox("MACD異同平均", value=config.get('use_macd', False), key=f"use_macd_{god_id}")
        config['use_bb'] = st.checkbox("布林通道", value=config.get('use_bb', False), key=f"use_bb_{god_id}")

        config['min_conditions'] = st.slider("需滿足條件數", 1, 3, config.get('min_conditions', 1), key=f"min_con_{god_id}")

    # 詳細參數
    with st.expander("進階參數設定"):
        cols = st.columns(3)
        if config.get('use_ma'):
            with cols[0]:
                config['ma_short'] = st.number_input("短MA週期", 3, 20, 5, key=f"ma_s_{god_id}")
                config['ma_long'] = st.number_input("長MA週期", 10, 60, 20, key=f"ma_l_{god_id}")

        if config.get('use_kd'):
            with cols[1]:
                config['kd_buy'] = st.number_input("KD買入閾值", 10, 40, 30, key=f"kd_b_{god_id}")
                config['kd_sell'] = st.number_input("KD賣出閾值", 60, 90, 70, key=f"kd_s_{god_id}")

        if config.get('use_rsi'):
            with cols[2]:
                config['rsi_buy'] = st.number_input("RSI買入閾值", 10, 40, 30, key=f"rsi_b_{god_id}")
                config['rsi_sell'] = st.number_input("RSI賣出閾值", 60, 90, 70, key=f"rsi_s_{god_id}")

    # 套用設定
    if st.button("💾 套用策略", key=f"apply_{god_id}", use_container_width=True):
        god.initial_capital = config['initial_capital']
        god.set_strategy(selected_stock, config)
        st.success(f"✅ {god_name} 已設定策略並載入 {selected_stock} 數據！")
        st.rerun()

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
            <div class="god-title">{god_name}</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">{god.selected_stock if god.selected_stock else '未選股'}</div>
        </div>
        """, unsafe_allow_html=True)

        if perf:
            # 績效指標
            ret_color = "profit-positive" if perf['total_return'] >= 0 else "profit-negative"
            status = "🟢 交易中" if perf['active'] else "🔴 已結束"

            st.markdown(f"""
            <div class="metric-row">
                <span>狀態:</span> <strong>{status}</strong>
            </div>
            <div class="metric-row">
                <span>總資產:</span> <strong>${perf['final_value']:,.0f}</strong>
            </div>
            <div class="metric-row">
                <span>總報酬:</span> <span class="{ret_color}">{perf['total_return']:+.2f}%</span>
            </div>
            <div class="metric-row">
                <span>交易次數:</span> <strong>{perf['trades_count']}</strong>
            </div>
            <div class="metric-row">
                <span>勝率:</span> <strong>{perf['win_rate']:.1f}%</strong>
            </div>
            <div class="metric-row">
                <span>進度:</span> <strong>{perf['current_idx']}/{perf['total_days']} 天</strong>
            </div>
            """, unsafe_allow_html=True)

            # 交易記錄
            with st.expander("📋 交易記錄"):
                if god.trades:
                    trades_df = pd.DataFrame(god.trades)
                    trades_df['date'] = trades_df['date'].dt.strftime('%m/%d')
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

            # 資金曲線
            fig.add_trace(go.Scatter(
                x=df['date'], y=df['total_value'],
                mode='lines',
                name=names[god_id],
                line=dict(color=colors[god_id], width=2),
                hovertemplate='%{y:,.0f}<br>%{x}<extra></extra>'
            ), row=1, col=1)

            # 計算累積報酬率
            init_cap = god.initial_capital
            df['cum_return'] = (df['total_value'] - init_cap) / init_cap * 100

            fig.add_trace(go.Scatter(
                x=df['date'], y=df['cum_return'],
                mode='lines',
                name=names[god_id],
                line=dict(color=colors[god_id], width=2),
                showlegend=False,
                hovertemplate='%{y:.2f}%<br>%{x}<extra></extra>'
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

    # 標題
    st.markdown("<h1 style='text-align: center; color: #FF6B6B;'>🚀 股神帶你飛 - 三強對決</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>台股量化交易模擬平台 | 雲端部署版</p>", unsafe_allow_html=True)

    # 側邊欄
    selected_stock = sidebar_controls()

    # 主要內容分頁
    tabs = st.tabs(["🏆 對決戰場", "⚙️ 短線快攻手設定", "⚙️ 技術分析大師設定", "⚙️ 波段操作之神設定"])

    # Tab 0: 對決戰場
    with tabs[0]:
        st.markdown("### 實時對決狀態")

        # 自動模擬控制
        if st.session_state.simulation_running:
            # 執行一步模擬
            for god in st.session_state.gods.values():
                if god.active:
                    god.run_simulation(steps=1)

            # 檢查是否全部結束
            all_finished = all(not god.active for god in st.session_state.gods.values())
            if all_finished:
                st.session_state.simulation_running = False
                st.balloons()
                st.markdown("""
                <div class="winner-banner">
                    🎉 對決結束！請查看最終績效
                </div>
                """, unsafe_allow_html=True)
            else:
                # 自動重新執行（模擬連續交易）
                st.rerun()

        # 顯示三股神卡片
        cols = st.columns(3)
        display_god_card('god_a', '🔥 短線快攻手', cols[0])
        display_god_card('god_b', '⚡ 技術分析大師', cols[1])
        display_god_card('god_c', '🧘 波段操作之神', cols[2])

        # 圖表
        st.markdown("---")
        st.subheader("📊 對決走勢圖")

        # 檢查是否有數據可繪圖
        has_data = any(len(god.daily_values) > 0 for god in st.session_state.gods.values())

        if has_data:
            fig = plot_comparison()
            st.plotly_chart(fig, use_container_width=True, height=600)
        else:
            st.info("👆 請先在「設定」頁面為每位股神配置策略，然後點擊「開始對決」")

        # 最終排名
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

    # 頁尾資訊
    st.markdown("---")
    st.caption("📌 數據來源：台灣證交所 TWSE | 本程式僅供教學參考，不構成投資建議")

if __name__ == "__main__":
    main()
