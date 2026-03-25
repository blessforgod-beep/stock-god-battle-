import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass
class Signal:
    date: str
    stock_id: str
    action: str  # 'BUY', 'SELL', 'HOLD'
    reason: str
    strength: int  # 1-5, 5最強
    price: float

class DayTradingRules:
    def __init__(self, df: pd.DataFrame):
        """
        df需包含: date, stock_id, open, high, low, close, volume, 
                  margin_balance, fini_hold_percent
        """
        self.df = df.sort_values(['stock_id', 'date'])
        self._precompute()
    
    def _precompute(self):
        """預計算所有日線指標"""
        g = self.df.groupby('stock_id')
        
        # 均線
        self.df['ma5'] = g['close'].transform(lambda x: x.rolling(5).mean())
        self.df['ma20'] = g['close'].transform(lambda x: x.rolling(20).mean())
        self.df['ma60'] = g['close'].transform(lambda x: x.rolling(60).mean())
        
        # 量能
        self.df['vol_ma5'] = g['volume'].transform(lambda x: x.rolling(5).mean())
        self.df['vol_ma20'] = g['volume'].transform(lambda x: x.rolling(20).mean())
        
        # VWAP（日線等效分時均價）
        self.df['vwap'] = (g['close'] * g['volume']).cumsum() / g['volume'].cumsum()
        
        # 技術指標
        self.df['rsi14'] = self._calculate_rsi(g['close'], 14)
        self.df['macd'], self.df['macd_signal'], self.df['macd_hist'] = self._calculate_macd(g['close'])
        
        # 漲跌停標記（台股10%）
        self.df['limit_up'] = self.df['close'] >= self.df['open'] * 1.095
        self.df['limit_down'] = self.df['close'] <= self.df['open'] * 0.905
        
        # 振幅
        self.df['amplitude'] = (self.df['high'] - self.df['low']) / self.df['low']
        
        # 籌碼變化率
        self.df['margin_change'] = g['margin_balance'].pct_change(3)  # 3日變化
        self.df['fini_change'] = g['fini_hold_percent'].pct_change(3)
    
    def generate_signals(self, stock_id: Optional[str] = None) -> List[Signal]:
        """生成所有交易訊號"""
        if stock_id:
            data = self.df[self.df['stock_id'] == stock_id].copy()
        else:
            data = self.df.copy()
        
        signals = []
        
        for idx, row in data.iterrows():
            signal = self._evaluate_day(row, data.loc[:idx].iloc[-20:])  # 傳過去20日上下文
            if signal:
                signals.append(signal)
        
        return signals
    
    def _evaluate_day(self, today: pd.Series, context: pd.DataFrame) -> Optional[Signal]:
        """評估單一交易日"""
        
        # === 優先檢查：高位離場訊號（最高優先級）===
        
        # 1. 雙頂+M頭
        if self._is_double_top(today, context):
            return Signal(
                date=today['date'],
                stock_id=today['stock_id'],
                action='SELL',
                reason='雙頂背離（M頭）',
                strength=5,
                price=today['close']
            )
        
        # 2. 高位放量滯漲（主力出貨）
        if self._is_distribution(today):
            return Signal(
                date=today['date'],
                stock_id=today['stock_id'],
                action='SELL',
                reason='高位天量滯漲',
                strength=5,
                price=today['close']
            )
        
        # 3. 量價背離
        if self._is_divergence(today, context):
            return Signal(
                date=today['date'],
                stock_id=today['stock_id'],
                action='SELL',
                reason='量價背離（價漲量縮）',
                strength=4,
                price=today['close']
            )
        
        # 4. 籌碼鬆動
        if today['margin_change'] < -0.05 or today['fini_change'] < -0.02:
            return Signal(
                date=today['date'],
                stock_id=today['stock_id'],
                action='SELL',
                reason='籌碼鬆動（融資/外資撤退）',
                strength=4,
                price=today['close']
            )
        
        # 5. 動能衰竭
        if self._is_exhaustion(today, context):
            return Signal(
                date=today['date'],
                stock_id=today['stock_id'],
                action='SELL',
                reason='動能衰竭（沖高回落）',
                strength=3,
                price=today['close']
            )
        
        # === 其次檢查：買入訊號 ===
        
        # 1. 強勢漲停板（蓄勢板/階梯板）
        if today['limit_up'] and self._is_healthy_limit_up(today):
            return Signal(
                date=today['date'],
                stock_id=today['stock_id'],
                action='BUY',
                reason='強勢漲停（蓄勢/階梯）',
                strength=5,
                price=today['close']
            )
        
        # 2. 換手板（分歧轉一致）
        if today['limit_up'] and today['amplitude'] > 0.10 and today['volume'] > today['vol_ma5'] * 2:
            return Signal(
                date=today['date'],
                stock_id=today['stock_id'],
                action='BUY',
                reason='換手板（分歧轉一致）',
                strength=4,
                price=today['close']
            )
        
        # 3. 均價突破（日線VWAP策略）
        if (today['close'] > today['vwap'] and 
            today['close'] > today['ma5'] and 
            today['low'] > today['ma5'] * 0.98 and
            today['volume'] > today['vol_ma5'] * 1.2):
            return Signal(
                date=today['date'],
                stock_id=today['stock_id'],
                action='BUY',
                reason='均價突破帶量',
                strength=4,
                price=today['close']
            )
        
        # 4. 超跌反彈（乖離率過大）
        if (today['close'] < today['ma20'] * 0.90 and 
            today['close'] > today['low'] * 1.02 and
            today['volume'] > today['vol_ma5'] * 1.5):
            return Signal(
                date=today['date'],
                stock_id=today['stock_id'],
                action='BUY',
                reason='超跌V型反彈（乖離過大）',
                strength=3,
                price=today['close']
            )
        
        # 5. 避雷：誘多陷阱（無量漲停）
        if today['limit_up'] and today['volume'] < today['vol_ma5'] * 0.5:
            return Signal(
                date=today['date'],
                stock_id=today['stock_id'],
                action='SELL',
                reason='誘多陷阱（無量漲停）',
                strength=5,
                price=today['close']
            )
        
        return None
    
    # === 輔助判斷函數 ===
    
    def _is_double_top(self, today, context):
        """偵測雙頂"""
        if len(context) < 20:
            return False
        
        recent_highs = context['high'].nlargest(2)
        if len(recent_highs) < 2:
            return False
        
        top1, top2 = recent_highs.iloc[0], recent_highs.iloc[1]
        price_similar = abs(top1 - top2) / top1 < 0.03  # 兩頂差距<3%
        
        # 第二頂量縮
        vol_shrink = today['volume'] < context['volume'].mean() * 0.8
        
        # MACD背離
        macd_div = today['macd'] < context['macd'].iloc[-5]
        
        return price_similar and vol_shrink and macd_div
    
    def _is_distribution(self, today):
        """高位放量滯漲"""
        at_high = today['close'] > today['ma60'] * 1.2  # 離60日線20%以上
        huge_vol = today['volume'] > today['vol_ma20'] * 4
        long_upper_shadow = (today['high'] - today['close']) > (today['close'] - today['open']) * 2
        
        return at_high and huge_vol and long_upper_shadow
    
    def _is_divergence(self, today, context):
        """量價背離"""
        price_new_high = today['close'] == context['close'].max()
        vol_shrink = today['volume'] < today['vol_ma5']
        return price_new_high and vol_shrink
    
    def _is_exhaustion(self, today, context):
        """動能衰竭"""
        if len(context) < 5:
            return False
        
        # 多次沖高回落
        rejections = sum((h > h.shift(1) * 1.01) & (c < h * 0.98) 
                        for h, c in zip(context['high'], context['close']))
        
        macd_fade = today['macd_hist'] < context['macd_hist'].iloc[-3]
        
        return rejections >= 2 or macd_fade
    
    def _is_healthy_limit_up(self, today):
        """健康的漲停（非誘多）"""
        not_trap = not (today['volume'] < today['vol_ma5'] * 0.5 and today['high'] != today['close'])
        strong_body = (today['close'] - today['open']) / (today['high'] - today['low'] + 0.001) > 0.5
        return not_trap and strong_body
    
    @staticmethod
    def _calculate_rsi(prices, window=14):
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def _calculate_macd(prices, fast=12, slow=26, signal=9):
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        macd_hist = macd - macd_signal
        return macd, macd_signal, macd_hist


# === 使用範例 ===
if __name__ == "__main__":
    # 模擬資料（實際使用時從你的 SQLite 讀取）
    data = {
        'date': pd.date_range('2026-01-01', periods=30, freq='D').astype(str),
        'stock_id': ['2330'] * 30,
        'open': np.random.normal(500, 10, 30),
        'high': np.random.normal(510, 10, 30),
        'low': np.random.normal(490, 10, 30),
        'close': np.random.normal(505, 10, 30),
        'volume': np.random.randint(1000, 5000, 30),
        'margin_balance': np.random.randint(10000, 20000, 30),
        'fini_hold_percent': np.random.uniform(20, 40, 30)
    }
    df = pd.DataFrame(data)
    
    # 確保high/low合理
    df['high'] = df[['open', 'close', 'high']].max(axis=1)
    df['low'] = df[['open', 'close', 'low']].min(axis=1)
    
    # 執行規則引擎
    engine = DayTradingRules(df)
    signals = engine.generate_signals('2330')
    
    for sig in signals:
        print(f"{sig.date}: {sig.action} [{sig.reason}] 強度{sig.strength} @ {sig.price:.2f}")
