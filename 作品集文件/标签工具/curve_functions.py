import pandas as pd
from loguru import logger
from datetime import timedelta
import os
import matplotlib.pyplot as plt

import sys
from pathlib import Path
project_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(project_dir))

# 设置中文字体，避免字体警告
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']  # 设置中文字体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 辅助函数：获取特殊状态事件的位置信息
def get_special_state_text_by_pot(data, event):
    df = data.copy()
    special_state = ['保留字段', '保留字段', '纯手动', '抬母线', '辅料', '换极', '出铝', '效应']
    feeding_state = ['保留字段', '保留字段', '自动AlF3下料(氟盐下料)', '手动AlF3下料(氟盐下料)',
                     '自动小下料', '手动小下料', '自动AEB(大下料)', '手动AEB(大下料)']
    logger.info(f'event:{event}')
    if event in special_state:
        contains = df['special_state_zh'].astype(str).str.contains(f'{event}', na=False)
        df['specialState_flag'] = contains & (~contains.shift(1).fillna(False))  # 定义specialState_flag事件开始标志
        mask = df['special_state_zh'].astype(str).str.contains(event, na=False) & (df['specialState_flag'] == True)
        x_index = df[mask].index.astype(str).values
        y_value = [3350 for i in range(len(x_index))]
        y_text = [f'{event}' for i in range(len(x_index))]
        logger.info(f'普通{event}事件标注成功，event:{event}, x_index:{x_index}, y_value:{y_value}, y_text={y_text}')
    for event_target in feeding_state:
        if event in event_target:
            # 修改这里，避免使用query方法直接操作object类型数据
            mask = df['feeding_state_zh'].astype(str).str.contains(f"{event}", na=False)
            x_index = df[mask].index.astype(str).values
            y_value = [3350 for i in range(len(x_index))]
            y_text = [f'{event_target}' for i in range(len(x_index))]

    logger.info(f'event:{event}, x_index:{x_index}, y_value:{y_value}, y_text={y_text}')
    return x_index, y_value, y_text


def get_gongyirpt_text(data):
    field_notnull_info = {}
    for col in data.columns:
        # 只处理数值型字段
        if data[col].notna().sum() > 0:
            notnull_idx = data[data[col].notna()]['k_ts'].tolist()[0].strftime('%Y-%m-%d')
            notnull_vals = data[data[col].notna()][col].values.tolist()[0]
            field_notnull_info.update({col: {"index": notnull_idx, "value": notnull_vals}})
        else:
            # 如果前推60天依旧无数据，用"--"填充该字段
            field_notnull_info.update({col: {"index": "--", "value": "--"}})

    # field_notnull_info 现在保存了每个字段不为空的索引和值，无数据时显示"--"
    # 辅助函数：安全获取字段值，字段不存在时返回默认值
    def get_field_value(field_name):
        if field_name in field_notnull_info:
            return field_notnull_info[field_name]['value'], field_notnull_info[field_name]['index']
        return "--", "--"

    gongyirpt_text = [
        f"[槽龄]:{get_field_value('age')[0]} ({get_field_value('age')[1]})",
        f"[设定电压]:{get_field_value('set_voltage')[0]} ({get_field_value('set_voltage')[1]}); [运行电压]:{get_field_value('working_voltage')[0]} ({get_field_value('working_voltage')[1]})",
        f"[槽温]:{get_field_value('temperature')[0]} ({get_field_value('temperature')[1]}); [分子比]:{get_field_value('molecular_ratio')[0]} ({get_field_value('molecular_ratio')[1]})",
        f"[铝水平]:{get_field_value('aluminum_level')[0]} ({get_field_value('aluminum_level')[1]}); [电解质水平]:{get_field_value('electrolyte_level')[0]} ({get_field_value('electrolyte_level')[1]})",
        f"[Fe含量]:{get_field_value('fe_content')[0]} ({get_field_value('fe_content')[1]}); [Si含量]:{get_field_value('si_content')[0]} ({get_field_value('si_content')[1]})",
        f"[出铝量]:{get_field_value('aluminum_output_weight')[0]} ({get_field_value('aluminum_output_weight')[1]}); [炉底压降]:{get_field_value('bottom_voltage')[0]} ({get_field_value('bottom_voltage')[1]})",
    ]
    return gongyirpt_text


def _parse_state(value, map_list):
    """历史曲线字段映射
    32位进制状态映射信息(目前都没有超过8位)
    """
    binary_str = bin(int(value))[2:].zfill(8)
    bin_list = [binary_str[i] for i in range(0, len(binary_str), 1)]
    feature = []
    for index, state in enumerate(bin_list):
        if int(state) != 0:
            feature.append(map_list[index])
    return '、'.join(feature)


def _add_field_comments(data):
    df = data.copy()
    special_state = ['保留字段', '保留字段', '纯手动', '抬母线', '辅料', '换极', '出铝', '效应']
    feeding_state = ['保留字段', '保留字段', '自动AlF3下料(氟盐下料)', '手动AlF3下料(氟盐下料)', '自动小下料',
                     '手动小下料', '自动AEB(大下料)', '手动AEB(大下料)']
    andoe_move_state = ['保留字段', '保留字段', '保留字段', '保留字段', '自动阳极降', '手动阳极降', '自动阳极升',
                        '手动阳极升']

    # 兼容两种数据来源：
    # 1）MySQL 历史库：specialState / feedingState / andoeMoveState 为数值编码
    # 2）K2 实时库：special_state_zh / feeding_state_zh / andoe_move_state_zh 已经是中文
    if 'specialState' in df.columns:
        df['specialState_zh'] = df['specialState'].map(lambda x: _parse_state(x, special_state))
    elif 'special_state_zh' in df.columns:
        df['specialState_zh'] = df['special_state_zh'].astype(str)

    if 'feedingState' in df.columns:
        df['feedingState_zh'] = df['feedingState'].map(lambda x: _parse_state(x, feeding_state))
    elif 'feeding_state_zh' in df.columns:
        df['feedingState_zh'] = df['feeding_state_zh'].astype(str)

    if 'andoeMoveState' in df.columns:
        df['andoeMoveState_zh'] = df['andoeMoveState'].map(lambda x: _parse_state(x, andoe_move_state))
    elif 'andoe_move_state_zh' in df.columns:
        df['andoeMoveState_zh'] = df['andoe_move_state_zh'].astype(str)

    return df


