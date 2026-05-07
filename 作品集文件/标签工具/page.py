import sys
import os

# 添加当前目录到路径以支持导入
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)


from data_process import *
from download_feedbacks import download_feedback_records


def main():
    """
    主函数

    输入：无
    输出：无
    功能：主入口函数，根据用户选择渲染不同的工具界面
    """
    col1, col2 = st.columns([3, 1])

    with col1:
        st.title("📋 数据记录")

        st.caption("""
        ❗ Reminders:
        1. 确认上传的CSV文件格式，前三列严格按照“k_device”、“k_ts”、“k_model”顺序排列；
        2. 完成“标记”和“反馈”后，务必点击“提交”按钮，以防下载的反馈记录不完整。
        """)

    # 下载按钮在右侧
    with col2:
        if st.button('完成反馈并下载反馈记录', type='primary', use_container_width=True):
            download_feedback_records()

    # 使用session state避免重复创建，但保持组件可见
    if 'data_source_value' not in st.session_state:
        st.session_state.data_source_value = '离线文件'

    # 调用 load_data_for_analysis()，内部会渲染交互表格
    # 返回值为数据源类型（'离线文件' 或 '实时数据'）
    data_source_type = load_data_for_analysis()

    # 显示选中行的槽控曲线图表
    # show_selected_dialog(raw_idx)

    # 根据数据源类型显示提示信息
    if data_source_type == '离线文件':
        # 检查是否有数据已加载
        if 'raw_data' in st.session_state:
            count = len(st.session_state.raw_data)
            st.caption(f'离线文件共{count}条记录')
        else:
            st.caption('请上传CSV数据文件')
    else:  # 实时数据
        st.caption('实时数据共0条记录')  # 临时显示

    st.divider()

if __name__ == "__main__":
    st.set_page_config(page_title="电解槽数据分析反馈系统", page_icon=":material/home:", layout="wide")
    main()
else:
    main()