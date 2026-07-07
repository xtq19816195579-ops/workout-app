import streamlit as st
import pandas as pd
from datetime import datetime, date
import calendar
import json
from io import StringIO
from github import Github, GithubException

# ---------- 页面配置 ----------
st.set_page_config(page_title="量化训练日志", page_icon="💪", layout="wide")

# ---------- GitHub 配置 ----------
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
REPO_NAME = "xtq19816195579-ops/workout-app"
DATA_FILE = "workout_log.csv"
STATUS_FILE = "training_status.json"
PROFILE_FILE = "user_profile.json"

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

# ---------- 通用文件读写 ----------
def github_read(filepath):
    if not GITHUB_TOKEN:
        return None
    g = Github(GITHUB_TOKEN)
    try:
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(filepath)
        return contents.decoded_content.decode('utf-8')
    except:
        return None

def github_write(filepath, content_str, commit_msg):
    if not GITHUB_TOKEN:
        return False
    g = Github(GITHUB_TOKEN)
    try:
        repo = g.get_repo(REPO_NAME)
        try:
            contents = repo.get_contents(filepath)
            repo.update_file(filepath, commit_msg, content_str, contents.sha)
        except GithubException as e:
            if e.status == 404:
                repo.create_file(filepath, commit_msg, content_str)
            else:
                raise e
        return True
    except Exception as e:
        st.error(f"写入失败: {e}")
        return False

def github_delete(filepath, commit_msg):
    if not GITHUB_TOKEN:
        return False
    g = Github(GITHUB_TOKEN)
    try:
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(filepath)
        repo.delete_file(filepath, commit_msg, contents.sha)
        return True
    except:
        return False

# ---------- 训练状态管理（包含草稿、计时）----------
def load_training_status():
    raw = github_read(STATUS_FILE)
    if raw:
        try:
            return json.loads(raw)
        except:
            pass
    return None

def save_training_status(status_dict):
    github_write(STATUS_FILE, json.dumps(status_dict), "更新训练状态")

def clear_training_status():
    github_delete(STATUS_FILE, "清除训练状态")

# ---------- 用户配置 ----------
def load_profile():
    raw = github_read(PROFILE_FILE)
    if raw:
        try:
            return json.loads(raw)
        except:
            pass
    return {"weight": 70, "height": 175}

def save_profile(profile):
    github_write(PROFILE_FILE, json.dumps(profile), "更新个人设置")

# ---------- 训练数据读取/保存 ----------
@st.cache_data(ttl=30)
def load_data():
    if not GITHUB_TOKEN:
        return pd.DataFrame(columns=["日期", "部位", "动作", "组数", "每组详情", "记录时间", "实际时长(分钟)"])
    g = Github(GITHUB_TOKEN)
    try:
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(DATA_FILE)
        csv_text = contents.decoded_content.decode('utf-8')
        df = pd.read_csv(StringIO(csv_text))
        if "实际时长(分钟)" not in df.columns:
            df["实际时长(分钟)"] = None
        return df
    except:
        return pd.DataFrame(columns=["日期", "部位", "动作", "组数", "每组详情", "记录时间", "实际时长(分钟)"])

