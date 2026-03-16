import streamlit as st
import pandas as pd
import io
import base64
from datetime import datetime

# ==================== 頁面設定 ====================
st.set_page_config(
    page_title="CSV分析工具 v3.2",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CSS 樣式 ====================
st.markdown("""
<style>
    .main { padding: 0rem 1rem; }
    .stTextArea textarea { font-family: monospace; font-size: 14px; }
    .success-box { padding: 1rem; border-radius: 0.5rem; background-color: #d4edda; border: 1px solid #c3e6cb; }
    .warning-box { padding: 1rem; border-radius: 0.5rem; background-color: #fff3cd; border: 1px solid #ffeaa7; }
</style>
""", unsafe_allow_html=True)

# ==================== 標題區 ====================
st.title("📊 CSV 資料分析工具")
st.markdown("### v3.2 緊急修正版 - 支援手機文字貼上")

st.markdown("---")

# ==================== 資料輸入區（核心修改處）====================
st.header("📥 資料輸入")

# 使用分頁提供兩種方式
tab1, tab2 = st.tabs(["📱 手機版：文字貼上（推薦）", "💻 電腦版：檔案上傳"])

df = None  # 初始化資料框

with tab1:
    st.info("**手機用戶請使用此方式**：複製 CSV 檔案內容 → 貼上下方文字框")
    
    csv_text = st.text_area(
        "在此貼上 CSV 內容：",
        height=250,
        placeholder="姓名,年齡,城市\n小明,25,台北\n小華,30,高雄\n...",
        help="請確保包含標題列，使用逗號分隔"
    )
    
    if csv_text and csv_text.strip():
        try:
            # 智能處理：自動檢測常見分隔符
            if csv_text.count('\t') > csv_text.count(','):
                df = pd.read_csv(io.StringIO(csv_text), sep='\t')
                st.success("✅ 成功解析（偵測到 Tab 分隔格式）")
            else:
                df = pd.read_csv(io.StringIO(csv_text))
                st.success("✅ 成功解析 CSV 格式")
        except Exception as e:
            st.error(f"❌ 解析失敗：{str(e)}")
            st.markdown("""
            **常見錯誤排除：**
            1. 檢查第一行是否為欄位名稱
            2. 確認使用英文逗號 `,` 分隔
            3. 文字內容含逗號時，請用引號包覆（如："台北,台灣"）
            """)

with tab2:
    st.info("**電腦用戶可使用傳統檔案上傳**")
    uploaded_file = st.file_uploader("選擇 CSV 檔案", type=['csv', 'txt'])
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.success("✅ 檔案上傳成功")
        except Exception as e:
            st.error(f"❌ 讀取失敗：{str(e)}")

# ==================== 資料分析區 ====================
if df is not None:
    st.markdown("---")
    st.header("🔍 資料預覽")
    
    # 基本資訊
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("總筆數", len(df))
    col2.metric("欄位數", len(df.columns))
    col3.metric("缺少值", df.isnull().sum().sum())
    col4.metric("欄位列", ", ".join(df.columns[:3]) + ("..." if len(df.columns) > 3 else ""))
    
    # 資料表格
    st.subheader("完整資料表")
    st.dataframe(df, use_container_width=True, height=400)
    
    # 欄位型態
    st.subheader("📋 欄位資訊")
    col_info = pd.DataFrame({
        '欄位名稱': df.columns,
        '資料型態': df.dtypes.values,
        '非空值數': df.count().values,
        '唯一值數': df.nunique().values
    })
    st.dataframe(col_info, use_container_width=True)
    
    # 統計摘要（僅針對數值欄位）
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    if numeric_cols:
        st.subheader("📈 數值統計")
        st.dataframe(df[numeric_cols].describe(), use_container_width=True)
        
        # 簡易圖表
        st.subheader("📊 快速圖表")
        chart_col = st.selectbox("選擇要繪製的欄位", numeric_cols)
        st.bar_chart(df[chart_col])
    
    # ==================== 匯出功能 ====================
    st.markdown("---")
    st.header("💾 資料匯出")
    
    col_dl1, col_dl2 = st.columns(2)
    
    with col_dl1:
        # CSV 下載
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_str = csv_buffer.getvalue()
        b64_csv = base64.b64encode(csv_str.encode()).decode()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"processed_data_{timestamp}.csv"
        
        href = f'<a href="data:file/csv;base64,{b64_csv}" download="{filename}" style="text-decoration:none;">' \
               f'<button style="padding:10px 20px; background-color:#4CAF50; color:white; border:none; border-radius:5px; cursor:pointer;">' \
               f'⬇️ 下載 CSV 檔案</button></a>'
        st.markdown(href, unsafe_allow_html=True)
    
    with col_dl2:
        # JSON 下載
        json_str = df.to_json(orient='records', force_ascii=False)
        b64_json = base64.b64encode(json_str.encode()).decode()
        href_json = f'<a href="data:application/json;base64,{b64_json}" download="data_{timestamp}.json" style="text-decoration:none;">' \
                    f'<button style="padding:10px 20px; background-color:#2196F3; color:white; border:none; border-radius:5px; cursor:pointer;">' \
                    f'⬇️ 下載 JSON 檔案</button></a>'
        st.markdown(href_json, unsafe_allow_html=True)

else:
    st.markdown("---")
    st.info("👆 請先在上方選擇輸入方式（貼上文字或上傳檔案）開始分析")

# ==================== 頁尾 ====================
st.markdown("---")
st.caption("📱 v3.2 更新：新增手機文字貼上功能，解決行動裝置檔案上傳相容性問題")
