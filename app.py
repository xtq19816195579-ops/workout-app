import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
from supabase import create_client, Client
import streamlit_cookies_controller as cookies

# -------------------- 初始化与配置 --------------------
st.set_page_config(page_title="量化训练日志", page_icon="💪", layout="wide")

cookie_manager = cookies.CookieController()

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]

# 仅使用匿名客户端，所有操作通过用户 Token 进行 RLS 控制
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# -------------------- 数据表结构（供参考） --------------------
# profiles 表需有 user_id (uuid, unique), weight (float4), height (float4)
# user_push_settings 表需有 user_id (uuid, unique), pushplus_token (text), is_enabled (bool, default true)
# 请确保已执行 RLS 策略：
#   ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
#   CREATE POLICY "..." ON profiles FOR ... USING (auth.uid() = user_id);
#   同理 user_push_settings 也需开启 RLS。

# -------------------- 动作库 --------------------
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

EXERCISE_TYPE = {}
for part, exercises in BODY_PARTS.items():
    for ex in exercises:
        if ex in ["有氧跑步", "跳绳", "波比跳", "壶铃摆荡", "战绳"]:
            EXERCISE_TYPE[ex] = "cardio"
        else:
            EXERCISE_TYPE[ex] = "strength"

CARDIO_MET_OPTIONS = {
    "跑步 (8 km/h)": 8.0, "跑步 (10 km/h)": 10.0, "慢跑": 7.0,
    "跳绳 (中速)": 10.0, "跳绳 (快速)": 12.0, "游泳 (自由泳)": 8.0,
    "游泳 (蛙泳)": 7.0, "骑行 (中等)": 6.0, "椭圆机": 5.0,
    "划船机": 7.0, "高强度间歇训练": 12.0, "自定义": None
}

# -------------------- 认证与持久化 --------------------
def restore_session():
    refresh_token = cookie_manager.get('refresh_token')
    if refresh_token:
        try:
            res = supabase.auth.sign_in_with_refresh_token(refresh_token)
            st.session_state.user = res.user
            st.session_state.access_token = res.session.access_token
            supabase.postgrest.auth(res.session.access_token)
            cookie_manager.set('refresh_token', res.session.refresh_token,
                               max_age=30 * 24 * 60 * 60, path='/')
            return True
        except:
            cookie_manager.remove('refresh_token', path='/')
    return False

