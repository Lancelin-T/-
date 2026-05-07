import pandas as pd
import streamlit as st
from loguru import logger
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os

# 解决跨包引入的问题
import sys
from pathlib import Path
project_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_dir))

from common.mysql_handler import *
from curve_functions import (_add_field_comments, plotly_pot_voltage_curve,
                               plotly_gongyirpt_multi_subplots, plot_anode_current_and_pot_voltage)


def create_data_source_sidebar():
    """创建数据源选择侧边栏"""
    st.sidebar.header("📁 数据源选择")

    # 使用session state避免重复创建，但保持组件可见
    if 'data_source_value' not in st.session_state:
        st.session_state.data_source_value = "离线文件"

    data_source = st.sidebar.radio(
        "选择数据源:",
        ["离线文件", "实时数据"],
        help="选择数据来源方式",
        key="data_source_radio",
        index=['离线文件', '实时数据'].index(st.session_state.data_source_value)
    )

    # 更新session state中的值
    st.session_state.data_source_value = data_source
    return data_source


def load_offline_file():
    """加载离线文件"""
    uploaded_file = st.sidebar.file_uploader(
        "选择CSV文件",
        type=['csv'],
        help="请上传包含实时生产数据的CSV文件",
        key="csv_file_uploader"
    )
    if uploaded_file is not None:
        return uploaded_file
    return None


def reset_data():
    """重置数据状态"""
    if 'data_loaded' in st.session_state:
        del st.session_state.data_loaded
    if 'loaded_data' in st.session_state:
        del st.session_state.loaded_data


def load_data_for_analysis():
    """
    加载数据进行分析

    返回:
        data_source: 数据源类型（'离线文件' 或 '实时数据'）
    """
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    if 'loaded_data' not in st.session_state:
        st.session_state.loaded_data = None

    # 始终显示数据源选择组件
    data_source = create_data_source_sidebar()

    # 如果数据已经加载，显示状态信息并渲染交互界面
    if st.session_state.data_loaded and 'raw_data' in st.session_state:
        st.sidebar.success("✅ 数据已加载")
        if st.sidebar.button("🔄 重新加载数据", key="reload_data_button"):
            reset_data()
            st.rerun()
        # 每次都渲染交互界面
        render_interactive_table()
        return data_source

    # 根据数据源类型加载数据
    if data_source == "离线文件":
        uploaded_file = load_offline_file()
        if uploaded_file is not None:
            # 读取文件并存储原始数据
            csv_process(uploaded_file)
            st.session_state.data_loaded = True
            # 渲染交互界面
            render_interactive_table()
        return data_source
    else:
        st.sidebar.error("未实现实时数据读取功能")
        return data_source


# ========== 数据读取函数 ==========
def csv_process(uploaded_file):
    """
    读取用户上传的CSV文件，存储原始数据到 session_state

    参数:
        uploaded_file: Streamlit 的 UploadedFile 对象

    返回:
        无（数据存入 session_state.raw_data）
    """
    if uploaded_file is None:
        return

    try:
        # 读取整个CSV文件
        df_full = pd.read_csv(uploaded_file, header=0)

        # 检查至少有3列
        if df_full.shape[1] < 3:
            st.error("上传的文件列数不足3列，请检查格式。")
            return

        # 保留所有列数据
        df_raw = df_full.copy()

        # 重命名前三列为中文
        original_columns = list(df_raw.columns)
        if len(original_columns) >= 3:
            if original_columns[:3] == ['k_device', 'k_ts', 'k_model']:
                # 标准格式：重命名前三列，保留其他列名
                new_columns = ['槽号', '时间', '类型'] + original_columns[3:]
            else:
                # 非标准格式：强制重命名前三列
                new_columns = ['槽号', '时间', '类型'] + original_columns[3:]
            df_raw.columns = new_columns

    except ValueError as e:
        st.error(f"读取文件时出错: {e}")
        return

        # 初始化显示列
    df_raw['槽控曲线'] = '📊'

    # 存储原始数据到 session_state
    st.session_state.raw_data = df_raw

    # 保存完整的原始数据（用于导出）
    st.session_state.original_data = df_full

    # 初始化用户交互数据存储
    st.session_state.mark_values = {}
    st.session_state.feedback_values = {}

    # 重置checkbox状态（因为新数据可能有不同的额外列）
    st.session_state.selected_extra_cols = []

    # 保存当前数据的额外列名称列表（供 checkbox 使用）
    extra_cols = [col for col in df_raw.columns if col not in ['槽号', '时间', '类型', '槽控曲线']]
    st.session_state.available_extra_cols = extra_cols
    logger.info(f'检测到额外列: {extra_cols}')

    return df_full


