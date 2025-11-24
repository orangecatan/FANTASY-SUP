import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from nba_api.stats.endpoints import scoreboardv2

# Page Config
st.set_page_config(page_title="Fantasy NBA Streaming Assistant", layout="wide")

st.title("🏀 Fantasy NBA Streaming Assistant")

# Sidebar - Inputs
st.sidebar.header("設定 (Settings)")
today = datetime.now().date()
# Default to this Sunday
days_until_sunday = (6 - today.weekday()) % 7
this_sunday = today + timedelta(days=days_until_sunday)

start_date = st.sidebar.date_input("開始日期 (Start Date)", today)
end_date = st.sidebar.date_input("結束日期 (End Date)", this_sunday)

if start_date > end_date:
    st.error("結束日期必須晚於開始日期！")

st.write(f"分析區間: {start_date} 至 {end_date}")

# Placeholder for data
st.info("正在開發中... 請稍候 (Under Construction)")