def login_page():
    st.title("欢迎使用量化训练日志")
    menu = st.radio("选择操作", ["登录", "注册"])
    email = st.text_input("邮箱")
    password = st.text_input("密码", type="password")

    if menu == "登录":
        if st.button("登录"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                if not res.user.confirmed_at:
                    st.warning("您的邮箱尚未确认，请检查邮件并点击确认链接。")
                else:
                    st.session_state.user = res.user
                    st.session_state.access_token = res.session.access_token
                    supabase.postgrest.auth(res.session.access_token)
                    cookie_manager.set('refresh_token', res.session.refresh_token,
                                       max_age=30*24*60*60, path='/')
                    st.rerun()
            except Exception as e:
                st.error("登录失败：" + str(e))
    else:
        if st.button("注册"):
            try:
                res = supabase.auth.sign_up({"email": email, "password": password})
                if res.user:
                    st.success(f"注册成功！验证邮件已发送至 {email}，请点击确认链接后登录。")
                else:
                    st.error("注册失败，请稍后重试。")
            except Exception as e:
                st.error("注册失败：" + str(e))

# -------------------- 主程序 --------------------
if "user" not in st.session_state:
    if not restore_session():
        login_page()
        st.stop()

user = st.session_state.user
# 确保 token 绑定
if "access_token" in st.session_state:
    supabase.postgrest.auth(st.session_state.access_token)

# -------------------- 侧边栏 --------------------
with st.sidebar:
    st.write(f"👤 {user.email}")
    if st.button("退出登录"):
        supabase.auth.sign_out()
        supabase.postgrest.auth(None)
        cookie_manager.remove('refresh_token', path='/')
        for key in ["user", "access_token"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    # 个人设置（使用用户 Token）
    with st.expander("⚙️ 个人设置", expanded=False):
        # 读取当前用户的身体数据
        try:
            profile_res = supabase.table("profiles").select("weight", "height").eq("user_id", user.id).execute()
            if profile_res.data:
                profile = profile_res.data[0]
            else:
                profile = {"weight": 70, "height": 175}
        except Exception as e:
            st.error(f"读取身体数据失败：{e}")
            profile = {"weight": 70, "height": 175}

        weight = st.number_input("体重 (kg)", min_value=30.0, max_value=200.0,
                                 value=float(profile.get("weight", 70.0)), step=1.0, key="profile_weight")
        height = st.number_input("身高 (cm)", min_value=100, max_value=250,
                                 value=int(profile.get("height", 175)), step=1, key="profile_height")
        if st.button("保存身体数据"):
            try:
                data = {"user_id": user.id, "weight": weight, "height": height}
                supabase.table("profiles").upsert(data).execute()
                st.success("身体数据已保存")
                st.rerun()   # 刷新显示最新值
            except Exception as e:
                st.error(f"保存失败：{e}")

    # 推送设置（多用户推送）
    with st.expander("📲 微信推送设置", expanded=False):
        try:
            # 读取当前用户的推送设置
            push_res = supabase.table("user_push_settings").select("pushplus_token", "is_enabled").eq("user_id", user.id).execute()
            if push_res.data:
                push_data = push_res.data[0]
                current_token = push_data.get("pushplus_token", "")
                is_enabled = push_data.get("is_enabled", True)
            else:
                current_token = ""
                is_enabled = True
        except Exception as e:
            st.error(f"读取推送设置失败：{e}")
            current_token = ""
            is_enabled = True

        new_token = st.text_input("PushPlus Token", value=current_token, placeholder="请前往 pushplus.plus 获取", key="push_token_input")
        enabled = st.checkbox("开启每日推送", value=is_enabled, key="push_enabled")
        if st.button("保存推送设置"):
            try:
                data = {
                    "user_id": user.id,
                    "pushplus_token": new_token.strip(),
                    "is_enabled": enabled
                }
                supabase.table("user_push_settings").upsert(data).execute()
                st.success("推送设置已保存")
                st.rerun()
            except Exception as e:
                st.error(f"保存推送设置失败：{e}")

    # 数据导出
    with st.expander("📤 导出数据", expanded=False):
        if st.button("导出我的训练数据 (CSV)"):
            try:
                data = supabase.table("workouts").select("*").eq("user_id", user.id).execute()
                if data.data:
                    df = pd.DataFrame(data.data)
                    csv = df.to_csv(index=False)
                    st.download_button("点击下载", data=csv, file_name=f"my_workouts_{date.today()}.csv", mime="text/csv")
                else:
                    st.info("暂无数据可导出")
            except Exception as e:
                st.error(f"导出失败：{e}")

    # 训练记录表单（在侧边栏，使用 session_state 持久化）
    st.header("📝 快速记录")
    # 为了保留表单数据，所有控件 key 必须固定
    if "record_parts" not in st.session_state:
        st.session_state.record_parts = []
    selected_parts = st.multiselect("1️⃣ 选择部位", options=list(BODY_PARTS.keys()), key="record_parts")
    if selected_parts:
        for part in selected_parts:
            part_key = f"record_{part}"
            if part_key not in st.session_state:
                st.session_state[part_key] = []
            st.multiselect(f"「{part}」的动作", options=BODY_PARTS[part], key=part_key)
    all_exercises = []
    for part in selected_parts:
        for ex in st.session_state.get(f"record_{part}", []):
            all_exercises.append((part, ex))
    training_data = []
    if all_exercises:
        st.markdown("### 填写详情")
        for part, exercise in all_exercises:
            ex_type = EXERCISE_TYPE.get(exercise, "strength")
            with st.container():
                st.write(f"**{part} - {exercise}**")
                if ex_type == "strength":
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
                        "date": date.today().isoformat(),
                        "body_part": part,
                        "exercise": exercise,
                        "set_count": sets,
                        "details": "; ".join(details),
                        "cardio_duration": None,
                        "met_value": None
                    })
                else:
                    duration = st.number_input("时长 (分钟)", 0, 300, 30, key=f"cardio_dur_{part}_{exercise}")
                    met_option = st.selectbox("强度 (MET)", options=list(CARDIO_MET_OPTIONS.keys()), key=f"cardio_met_{part}_{exercise}")
                    if met_option == "自定义":
                        met_val = st.number_input("输入 MET 值", 0.0, 20.0, 8.0, key=f"cardio_met_val_{part}_{exercise}")
                    else:
                        met_val = CARDIO_MET_OPTIONS[met_option]
                    training_data.append({
                        "date": date.today().isoformat(),
                        "body_part": part,
                        "exercise": exercise,
                        "set_count": 0,
                        "details": "",
                        "cardio_duration": duration,
                        "met_value": met_val
                    })
    if st.button("📥 保存训练记录", type="primary"):
        if not training_data:
            st.warning("请先选择部位和动作")
        else:
            for record in training_data:
                try:
                    record["user_id"] = user.id
                    supabase.table("workouts").insert(record).execute()
                except Exception as e:
                    st.error(f"保存失败：{e}")
                    break
            else:
                st.success("保存成功！")
                st.balloons()
                st.rerun()

# -------------------- 主界面 --------------------
st.title("💪 量化训练日志")

# 计时器（保留 session_state，不重置表单）
st.markdown("---")
st.subheader("⏱️ 训练计时器")
if "timer_start" not in st.session_state:
    st.session_state.timer_start = None

now = datetime.now()
if st.session_state.timer_start is None:
    if st.button("▶️ 开始训练"):
        st.session_state.timer_start = now
        st.rerun()
