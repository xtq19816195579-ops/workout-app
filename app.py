import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ---------- 配置 ----------
DATA_FILE = "workout_log.csv"

# 训练部位与动作库
BODY_PARTS = {
    "胸部": ["杠铃卧推", "上斜卧推", "哑铃飞鸟", "器械卧推", "夹胸", "俯卧撑"],
    "肩部": ["哑铃推举", "杠铃推举", "侧平举", "前平举", "面拉", "蝴蝶机反向飞鸟"],
    "背部": ["引体向上", "杠铃划船", "哑铃划船", "高位下拉", "坐姿划船", "硬拉"],
    "二头": ["杠铃弯举", "哑铃弯举", "锤式弯举", "集中弯举", "牧师凳弯举"],
    "三头": ["窄距卧推", "绳索下压", "哑铃臂屈伸", "双杠臂屈伸", "俯身臂屈伸"],
    "腹部": ["卷腹", "平板支撑", "仰卧抬腿", "俄罗斯转体", "悬垂举腿", "健腹轮"],
    "腿部": ["深蹲", "腿举", "腿弯举", "腿屈伸", "箭步蹲", "罗马尼亚硬拉"],
    "全身/其他": ["波比跳", "壶铃摆荡", "战绳", "有氧跑步", "跳绳"]
}

# ---------- 初始化数据文件 ----------
if not os.path.exists(DATA_FILE):
    df_init = pd.DataFrame(columns=["日期", "部位", "动作", "组数", "每组详情", "记录时间"])
    df_init.to_csv(DATA_FILE, index=False)

# ---------- 页面布局 ----------
st.set_page_config(page_title="个人训练日志", page_icon="💪")
st.title("💪 量化训练日志")

# --- 第一步：多选训练部位 ---
st.markdown("### 1️⃣ 选择训练部位（可多选）")
selected_parts = st.multiselect(
    "今天练哪些部位？",
    options=list(BODY_PARTS.keys()),
    default=[]
)

# --- 第二步：根据选中的部位，分别显示动作多选 ---
all_selected_exercises = []  # 存储 (部位, 动作) 对

if selected_parts:
    st.markdown("### 2️⃣ 勾选每个部位的具体动作")
    for part in selected_parts:
        with st.container():
            st.markdown(f"**🏷️ {part}**")
            exercises = BODY_PARTS[part]
            chosen = st.multiselect(
                f"选择「{part}」的动作",
                options=exercises,
                key=f"multiselect_{part}"
            )
            for exercise in chosen:
                all_selected_exercises.append((part, exercise))

# --- 第三步：动态表单（为所有选中的动作填写详情）---
training_data = []
if all_selected_exercises:
    st.markdown("### 3️⃣ 填写每组详情（次数 × 重量）")
    for part, exercise in all_selected_exercises:
        with st.container():
            st.subheader(f"🏋️ {part} - {exercise}")
            sets = st.number_input(
                f"{part}_{exercise} - 组数",
                min_value=0, max_value=20, value=3, step=1,
                key=f"{part}_{exercise}_sets"
            )
            details = []
            for s in range(int(sets)):
                col1, col2 = st.columns(2)
                with col1:
                    reps = st.number_input(
                        f"第{s+1}组 次数", min_value=0, value=10, step=1,
                        key=f"{part}_{exercise}_{s}_reps"
                    )
                with col2:
                    weight = st.number_input(
                        f"第{s+1}组 重量(kg)", min_value=0.0, value=20.0, step=2.5,
                        key=f"{part}_{exercise}_{s}_weight"
                    )
                details.append(f"{reps}次×{weight}kg")
            training_data.append({
                "部位": part,
                "动作": exercise,
                "组数": sets,
                "每组详情": "; ".join(details)
            })

# --- 第四步：保存按钮 ---
if st.button("📥 保存训练记录", type="primary", use_container_width=True):
    if not training_data:
        st.warning("请先选择部位和动作，并填写详情")
    else:
        today_str = datetime.now().strftime("%Y-%m-%d")
        now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows = []
        for item in training_data:
            rows.append({
                "日期": today_str,
                "部位": item["部位"],
                "动作": item["动作"],
                "组数": item["组数"],
                "每组详情": item["每组详情"],
                "记录时间": now_time
            })
        df_new = pd.DataFrame(rows)
        df_old = pd.read_csv(DATA_FILE)
        df_all = pd.concat([df_old, df_new], ignore_index=True)
        df_all.to_csv(DATA_FILE, index=False)
        st.success("训练记录已保存！")
        st.balloons()

# --- 今日记录预览 ---
st.markdown("---")
st.subheader("📋 今日训练记录")
try:
    df_log = pd.read_csv(DATA_FILE)
    today = datetime.now().strftime("%Y-%m-%d")
    today_df = df_log[df_log["日期"] == today]
    if not today_df.empty:
        st.dataframe(today_df[["部位", "动作", "组数", "每组详情"]], use_container_width=True)
    else:
        st.info("今天还没有记录，练完记得保存哦。")
except:
    st.info("暂无数据")