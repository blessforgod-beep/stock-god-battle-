# 📈 股神帶你飛 - 三強對決 v3.2

一個支援多資料來源、多策略回測的台股交易模擬應用。

## 🚀 功能特色

- 📊 **多資料來源**: TWSE公開資料、CSV貼上、FinMind API
- 🎮 **三位股神對決**: 趨勢股神、震盪股神、綜合股神
- 📈 **多種技術指標**: MA均線、KD、RSI、MACD、布林通道
- 📉 **完整回測報告**: 資產曲線、交易明細、績效比較
- 📱 **手機友善**: 支援CSV貼上，方便手機使用

## 🛠️ 快速開始

### 本地運行

```bash
# 安裝依賴
pip install -r requirements.txt

# 運行應用
streamlit run app.py
```

### 線上部署

點擊下方按鈕一鍵部署到 Streamlit Cloud:

[![Deploy to Streamlit](https://img.shields.io/badge/Deploy-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit)](https://share.streamlit.io/deploy)

## 📋 使用說明

1. **選擇資料來源**: TWSE公開資料、貼上CSV、或FinMind API
2. **選擇股票**: 從下拉選單選擇或輸入股票代碼
3. **設定股神策略**: 調整每位股神的技術指標參數
4. **執行回測**: 點擊「開始回測對決」查看結果
5. **分析結果**: 比較三位股神的績效表現

## 📦 系統需求

- Python 3.8+
- Streamlit 1.28+
- Pandas, NumPy, Plotly

## ⚠️ 免責聲明

本應用僅供學習參考，不構成任何投資建議。投資有風險，決策需謹慎。

## 📝 版本紀錄

- v3.2: 新增CSV貼上支援、手機優化
- v3.1: 新增FinMind API支援
- v3.0: 三強對決模式
