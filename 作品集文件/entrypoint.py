import streamlit as st

page_potvolt = st.Page("pot_voltage/index.py", url_path="pot_volt", title="槽电压", icon=":material/edit:")
page_potprocess = st.Page("pot_process/index.py", url_path="pot_process", title="工艺曲线", icon=":material/edit:")
page_potprocess_plotly = st.Page("pot_process_plotly/index.py", url_path="pot_process_plotly", title="工艺曲线_plotly（V2）", icon=":material/edit:")
page_mark_tool = st.Page("标签工具/page.py", url_path="mark_tool", title="标签工具", icon=":material/edit:")

pg = st.navigation([page_potvolt, page_potprocess, page_potprocess_plotly, page_mark_tool])
st.set_page_config(page_title="魏桥智铝-铝一 一分厂", page_icon=":material/home:", layout="wide")
pg.run()