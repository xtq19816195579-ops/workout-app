import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
import os
from github import Github, GithubException

# ---------- 页面配置 ----------
st.set_page_config(page_title="量化训练日志", page_icon="💪", layout="wide")

# ---------- GitHub 配置 ----------
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
REPO_NAME = "xtq19816195579-ops/workout-app"
FILE_PATH = "workout_log.csv"

# ---------- 训练部位与动作库 ----------
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

# ---------- 数据读取/保存（带缓存） ----------
@st.cache_data(ttl=30)
def load_data():
    if not GITHUB_TOKEN:
        return pd.DataFrame(columns=["日期", "部位", "动作", "组数", "每组详情", "记录时间"])
    g = Github(GITHUB_TOKEN)
    try:
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        csv_text = contents.decoded_content.decode('utf-8')
        df = pd.read_csv(pd.compat.StringIO(csv_text))
        return df
    except:
        return pd.DataFrame(columns=["日期", "部位", "动作", "组数", "每组详情", "记录时间"])

def save_data(df):
    if not GITHUB_TOKEN:
        st.error("未配置 GitHub Token，无法保存")
        return False
    g = Github(GITHUB_TOKEN)
    try:
        repo = g.get_repo(REPO_NAME)
        try:
            contents = repo.get_contents(FILE_PATH)
            repo.update_file(
                contents.path,
                f"训练记录更新 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                df.to_csv(index=False),
                contents.sha
            )
        except GithubException as e:
            if e.status == 404:
                repo.create_file(FILE_PATH, "初始化训练日志", df.to_csv(index=False))
            else:
                raise e
        st.cache_data.clear()  # 清除缓存，下次加载最新数据
        return True
    except Exception as e:
        st.error(f"保存失败: {e}")
        return False

# ---------- 日历生成相关函数 ----------
def get_month_calendar(year, month, trained_dates):
    """生成一个月的日历数据，标记每天状态"""
    cal = calendar.monthcalendar(year, month)
    today = date.today()
    # 状态: 0=未来/无记录(灰), 1=已训练(绿), 2=过去但未训练(红)
    month_days = []
    for week in cal:
        week_days = []
        for day in week:
            if day == 0:
                week_days.append({"day": 0, "status": -1, "date": None})
                continue
            current_date = date(year, month, day)
            if current_date > today:
                status = 0  # 未来
            elif current_date in trained_dates:
                status = 1  # 已训练
            else:
                status = 2  # 错过
            week_days.append({"day": day, "status": status, "date": current_date})
        month_days.append(week_days)
    return month_days

def render_calendar(year, month, trained_dates):
    """使用 HTML/CSS 渲染交互式日历"""
    cal_data = get_month_calendar(year, month, trained_dates)
    
    # CSS 样式
    st.markdown("""
    <style>
    .calendar { width: 100%; border-collapse: collapse; }
    .calendar th { text-align: center; padding: 8px; background: #f0f2f6; }
    .calendar td { padding: 0; text-align: center; vertical-align: middle; }
    .cal-day {
        display: block; width: 100%; height: 60px;
        line-height: 60px; border-radius: 10px;
        text-decoration: none; color: #333; font-weight: bold;
        border: 2px solid transparent; transition: 0.2s;
    }
    .cal-day:hover { border-color: #4a90e2; }
    .status-trained { background: #a5d6a5; }  /* 绿色 */
    .status-missed { background: #ef9a9a; }   /* 红色 */
    .status-future { background: #e0e0e0; }   /* 灰色 */
    .status-empty { background: transparent; }
    </style>
    """, unsafe_allow_html=True)

    # 构建 HTML 表格
    html = '<table class="calendar">'
    html += '<tr><th>月</th><th>二</th><th>三</th><th>四</th><th>五</th><th>六</th><th>日</th></tr>'
    for week in cal_data:
        html += '<tr>'
        for day_info in week:
            if day_info["day"] == 0:
                html += '<td></td>'
                continue
            day = day_info["day"]
            status = day_info["status"]
            date_str = day_info["date"].strftime("%Y-%m-%d") if day_info["date"] else ""
            if status == 1:
                css_class = "status-trained"
            elif status == 2:
                css_class = "status-missed"
            elif status == 0:
                css_class = "status-future"
            else:
                css_class = "status-empty"
            # 使用 Streamlit 的查询参数模拟点击，但更简单：用链接形式，但 st.markdown 不支持 JS。
            # 我们改用 form 提交或直接使用 st.button 网格，这里改为使用可点击的 div 配合 on_click 回调较难。
            # 最终方案：在日历下方放一个日期选择器，日历仅作可视化。
            html += f'<td><span class="cal-day {css_class}">{day}</span></td>'
        html += '</tr>'
    html += '</table>'
    st.markdown(html, unsafe_allow_html=True)

    # 日期选择器（用于查看详情）
    st.markdown("---")
    st.markdown("#### 点击下方选择日期查看详情")
    # 默认选今天，但不超过今天
    default_date = date.today()
    selected_date = st.date_input(
        "选择日期",
        value=default_date,
        min_value=date(year, month, 1),
        max_value=default_date,
        key="calendar_date_select"
    )
    return selected_date