# ========== 渲染交互界面函数 ==========
def render_interactive_table():
    """
    渲染交互表格界面
    - 从 session_state.raw_data 获取原·始数据
    - 每行显示：槽号、时间、类型、槽控曲线、阳极电流、工艺曲线、标记(下拉框)、反馈(文本框)
    """
    if 'raw_data' not in st.session_state:
        st.warning("请先上传数据文件")
        return

    df = st.session_state.raw_data

    # ========== 在顶部添加标题和checkbox区域 ==========
    checkbox_col = st.columns(1)

    with checkbox_col[0]:
        # 使用预存储的额外列列表（在 csv_process 中设置）
        extra_cols = st.session_state.get('available_extra_cols', [])

        if extra_cols:
            st.markdown("**显示额外列：**")
            # 初始化checkbox状态
            if 'selected_extra_cols' not in st.session_state:
                st.session_state.selected_extra_cols = []

            # 计算每行显示的checkbox数量（最多每行4个）
            max_per_row = 7
            cols_per_row = min(len(extra_cols), max_per_row)

            # 第一行checkbox
            row1_cols = st.columns(cols_per_row)
            for i, col in enumerate(extra_cols[:cols_per_row]):
                with row1_cols[i]:
                    checked = st.checkbox(col, value=(col in st.session_state.selected_extra_cols),
                                          key=f"check_{col}")
                    if checked and col not in st.session_state.selected_extra_cols:
                        st.session_state.selected_extra_cols.append(col)
                    elif not checked and col in st.session_state.selected_extra_cols:
                        st.session_state.selected_extra_cols.remove(col)

            # 第二行checkbox（如果有更多列）
            if len(extra_cols) > cols_per_row:
                remaining_cols = extra_cols[cols_per_row:cols_per_row * 2]
                row2_cols = st.columns(len(remaining_cols))
                for i, col in enumerate(remaining_cols):
                    with row2_cols[i]:
                        checked = st.checkbox(col, value=(col in st.session_state.selected_extra_cols),
                                              key=f"check_{col}")
                        if checked and col not in st.session_state.selected_extra_cols:
                            st.session_state.selected_extra_cols.append(col)
                        elif not checked and col in st.session_state.selected_extra_cols:
                            st.session_state.selected_extra_cols.remove(col)

            # 如果还有更多列，继续添加第三行
            if len(extra_cols) > cols_per_row * 2:
                remaining_cols = extra_cols[cols_per_row * 2:]
                row3_cols = st.columns(len(remaining_cols))
                for i, col in enumerate(remaining_cols):
                    with row3_cols[i]:
                        checked = st.checkbox(col, value=(col in st.session_state.selected_extra_cols),
                                              key=f"check_{col}")
                        if checked and col not in st.session_state.selected_extra_cols:
                            st.session_state.selected_extra_cols.append(col)
                        elif not checked and col in st.session_state.selected_extra_cols:
                            st.session_state.selected_extra_cols.remove(col)

    st.divider()

    # 分页设置
    page_size = 10
    total_pages = (len(df) + page_size - 1) // page_size

    # 获取当前页码
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 0

    # 计算当前页的数据范围
    start_idx = st.session_state.current_page * page_size
    end_idx = min(start_idx + page_size, len(df))
    current_page_data = df.iloc[start_idx:end_idx]

    # 下拉选项
    dropdown_options = [" ", "人工调整有误", "人工调整正确", "调整待研究", "已处理"]

    # 获取当前勾选的额外列
    selected_cols = st.session_state.get('selected_extra_cols', [])

    # ========== 动态计算列宽度 ==========
    # 基础列
    base_widths = [0.6, 0.6, 1, 0.6, 0.5, 0.5, 0.8]
    base_headers = ['槽号', '时间', '类型', '槽控曲线', '标记', '反馈', '提交']

    # 为勾选的额外列添加宽度和标题
    extra_widths = [1.2] * len(selected_cols)  # 每个额外列宽度为1.5

    # 合并列宽度和标题：槽号, 时间, 类型, [额外列...], 槽控曲线, 标记, 反馈, 提交
    col_widths = base_widths[:3] + extra_widths + base_widths[3:]
    headers = base_headers[:3] + selected_cols + base_headers[3:]

    # ========== 渲染表头 ==========
    header_cols = st.columns(col_widths)
    for i, header in enumerate(headers):
        header_cols[i].markdown(f"<div style='font-weight: bold; line-height: 0; margin: 2px 0;'>{header}</div>",
                                unsafe_allow_html=True)
    st.divider()

    # ========== 逐行渲染数据和交互组件 ==========
    for idx, row in current_page_data.iterrows():
        cols = st.columns(col_widths)
        col_idx = 0

        # 槽号、时间、类型
        cols[col_idx].write(row['槽号'])
        col_idx += 1
        cols[col_idx].write(row['时间'])
        col_idx += 1
        cols[col_idx].write(row['类型'])
        col_idx += 1

        # 显示勾选的额外列数据
        for extra_col in selected_cols:
            if extra_col in row.index:
                value = row[extra_col]
                # 处理空值和长数值
                if pd.isna(value):
                    display_val = "--"
                elif isinstance(value, float):
                    display_val = f"{value:.4f}" if abs(value) < 1 else f"{value:.2f}"
                else:
                    display_val = str(value)
                cols[col_idx].write(display_val)
            else:
                cols[col_idx].write("--")
            col_idx += 1

        # 槽控曲线按钮
        button_key = f'curve_button_{idx}'
        if cols[col_idx].button("📊", key=button_key):
            show_curve_dialog(idx)
        col_idx += 1

        # 标记 - 下拉选择框
        default_mark = st.session_state.mark_values.get(idx, "None")
        default_index = dropdown_options.index(default_mark) if default_mark in dropdown_options else 0
        mark_value = cols[col_idx].selectbox(
            label="标记",
            options=dropdown_options,
            index=default_index,
            key=f"mark_{idx}",
            label_visibility="collapsed"
        )
        st.session_state.mark_values[idx] = mark_value
        col_idx += 1

        # 反馈 - 文本输入框
        default_feedback = st.session_state.feedback_values.get(idx, "")
        feedback_value = cols[col_idx].text_input(
            label="反馈",
            value=default_feedback,
            key=f"feedback_{idx}",
            placeholder="输入反馈...",
            label_visibility="collapsed"
        )
        st.session_state.feedback_values[idx] = feedback_value
        col_idx += 1

        # 提交按钮
        submit_key = f'submit_button_{idx}'
        if cols[col_idx].button("提交", key=submit_key):
            current_mark = st.session_state.mark_values.get(idx, "None")
            current_feedback = st.session_state.feedback_values.get(idx, "")
            st.success(f"{row['槽号']}号槽已提交反馈：{current_feedback}")

    # 显示分页信息
    st.caption(f"第 {st.session_state.current_page + 1} 页，共 {total_pages} 页")

    # 页面导航
    col1, col2 = st.columns([0.1, 1])
    with col1:
        if st.button("⬅️ 上一页") and st.session_state.current_page > 0:
            st.session_state.current_page -= 1
            st.rerun()

    with col2:
        if st.button("下一页 ➡️") and st.session_state.current_page < total_pages - 1:
            st.session_state.current_page += 1
            st.rerun()


