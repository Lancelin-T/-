import os
import warnings
from datetime import datetime, time, timedelta

import streamlit as st
import numpy as np
import pandas as pd
from  loguru import logger
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# Global config
plt.rcParams['font.family'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False  # 避免字体警告

# 解决跨包引入的问题
import sys
from pathlib import Path
project_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_dir))

from common.process_plot import plot_gongyirpt_multi_subplots
from common.mysql_handler import get_gongyirpt_range_data

# 添加一些空行来增加按钮之间的间隔
st.markdown("")  # 添加一个空行
st.markdown("")  # 添加另一个空行
col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
# 工区列表
area_list = [''] + [f'{i}工区' for i in range(3, 4)]

with col1:
    selected_area = st.selectbox('请选择工区：', area_list, index=0, key='area_select')
    # 创建两个按钮在同一行
with col2:
    # if selected_area:
    # 根据工区选择槽号，假设每个工区槽号范围不同，这里举例
    pot_dict = {
        '3工区': [f'13{str(num).zfill(2)}' for num in range(1, 35)]
    }
    pot_list = [''] + pot_dict.get(selected_area, [])
    selected_pot = st.selectbox('请选择槽号：', pot_list, index=0, key='pot_select')
    # else:
    # selected_pot = ''

# 设置最晚日期和最早日期
earlist_date = datetime.strptime('2025-10-01 00:00:00', '%Y-%m-%d %H:%M:%S')
latest_date = datetime.strptime('2026-05-01 23:59:59', '%Y-%m-%d %H:%M:%S')
one_month_ago = latest_date - timedelta(days=30)

with col3:
    start_date = st.date_input("请选择开始日期", min_value=earlist_date, max_value=latest_date, value=one_month_ago)
with col4:
    end_date = st.date_input("请选择结束日期", min_value=earlist_date, max_value=latest_date, value=latest_date)

# 查询按钮
with col5:
    query_button = st.button("查询")

# # 只有点击查询按钮才进入下一步
if query_button or (selected_pot and start_date and end_date):

    start_date = pd.to_datetime(start_date).strftime("%Y-%m-%d")
    end_date = pd.to_datetime(end_date).strftime("%Y-%m-%d")
    logger.info(f'selected_pot:{selected_pot},start_date:{start_date},end_date:{end_date}')
    #     # 本地图片路径
    image_path = f'./fig/铝一1分厂/工艺曲线/默认图片.png'

    # 使用K2DataFrameDB获取数据（函数内部会获取 start_date-30天 到 end_date 的数据）
    data_gongyprt = get_gongyirpt_range_data(selected_pot, start_date, end_date)

    # 过滤数据：严格按照用户选择的时间范围（start_date 到 end_date）
    # 将 start_date 和 end_date 转换为 datetime 对象用于比较
    start_datetime = pd.to_datetime(start_date).date()
    end_datetime = pd.to_datetime(end_date).date()

    # 过滤 k_ts 字段在用户选择的时间范围内的数据
    data_gongyprt = data_gongyprt[
        (data_gongyprt['k_ts'] >= start_datetime) &
        (data_gongyprt['k_ts'] <= end_datetime)
        ].copy()

    logger.info(f"过滤后的数据行数：{len(data_gongyprt)}")
    # 定义字段分组：每组可以包含单个字段或多个字段（列表形式）
    # 多个字段的组会合并到一个子图中显示
    selected_fields = [
        ["set_voltage", "working_voltage"],  # 电压组：合并显示
        ["set_fluoride_weight", "fluoride_actual_weight"],  # 氟盐组：合并显示
        ["planned_aluminum_output", "aluminum_output_weight"],  # 出铝组：合并显示
        "temperature",
        "molecular_ratio",
        "feeding_weight",
        ["fluctuation", "waving"],  # 噪声组：合并显示
        "set_feeding_interval",
        "aluminum_level",
        "electrolyte_level",
        "fe_content",
        "si_content"
    ]
    # 字段名称映射（用于显示中文）
    field_name_map = {
        "set_voltage": "设定电压",
        "working_voltage": "工作电压",
        "set_fluoride_weight": "设定氟盐下料量",
        "fluoride_actual_weight": "实际氟盐下料量（取整）",
        "temperature": "槽温",
        "molecular_ratio": "分子比",
        "feeding_weight": "下料量",
        "fluctuation": "针振",
        "set_feeding_interval": "基准下料间隔",
        "planned_aluminum_output": "计划出铝量",
        "aluminum_output_weight": "实际出铝量",
        "aluminum_level": "铝水平",
        "electrolyte_level": "电解质水平",
        "fe_content": "Fe含量",
        "si_content": "Si含量",
        "waving": "摆动"
    }
    # 字段组名称映射（用于合并字段的子图标题）
    group_name_map = {
        ("set_voltage", "working_voltage"): "电压",
        ("set_fluoride_weight", "fluoride_actual_weight"): "氟盐",
        ("planned_aluminum_output", "aluminum_output_weight"): "出铝",
        ("fluctuation", "waving"): "噪声"
    }
    # 将所有涉及的字段的数据转为数值类型，无法转换的设为NaN
    # 先提取所有字段（包括分组中的字段）
    all_fields = []
    for field in selected_fields:
        if isinstance(field, list):
            all_fields.extend(field)
        else:
            all_fields.append(field)
    # 去重，保持顺序
    all_fields = list(dict.fromkeys(all_fields))
    # 逐个字段转换为数值类型
    for field in all_fields:
        data_gongyprt[field] = pd.to_numeric(data_gongyprt[field], errors='coerce')

    # 对fluoride_actual_weight字段的值取整
    data_gongyprt['fluoride_actual_weight'] = data_gongyprt['fluoride_actual_weight'].round(0)

    # 调用绘图函数
    plot_gongyirpt_multi_subplots(data_gongyprt, selected_fields, field_name_map, group_name_map)
    # 读取png图片，并展示在页面上
    fig = mpimg.imread(image_path)
    st.image(fig, width=1600)