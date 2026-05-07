import os
import warnings
warnings.filterwarnings('ignore')
import pandas as pd

def _parse_state(value,map_list):
    """历史曲线字段映射
    32位进制状态映射信息(目前都没有超过8位)
    """
    binary_str=bin(int(value))[2:].zfill(8)
    bin_list=[ binary_str[i] for i in range(0,len(binary_str),1) ]
    feature=[]
    for index,state in enumerate(bin_list) :
        if int(state) !=0:
            feature.append(map_list[index])
    return '、'.join(feature)

def _add_field_comments(data):

    df = data.copy()
    special_state = ['保留字段','保留字段','纯手动','抬母线','辅料','换极','出铝','效应']
    feeding_state = ['保留字段','保留字段','自动AlF3下料(氟盐下料)','手动AlF3下料(氟盐下料)','自动小下料','手动小下料','自动AEB(大下料)','手动AEB(大下料)']
    andoe_move_state = ['保留字段','保留字段','保留字段','保留字段','自动阳极降','手动阳极降','自动阳极升','手动阳极升']

    # 兼容两种数据来源：
    # 1）MySQL 历史库：specialState / feedingState / andoeMoveState 为数值编码
    # 2）K2 实时库：special_state_zh / feeding_state_zh / andoe_move_state_zh 已经是中文
    if 'specialState' in df.columns:
        df['specialState_zh'] = df['specialState'].map(lambda x: _parse_state(x, special_state))
    elif 'special_state_zh' in df.columns:
        df['specialState_zh'] = df['special_state_zh']

    if 'feedingState' in df.columns:
        df['feedingState_zh'] = df['feedingState'].map(lambda x: _parse_state(x, feeding_state))
    elif 'feeding_state_zh' in df.columns:
        df['feedingState_zh'] = df['feeding_state_zh']

    if 'andoeMoveState' in df.columns:
        df['andoeMoveState_zh'] = df['andoeMoveState'].map(lambda x: _parse_state(x, andoe_move_state))
    elif 'andoe_move_state_zh' in df.columns:
        df['andoeMoveState_zh'] = df['andoe_move_state_zh']

    return df

def get_special_state_text(data,event):
    """
    """
    df=data.copy()
    special_state=['保留字段','保留字段','纯手动','抬母线','辅料','换极','出铝','效应']
    feeding_state=['保留字段','保留字段','自动AlF3下料(氟盐下料)','手动AlF3下料(氟盐下料)','自动小下料','手动小下料','自动AEB(大下料)','手动AEB(大下料)']
    if event in special_state:
        df['specialState_flag']=df['specialState_zh'].str.contains(f'{event}')!=df['specialState_zh'].str.contains(f'{event}').shift(1)
        x_index=df.query(f'specialState_zh.str.contains("{event}")&specialState_flag==True')['k_ts'].values
        y_value=[3700 for i in range(len(x_index))]
        y_text=[f'{event}' for i in range(len(x_index))]
    for event_target in feeding_state:
        if event in event_target:
            # df['feedingState_flag']=df['feedingState_zh'].str.contains(f'{event}')!=df['feedingState_zh'].str.contains(f'{event}').shift(1)
            x_index=df.query(f'feedingState_zh.str.contains("{event}")')['k_ts'].values
            y_value=[10 for i in range(len(x_index))]
            y_text=[f'{event}' for i in range(len(x_index))]
            # logger.info(f'event:{event},event_target:{event_target}')
    return x_index,y_value,y_text


