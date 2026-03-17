# 🚀 部署指南

## 方法一：Streamlit Cloud (推薦，免費)

### 步驟 1: 準備檔案
- 下載 `stock-god-app.zip`
- 解壓縮得到 `app.py`, `requirements.txt`, `README.md`

### 步驟 2: 建立 GitHub 倉庫
1. 前往 [GitHub](https://github.com)
2. 建立新倉庫 (例如: `stock-god-app`)
3. 上傳三個檔案到倉庫

### 步驟 3: 部署到 Streamlit Cloud
1. 前往 [Streamlit Cloud](https://share.streamlit.io)
2. 使用 GitHub 帳號登入
3. 點擊 "New app"
4. 選擇你的倉庫
5. 主檔案路徑填寫: `app.py`
6. 點擊 "Deploy"

🎉 完成！應用將在幾分鐘內上線。

---

## 方法二：本地運行

### Windows
```bash
# 1. 安裝 Python 3.8+
# 2. 開啟命令提示字元，進入檔案所在目錄

pip install -r requirements.txt
streamlit run app.py
```

### Mac/Linux
```bash
# 1. 安裝 Python 3.8+
# 2. 開啟終端機，進入檔案所在目錄

pip3 install -r requirements.txt
streamlit run app.py
```

瀏覽器會自動開啟 `http://localhost:8501`

---

## 方法三：PythonAnywhere (免費)

1. 註冊 [PythonAnywhere](https://www.pythonanywhere.com)
2. 上傳檔案到 Files 區
3. 開啟 Bash console
4. 安裝依賴: `pip install --user streamlit pandas numpy plotly requests`
5. 創建 web app，選擇 "Streamlit" 框架
6. 設定 WSGI 檔案指向你的 app.py

---

## 方法四：Heroku

需要建立 `Procfile`:
```
web: streamlit run app.py --server.port $PORT
```

然後使用 Heroku CLI 部署:
```bash
heroku create your-app-name
git push heroku main
```

---

## 💡 推薦

- **快速體驗**: 使用方法二（本地運行）
- **長期使用**: 使用方法一（Streamlit Cloud，免費且穩定）
