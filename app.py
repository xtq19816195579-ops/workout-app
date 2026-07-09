import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
from supabase import create_client, Client
import streamlit_cookies_controller as cookies
import urllib.parse

# -------------------- 初始化与配置 --------------------
st.set_page_config(page_title="茧记", page_icon="🦋", layout="wide")

# ==================== 移动端适配 CSS ====================
st.markdown("""
<style>
    .main .block-container { max-width: 100% !important; padding: 0.8rem; }
    .stButton button { width: 100%; border-radius: 8px; padding: 0.6rem 0; font-size: 1rem; background-color: #f5c842; color: #1a1a2e; border: none; margin-bottom: 0.3rem; }
    .stButton button:hover { background-color: #e0b03a; }
    .stTextInput, .stNumberInput, .stSelectbox, .stDateInput { font-size: 16px; }
    h1 { font-size: 1.8rem !important; }
    h2 { font-size: 1.4rem !important; }
    h3 { font-size: 1.2rem !important; }
    .calendar td { padding: 2px !important; }
    .cal-day { height: 40px !important; line-height: 40px !important; font-size: 0.9rem !important; }
    .stSelectbox div[data-baseweb="select"] { min-height: 38px; }
    .stMultiSelect div[data-baseweb="select"] { min-height: 38px; }
    .element-container { margin-bottom: 0.5rem; }
    .streamlit-expanderHeader { font-size: 1rem !important; }
</style>
""", unsafe_allow_html=True)

# -------------------- Cookie & Supabase 客户端 --------------------
cookie_manager = cookies.CookieController()
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# 固定密码（用于微信自动登录）
WECHAT_FIXED_PASSWORD = st.secrets.get("WECHAT_FIXED_PASSWORD", "wechat123")

# -------------------- 动作库（不变） --------------------
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
    st.title("🦋 茧记")
    st.write("欢迎回来，请登录")
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

# ==================== 微信自动登录（新增） ====================
def wechat_auto_login(openid):
    """使用 openid 自动注册/登录 Supabase"""
    email = f"{openid}@wechat.com"
    try:
        # 尝试登录
        res = supabase.auth.sign_in_with_password({"email": email, "password": WECHAT_FIXED_PASSWORD})
        st.session_state.user = res.user
        st.session_state.access_token = res.session.access_token
        supabase.postgrest.auth(res.session.access_token)
        cookie_manager.set('refresh_token', res.session.refresh_token,
                           max_age=30*24*60*60, path='/')
        return True
    except Exception as e:
        # 用户不存在，尝试注册
        try:
            res = supabase.auth.sign_up({"email": email, "password": WECHAT_FIXED_PASSWORD})
            if res.user:
                # 注册成功，直接登录（因为已关闭邮箱确认）
                # 重新调用登录
                res2 = supabase.auth.sign_in_with_password({"email": email, "password": WECHAT_FIXED_PASSWORD})
                st.session_state.user = res2.user
                st.session_state.access_token = res2.session.access_token
                supabase.postgrest.auth(res2.session.access_token)
                cookie_manager.set('refresh_token', res2.session.refresh_token,
                                   max_age=30*24*60*60, path='/')
                return True
            else:
                return False
        except Exception as e2:
            st.error(f"自动注册失败：{e2}")
            return False

# ==================== URL 参数解析 ====================
query_params = st.query_params
tab = query_params.get("tab", "home")
wechat_openid = query_params.get("wechat_openid", "")

# 如果存在 wechat_openid 且未登录，则尝试自动登录
if wechat_openid and "user" not in st.session_state:
    if wechat_auto_login(wechat_openid):
        st.rerun()

# 设置 active_tab（用于后续跳转）
if tab == "training":
    st.session_state.active_tab = "训练记录"
elif tab == "calendar":
    st.session_state.active_tab = "日历"
elif tab == "settings":
    st.session_state.active_tab = "设置"
elif tab == "report":
    st.session_state.active_tab = "战报"
else:
    st.session_state.active_tab = "首页"

# ==================== 主程序 ====================
if "user" not in st.session_state:
    if not restore_session():
        login_page()
        st.stop()

user = st.session_state.user
if "access_token" in st.session_state:
    supabase.postgrest.auth(st.session_state.access_token)

# 以下为原有主体代码（侧边栏、计时器、日历等），此处省略重复部分，实际使用请粘贴原有代码
# （为节省篇幅，此处仅示意，实际必须包含完整功能）
st.success(f"✅ 已自动登录，欢迎 {user.email}！")

# 加载主界面（计时器、日历、记录表单等）
# 这里可以调用原有的主界面函数，或直接复制之前的全部内容
# 由于篇幅，下面仅保留一个占位，实际部署请将原 app.py 中 `if "user" in st.session_state:` 之后的所有代码复制过来。

# --- 原有主界面代码（请复制完整的训练日志界面） ---
# 注意：需保留所有功能（计时器、日历、侧边栏记录表单等）
# 以下仅示例结构：
st.markdown("---")
st.subheader("⏱️ 训练计时器")
# ... 计时器代码 ...
st.markdown("---")
# ... 日历代码 ...
