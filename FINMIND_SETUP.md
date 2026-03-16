
# 🔑 FinMind API 設定教學

## 為什麼需要 FinMind API？

**TWSE 公開 API 的問題：**
- 在雲端環境常被阻擋或連線不穩
- 沒有認證機制，容易被限制
- 無法取得歷年資料，只能逐月抓取

**FinMind API 的優點：**
- ✅ 認證機制，連線穩定
- ✅ 可一次抓取多年歷史資料
- ✅ 資料格式標準化
- ✅ 免費額度：300次/小時（註冊後600次/小時）

---

## 📝 設定步驟（3分鐘完成）

### 步驟 1：註冊 FinMind 帳號
1. 前往 https://finmindtrade.com/
2. 點擊右上角「登入/註冊」
3. 使用 Email 或 Google 帳號註冊
4. **驗證信箱**（一定要驗證，才能獲得 600次/小時）

### 步驟 2：取得 API Token
1. 登入後，點擊右上角「帳號」
2. 在「API Token」欄位，點擊「複製」
3. 您的 Token 看起來像這樣：`eyJhbGciOiJIUzI1NiIs...`

### 步驟 3：在 Streamlit Cloud 設定 Secrets

**重要：不要將 Token 寫在程式碼裡！**

1. 前往 https://share.streamlit.io/
2. 找到您的 App，點擊「⋯」→「Settings」
3. 點擊左側「Secrets」
4. 輸入以下內容：

```toml
FINMIND_API_TOKEN = "您的實際Token貼在這裡"
```

5. 點擊「Save」

### 步驟 4：重新啟動 App
- 在 Settings 頁面點擊「Reboot」，或
- 推送一個小更新到 GitHub

---

## 🔍 驗證是否成功

重新開啟 App 後，側邊欄會顯示：

```
✅ 資料來源
FinMind API
更新頻率：每日
```

如果沒設定 Token，會顯示：

```
⚠️ 資料來源
TWSE 公開資料
```

---

## ⚠️ 免費額度說明

| 類型 | 請求限制 | 說明 |
|------|---------|------|
| 未驗證信箱 | 300次/小時 | 基本額度 |
| 已驗證信箱 | 600次/小時 | 建議驗證 |
| 每次下載 | 1次請求 | 3年資料只需1次請求 |

**計算範例：**
- 3位股神 × 3年資料 = 約 3-9 次請求（含快取更新）
- 遠低於 600次/小時限制，完全免費使用

---

## 💡 無法使用 FinMind 的備援方案

如果暫時不想設定 FinMind，程式會自動使用 **TWSE 公開資料**：
- 仍能運作，但連線較不穩定
- 選股時可能需要多試幾次
- 建議還是設定 FinMind 以獲得最佳體驗

---

## 📚 相關連結

- FinMind 官網：https://finmindtrade.com/
- FinMind 文件：https://finmind.github.io/
- GitHub：https://github.com/FinMind/FinMind

**有任何問題，歡迎在 GitHub Issues 或 FinMind Discord 社群詢問！**