# ---------- 主界面 ----------
st.title("💪 量化训练日志")

# 月份导航
col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    if st.button("◀ 上月"):
        if "view_month" not in st.session_state:
            st.session_state.view_month = date.today().month
        if "view_year" not in st.session_state:
            st.session_state.view_year = date.today().year
        if st.session_state.view_month == 1:
            st.session_state.view_month = 12
            st.session_state.view_year -= 1
        else:
            st.session_state.view_month -= 1
with col2:
    if "view_month" not in st.session_state:
        st.session_state.view_month = date.today().month
    if "view_year" not in st.session_state:
        st.session_state.view_year = date.today().year
    st.markdown(f"### {st.session_state.view_year} 年 {st.session_state.view_month} 月")
with col3:
    if st.button("下月 ▶"):
        if "view_month" not in st.session_state:
            st.session_state.view_month = date.today().month
        if "view_year" not in st.session_state:
            st.session_state.view_year = date.today().year
        if st.session_state.view_month == 12:
            st.session_state.view_month = 1
            st.session_state.view_year += 1
        else:
            st.session_state.view_month += 1

# 加载数据
df_all = load_data()
if not df_all.empty:
    df_all["日期"] = pd.to_datetime(df_all["日期"]).dt.date
    trained_dates = set(df_all["日期"].unique())
else:
    trained_dates = set()

# 获取当前展示的年月
year = st.session_state.get("view_year", date.today().year)
month = st.session_state.get("view_month", date.today().month)

# 渲染日历，并获取选中的日期
selected_date = render_calendar(year, month, trained_dates)

# 统计出勤天数
if not df_all.empty:
    month_mask = (df_all["日期"].apply(lambda d: d.year == year and d.month == month))
    attendance = df_all[month_mask]["日期"].nunique()
else:
    attendance = 0
days_in_month = calendar.monthrange(year, month)[1]
st.markdown(f"**本月出勤：{attendance} / {min(date.today().day, days_in_month) if year == date.today().year and month == date.today().month else days_in_month} 天**")

# ---------- 显示选中日期的详细记录 ----------
st.markdown("---")
st.subheader(f"📋 {selected_date} 训练详情")

# 从数据中筛选
if not df_all.empty:
    day_data = df_all[df_all["日期"] == selected_date]
else:
    day_data = pd.DataFrame()

if day_data.empty:
    st.info("该日无训练记录")
else:
    # 按部位分组
    for part in day_data["部位"].unique():
        with st.expander(f"🏷️ {part}", expanded=True):
            part_data = day_data[day_data["部位"] == part]
            for _, row in part_data.iterrows():
                st.markdown(f"**🏋️ {row['动作']}**  |  组数：{int(row['组数'])}")
                # 每组详情解析
                details = row["每组详情"]
                if details:
                    st.text(f"　{details.replace('; ', '\n　')}")
                st.markdown("---")

# ---------- 添加训练记录入口 ----------
with st.sidebar:
    st.header("📝 快速记录")
    selected_parts = st.multiselect("1️⃣ 选择部位", options=list(BODY_PARTS.keys()), key="record_parts")
    all_exercises = []
    if selected_parts:
        for part in selected_parts:
            exercises = BODY_PARTS[part]
            chosen = st.multiselect(f"「{part}」的动作", options=exercises, key=f"record_{part}")
            for ex in chosen:
                all_exercises.append((part, ex))
    training_data = []
    if all_exercises:
        st.markdown("### 填写详情")
        for part, exercise in all_exercises:
            with st.container():
                st.write(f"**{part} - {exercise}**")
                sets = st.number_input("组数", 0, 20, 3, key=f"set_{part}_{exercise}")
                details = []
                for s in range(int(sets)):
                    c1, c2 = st.columns(2)
                    with c1:
                        reps = st.number_input("次数", 0, 100, 10, key=f"rep_{part}_{exercise}_{s}")
                    with c2:
                        weight = st.number_input("重量kg", 0.0, 500.0, 20.0, 2.5, key=f"wt_{part}_{exercise}_{s}")
                    details.append(f"{reps}次×{weight}kg")
                training_data.append({
                    "部位": part,
                    "动作": exercise,
                    "组数": sets,
                    "每组详情": "; ".join(details)
                })
    if st.button("📥 保存训练记录", type="primary"):
        if not training_data:
            st.warning("请先选择部位和动作")
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
            new_df = pd.DataFrame(rows)
            df_old = load_data()
            df_combined = pd.concat([df_old, new_df], ignore_index=True)
            if save_data(df_combined):
                st.success("保存成功！")
                st.balloons()
                # 强制刷新数据缓存
                st.cache_data.clear()