def save_data(df):
    if not GITHUB_TOKEN:
        st.error("未配置 GitHub Token，无法保存")
        return False
    return github_write(DATA_FILE, df.to_csv(index=False), f"训练记录更新 {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# ---------- 组数合并 ----------
def compress_details(detail_str):
    if pd.isna(detail_str) or detail_str.strip() == "":
        return ""
    groups = detail_str.split('; ')
    order_map = {}
    count_map = {}
    for idx, g in enumerate(groups):
        try:
            reps, weight = g.split('次×')
            weight = weight.rstrip('kg')
        except:
            return detail_str
        key = (reps, weight)
        if key not in order_map:
            order_map[key] = idx
            count_map[key] = 0
        count_map[key] += 1
    sorted_keys = sorted(order_map.keys(), key=lambda k: order_map[k])
    lines = []
    for reps, weight in sorted_keys:
        cnt = count_map[(reps, weight)]
        if cnt == 1:
            lines.append(f"1组×{reps}次×{weight}kg")
        else:
            lines.append(f"{cnt}组×{reps}次×{weight}kg")
    return '\n'.join(lines)

# ---------- 日历 ----------
def get_month_calendar(year, month, trained_dates):
    cal = calendar.monthcalendar(year, month)
    today = date.today()
    month_days = []
    for week in cal:
        week_days = []
        for day in week:
            if day == 0:
                week_days.append({"day": 0, "status": -1, "date": None})
                continue
            current_date = date(year, month, day)
            if current_date > today:
                status = 0
            elif current_date in trained_dates:
                status = 1
            else:
                status = 2
            week_days.append({"day": day, "status": status, "date": current_date})
        month_days.append(week_days)
    return month_days

def render_calendar(year, month, trained_dates):
    cal_data = get_month_calendar(year, month, trained_dates)
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
    .status-trained { background: #a5d6a5; }
    .status-missed { background: #ef9a9a; }
    .status-future { background: #e0e0e0; }
    .status-empty { background: transparent; }
    </style>
    """, unsafe_allow_html=True)

    html = '<table class="calendar">'
    html += '<tr><th>一</th><th>二</th><th>三</th><th>四</th><th>五</th><th>六</th><th>日</th></tr>'
    for week in cal_data:
        html += '<tr>'
        for day_info in week:
            if day_info["day"] == 0:
                html += '<td></td>'
                continue
            day = day_info["day"]
            status = day_info["status"]
            if status == 1:
                css_class = "status-trained"
            elif status == 2:
                css_class = "status-missed"
            elif status == 0:
                css_class = "status-future"
            else:
                css_class = "status-empty"
            html += f'<td><span class="cal-day {css_class}">{day}</span></td>'
        html += '</tr>'
    html += '</table>'
    st.markdown(html, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 选择日期查看详情")
    default_date = date.today()
    selected_date = st.date_input(
        "选择日期",
        value=default_date,
        min_value=date(year, month, 1),
        max_value=default_date,
        key="calendar_date_select"
    )
    return selected_date

# ---------- 读取当前表单值（用于保存草稿）----------
def collect_form_state():
    """遍历 session_state 中与记录相关的 key，收集当前填写的动作详情"""
    form = {"selected_parts": [], "exercises": {}}
    if "record_parts" in st.session_state:
        form["selected_parts"] = st.session_state.record_parts
    for part in BODY_PARTS:
        key = f"record_{part}"
        if key in st.session_state and st.session_state[key]:
            form["exercises"][part] = st.session_state[key]
    # 保存具体的组数、次数、重量（通过遍历所有可能 key）
    details = {}
    for part in BODY_PARTS:
        for ex in BODY_PARTS[part]:
            set_key = f"set_{part}_{ex}"
            if set_key in st.session_state:
                sets = st.session_state[set_key]
                details[f"set_{part}_{ex}"] = sets
                for s in range(sets):
                    rep_key = f"rep_{part}_{ex}_{s}"
                    wt_key = f"wt_{part}_{ex}_{s}"
                    if rep_key in st.session_state:
                        details[rep_key] = st.session_state[rep_key]
                    if wt_key in st.session_state:
                        details[wt_key] = st.session_state[wt_key]
    return {
        "selected_parts": form["selected_parts"],
        "exercises": form["exercises"],
        "details": details
    }

def restore_form_state(draft):
    """根据草稿恢复 session_state 中的表单值"""
    if not draft:
        return
    # 恢复选中的部位
    if "selected_parts" in draft:
        st.session_state.record_parts = draft["selected_parts"]
    # 恢复每个部位选中的动作
    if "exercises" in draft:
        for part, ex_list in draft["exercises"].items():
            st.session_state[f"record_{part}"] = ex_list
    # 恢复具体数值
    if "details" in draft:
        for key, value in draft["details"].items():
            st.session_state[key] = value

# ---------- 主界面 ----------
st.title("💪 量化训练日志")

# ---------- 训练计时器与草稿恢复 ----------
st.markdown("---")
st.subheader("⏱️ 训练计时器")
status = load_training_status()
now = datetime.now()

# 自动清理超时状态（超过24小时视为无效，清除）
if status and status.get("start"):
    start = datetime.fromisoformat(status["start"])
    if (now - start).total_seconds() > 86400:
        clear_training_status()
        status = None

# 如果有草稿（训练已结束但未保存）或进行中的训练，提示用户
if status:
    if status.get("active"):
        # 训练进行中
        start = datetime.fromisoformat(status["start"])
        elapsed = now - start
        mins = int(elapsed.total_seconds() // 60)
        secs = int(elapsed.total_seconds() % 60)
        st.info(f"⏱️ 训练已进行：{mins} 分 {secs} 秒")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("⏹️ 结束训练并暂存草稿", key="end_training"):
                duration_min = round(elapsed.total_seconds() / 60, 1)
                # 保存草稿（当前表单内容 + 时长）
                draft = collect_form_state()
                new_status = {
                    "active": False,
                    "start": status["start"],
                    "end": now.isoformat(),
                    "actual_duration": duration_min,
                    "draft": draft
                }
                save_training_status(new_status)
                st.success(f"训练已结束，时长 {duration_min} 分钟，草稿已保存。请填写动作后保存记录。")
                st.rerun()
        with col2:
            if st.button("❌ 取消训练", key="cancel_training"):
                clear_training_status()
                st.warning("训练已取消，草稿已清除。")
                st.rerun()

    elif not status.get("active") and status.get("draft"):
        # 存在未保存的草稿（训练已结束）
        st.warning("📝 你有未保存的训练草稿（包含时长和动作详情）。")
        if st.button("📂 加载草稿"):
            restore_form_state(status["draft"])
            # 将草稿中的时长暂存到 session_state 供保存时使用
            st.session_state["actual_duration"] = status.get("actual_duration", 0)
            # 保留状态文件，但清除 draft 字段避免重复加载？保留以便再次加载
            # 我们仅恢复表单，不清除状态，保存时才清除
            st.rerun()
        if st.button("🗑️ 清除草稿"):
            clear_training_status()
            st.session_state.pop("actual_duration", None)
            st.rerun()

else:
    # 无任何状态，显示开始训练按钮
    if st.button("▶️ 开始训练", key="start_training"):
        save_training_status({"active": True, "start": now.isoformat()})
        st.rerun()

# ---------- 月份导航 ----------
st.markdown("---")
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

year = st.session_state.get("view_year", date.today().year)
month = st.session_state.get("view_month", date.today().month)

# 删除记录逻辑
if "delete_target" in st.session_state:
    target_time = st.session_state["delete_target"]
    mask = df_all["记录时间"] != target_time
    if mask.sum() < len(df_all):
        df_all = df_all[mask]
        if save_data(df_all):
            st.success("已删除该记录")
        else:
            st.error("删除失败，请重试")
            st.stop()
    del st.session_state["delete_target"]
    st.cache_data.clear()
    st.rerun()

selected_date = render_calendar(year, month, trained_dates)

# 出勤统计
if not df_all.empty:
    month_mask = df_all["日期"].apply(lambda d: d.year == year and d.month == month)
    attendance = df_all[month_mask]["日期"].nunique()
else:
    attendance = 0
days_in_month = calendar.monthrange(year, month)[1]
today_day = date.today().day if year == date.today().year and month == date.today().month else days_in_month
st.markdown(f"**本月出勤：{attendance} / {min(today_day, days_in_month)} 天**")

# 选中日期详细记录
st.markdown("---")
st.subheader(f"📋 {selected_date} 训练详情")
if not df_all.empty:
    day_data = df_all[df_all["日期"] == selected_date]
else:
    day_data = pd.DataFrame()

if day_data.empty:
    st.info("该日无训练记录")
else:
    for part in day_data["部位"].unique():
        with st.expander(f"🏷️ {part}", expanded=True):
            part_data = day_data[day_data["部位"] == part]
            for _, row in part_data.iterrows():
                st.markdown(f"**🏋️ {row['动作']}**  |  组数：{int(row['组数'])}")
                details = row["每组详情"]
                if details:
                    compressed = compress_details(details)
                    st.text(compressed)
                if st.button("🗑️ 删除本条", key=f"del_{row['记录时间']}_{row['动作']}"):
                    st.session_state["delete_target"] = row["记录时间"]
                    st.rerun()
                st.markdown("---")

# ---------- 侧边栏：快速记录 + 个人设置 ----------
with st.sidebar:
    with st.expander("⚙️ 个人设置", expanded=False):
        profile = load_profile()
        weight = st.number_input("体重 (kg)", min_value=30, max_value=200, value=profile.get("weight", 70), step=1, key="profile_weight")
        height = st.number_input("身高 (cm)", min_value=100, max_value=250, value=profile.get("height", 175), step=1, key="profile_height")
        if st.button("保存身体数据"):
            profile["weight"] = weight
            profile["height"] = height
            save_profile(profile)
            st.success("身体数据已保存")
        st.caption("保存一次即可，后续自动读取。")

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

        # 暂存草稿按钮
        if st.button("💾 暂存草稿"):
            draft = collect_form_state()
            status = load_training_status()
            if status is None:
                status = {"active": False}
            status["draft"] = draft
            # 如果已有 actual_duration 保留
            save_training_status(status)
            st.success("草稿已保存到云端，刷新页面后可加载。")

    # 显示当前训练时长（来自草稿恢复或刚结束训练）
    actual_duration = st.session_state.get("actual_duration", None)
    if actual_duration is not None:
        st.info(f"本次训练时长：{actual_duration} 分钟")
    else:
        # 检查状态文件中是否有未保存的时长
        status = load_training_status()
        if status and not status.get("active") and "actual_duration" in status:
            actual_duration = status["actual_duration"]
            st.session_state["actual_duration"] = actual_duration

    if st.button("📥 保存训练记录", type="primary"):
        if not training_data:
            st.warning("请先选择部位和动作")
        else:
            # 如果训练仍在进行中，先自动结束
            status_now = load_training_status()
            if status_now and status_now.get("active"):
                start_time = datetime.fromisoformat(status_now["start"])
                duration_min = round((datetime.now() - start_time).total_seconds() / 60, 1)
                actual_duration = duration_min
                st.session_state["actual_duration"] = duration_min
                # 结束状态
                status_now["active"] = False
                status_now["end"] = datetime.now().isoformat()
                status_now["actual_duration"] = duration_min
                status_now["draft"] = collect_form_state()
                save_training_status(status_now)

            actual_duration = st.session_state.get("actual_duration", 0.0)

            today_str = datetime.now().strftime("%Y-%m-%d")
            now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            rows = []
            for item in training_data:
                rows.append({
                    "日期": today_str,
                    "部位": item["部位"],
                    "动作": item["动作"],
                    "组数": item["组数"],
                    "每组详情": item["每组详情"],
                    "记录时间": now_time,
                    "实际时长(分钟)": actual_duration if actual_duration > 0 else None
                })
            new_df = pd.DataFrame(rows)
            df_old = load_data()
            df_combined = pd.concat([df_old, new_df], ignore_index=True)
            if save_data(df_combined):
                st.success("保存成功！")
                st.balloons()
                st.cache_data.clear()
                # 清除状态文件和 session_state 中的时长、草稿
                clear_training_status()
                if "actual_duration" in st.session_state:
                    del st.session_state["actual_duration"]
                st.rerun()