else:
    elapsed = now - st.session_state.timer_start
    mins = int(elapsed.total_seconds() // 60)
    secs = int(elapsed.total_seconds() % 60)
    st.info(f"⏱️ 训练已进行：{mins} 分 {secs} 秒")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⏹️ 结束训练并保存时长"):
            duration_min = round(elapsed.total_seconds() / 60, 1)
            try:
                supabase.table("training_durations").insert({
                    "user_id": user.id,
                    "date": date.today().isoformat(),
                    "start_time": st.session_state.timer_start.isoformat(),
                    "end_time": now.isoformat(),
                    "duration_min": duration_min
                }).execute()
                st.success(f"训练时长 {duration_min} 分钟已保存。")
                st.session_state.timer_start = None
                st.rerun()
            except Exception as e:
                st.error(f"保存时长失败：{e}")
    with col2:
        if st.button("❌ 取消训练"):
            st.session_state.timer_start = None
            st.warning("训练已取消，时长不会保存。")
            st.rerun()

# 日历与数据展示
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
if "view_month" not in st.session_state:
    st.session_state.view_month = date.today().month
if "view_year" not in st.session_state:
    st.session_state.view_year = date.today().year
with col1:
    if st.button("◀ 上月"):
        if st.session_state.view_month == 1:
            st.session_state.view_month = 12
            st.session_state.view_year -= 1
        else:
            st.session_state.view_month -= 1
with col2:
    st.markdown(f"### {st.session_state.view_year} 年 {st.session_state.view_month} 月")
with col3:
    if st.button("下月 ▶"):
        if st.session_state.view_month == 12:
            st.session_state.view_month = 1
            st.session_state.view_year += 1
        else:
            st.session_state.view_month += 1

# 加载数据（自动过滤当前用户）
def load_all_workouts():
    try:
        res = supabase.table("workouts").select("*").eq("user_id", user.id).execute()
        return res.data
    except Exception as e:
        st.error(f"加载训练记录失败：{e}")
        return []

all_workouts = load_all_workouts()
df_all = pd.DataFrame(all_workouts)
if not df_all.empty:
    df_all["date"] = pd.to_datetime(df_all["date"]).dt.date
    trained_dates = set(df_all["date"].unique())
else:
    trained_dates = set()

year = st.session_state.view_year
month = st.session_state.view_month

# 删除处理
if "delete_id" in st.session_state:
    delete_id = st.session_state.delete_id
    supabase.table("workouts").delete().eq("id", delete_id).execute()
    st.success("已删除")
    del st.session_state["delete_id"]
    st.rerun()

# 渲染日历
def render_calendar(year, month, trained_dates):
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
    for week in month_days:
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
    selected_date = st.date_input("选择日期", value=default_date,
                                  min_value=date(year, month, 1),
                                  max_value=default_date, key="calendar_date_select")
    return selected_date

selected_date = render_calendar(year, month, trained_dates)

if not df_all.empty:
    month_mask = df_all["date"].apply(lambda d: d.year == year and d.month == month)
    attendance = df_all[month_mask]["date"].nunique()
else:
    attendance = 0
days_in_month = calendar.monthrange(year, month)[1]
today_day = date.today().day if year == date.today().year and month == date.today().month else days_in_month
st.markdown(f"**本月出勤：{attendance} / {min(today_day, days_in_month)} 天**")

st.markdown("---")
st.subheader(f"📋 {selected_date} 训练详情")
day_data = df_all[df_all["date"] == selected_date] if not df_all.empty else pd.DataFrame()
if day_data.empty:
    st.info("该日无训练记录")
else:
    # 合并显示
    for _, row in day_data.iterrows():
        ex_type = EXERCISE_TYPE.get(row["exercise"], "strength")
        with st.expander(f"🏷️ {row['body_part']} - {row['exercise']}", expanded=True):
            if ex_type == "strength":
                st.write(f"组数：{int(row['set_count'])}")
                if row["details"]:
                    # 压缩显示
                    detail_str = row["details"]
                    groups = detail_str.split('; ')
                    order_map = {}
                    count_map = {}
                    for idx, g in enumerate(groups):
                        try:
                            reps, weight = g.split('次×')
                            weight = weight.rstrip('kg')
                        except:
                            st.text(detail_str)
                            break
                        key = (reps, weight)
                        if key not in order_map:
                            order_map[key] = idx
                            count_map[key] = 0
                        count_map[key] += 1
                    else:
                        sorted_keys = sorted(order_map.keys(), key=lambda k: order_map[k])
                        lines = []
                        for reps, weight in sorted_keys:
                            cnt = count_map[(reps, weight)]
                            lines.append(f"{cnt}组×{reps}次×{weight}kg" if cnt > 1 else f"1组×{reps}次×{weight}kg")
                        st.text('\n'.join(lines))
            else:
                st.write(f"时长：{row['cardio_duration']} 分钟，MET：{row['met_value']}")
            if st.button("🗑️ 删除本条", key=f"del_{row['id']}"):
                st.session_state.delete_id = row["id"]
                st.rerun()
