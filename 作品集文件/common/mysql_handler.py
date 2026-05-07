import pandas as pd
import pymysql
import math
from loguru import logger

# 检查系统hostname
import socket

hostname = socket.gethostname()
logger.info(f"系统hostname: {hostname}")

import platform

system_name = platform.system()
if system_name.lower().startswith("win"):
    logger.info("当前操作系统为 Windows")
    db_info = {"database": "db_for_portfolio",
               "db_user": "root",
               "db_password": "385538",
               "db_url": "localhost",
               "db_port": 3306}
else:
    logger.info(f"当前操作系统为 {system_name}")
    db_info = {"database": "db_for_portfolio",
               "db_user": "root",
               "db_password": "385538",
               "db_url": "localhost",
               "db_port": 3306}

# 读取数据，返回DataFrame
def read_sql(sql):
    conn = pymysql.connect(
        database=db_info["database"],
        user=db_info["db_user"],
        password=db_info["db_password"],
        host=db_info["db_url"],
        port=db_info["db_port"]
    )

    try:
        cur = conn.cursor()
    except:
        logger.error("数据库登录失败!")

    df = pd.DataFrame()
    try:
        cur.execute(sql)
        desc = cur.description
        rows = cur.fetchall()
        df = pd.DataFrame(rows, columns=[x[0] for x in desc])
        conn.commit()
    except Exception as e:
        logger.error(f"数据读取失败，错误原因：{e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()
        return df

# 获取工艺图谱数据
def get_gongyirpt_range_data(k_device, st_date, ed_date):
    """
        从mysql数据库获取工艺报表数据

        参数:
            k_device: 设备号，如 '3101'
            st_date: 开始日期，格式 '2025-11-01'
            ed_date: 结束日期，格式 '2025-12-01'

        返回:
            pd.DataFrame: 包含工艺参数的数据框
        """
    import datetime

    # 确保k_device是字符串格式
    k_device = str(k_device)

    # 转换日期格式：从 'YYYY-MM-DD' 到 'YYYY-MM-DD HH:MM:SS'
    # 将日期字符串转换为 datetime 对象，再减去 30 天
    st_datetime = datetime.datetime.strptime(st_date, "%Y-%m-%d") - datetime.timedelta(days=30)
    start_time = st_datetime.strftime("%Y-%m-%d %H:%M:%S")
    end_time = f"{ed_date} 23:59:59"

    logger.info(f"开始从K2获取{k_device}的天级数据，时间范围：{start_time} ~ {end_time}")

    query_sql = f"""SELECT * FROM dwd_daily_para
                WHERE k_device = '{k_device}' and k_ts between '{start_time}' and '{end_time}'
                ORDER BY k_ts asc, k_device asc"""
    logger.info(query_sql)
    df = read_sql(sql=query_sql)
    num_col_list = df.columns.drop(['k_ts', 'k_device'], errors='ignore')
    df[num_col_list] = df[num_col_list].apply(pd.to_numeric, errors='coerce')

    return df

# 获取实时数据
def get_tenrpt_data(k_device, st_date, ed_date):
    """
        从mysql数据库获取各工区2分钟级实时数据

        参数:
            k_device: 设备号，如 '3101'
            st_date: 开始日期，格式 '2025-11-01'
            ed_date: 结束日期，格式 '2025-12-01'

        返回:
            pd.DataFrame: 包含工艺参数的数据框
        """
    import datetime

    k_device = str(k_device)

    # 转换日期格式：从'YYYY-MM-DD' 到 'YYYY-MM-DD HH:MM:SS'
    prev_date = (datetime.datetime.strptime(ed_date, '%Y-%m-%d') - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    start_time = f'{prev_date} 23:00:00'
    end_time = f'{ed_date} 23:59:59'

    logger.info(f'开始从K2获取{k_device}{k_device[1]}工区的2分钟级实时数据， 时间范围:{start_time} ~ {end_time}')

    query_sql = f"""SELECT * FROM dwd_realtime_2t
                    WHERE k_device = '{k_device}' and k_ts between '{start_time}' and '{end_time}'
                    ORDER BY k_ts asc, k_device asc"""
    logger.info(query_sql)
    df = read_sql(sql=query_sql)
    num_col_list = df.columns.drop(['k_ts', 'k_device'], errors='ignore')
    df[num_col_list] = df[num_col_list].apply(pd.to_numeric, errors='coerce')

    return df