@st.dialog(title="槽控曲线详情", width="large")
def show_curve_dialog(row_idx):
    """
    在弹窗中显示选中行的槽控曲线
    """

    from pathlib import Path

    # 添加自定义CSS扩大弹窗宽度
    st.markdown("""
            <style>
            /* 覆盖所有可能的弹窗容器 */
            [data-testid="stDialog"] > div:first-child,
            [data-testid="stDialog"] > div:first-child > div,
            [data-testid="stDialog"] > div,
            div[role="dialog"],
            div[role="dialog"] > div {
                width: 95vw !important;
                max-width: 95vw !important;
                min-width: 95vw !important;
            }
            /* 弹窗内部内容 */
            [data-testid="stDialog"] [data-testid="stVerticalBlockBorderWrapper"],
            [data-testid="stDialog"] [data-testid="stVerticalBlock"] {
                width: 100% !important;
                max-width: 100% !important;
            }
            /* 图表容器 */
            [data-testid="stDialog"] .stPlotlyChart {
                width: 100% !important;
            }
            </style>
        """, unsafe_allow_html=True)

    if 'raw_data' not in st.session_state:
        st.error("没有可用数据")
        if st.button("关闭", key="close_dialog_error"):
            return
        return

    df = st.session_state.raw_data
    if row_idx >= len(df):
        st.error("无效的数据索引")
        if st.button("关闭", key="close_dialog_invalid"):
            return
        return

    row = df.iloc[row_idx]

    # 初始化当前页码
    if f'dialog_current_page_{row_idx}' not in st.session_state:
        st.session_state[f'dialog_current_page_{row_idx}'] = 0

    current_page = st.session_state[f'dialog_current_page_{row_idx}']

    st.subheader(f"📊 槽号 {row['槽号']} - 时间 {row['时间']} - 类型 {row['类型']}")

    # 显示勾选的额外列信息
    if 'selected_extra_cols' in st.session_state and st.session_state.selected_extra_cols:
        extra_info = []
        for col in st.session_state.selected_extra_cols:
            if col in row.index:
                value = row[col]
                # 处理空值
                if pd.isna(value):
                    value = "--"
                extra_info.append(f"**{col}:** {value}")

        if extra_info:
            st.info(" | ".join(extra_info))

    # 准备时间范围并生成图表
    try:
        k_ts = pd.to_datetime(row['时间'])
        k_device = row['槽号']
        k_model = row['类型']

        catch_id = f'{k_device}_{k_ts.strftime("%Y%m%d_%H%M%S")}'

        # 定义文件保存路径
        current_dir = Path(__file__).parent
        html_dir = current_dir / 'html_charts'
        html_dir.mkdir(exist_ok=True)

        voltage_html_path = html_dir / f'{catch_id}_槽电压.html'
        gongyirpt_html_path = html_dir / f'{catch_id}_工艺曲线.html'

        # 获取时间范围
        start_time_v = (k_ts - timedelta(hours=12)).strftime('%Y-%m-%d %H:%M:%S')
        end_time_v = (k_ts + timedelta(hours=12)).strftime('%Y-%m-%d %H:%M:%S')
        start_time_p = (k_ts - timedelta(days=30)).strftime('%Y-%m-%d')
        end_time_p = (k_ts + timedelta(days=6)).strftime('%Y-%m-%d')

        # 只标记当前选中的这条记录，不显示其他记录的标记
        # 使用当前行的时间和类型作为单个标记
        k_ts_mark_list = [k_ts]  # 只传递当前记录的时间
        k_model_list = [k_model]  # 只传递当前记录的类型

        logger.info(f'为槽号{k_device}的当前记录添加标记：时间={k_ts}, 类型={k_model}')

        # 使用 tabs 组件切换图表（不需要 rerun）
        tab1, tab2, tab3 = st.tabs(["📈 槽控曲线", "📊 工艺曲线", "⚡ 阳极电流"])

        with tab1:
            if voltage_html_path.exists():
                with open(voltage_html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                # 不设置宽度，让HTML自适应容器宽度
                st.components.v1.html(html_content, height=900, scrolling=True)
            else:
                data_tenrpt = get_tenrpt_data(k_device, start_time_v[:10], end_time_v[:10]).pipe(_add_field_comments)
                data_gongyirpt = get_gongyirpt_range_data(k_device, start_time_p, end_time_p)

                if data_tenrpt.empty:
                    st.warning(f"槽号 {k_device} 在所选时间范围内无十分钟报表数据，无法生成槽电压曲线图")
                else:
                    # 传入目标日期，确保标题时间与用户选择的日期一致
                    target_date = pd.to_datetime(row['时间']).strftime('%Y-%m-%d')
                    fig_voltage = plotly_pot_voltage_curve(data_tenrpt, data_gongyirpt, data_type='2m',
                                                           k_ts_mark=k_ts_mark_list,
                                                           k_model=k_model_list, target_date=target_date)

                    # 保存为HTML本地文件
                    fig_voltage.write_html(str(voltage_html_path), include_plotlyjs='cdn', config={'displayModeBar': True})

                    # use_container_width=True 让图表自适应容器宽度
                    st.plotly_chart(fig_voltage, use_container_width=True)

        with tab2:
            if gongyirpt_html_path.exists():
                with open(gongyirpt_html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                # 不设置宽度，让HTML自适应容器宽度
                st.components.v1.html(html_content, height=1580, scrolling=True)
            else:
                data_gongyirpt = get_gongyirpt_range_data(k_device, start_time_p, end_time_p)

                if data_gongyirpt.empty:
                    st.warning(f"槽号 {k_device} 在所选时间范围内无工艺报表数据，无法生成工艺曲线图")
                else:
                    fig_gongyirpt = plotly_gongyirpt_multi_subplots(data_gongyirpt)

                    fig_gongyirpt.write_html(str(gongyirpt_html_path), include_plotlyjs='cdn',
                                             config={'displayModeBar': True})

                    # use_container_width=True 让图表自适应容器宽度
                    st.plotly_chart(fig_gongyirpt, use_container_width=True)

        with tab3:
            date = pd.to_datetime(row['时间']).strftime('%Y-%m-%d')
            logger.info(f'槽号:{k_device}, 日期:{date}')

            # 本地图片路径
            image_path = Path(f'./images/阳极电流图/{k_device}/{k_device}_{date}_阳极电流.png')

            if os.path.exists(image_path):
                logger.info(f'从本地文件夹获取图片: {image_path}')
            else:
                logger.info(f'本地图片不存在，从数据库获取数据并绘制图片')
                data_tenrpt = get_tenrpt_data(k_device, start_time_p, end_time_p).pipe(_add_field_comments)
                # data_anode = get_anode_data(k_device, start_time_p, end_time_p)
                # if data_anode.empty or data_tenrpt.empty:
                #     st.warning(f"槽号 {k_device} 在所选时间范围内无阳极电流数据或槽控数据，无法生成阳极电流图")
                # else:
                #     plot_anode_current_and_pot_voltage(data_anode, data_tenrpt, target_date=date)

            # 显示标题
            st.subheader(f'槽号 {k_device} - {date} - 阳极电流图')

            # 使用容器包裹图片实现滚动
            with st.container(height=800):  # Streamlit 1.28+ 支持容器高度
                st.image(
                    str(image_path),
                    use_container_width=True
                )

        # 关闭按钮
        if st.button("关闭图表", key="dialog_close_button"):
            return

    except Exception as e:
        st.error(f"生成图表时出错: {e}")
        if st.button("关闭", key="close_dialog_error_chart"):
            return


# ========== 获取用户交互数据函数 ==========
def get_interaction_data():
    """
    获取包含用户交互结果的完整 DataFrame

    返回:
        pd.DataFrame: 包含原始数据 + 标记 + 反馈 的完整数据
        如果没有数据，返回 None
    """
    if 'raw_data' not in st.session_state:
        return None

    df = st.session_state.raw_data.copy()

    # 添加用户交互结果
    mark_values = st.session_state.get('mark_values', {})
    feedback_values = st.session_state.get('feedback_values', {})

    df['标记'] = [mark_values.get(i, "None") for i in range(len(df))]
    df['反馈'] = [feedback_values.get(i, "") for i in range(len(df))]

    return df