def plot_anode_current_and_pot_voltage(data_anode, data_tenrpt):
    from loguru import logger

    # 检查数据是否为空
    if data_anode.empty or data_tenrpt.empty:
        logger.error("阳极电流数据或槽控数据为空，无法生成图表")
        raise ValueError("数据为空，无法生成图表")

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
    fig, axes = plt.subplots(5, 2, figsize=(26, 18), sharex=True)
    # 示例：绘制阳极电流分组曲线
    for (row, col), anodes in anode_groups.items():
        ax = axes[row, col]
        for anode in anodes:
            if anode in data_anode_dev.columns:
                ax.plot(
                    data_anode_dev['k_ts'].values,
                    data_anode_dev[anode].values,
                    label=anode
                )
        # ax.set_title(f"阳极电流: {', '.join(anodes)}")
        ax.set_ylabel('电流')
        ax.set_ylim(feature_dict['电流'][0], feature_dict['电流'][1])
        ax.legend(loc='upper left', fontsize=16, ncol=4)
        ax.grid(True)

    logger.info("DEBUG11 ++=================================")
    logger.info(data_anode_dev.head(2))
    logger.info("++++++++++++++++++++++================================")
    # （0,0）子图：工作电压、电压上限、电压下限，手动/自动 3角标记，出铝，换机标记
    ax00 = axes[0, 0]
    if 'potVolt' in data_tenrpt_dev.columns:
        ax00.plot(data_tenrpt_dev['k_ts'], data_tenrpt_dev['potVolt'], label='工作电压', color='b')
    if 'settingVoltMax' in data_tenrpt_dev.columns:
        ax00.plot(data_tenrpt_dev['k_ts'], data_tenrpt_dev['settingVoltMax'], label='电压上下限', linestyle='--',
                  color='r')
    if 'settingVoltMin' in data_tenrpt_dev.columns:
        ax00.plot(data_tenrpt_dev['k_ts'], data_tenrpt_dev['settingVoltMin'], label=None, linestyle='--', color='r')
    for ano_state in ["自动阳极降", "自动阳极升", "手动阳极降", "手动阳极升", ]:
        _x = data_tenrpt_dev[data_tenrpt_dev['andoeMoveState_zh'].str.contains(ano_state, na=False)][['k_ts']].values
        _y = data_tenrpt_dev[data_tenrpt_dev['andoeMoveState_zh'].str.contains(ano_state, na=False)]['potVolt'].values
        ax00.scatter(x=_x, y=_y, marker=anode_state_map[ano_state]['marker'], c=anode_state_map[ano_state]['color'],
                     s=100)

    # 不使用新的库，仅加上文字信息
    for event in ['换极', '出铝', '抬母线', '纯手动', '效应']:
        _x, _y, _text = get_special_state_text(data_tenrpt_dev, event)
        # logger.info(f'{_x},{_y},{_text}')
        for i in range(len(_x)):
            ax00.text(_x[i], _y[i], event, color='k', fontsize=12, ha='center', va='bottom', rotation=0)
        # ax00.scatter(x=_x,y=_y,marker='o',c='k',text=event,s=100)

    # ax00.set_title('工作电压及上下限')
    ax00.set_ylabel('电压(mV)')
    ax00.set_ylim(feature_dict['电压'][0], feature_dict['电压'][1])
    ax00.legend(loc='upper left', fontsize=16)
    ax00.grid(True)
    logger.info("DEBUG22 ++=================================")
    logger.info(data_anode_dev.head(2))
    logger.info("++++++++++++++++++++++================================")
    # （0,1）子图：双Y轴，左Y轴：基准下料间隔，实际下料间隔，右Y轴：针振、摆动
    ax01 = axes[0, 1]
    ax01_2 = ax01.twinx()
    if 'baseFeedingInter' in data_tenrpt_dev.columns:
        ax01.plot(data_tenrpt_dev['k_ts'].values, data_tenrpt_dev['baseFeedingInter'].values, label='基准下料间隔',
                  color='b')
    if 'actualFeedingInter' in data_tenrpt_dev.columns:
        ax01.plot(data_tenrpt_dev['k_ts'].values, data_tenrpt_dev['actualFeedingInter'].values, label='实际下料间隔',
                  color='orange', drawstyle='steps-pre')
    if 'fluctDelta' in data_tenrpt_dev.columns:
        ax01_2.plot(data_tenrpt_dev['k_ts'].values, data_tenrpt_dev['fluctDelta'].values, label='针振', color='m')
    if 'wavingDelta' in data_tenrpt_dev.columns:
        ax01_2.plot(data_tenrpt_dev['k_ts'].values, data_tenrpt_dev['wavingDelta'].values, label='摆动', color='y')

    for event in ['氟盐下料']:
        _x, _y, _text = get_special_state_text(data_tenrpt_dev, event)
        # logger.info(f'{_x},{_y},{_text}')
        for i in range(len(_x)):
            ax01_2.text(_x[i], _y[i], 'F', color='r', fontsize=12, ha='center', va='bottom', rotation=0)

    # ax01.set_title('下料间隔/针振/摆动')
    ax01.set_ylabel('下料间隔(ms)')
    ax01.set_ylim(feature_dict['下料间隔'][0], feature_dict['下料间隔'][1])
    ax01_2.set_ylabel('针振/摆动')
    ax01_2.set_ylim(feature_dict['针振&摆动'][0], feature_dict['针振&摆动'][1])
    # 将图例设置为横向排布
    ax01.legend(loc='upper left', fontsize=16, )
    ax01_2.legend(loc='upper right', fontsize=16, )
    ax01.grid(True)

    k_device = data_tenrpt["k_device"].values[0]
    k_ts = pd.to_datetime(data_tenrpt["k_ts"].values[0]).strftime('%Y%m%d')
    str_title = f'{k_device}_{k_ts}_阳极电流'
    fig.suptitle(f'{str_title}', fontsize=20)
    plt.tight_layout(pad=1, w_pad=0.2, h_pad=0.01, rect=[0, 0, 1, 0.97])

    # 确保图片保存目录存在
    save_dir = f'./fig/铝一1分厂/阳极电流图/{k_device}'
    os.makedirs(save_dir, exist_ok=True)
    save_path = f'{save_dir}/{str_title}.png'
    plt.savefig(save_path)
    logger.info(f'阳极电流图片已保存: {save_path}')
    plt.close(fig)  # 关闭图形释放内存
