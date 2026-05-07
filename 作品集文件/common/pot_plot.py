import pandas as pd
import os
from loguru import logger

def get_gongyirpt_text(data):
    field_notnull_info = {}
    for col in data.columns:
        # 只处理数值型字段
        if data[col].notna().sum() > 0:
            notnull_idx = data[data[col].notna()]['k_ts'].tolist()[0].strftime('%Y-%m-%d')
            notnull_vals = data[data[col].notna()][col].values.tolist()[0]
            field_notnull_info.update({col:{"index":notnull_idx, "value":notnull_vals}})
   # field_notnull_info # 现在保存了每个字段不为空的索引和值
    gongyirpt_text = [
            f"[槽龄]:{field_notnull_info['age']['value']} ({field_notnull_info['age']['index']})",
        f"[设定电压]:{field_notnull_info['set_voltage']['value']} ({field_notnull_info['set_voltage']['index']}); [运行电压]:{field_notnull_info['working_voltage']['value']} ({field_notnull_info['working_voltage']['index']})",
        f"[槽温]:{field_notnull_info['temperature']['value']} ({field_notnull_info['temperature']['index']}); [分子比]:{field_notnull_info['molecular_ratio']['value']} ({field_notnull_info['molecular_ratio']['index']})",
        f"[铝水平]:{field_notnull_info['aluminum_level']['value']} ({field_notnull_info['aluminum_level']['index']}); [电解质水平]:{field_notnull_info['electrolyte_level']['value']} ({field_notnull_info['electrolyte_level']['index']})",
        f"[Fe含量]:{field_notnull_info['fe_content']['value']} ({field_notnull_info['fe_content']['index']}); [Si含量]:{field_notnull_info['si_content']['value']} ({field_notnull_info['si_content']['index']})",
        f"[出铝量]:{field_notnull_info['aluminum_output_weight']['value']} ({field_notnull_info['aluminum_output_weight']['index']}); [炉底压降]:{field_notnull_info['bottom_voltage']['value']} ({field_notnull_info['bottom_voltage']['index']})",
        ]
    return gongyirpt_text

def plotly_pot_voltage_curve(data_tenrpt, data_gongyirpt, data_type='2m'):
    """
        使用 Plotly 绘制槽电压曲线图，支持多个Y轴和交互式操作

        参数:
            data_tenrpt: 十分钟报表数据
            data_gongyprt: 工艺报表数据
        """
    if data_tenrpt.empty:
        raise ValueError("槽控数据为空，无法生成槽电压曲线图")

    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    # 阳极状态映射
    anode_state_map = {
        '自动阳极升': {"symbol": "triangle-up", "color": "green", "name": "自动阳极升"},
        '自动阳极降': {"symbol": "triangle-down", "color": "green", "name": "自动阳极降"},
        '手动阳极升': {"symbol": "triangle-up", "color": "red", "name": "手动阳极升"},
        '手动阳极降': {"symbol": "triangle-down", "color": "red", "name": "手动阳极降"},
    }

    # 数据准备
    df = data_tenrpt.copy().sort_values('k_ts').set_index('k_ts')

    # 辅助函数：获取特殊状态事件的位置信息
    def get_special_state_text_by_pot(data, event):
        df = data.copy()
        special_state = ['保留字段', '保留字段', '纯手动', '抬母线', '辅料', '换极', '出铝', '效应']
        feeding_state = ['保留字段', '保留字段', '自动AlF3下料(氟盐下料)', '手动AlF3下料(氟盐下料)',
                         '自动小下料', '手动小下料', '自动AEB(大下料)', '手动AEB(大下料)']
        logger.info(f'event:{event}')
        if event in special_state:
            df['specialState_flag'] = df['special_state_zh'].astype(str).str.contains(f'{event}') != df['special_state_zh'].astype(str).str.contains(f'{event}').shift(1) # 定义specialState_flag事件开始标志
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

        logger.info(f'event:{event}, x_index:{x_index}, y_value:{y_value}, y_text={y_text}' )
        return x_index, y_value, y_text

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
                   yaxis='y1', showlegend=False,
                   hovertemplate='设定电压: %{y:.0f} mV<extra></extra>')
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
        go.Scatter(x=df.index, y=df['set_feeding_interval'] + 3600,
                   mode='lines', name='基准下料间隔',
                   line=dict(color='darkred', width=1.5, dash='dash'),
                   yaxis='y1', showlegend=False,
                   hovertemplate='基准下料间隔: %{customdata:.0f} s<extra></extra>',
                   customdata=df['set_feeding_interval'])
    )

    fig.add_trace(
        go.Scatter(x=df.index, y=df['actual_feeding_interval'] + 3600,
                   mode='lines', name='实际下料间隔',
                   line=dict(color='orange', width=2, shape='hv'),
                   yaxis='y1', showlegend=False,
                   hovertemplate='实际下料间隔: %{customdata:.0f} s<extra></extra>',
                   customdata=df['actual_feeding_interval']
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
        go.Scatter(x=df.index, y=df['series_current']/10+30,
                   mode='lines', name='系列电流',
                   line=dict(color='crimson', width=2),
                   hovertemplate='系列电流: %{customdata: .0f} kA<extra></extra>',
                   yaxis='y2', showlegend=False,
                   customdata=df['series_current']/10)
    )

    # Y5:累斜和斜率（映射到y1轴，偏移3500使其显示在针振与电压之间）
    fig.add_trace(
        go.Scatter(x=df.index, y=df['slope'] + 3500,
                   mode='lines', name='斜率',
                   line=dict(color='#7d5886', width=2),
                   hovertemplate='斜率: %{customdata:.3f} <extra></extra>',
                   showlegend=False,
                   customdata=df['slope'],
                   )
    )

    fig.add_trace(
        go.Scatter(x=df.index, y=df['cumulative_voltage_slope'] + 3500,
                   mode='lines', name='累斜',
                   line=dict(color='#f58220', width=2),
                   hovertemplate='累斜: %{customdata:.3f} <extra></extra>',
                   showlegend=False,
                   customdata=df['cumulative_voltage_slope'],
        )
    )

    fig.add_trace(
        go.Scatter(x=df.index, y=[3500] * len(df.index),
                   mode='lines', name='定斜',
                   line=dict(color='#d71345', width=1, dash='dash'),
                   hoverinfo='skip',
                   showlegend=False,
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
        xanchor='left',yanchor='top',
        # bgcolor='rgba(255, 255, 255, 0.8)',
        # bordercolor='green', borderwidth=1, borderpad=5
    )

    # 设置图表标题
    k_device = data_tenrpt['k_device'].values[0]
    k_ts = pd.to_datetime(data_tenrpt['k_ts'].values[-60]).strftime('%Y%m%d')
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

    return fig
    # plt.show()