# 槽电压绘图函数
def plotly_pot_voltage_curve(data_tenrpt, data_gongyirpt, data_type='2m', k_ts_mark=None, k_model=None,
                             target_date=None):
    """
        使用 Plotly 绘制槽电压曲线图，支持多个Y轴和交互式操作

        参数:
            data_tenrpt: 十分钟报表数据
            data_gongyprt: 工艺报表数据
            target_date: 目标日期，用于文件命名，格式 'YYYY-MM-DD' 或 'YYYYMMDD'，如果为None则从数据中提取
        """
    if data_tenrpt.empty:
        raise ValueError("槽控数据为空，无法生成槽电压曲线图")

    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    anode_state_map = {
        '自动阳极升': {"symbol": "triangle-up", "color": "green", "name": "自动阳极升"},
        '自动阳极降': {"symbol": "triangle-down", "color": "green", "name": "自动阳极降"},
        '手动阳极升': {"symbol": "triangle-up", "color": "red", "name": "手动阳极升"},
        '手动阳极降': {"symbol": "triangle-down", "color": "red", "name": "手动阳极降"},
    }

    # 数据准备
    df = data_tenrpt.copy().sort_values('k_ts').set_index('k_ts')

    # 创建带有多个Y轴的图表
    fig = make_subplots(specs=[[{'secondary_y': False}]])

    # Y1： 电压曲线（左侧）
    fig.add_trace(
        go.Scatter(x=df.index, y=df['pot_voltage'],
                   mode='lines', name='槽电压',
                   line=dict(color='blue', width=2),
                   yaxis='y1', showlegend=False,
                   hovertemplate='槽电压: %{y:.0f} mV<extra></extra>'
                   )
    )

    fig.add_trace(
        go.Scatter(x=df.index, y=df['set_voltage'],
                   mode='lines', name='设定电压',
                   line=dict(color='red', width=2, dash='dash'),
                   yaxis='y1', showlegend=False)
    )

    fig.add_trace(
        go.Scatter(x=df.index, y=df['voltage_upper_limit'],
                   mode='lines', name='设定电压上限',
                   line=dict(color='grey', width=2, dash='dash'),
                   yaxis='y1', showlegend=False)
    )

    fig.add_trace(
        go.Scatter(x=df.index, y=df['voltage_lower_limit'],
                   mode='lines', name='设定电压下限',
                   line=dict(color='grey', width=2, dash='dash'),
                   yaxis='y1', showlegend=False)
    )

    # 添加阳极升降散点
    for ano_state in ["自动阳极降", "自动阳极升", "手动阳极降", "手动阳极升"]:
        mask = df['andoe_move_state_zh'].astype(str).str.contains(ano_state, na=False)
        if mask.any():
            _df = df[mask]
            fig.add_trace(
                go.Scatter(x=_df.index, y=_df['pot_voltage'],
                           mode='markers', name=anode_state_map[ano_state]['name'],
                           marker=dict(symbol=anode_state_map[ano_state]['symbol'],
                                       color=anode_state_map[ano_state]['color'],
                                       size=10, line=dict(width=1, color='white')),
                           yaxis='y1', showlegend=False,
                           # hovertemplate=f'{ano_state}<br>时间: %{{x}}<br>电压: %{{y:.0f}} mV<extra></extra>'
                           ),
            )

    # Y2: 下料间隔 (不显示坐标轴，但数据映射到相应范围)
    # 将下料间隔映射到电压范围进行显示
    fig.add_trace(
        go.Scatter(x=df.index, y=df['set_feeding_interval'] / 10 * 3 + 3200,
                   mode='lines', name='基准下料间隔',
                   line=dict(color='darkred', width=1.5, dash='dash'),
                   yaxis='y1', showlegend=False,
                   hovertemplate='基准下料间隔: %{customdata:.0f} s<extra></extra>',
                   customdata=df['set_feeding_interval'] / 10)
    )

    fig.add_trace(
        go.Scatter(x=df.index, y=df['actual_feeding_interval'] / 10 * 3 + 3200,
                   mode='lines', name='实际下料间隔',
                   line=dict(color='orange', width=2, shape='hv'),
                   yaxis='y1', showlegend=False,
                   hovertemplate='实际下料间隔: %{customdata:.0f} s<extra></extra>',
                   customdata=df['actual_feeding_interval'] / 10
                   )
    )

    # 氟盐下料标注
    _x, _y, _text = get_special_state_text_by_pot(df, '氟盐下料')
    if len(_x) > 0:
        for i in range(len(_x)):
            fig.add_annotation(
                x=_x[i], y=_y[i],
                text='F', showarrow=False,
                font=dict(size=14, color='red', family='Arial Black'),
                xanchor='center', yanchor='bottom'
            )

    # 针振和摆动（映射显示）
    if 'fluctuation' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['fluctuation'] * 10 + 3200,
                       mode='lines', name='针振',
                       line=dict(color='green', width=1.5),
                       yaxis='y1', showlegend=False,
                       hovertemplate='针振: %{customdata:.0f} mV<extra></extra>',
                       customdata=df['fluctuation']
                       )
        )

    if 'waving' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['waving'] * 10 + 3200,
                       mode='lines', name='摆动',
                       line=dict(color='yellowgreen', width=1.5),
                       yaxis='y1', showlegend=False,
                       hovertemplate='摆动: %{customdata:.0f} mV<extra></extra>',
                       customdata=df['waving']
                       )
        )

    for event in ['换极', '出铝', '抬母线', '纯手动', '效应']:
        _x, _y, _text = get_special_state_text_by_pot(df, event)
        if len(_x) > 0:
            for i in range(len(_x)):
                fig.add_annotation(
                    x=_x[i], y=_y[i],
                    text=_text[i], showarrow=False,
                    arrowhead=2, arrowsize=1, arrowcolor='red',
                    font=dict(size=12, color='red', family='SimHei'),
                    bgcolor='rgba(255, 255, 255, 0.8)',
                    bordercolor='red', borderwidth=1,
                    xanchor='center', yanchor='bottom'
                )

    # Y4：电流（右侧Y轴）
    fig.add_trace(
        go.Scatter(x=df.index, y=df['series_current'] / 10,
                   mode='lines', name='系列电流',
                   line=dict(color='crimson', width=2),
                   yaxis='y2', showlegend=False)
    )

    # Y5:斜率和累斜
    fig.add_trace(
        go.Scatter(x=df.index, y=df['slope'] / 2 - 700,
                   mode='lines', name='斜率',
                   line=dict(color='#7d5886', width=2),
                   hovertemplate='斜率: %{customdata:.0f} <extra></extra>',
                   yaxis='y2', showlegend=False,
                   customdata=df['slope'] - 2000,
                   )
    )

    fig.add_trace(
        go.Scatter(x=df.index, y=df['cumulative_voltage_slope'] / 2 - 700,
                   mode='lines', name='累斜',
                   line=dict(color='#f58220', width=2),
                   hovertemplate='累斜: %{customdata:.0f} <extra></extra>',
                   yaxis='y2', showlegend=False,
                   customdata=df['cumulative_voltage_slope'] - 2000,
                   )
    )

    fig.add_trace(
        go.Scatter(x=df.index, y=[2000 / 2 - 700] * len(df.index),
                   mode='lines', name='定斜',
                   line=dict(color='#d71345', width=1, dash='dash'),
                   hoverinfo='skip',
                   yaxis='y2', showlegend=False,
                   customdata=[0] * len(df.index),
                   )
    )

    # 获取工艺参数文字信息
    gongyirpt_text = get_gongyirpt_text(data_gongyirpt)
    annotation_text = '<br>'.join(gongyirpt_text)

    # 添加工艺参数文本框
    fig.add_annotation(
        xref='paper', yref='paper',
        x=0.005, y=0.99,
        text=annotation_text,
        showarrow=False,
        font=dict(size=12, color='green', family='SimHei'),
        align='left',
        xanchor='left', yanchor='top',
        # bgcolor='rgba(255, 255, 255, 0.8)',
        # bordercolor='green', borderwidth=1, borderpad=5
    )

    # 设置图表标题
    k_device = data_tenrpt['k_device'].values[0]
    # 优先使用传入的目标日期，确保标题时间与用户选择的日期一致
    if target_date is not None:
        # 统一转换为 YYYYMMDD 格式
        k_ts = pd.to_datetime(target_date).strftime('%Y%m%d')
    else:
        k_ts = pd.to_datetime(data_tenrpt['k_ts'].values[0]).strftime('%Y%m%d')
    title_text = f'{k_device}_{k_ts}_槽电压曲线'

    # 获取时间范围
    x_min = df.index.min()
    x_max = df.index.max()

    # 更新布局
    fig.update_layout(
        title=dict(text=title_text,
                   font=dict(size=15, family='SimHei'), x=0.5, xanchor='center',
                   pad=dict(t=10, b=0)),
        xaxis=dict(
            title='时间',
            title_font=dict(size=14, family='SimHei'),
            tickformat='%m-%d %H:%M',
            showgrid=True,
            gridcolor='lightgrey',
            range=[x_min, x_max],  # 明确设置初始范围
        ),
        yaxis=dict(
            title='电压 (mV)',
            title_font=dict(size=14, color='blue', family='SimHei'),
            tickfont=dict(color='blue'),
            range=[3200, 4300],
            showgrid=True,
            gridcolor='lightgrey',
        ),
        yaxis2=dict(
            title='电流 (kA)',
            title_font=dict(size=14, color='crimson', family='SimHei'),
            tickfont=dict(color='crimson'),
            range=[360, 650],
            overlaying='y',
            side='right',
        ),

        hovermode='x unified',
        # hovermode=False,
        hoverlabel=dict(
            bgcolor='rgba(255,255,255,0.01)',
            bordercolor='rgba(255,255,255,0.01)',
            font=dict(color='grey')),
        dragmode='zoom',
        width=1400,
        height=900,
        plot_bgcolor='rgba(240, 240, 240, 0.5)',
        paper_bgcolor='white',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            xanchor='center',
            x=0.5,
            y=-0.15,
            font=dict(size=11, family='SimHei'),
            bgcolor='rgba(255, 255, 255, 0.8)'
        ),
        margin=dict(l=80, r=80, t=50, b=100),
    )

    # ====================新增：设置半透明标记区域====================
    # 根据 k_ts 前后10分钟添加标记区域
    def add_time_mark_area(fig_mark, data_tenrpt, k_ts_mark=None, k_model=None):
        """
        添加时间标记区域，支持单个或多个标记
        :param fig_mark: plotly图表对象
        :param data_tenrpt: 数据
        :param k_ts_mark: 标记中心时间（字符串、datetime对象或列表）
        :param k_model: 标记类型（字符串或列表，与k_ts_mark一一对应）
        :return: 修改后的图表对象
        """

        try:
            # 获取设备号
            k_device = data_tenrpt['k_device'].values[0] if len(data_tenrpt) > 0 else '未知设备'

            # 将单个值转换为列表，统一处理
            if not isinstance(k_ts_mark, list):
                k_ts_mark_list = [k_ts_mark]
            else:
                k_ts_mark_list = k_ts_mark

            if not isinstance(k_model, list):
                k_model_list = [k_model] * len(k_ts_mark_list)
            else:
                k_model_list = k_model

            # 确保k_ts_mark和k_model长度一致
            if len(k_model_list) != len(k_ts_mark_list):
                logger.warning(f'k_ts_mark和k_model长度不一致，进行补齐处理')
                # 如果k_model较短，用最后一个值补齐
                while len(k_model_list) < len(k_ts_mark_list):
                    k_model_list.append(k_model_list[-1] if k_model_list else '未知类型')

            # 为每个标记点添加区域
            for mark_time, model_type in zip(k_ts_mark_list, k_model_list):
                # 将传入的 k_ts_mark 转换为 datetime 对象
                mark_center = pd.to_datetime(mark_time)

                # 计算标记区域的开始和结束时间（保持 datetime 格式，与 x 轴兼容）
                mark_start = mark_center - timedelta(minutes=10)
                mark_end = mark_center + timedelta(minutes=10)

                # 标记类型文本
                annotation_label = str(model_type) if model_type else '标记'

                logger.info(f'设备{k_device}：添加标记区域 {mark_start} ~ {mark_end}, 类型: {annotation_label}')

                # 添加半透明标记区域
                fig_mark.add_vrect(
                    x0=mark_start,
                    x1=mark_end,
                    fillcolor='rgba(255, 0, 0, 0.2)',  # 红色半透明
                    opacity=0.5,
                    line_width=1,
                    line_color='red',
                    layer='below',
                    annotation_text=annotation_label,
                    annotation_position='top left',
                    annotation=dict(
                        font=dict(size=12, color='red', family='SimHei'),
                        bgcolor='rgba(255, 255, 255, 0.8)'
                    )
                )

            return fig_mark

        except Exception as e:
            logger.error(f'添加标记区域失败: {e}')
            return fig_mark

    # ====================标记结束====================

    # 如果传入了标记时间，则添加标记区域
    if k_ts_mark is not None:
        fig = add_time_mark_area(fig, data_tenrpt, k_ts_mark, k_model)

    # 更新布局
    fig.update_layout(
        title=dict(text=title_text,
                   font=dict(size=15, family='SimHei'), x=0.5, xanchor='center',
                   pad=dict(t=10, b=0)),
        xaxis=dict(
            title='时间',
            title_font=dict(size=14, family='SimHei'),
            tickformat='%m-%d %H:%M',
            showgrid=True,
            gridcolor='lightgrey',
            range=[x_min, x_max],  # 明确设置初始范围
        ),
        yaxis=dict(
            title='电压 (mV)',
            title_font=dict(size=14, color='blue', family='SimHei'),
            tickfont=dict(color='blue'),
            range=[3200, 4500],
            showgrid=True,
            gridcolor='lightgrey',
        ),
        yaxis2=dict(
            title='电流 (kA)',
            title_font=dict(size=14, color='crimson', family='SimHei'),
            tickfont=dict(color='crimson'),
            range=[0, 650],
            overlaying='y',
            side='right',
        ),

        hovermode='x unified',
        # hovermode=False,
        hoverlabel=dict(
            bgcolor='rgba(255,255,255,0.01)',
            bordercolor='rgba(255,255,255,0.01)',
            font=dict(color='grey')),
        dragmode='zoom',
        # width不设置，让图表自适应容器宽度
        height=900,
        plot_bgcolor='rgba(240, 240, 240, 0.5)',
        paper_bgcolor='white',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            xanchor='center',
            x=0.5,
            y=-0.15,
            font=dict(size=11, family='SimHei'),
            bgcolor='rgba(255, 255, 255, 0.8)'
        ),
        margin=dict(l=80, r=80, t=50, b=100),
    )

    return fig
    # plt.show()


