from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
from loguru import logger
import matplotlib.pyplot as plt

# 解决跨包引入问题
import sys
from pathlib import Path
project_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_dir))

from common.pot_plot import plotly_pot_voltage_curve
from common.mysql_handler import *
from common.anodecurrent_plot import _add_field_comments

# 设置最晚日期和最早日期
earlist_date = datetime.strptime('2025-10-01 00:00:00', '%Y-%m-%d %H:%M:%S')
latest_date = datetime.strptime('2026-05-01 23:59:59', '%Y-%m-%d %H:%M:%S')

# 添加一些空行来增加按钮之间的间隔
col1, col2, col3, col4= st.columns([1, 1, 1, 1])
# 工区列表
area_list = [''] + [f'{i}工区' for i in range(3, 4)]

with col1:
    selected_area = st.selectbox('请选择工区：', area_list, index=0, key='area_select')
    # 创建两个按钮在同一行
with col2:
    if selected_area:
        # 根据工区选择槽号，假设每个工区槽号范围不同，这里举例
        pot_dict = {
            '3工区': [f'13{str(num).zfill(2)}' for num in range(1, 35)]
        }
        pot_list = [''] + pot_dict.get(selected_area, [])
        selected_pot = st.selectbox('请选择槽号：', pot_list, index=0, key='pot_select')
    else:
        selected_pot = ''

with col3:
    if selected_pot:
        # 日期选择，范围为近2年
        selected_date = st.date_input(
            '请选择日期：',
            value=latest_date,
            min_value=earlist_date,
            max_value=latest_date,
            key='date_select'
        )
    else:
        selected_date = None

with col4:
    # 查询按钮
    query_button = st.button('查询', type='primary', key='query_btn')

# 在页面现实plotly图
if query_button:
    # 标准化格式
    selected_date_dt = pd.to_datetime(selected_date).date()
    date = selected_date_dt.strftime("%Y-%m-%d")

    logger.info(f'selected_pot:{selected_pot},date:{date}')

    # 计算与今天的天数差
    days_diff = (latest_date.date() - selected_date_dt).days

    # 无论是否是最近三天，都从数据库获取数据
    logger.info(f'从数据库获取数据并绘制plotly图片')
    data_tenrpt = get_tenrpt_data(selected_pot, date, date).pipe(_add_field_comments)
    data_gongyprt = get_gongyirpt_range_data(selected_pot, date, date)
    fig = plotly_pot_voltage_curve(data_tenrpt, data_gongyprt, data_type='2m')

    st.plotly_chart(fig, use_container_width=True)