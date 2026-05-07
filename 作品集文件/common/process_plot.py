import pandas as pd
import os
import matplotlib.pyplot as plt

import pandas as pd
import os
import numpy as np

# 根据工艺报表中的字段，绘制多个子图（单列排列）。
# 每个子图的Y轴标签为字段名，X轴为k_ts（时间）。
# 每个子图为散点+折线图，所有点均显示。
# 子图顺序严格按照如下字段列表：
# ['fenzb', 'fehl', 'sihl', 'wend', 'lvshp', 'dianjzhshp', 'xichll', 'ludyj']
# 适用于工艺报数据分析的可视化需求。

import matplotlib.pyplot as plt


def plot_gongyirpt_multi_subplots(df, fields, field_name_map=None, group_name_map=None):
    """
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
    from loguru import logger
    logger.info("开始绘图")

    if df.empty:
        raise ValueError("工艺报表数据为空，无法生成图表")

    # 设置默认值
    if field_name_map is None:
        field_name_map = {}
    if group_name_map is None:
        group_name_map = {}

    # 定义不同曲线的颜色列表
    colors = ['#445f7e', '#e29135']

    n = len(fields)
    figsize = (20, 1.5 * n)
    fig, axes = plt.subplots(n, 1, figsize=figsize, sharex=True)
    if n == 1:
        axes = [axes]

    for i, field in enumerate(fields):
        ax = axes[i]

        # 判断是单个字段还是字段组
        if isinstance(field, list):
            # 多个字段合并显示
            field_list = field
            # 获取组名称（用于子图Y轴标签）
            group_key = tuple(field_list)
            ylabel = group_name_map.get(group_key, '/'.join(field_list))
        else:
            # 单个字段
            field_list = [field]
            # 获取字段的中文名称
            ylabel = field_name_map.get(field, field)

        # 绘制每个字段的曲线
        for idx, fld in enumerate(field_list):
            color = colors[idx % len(colors)]
            legend_label = field_name_map.get(fld, fld)

            # 计算当前指标的有效数据量（非 NaN 的数据点数量）
            valid_count = df[fld].notna().sum()

            # 根据当前指标的有效数据量决定标签显示策略
            label_step = 4 if valid_count > 100 else (2 if valid_count > 50 else 1)

            # 根据字段索引确定标签位置（交错显示）
            # 第一个字段标签在上方，第二个字段标签在下方
            va_position = 'bottom' if idx == 0 else 'top'

            # 绘制数据标签（根据label_step决定显示频率）
            for j in range(0, len(df), label_step):
                value = df[fld].values[j]
                if pd.notna(value):
                    if isinstance(value, float):
                        text = f'{value:.2f}'
                        if str(text)[-3:] == '.00':
                            text = int(float(text))
                    else:
                        text = f'{value}'
                else:
                    text = ''
                # 修改判断条件：确保0值也能显示（判断 text != '' 而非 if text）
                if text != '':
                    # 标签颜色与曲线颜色统一，位置交错显示
                    ax.text(df['k_ts'].values[j], value, text, color=color,
                            fontsize=16, ha='center', va=va_position, rotation=45)

            # 过滤掉NaN值后再绘图
            valid_data = df[['k_ts', fld]].dropna()
            if not valid_data.empty:
                ax.plot(valid_data['k_ts'], valid_data[fld],
                        marker='o', linestyle='-', label=legend_label, color=color, linewidth=2)

        # 自动扩展Y轴范围，为数据标签预留空间
        # 获取当前Y轴的数据范围
        y_min, y_max = ax.get_ylim()
        y_range = y_max - y_min

        # 为上下标签预留额外空间（根据数据范围的比例）
        # 标签在上方需要额外空间，标签在下方也需要额外空间
        padding_percent = 0.50  # 上下各预留70%的空间
        y_padding = y_range * padding_percent

        # 设置新的Y轴范围
        ax.set_ylim(y_min - y_padding, y_max + y_padding)

        # 设置Y轴标签和刻度字体大小
        ax.set_ylabel(ylabel, fontproperties="SimHei", fontsize=16)
        ax.tick_params(axis='y', labelsize=16)  # Y轴刻度数字字体大小
        ax.tick_params(axis='x', labelsize=16)  # X轴刻度数字字体大小
        ax.grid(True, linestyle='--', alpha=0.5)
        # 显示图例（右上角）
        ax.legend(loc='upper left', prop={"family": "SimHei"}, framealpha=0.7, edgecolor='gray')
    # 设置X轴标签字体大小
    axes[-1].set_xlabel('k_ts (时间)', fontproperties="SimHei", fontsize=16)

    k_device = df["k_device"].values[0]
    k_ts_start = pd.to_datetime(df["k_ts"].values[-1]).strftime('%Y%m%d')
    k_ts_end = pd.to_datetime(df["k_ts"].values[0]).strftime('%Y%m%d')
    str_title = f'{k_device}_{k_ts_start}_{k_ts_end}_工艺报表'
    # 设置一个整体标题
    # 添加中文标题
    plt.suptitle(str_title, fontproperties="SimHei", fontsize=20, y=1)
    plt.tight_layout(pad=1, h_pad=0, w_pad=0)
    plt.subplots_adjust(hspace=0)

    # 识别有没有这个目录，没有则创建
    if not os.path.exists(f'./fig/铝一1分厂/工艺曲线'):
        os.makedirs(f'./fig/铝一1分厂/工艺曲线')
    # 保存图片，设置DPI=300提高分辨率
    plt.savefig(f'./fig/铝一1分厂/工艺曲线/默认图片.png', dpi=300, bbox_inches='tight')
    # plt.show()
    # return fig


# 示例调用
# selected_fields = ['fenzb', 'fehl', 'sihl', 'wend', 'lvshp', 'dianjzhshp', 'xichll', 'ludyj']
# plot_gongyirpt_multi_subplots(data_gongyprt, selected_fields)

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
    import pandas as pd
    import datetime

    from loguru import logger
    logger.info("开始绘图")

    if data_tenrpt.empty:
        raise ValueError("工艺报表数据为空，无法生成图表")

    # 确保k_ts是索引（时间戳格式）
    if 'k_ts' in data_tenrpt.columns:
        data_tenrpt = data_tenrpt.set_index('k_ts')

    # 确保索引是datetime类型
    if not isinstance(data_tenrpt.index, pd.DatetimeIndex):
        data_tenrpt.index = pd.to_datetime(data_tenrpt.index)

    # 排序索引（按时间升序）
    data_tenrpt = data_tenrpt.sort_index()

    # 重新获取x轴数据（现在作为索引）
    x_data = data_tenrpt.index

    # 定义不同曲线的颜色
    colors = ['#445f7e', '#e29135']
    subplot_titles = ['电压', '氟盐', '槽温', '出铝',
                      '分子比', '下料量', '噪声', '基准下料间隔',
                      '铝水平', '电解质水平', 'Fe含量', 'Si含量']
    fig_whole = make_subplots(rows=12, cols=1,
                              shared_xaxes=True,
                              vertical_spacing=0.01)  # 绘制总图

    # 设置数据标签显示逻辑 - 基于非空数据点计算
    def get_label_step(field_name, df):
        valid_count = df[field_name].notna().sum()
        return 8 if valid_count > 100 else (4 if valid_count > 75 else (3 if valid_count > 35 else 1))

    # 辅助函数：生成text数组，长度与x_data一致
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
            x=x_data,
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
            x=x_data,
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
            x=x_data,
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
            x=x_data,
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
            x=x_data,
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
            x=x_data,
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
            x=x_data,
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
            x=x_data,
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
            x=x_data,
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
            x=x_data,
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
            x=x_data,
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
            x=x_data,
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
            x=x_data,
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
            x=x_data,
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
            x=x_data,
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
            x=x_data,
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
    if len(x_data) > 0:
        k_ts_start = x_data[0].strftime('%Y%m%d')
        k_ts_end = x_data[-1].strftime('%Y%m%d')
        str_title = f'{k_device}_{k_ts_start}_{k_ts_end}_工艺报表'
    else:
        str_title = f'{k_device}_工艺报表'

    # 获取时间范围
    x_min = x_data.min() if len(x_data) > 0 else None
    x_max = x_data.max() if len(x_data) > 0 else None

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
        width=1400,
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