# 工艺曲线绘图函数
def plotly_gongyirpt_multi_subplots(data_tenrpt):
    """
    利用plotly库绘制可交互的工艺曲线页面。
    根据工艺报表中的字段，绘制多个子图（单列排列）。
    每个子图的Y轴标签为字段名，X轴为k_ts（时间）。
    每个子图为散点+折线图，所有点均显示。
    子图顺序严格按照fields列表。

    参数:
        df: DataFrame, 包含数据的数据框
        fields: list, 字段列表，可以是字符串（单个字段）或列表（多个字段合并）
        field_name_map: dict, 字段名到中文名称的映射
        group_name_map: dict, 字段组（元组形式）到中文名称的映射
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import datetime

    from loguru import logger
    logger.info("开始绘图")

    # 确保k_ts是索引（时间戳格式）
    df = data_tenrpt.copy().sort_values('k_ts').set_index('k_ts')

    # 定义不同曲线的颜色
    colors = ['#445f7e', '#e29135']
    subplot_titles = ['电压', '氟盐', '槽温', '出铝',
                      '分子比', '下料量', '噪声', '基准下料间隔',
                      '铝水平', '电解质水平', 'Fe含量', 'Si含量']
    fig_whole = make_subplots(rows=12, cols=1,
                              shared_xaxes=True,
                              vertical_spacing=0.01)  # 绘制总图

    for i in range(1, 13):
        fig_whole.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray', row=i, col=1)
        fig_whole.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray', row=i, col=1)

    # 设置数据标签显示逻辑 - 基于非空数据点计算
    def get_label_step(field_name, df):
        valid_count = df[field_name].notna().sum()
        return 8 if valid_count > 100 else (4 if valid_count > 75 else (3 if valid_count > 35 else 1))

    # 辅助函数：生成text数组，长度与df.index一致
    def generate_text_array(series, step):
        """生成与原始数据长度一致的text数组"""
        text_array = []
        valid_count = 0  # 非空值计数器

        for value in series:
            if pd.isna(value):
                text_array.append('')
            else:
                valid_count += 1
                if (valid_count - 1) % step == 0:  # 第0个非空值显示标签
                    # 根据数值类型决定显示格式
                    if isinstance(value, (int, np.integer)):
                        text_array.append(f"{value}")
                    elif isinstance(value, (float, np.floating)):
                        text_array.append(f"{value:.2f}")
                    else:
                        text_array.append(f"{value}")
                else:
                    text_array.append('')
        return text_array

    # 导入numpy用于类型检查
    import numpy as np

    # 1. 绘制电压曲线的多条折线子图
    label_step_voltage = get_label_step('working_voltage', data_tenrpt)

    # 生成设定电压的text数组
    set_voltage_text = generate_text_array(data_tenrpt['set_voltage'], label_step_voltage)
    fig_whole.add_trace(
        go.Scatter(
            x=df.index,
            y=data_tenrpt['set_voltage'],
            mode='lines+markers+text',
            name='设定电压',
            line=dict(color=colors[0], width=2),
            marker=dict(size=5, color=colors[0]),
            text=set_voltage_text,
            textposition='top center',
            textfont=dict(size=16, family='SimHei', color=colors[0]),
            connectgaps=True,
            hovertemplate='设定电压: %{y:.2f}<extra></extra>'
        ),
        row=1, col=1
    )

    # 生成工作电压的text数组
    working_voltage_text = generate_text_array(data_tenrpt['working_voltage'], label_step_voltage)
    fig_whole.add_trace(
        go.Scatter(
            x=df.index,
            y=data_tenrpt['working_voltage'],
            mode='markers+lines+text',
            name='工作电压',
            line=dict(color=colors[1], width=2),
            marker=dict(size=5, color=colors[1]),
            text=working_voltage_text,
            textposition='bottom center',
            textfont=dict(size=16, family='SimHei', color=colors[1]),
            connectgaps=True,
            hovertemplate='工作电压: %{y:.2f}<extra></extra>'
        ),
        row=1, col=1
    )

    # 2. 绘制氟盐曲线的多条折线子图
    label_step_fluoride = get_label_step('set_fluoride_weight', data_tenrpt)

    # 生成设定氟盐的text数组
    set_fluoride_text = generate_text_array(data_tenrpt['set_fluoride_weight'], label_step_fluoride)
    set_fluoride_text = [
        str(int(float(text))) if text != '' and text.replace('.', '').replace('-', '').isdigit() else text
        for text in set_fluoride_text]
    fig_whole.add_trace(
        go.Scatter(
            x=df.index,
            y=data_tenrpt['set_fluoride_weight'],
            mode='lines+markers+text',
            name='设定氟盐下料量',
            line=dict(color=colors[0], width=2),
            marker=dict(size=5, color=colors[0]),
            text=set_fluoride_text,
            textposition='top center',
            textfont=dict(size=16, family='SimHei', color=colors[0]),
            connectgaps=True,
            hovertemplate='设定氟盐下料量: %{y:.0f}<extra></extra>'
        ),
        row=2, col=1
    )

    # 生成实际氟盐的text数组
    fluoride_actual_text = generate_text_array(data_tenrpt['fluoride_actual_weight'], label_step_fluoride)
    fluoride_actual_text = [
        str(int(float(text))) if text != '' and text.replace('.', '').replace('-', '').isdigit() else text
        for text in fluoride_actual_text]
    fig_whole.add_trace(
        go.Scatter(
            x=df.index,
            y=data_tenrpt['fluoride_actual_weight'],
            mode='lines+markers+text',
            name='实际氟盐下料量（取整）',
            line=dict(color=colors[1], width=2),
            marker=dict(size=5, color=colors[1]),
            text=fluoride_actual_text,
            textposition='bottom center',
            textfont=dict(size=16, family='SimHei', color=colors[1]),
            connectgaps=True,
            hovertemplate='实际氟盐下料量: %{y:.0f}<extra></extra>'
        ),
        row=2, col=1
    )

    # 3. 绘制槽温曲线的折线子图
    label_step_temp = get_label_step('temperature', data_tenrpt)
    temperature_text = generate_text_array(data_tenrpt['temperature'], label_step_temp)
    temperature_text = [
        str(int(float(text))) if text != '' and text.replace('.', '').replace('-', '').isdigit() else text
        for text in temperature_text]
    fig_whole.add_trace(
        go.Scatter(
            x=df.index,
            y=data_tenrpt['temperature'],
            mode='lines+markers+text',
            name='槽温',
            line=dict(color=colors[0], width=2),
            marker=dict(size=5, color=colors[0]),
            text=temperature_text,
            textposition='top center',
            textfont=dict(size=16, family='SimHei', color=colors[0]),
            connectgaps=True,
            hovertemplate='槽温: %{y:.0f}<extra></extra>'
        ),
        row=3, col=1
    )

    # 4. 绘制出铝曲线的多条折线子图
    label_step_al_output = get_label_step('planned_aluminum_output', data_tenrpt)

    # 生成计划出铝的text数组
    planned_al_output_text = generate_text_array(data_tenrpt['planned_aluminum_output'], label_step_al_output)
    planned_al_output_text = [
        str(int(float(text))) if text != '' and text.replace('.', '').replace('-', '').isdigit() else text
        for text in planned_al_output_text]
    fig_whole.add_trace(
        go.Scatter(
            x=df.index,
            y=data_tenrpt['planned_aluminum_output'],
            mode='lines+markers+text',
            name='计划出铝量',
            line=dict(color=colors[0], width=2),
            marker=dict(size=5, color=colors[0]),
            text=planned_al_output_text,
            textposition='top center',
            textfont=dict(size=16, family='SimHei', color=colors[0]),
            connectgaps=True,
            hovertemplate='计划出铝量: %{y:.0f}<extra></extra>'
        ),
        row=4, col=1
    )

    # 生成实际出铝的text数组
    actual_al_output_text = generate_text_array(data_tenrpt['aluminum_output_weight'], label_step_al_output)
    actual_al_output_text = [
        str(int(float(text))) if text != '' and text.replace('.', '').replace('-', '').isdigit() else text
        for text in actual_al_output_text]
    fig_whole.add_trace(
        go.Scatter(
            x=df.index,
            y=data_tenrpt['aluminum_output_weight'],
            mode='lines+markers+text',
            name='实际出铝量',
            line=dict(color=colors[1], width=2),
            marker=dict(size=5, color=colors[1]),
            text=actual_al_output_text,
            textposition='bottom center',
            textfont=dict(size=16, family='SimHei', color=colors[1]),
            connectgaps=True,
            hovertemplate='实际出铝量: %{y:.0f}<extra></extra>'
        ),
        row=4, col=1
    )

    # 5. 绘制分子比曲线的折线子图
    label_step_mr = get_label_step('molecular_ratio', data_tenrpt)
    molecular_ratio_text = generate_text_array(data_tenrpt['molecular_ratio'], label_step_mr)
    fig_whole.add_trace(
        go.Scatter(
            x=df.index,
            y=data_tenrpt['molecular_ratio'],
            mode='lines+markers+text',
            name='分子比',
            line=dict(color=colors[0], width=2),
            marker=dict(size=5, color=colors[0]),
            text=molecular_ratio_text,
            textposition='top center',
            textfont=dict(size=16, family='SimHei', color=colors[0]),
            connectgaps=True,
            hovertemplate='分子比: %{y:.2f}<extra></extra>'
        ),
        row=5, col=1,
    )

    # 6. 绘制下料量曲线的折线子图
    label_step_feeding = get_label_step('feeding_weight', data_tenrpt)
    feeding_weight_text = generate_text_array(data_tenrpt['feeding_weight'], label_step_feeding)
    feeding_weight_text = [
        str(int(float(text))) if text != '' and text.replace('.', '').replace('-', '').isdigit() else text
        for text in feeding_weight_text]
    fig_whole.add_trace(
        go.Scatter(
            x=df.index,
            y=data_tenrpt['feeding_weight'],
            mode='lines+markers+text',
            name='下料量',
            line=dict(color=colors[0], width=2),
            marker=dict(size=5, color=colors[0]),
            text=feeding_weight_text,
            textposition='top center',
            textfont=dict(size=16, family='SimHei', color=colors[0]),
            connectgaps=True,
            hovertemplate='下料量: %{y:.0f}<extra></extra>'
        ),
        row=6, col=1
    )

    # 7. 绘制噪声曲线的多条折线子图
    label_step_fluctuation = get_label_step('fluctuation', data_tenrpt)

    # 生成针振的text数组
    fluctuation_text = generate_text_array(data_tenrpt['fluctuation'], label_step_fluctuation)
    fluctuation_text = [
        str(int(float(text))) if text != '' and text.replace('.', '').replace('-', '').isdigit() else text
        for text in fluctuation_text]
    fig_whole.add_trace(
        go.Scatter(
            x=df.index,
            y=data_tenrpt['fluctuation'],
            mode='lines+markers+text',
            name='针振',
            line=dict(color=colors[0], width=2),
            marker=dict(size=5, color=colors[0]),
            text=fluctuation_text,
            textposition='top center',
            textfont=dict(size=16, family='SimHei', color=colors[0]),
            connectgaps=True,
            hovertemplate='针振: %{y:.0f}<extra></extra>'
        ),
        row=7, col=1
    )

    # 生成摆动的text数组
    waving_text = generate_text_array(data_tenrpt['waving'], label_step_fluctuation)
    waving_text = [str(int(float(text))) if text != '' and text.replace('.', '').replace('-', '').isdigit() else text
                   for text in waving_text]
    fig_whole.add_trace(
        go.Scatter(
            x=df.index,
            y=data_tenrpt['waving'],
            mode='lines+markers+text',
            name='摆动',
            line=dict(color=colors[1], width=2),
            marker=dict(size=5, color=colors[1]),
            text=waving_text,
            textposition='bottom center',
            textfont=dict(size=16, family='SimHei', color=colors[1]),
            connectgaps=True,
            hovertemplate='摆动: %{y:.0f}<extra></extra>'
        ),
        row=7, col=1
    )

    # 8. 绘制基准下料间隔曲线的折线子图
    label_step_feeding_interval = get_label_step('set_feeding_interval', data_tenrpt)
    feeding_interval_text = generate_text_array(data_tenrpt['set_feeding_interval'], label_step_feeding_interval)
    feeding_interval_text = [
        str(int(float(text))) if text != '' and text.replace('.', '').replace('-', '').isdigit() else text
        for text in feeding_interval_text]
    fig_whole.add_trace(
        go.Scatter(
            x=df.index,
            y=data_tenrpt['set_feeding_interval'],
            mode='lines+markers+text',
            name='基准下料间隔',
            line=dict(color=colors[0], width=2),
            marker=dict(size=5, color=colors[0]),
            text=feeding_interval_text,
            textposition='top center',
            textfont=dict(size=16, family='SimHei', color=colors[0]),
            connectgaps=True,
            hovertemplate='基准下料间隔: %{y:.0f}<extra></extra>'
        ),
        row=8, col=1
    )

    # 9. 绘制铝水平曲线的折线子图
    label_step_al_level = get_label_step('aluminum_level', data_tenrpt)
    aluminum_level_text = generate_text_array(data_tenrpt['aluminum_level'], label_step_al_level)
    aluminum_level_text = [
        str(int(float(text))) if text != '' and text.replace('.', '').replace('-', '').isdigit() else text
        for text in aluminum_level_text]
    fig_whole.add_trace(
        go.Scatter(
            x=df.index,
            y=data_tenrpt['aluminum_level'],
            mode='lines+markers+text',
            name='铝水平',
            line=dict(color=colors[0], width=2),
            marker=dict(size=5, color=colors[0]),
            text=aluminum_level_text,
            textposition='top center',
            textfont=dict(size=16, family='SimHei', color=colors[0]),
            connectgaps=True,
            hovertemplate='铝水平: %{y:.0f}<extra></extra>'
        ),
        row=9, col=1
    )

    # 10. 绘制电解质水平曲线的折线子图
    label_step_el_level = get_label_step('electrolyte_level', data_tenrpt)
    electrolyte_level_text = generate_text_array(data_tenrpt['electrolyte_level'], label_step_el_level)

    # 将电解质水平的文本数组转换为整数显示
    electrolyte_level_text = [
        str(int(float(text))) if text != '' and text.replace('.', '').replace('-', '').isdigit() else text
        for text in electrolyte_level_text]
    fig_whole.add_trace(
        go.Scatter(
            x=df.index,
            y=data_tenrpt['electrolyte_level'],
            mode='lines+markers+text',
            name='电解质水平',
            line=dict(color=colors[0], width=2),
            marker=dict(size=5, color=colors[0]),
            text=electrolyte_level_text,
            textposition='top center',
            textfont=dict(size=16, family='SimHei', color=colors[0]),
            connectgaps=True,
            hovertemplate='电解质水平: %{y:.0f}<extra></extra>'
        ),
        row=10, col=1
    )

    # 11. 绘制Fe含量曲线的折线子图
    label_step_fe = get_label_step('fe_content', data_tenrpt)
    fe_content_text = generate_text_array(data_tenrpt['fe_content'], label_step_fe)
    fig_whole.add_trace(
        go.Scatter(
            x=df.index,
            y=data_tenrpt['fe_content'],
            mode='lines+markers+text',
            name='Fe含量',
            line=dict(color=colors[0], width=2),
            marker=dict(size=5, color=colors[0]),
            text=fe_content_text,
            textposition='top center',
            textfont=dict(size=16, family='SimHei', color=colors[0]),
            connectgaps=True,
            hovertemplate='Fe含量: %{y:.2f}<extra></extra>'
        ),
        row=11, col=1
    )

    # 12. 绘制Si含量曲线的折线子图
    label_step_si = get_label_step('si_content', data_tenrpt)
    si_content_text = generate_text_array(data_tenrpt['si_content'], label_step_si)
    fig_whole.add_trace(
        go.Scatter(
            x=df.index,
            y=data_tenrpt['si_content'],
            mode='lines+markers+text',
            name='Si含量',
            line=dict(color=colors[0], width=2),
            marker=dict(size=5, color=colors[0]),
            text=si_content_text,
            textposition='top center',
            textfont=dict(size=16, family='SimHei', color=colors[0]),
            connectgaps=True,
            hovertemplate='Si含量: %{y:.2f}<extra></extra>'
        ),
        row=12, col=1
    )

    # 配置y轴标题
    for i in range(1, 13):
        fig_whole.update_yaxes(
            title_text=subplot_titles[i - 1],
            title_standoff=5,
            title_font=dict(size=14, family='SimHei'),
            row=i, col=1
        )

    # 配置x轴：只在最后一行显示x轴标签
    for i in range(1, 12):  # 对前11个子图隐藏x轴标签
        fig_whole.update_xaxes(
            showticklabels=False,  # 不显示刻度标签
            row=i, col=1
        )

    # 为最后一个子图显示x轴标签
    fig_whole.update_xaxes(
        title_text='时间',
        title_font=dict(size=14, family='SimHei'),
        tickformat='%Y-%m-%d',
        showgrid=True,
        gridcolor='lightgrey',
        row=12, col=1  # 最后一行显示x轴
    )

    # 设置图表标题
    # 注意：现在k_ts是索引，不能直接用.iloc或.values[-1]
    # 需要从索引中获取时间信息
    k_device = data_tenrpt["k_device"].iloc[0] if "k_device" in data_tenrpt.columns else "未知设备"

    # 获取开始和结束时间
    if len(df.index) > 0:
        k_ts_start = df.index[0].strftime('%Y%m%d')
        k_ts_end = df.index[-1].strftime('%Y%m%d')
        str_title = f'{k_device}_{k_ts_start}_{k_ts_end}_工艺报表'
    else:
        str_title = f'{k_device}_工艺报表'

    # 获取时间范围
    x_min = df.index.min() if len(df.index) > 0 else None
    x_max = df.index.max() if len(df.index) > 0 else None

    fig_whole.update_layout(
        title=dict(text=str_title,
                   font=dict(size=16, family='SimHei'),
                   x=0.5,
                   xanchor='center',
                   y=0.98,
                   yanchor='middle'),
        xaxis=dict(
            title_font=dict(size=14, family='SimHei'),
            tickformat='%Y-%m-%d',
            showgrid=True,
            gridcolor='lightgrey',
            range=[x_min, x_max] if x_min and x_max else None,  # 明确设置初始范围
        ),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor='rgba(255,255,255,0.01)',
            bordercolor='rgba(255,255,255,0.01)',
            font=dict(color='grey')),
        dragmode='zoom',
        # width不设置，让图表自适应容器宽度
        height=1580,
        plot_bgcolor='rgba(240, 240, 240, 0.5)',
        paper_bgcolor='white',
        showlegend=False,  # 隐藏底部图例
        margin=dict(l=60, r=40, t=80, b=40),
    )

    # 为每个子图添加左上角图例注释
    # 子图 y 轴域位置（从下到上）
    subplot_y_domains = [
        (0.9167, 1.0),  # 第1个子图 - 电压
        (0.8333, 0.9067),  # 第2个子图 - 氟盐
        (0.75, 0.8233),  # 第3个子图 - 槽温
        (0.6667, 0.74),  # 第4个子图 - 出铝
        (0.5833, 0.6567),  # 第5个子图 - 分子比
        (0.5, 0.5733),  # 第6个子图 - 下料量
        (0.4167, 0.49),  # 第7个子图 - 噪声
        (0.3333, 0.4067),  # 第8个子图 - 基准下料间隔
        (0.25, 0.3233),  # 第9个子图 - 铝水平
        (0.1667, 0.24),  # 第10个子图 - 电解质水平
        (0.0833, 0.1567),  # 第11个子图 - Fe含量
        (0.0, 0.0733),  # 第12个子图 - Si含量
    ]

    # 子图图例文本
    subplot_legends = [
        f"<span style='color:{colors[0]}'>● 设定电压</span><br><span style='color:{colors[1]}'>● 工作电压</span>",
        f"<span style='color:{colors[0]}'>● 设定氟盐</span><br><span style='color:{colors[1]}'>● 实际氟盐</span>",
        f"<span style='color:{colors[0]}'>● 槽温</span>",
        f"<span style='color:{colors[0]}'>● 计划出铝</span><br><span style='color:{colors[1]}'>● 实际出铝</span>",
        f"<span style='color:{colors[0]}'>● 分子比</span>",
        f"<span style='color:{colors[0]}'>● 下料量</span>",
        f"<span style='color:{colors[0]}'>● 针振</span><br><span style='color:{colors[1]}'>● 摆动</span>",
        f"<span style='color:{colors[0]}'>● 基准下料间隔</span>",
        f"<span style='color:{colors[0]}'>● 铝水平</span>",
        f"<span style='color:{colors[0]}'>● 电解质</span>",
        f"<span style='color:{colors[0]}'>● Fe含量</span>",
        f"<span style='color:{colors[0]}'>● Si含量</span>",
    ]

    # 添加图例注释
    for i, (legend_text, y_domain) in enumerate(zip(subplot_legends, subplot_y_domains)):
        fig_whole.add_annotation(
            text=legend_text,
            xref="paper", yref="paper",
            x=0.01, y=y_domain[1] - 0.005,
            xanchor='left', yanchor='top',
            showarrow=False,
            font=dict(size=10, family='SimHei'),
            bgcolor='rgba(255,255,255,0.7)',
            bordercolor='gray',
            borderwidth=2,
            borderpad=1
        )

    # 计算每个指标的均值并添加到子图右侧
    # 定义每个子图对应的指标和颜色
    subplot_mean_config = [
        # (子图行号, [(字段名, 颜色, 格式化字符串), ...])
        (1, [('set_voltage', colors[0], '.2f'), ('working_voltage', colors[1], '.2f')]),
        (2, [('set_fluoride_weight', colors[0], '.0f'), ('fluoride_actual_weight', colors[1], '.0f')]),
        (3, [('temperature', colors[0], '.0f')]),
        (4, [('planned_aluminum_output', colors[0], '.0f'), ('aluminum_output_weight', colors[1], '.0f')]),
        (5, [('molecular_ratio', colors[0], '.2f')]),
        (6, [('feeding_weight', colors[0], '.0f')]),
        (7, [('fluctuation', colors[0], '.0f'), ('waving', colors[1], '.0f')]),
        (8, [('set_feeding_interval', colors[0], '.0f')]),
        (9, [('aluminum_level', colors[0], '.0f')]),
        (10, [('electrolyte_level', colors[0], '.0f')]),
        (11, [('fe_content', colors[0], '.2f')]),
        (12, [('si_content', colors[0], '.2f')]),
    ]

    # 为每个子图添加均值注释
    for row_num, fields_config in subplot_mean_config:
        y_domain = subplot_y_domains[row_num - 1]
        y_center = (y_domain[0] + y_domain[1]) / 2

        # 计算每个字段的均值并生成注释文本
        mean_texts = []
        for field_name, color, fmt in fields_config:
            if field_name in data_tenrpt.columns:
                mean_val = data_tenrpt[field_name].mean()
                if pd.notna(mean_val):
                    formatted_val = f"{mean_val:{fmt}}"
                    mean_texts.append(f"<span style='color:{color}'>{formatted_val}</span>")

        if mean_texts:
            # 多个均值时换行显示
            annotation_text = "<br>".join(mean_texts)
            fig_whole.add_annotation(
                text=annotation_text,
                xref="paper", yref="paper",
                x=0.99, y=y_center,
                xanchor='right', yanchor='middle',
                showarrow=False,
                font=dict(size=14, family='SimHei'),
                bgcolor='rgba(255,255,255,0.7)',
                bordercolor='gray',
                borderwidth=1,
                borderpad=2
            )

    return fig_whole


# 阳极曲线静态图
def plot_anode_current_and_pot_voltage(data_anode, data_tenrpt, target_date=None):
    """
    绘制阳极电流和槽电压曲线图

    参数:
        data_anode: 阳极电流数据 DataFrame
        data_tenrpt: 槽控曲线数据 DataFrame
        target_date: 目标日期，用于文件命名，格式 'YYYY-MM-DD'，如果为None则从数据中提取
    """
    if data_anode.empty or data_tenrpt.empty:
        raise ValueError("阳极电流数据或槽控数据为空，无法生成阳极电流图")

    data_anode_dev = data_anode.reset_index(drop=True).copy()
    data_tenrpt_dev = data_tenrpt.reset_index(drop=True).copy()

    logger.info("DEBUG +00+=================================")
    logger.info(data_anode_dev.head(2))
    logger.info("++++++++++++++++++++++================================")

    # 设置阳极电流子图的分组
    anode_groups = {
        (1, 0): ['A1', 'A2', 'A3'],
        (1, 1): ['B1', 'B2', 'B3'],
        (2, 0): ['A4', 'A5', 'A6', 'A7'],
        (2, 1): ['B4', 'B5', 'B6', 'B7'],
        (3, 0): ['A8', 'A9', 'A10', 'A11'],
        (3, 1): ['B8', 'B9', 'B10', 'B11'],
        (4, 0): ['A12', 'A13', 'A14'],
        (4, 1): ['B12', 'B13', 'B14'],
    }
    anode_state_map = {
        '自动阳极升': {"marker": "^", "color": "green"},
        '自动阳极降': {"marker": "v", "color": "green"},
        '手动阳极升': {"marker": "^", "color": "red"},
        '手动阳极降': {"marker": "v", "color": "red"},
    }
    feature_dict = {
        '电压': [3600, 4200],
        '针振&摆动': [0, 50],
        '下料间隔': [500, 1600],
        '电流': [0, 1200],
    }
    # 调整每个子图的上下间距，使图像更紧凑
    # plt.subplots_adjust()  # hspace 数值可根据实际效果调整，0.25~0.5之间一般较合适
    logger.info("DEBUG +00011+=================================")
    logger.info(data_anode_dev.head(2))
    logger.info("++++++++++++++++++++++================================")
    import matplotlib.pyplot as plt
    # 设置全局字体大小
    plt.rcParams.update({
        'font.size': 12,
        'axes.titlesize': 16,
        'axes.labelsize': 10,
        'xtick.labelsize': 8,
        'ytick.labelsize': 10,
        'legend.fontsize': 16,
    })

    # 调整图表尺寸：宽度加大，高度适中
    fig, axes = plt.subplots(5, 2, figsize=(32, 26))
    fig.set_dpi(800)

    # 调整子图布局：减少空白，让子图填满画布
    plt.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.06, wspace=0.15, hspace=0.25)

    # 绘制阳极电流分组曲线
    for (row, col), anodes in anode_groups.items():
        ax = axes[row, col]
        for anode in anodes:
            if anode in data_anode_dev.columns:
                ax.plot(
                    data_anode_dev['k_ts'].values,
                    data_anode_dev[anode].values,
                    label=anode,
                    linewidth=1.5
                )
        ax.set_ylabel('电流(A)', fontsize=14, fontweight='bold')
        ax.set_ylim(feature_dict['电流'][0], feature_dict['电流'][1])
        ax.legend(loc='upper left', fontsize=16, ncol=4, framealpha=0.9)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='both', labelsize=11)

    logger.info("DEBUG11 ++=================================")
    logger.info(data_anode_dev.head(2))
    logger.info("++++++++++++++++++++++================================")

    # 创建设置了k_ts为索引的副本，用于get_special_state_text_by_pot函数
    df_with_ts_index = data_tenrpt_dev.copy().set_index('k_ts')

    # （0,0）子图：工作电压、电压上限、电压下限，手动/自动 3角标记，出铝，换机标记
    ax00 = axes[0, 0]
    if 'pot_voltage' in data_tenrpt_dev.columns:
        ax00.plot(data_tenrpt_dev['k_ts'], data_tenrpt_dev['pot_voltage'], label='工作电压', color='b', linewidth=1.5)
    if 'voltage_upper_limit' in data_tenrpt_dev.columns:
        ax00.plot(data_tenrpt_dev['k_ts'], data_tenrpt_dev['voltage_upper_limit'], label='电压上下限', linestyle='--',
                  color='r', linewidth=1.5)
    if 'voltage_lower_limit' in data_tenrpt_dev.columns:
        ax00.plot(data_tenrpt_dev['k_ts'], data_tenrpt_dev['voltage_lower_limit'], label=None, linestyle='--',
                  color='r', linewidth=1.5)
    for ano_state in ["自动阳极降", "自动阳极升", "手动阳极降", "手动阳极升", ]:
        _x = data_tenrpt_dev[data_tenrpt_dev['andoe_move_state_zh'].astype(str).str.contains(ano_state, na=False)][['k_ts']].values
        _y = data_tenrpt_dev[data_tenrpt_dev['andoe_move_state_zh'].astype(str).str.contains(ano_state, na=False)][
            'pot_voltage'].values
        ax00.scatter(x=_x, y=_y, marker=anode_state_map[ano_state]['marker'], c=anode_state_map[ano_state]['color'],
                     s=80)

    # 不使用新的库，仅加上文字信息
    for event in ['换极', '出铝', '抬母线', '纯手动', '效应']:
        _x, _y, _text = get_special_state_text_by_pot(df_with_ts_index, event)
        for i in range(len(_x)):
            x_datetime = pd.to_datetime(_x[i])
            ax00.text(x_datetime, _y[i], event, color='k', fontsize=11, ha='center', va='bottom', rotation=0,
                      fontweight='bold')

    ax00.set_ylabel('电压(mV)', fontsize=16, fontweight='bold')
    ax00.set_ylim(feature_dict['电压'][0], feature_dict['电压'][1])
    ax00.legend(loc='upper left', fontsize=16, framealpha=0.9)
    ax00.grid(True, alpha=0.3)
    ax00.tick_params(axis='both', labelsize=11)
    logger.info("DEBUG22 ++=================================")
    logger.info(data_anode_dev.head(2))
    logger.info("++++++++++++++++++++++================================")

    # （0,1）子图：双Y轴，左Y轴：基准下料间隔，实际下料间隔，右Y轴：针振、摆动
    ax01 = axes[0, 1]
    ax01_2 = ax01.twinx()
    if 'set_feeding_interval' in data_tenrpt_dev.columns:
        ax01.plot(data_tenrpt_dev['k_ts'].values, data_tenrpt_dev['set_feeding_interval'].values, label='基准下料间隔',
                  color='b')
    if 'actual_feeding_interval' in data_tenrpt_dev.columns:
        ax01.plot(data_tenrpt_dev['k_ts'].values, data_tenrpt_dev['actual_feeding_interval'].values,
                  label='实际下料间隔',
                  color='orange', drawstyle='steps-pre')
    if 'fluctuation' in data_tenrpt_dev.columns:
        ax01_2.plot(data_tenrpt_dev['k_ts'].values, data_tenrpt_dev['fluctuation'].values, label='针振', color='m')
    if 'waving' in data_tenrpt_dev.columns:
        ax01_2.plot(data_tenrpt_dev['k_ts'].values, data_tenrpt_dev['waving'].values, label='摆动', color='y')

    for event in ['氟盐下料']:
        _x, _y, _text = get_special_state_text_by_pot(df_with_ts_index, event)
        # logger.info(f'{_x},{_y},{_text}')
        for i in range(len(_x)):
            # 将字符串时间转换为datetime类型，以兼matplotlib的x轴
            x_datetime = pd.to_datetime(_x[i])
            ax01_2.text(x_datetime, _y[i], 'F', color='r', fontsize=12, ha='center', va='bottom', rotation=0)

    # ax01.set_title('下料间隔/针振/摆动')
    ax01.set_ylabel('下料间隔(ms)')
    ax01.set_ylim(feature_dict['下料间隔'][0], feature_dict['下料间隔'][1])
    ax01_2.set_ylabel('针振/摆动')
    ax01_2.set_ylim(feature_dict['针振&摆动'][0], feature_dict['针振&摆动'][1])
    # 将图例设置为横向排布
    ax01.legend(loc='upper left', fontsize=18, )
    ax01_2.legend(loc='upper right', fontsize=18, )
    ax01.grid(True)

    k_device = data_tenrpt["k_device"].values[0]
    # 优先使用传入的目标日期，否则从数据中提取
    if target_date is not None:
        k_ts = target_date if isinstance(target_date, str) else pd.to_datetime(target_date).strftime('%Y-%m-%d')
    else:
        k_ts = pd.to_datetime(data_tenrpt["k_ts"].values[0]).strftime('%Y-%m-%d')
    str_title = f'{k_device}_{k_ts}_阳极电流'
    fig.suptitle(f'{str_title}', fontsize=20)
    plt.tight_layout(pad=1, w_pad=0.2, h_pad=0.01, rect=[0, 0, 1, 0.97])

    # 保存路径与data_process.py中的读取路径保持一致
    save_dir = f'./images/阳极电流图/{k_device}'
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    plt.savefig(f'{save_dir}/{str_title}.png')
    plt.close(fig)  # 关闭图形释放内存