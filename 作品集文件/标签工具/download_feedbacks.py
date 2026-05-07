import streamlit as st
from datetime import datetime
from loguru import logger
import io


def download_feedback_records():
    """
    导出原始CSV数据 + 标记和反馈列
    """
    if 'original_data' not in st.session_state:
        st.warning('请上传数据')
        return

    # 获取原始完整数据（保留所有原始列）
    df = st.session_state.original_data.copy()
    mark_values = st.session_state.get('mark_values', {})
    feedback_values = st.session_state.get('feedback_values', {})

    # 添加标记和反馈列到原始数据末尾（"None"转为空字符串）
    df['标记'] = ['' if mark_values.get(i, '') in ('', 'None') else mark_values.get(i, '') for i in range(len(df))]
    df['反馈'] = [feedback_values.get(i, '') for i in range(len(df))]

    logger.info(f'导出数据，记录数：{len(df)}，列数：{len(df.columns)}')

    # 将完整数据转化为csv文件
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False, encoding='utf-8-sig')
    csv_bytes = buffer.getvalue()

    # 创建下载按钮
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"标注数据_{timestamp}.csv"

    st.download_button(
        label="📥 下载标注数据",
        data=csv_bytes,
        file_name=filename,
        mime='text/csv',
        key=f'download_feedback_{timestamp}'
    )

    # 统计有标记或反馈的记录数
    marked_count = ((df['标记'].str.strip() != '') | (df['反馈'].str.strip() != '')).sum()
