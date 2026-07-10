import streamlit as st
from datetime import datetime
import json

st.set_page_config(page_title="茧记", page_icon="🦋", layout="wide")

query_params = st.query_params

if query_params.get("webview") != "1":
    st.write("请通过微信小程序访问")
    st.stop()

tab = query_params.get("tab", "home")
wechat_openid = query_params.get("wechat_openid", "")
avatar = query_params.get("avatar", "")
nickname = query_params.get("nickname", "微信用户")

supabase_url = st.secrets["SUPABASE_URL"]
supabase_anon_key = st.secrets["SUPABASE_ANON_KEY"]

# ---------- 动作库 ----------
strength_parts = {
    "胸部": ["杠铃卧推", "上斜卧推", "哑铃飞鸟", "器械卧推", "夹胸", "俯卧撑"],
    "肩部": ["哑铃推举", "杠铃推举", "侧平举", "前平举", "面拉", "蝴蝶机反向飞鸟"],
    "背部": ["引体向上", "杠铃划船", "哑铃划船", "高位下拉", "坐姿划船", "硬拉"],
    "二头": ["杠铃弯举", "哑铃弯举", "锤式弯举", "集中弯举", "牧师凳弯举"],
    "三头": ["窄距卧推", "绳索下压", "哑铃臂屈伸", "双杠臂屈伸", "俯身臂屈伸"],
    "腹部": ["卷腹", "平板支撑", "仰卧抬腿", "俄罗斯转体", "悬垂举腿", "健腹轮"],
    "腿部": ["深蹲", "腿举", "腿弯举", "腿屈伸", "箭步蹲", "罗马尼亚硬拉"]
}
cardio_parts = {
    "有氧": ["跑步", "慢跑", "跳绳", "游泳", "骑行", "椭圆机", "划船机", "高强度间歇训练", "波比跳", "壶铃摆荡", "战绳"]
}
cardio_met_options = [
    ("跑步 (8 km/h)", "8.0"),
    ("跑步 (10 km/h)", "10.0"),
    ("慢跑", "7.0"),
    ("跳绳 (中速)", "10.0"),
    ("跳绳 (快速)", "12.0"),
    ("游泳 (自由泳)", "8.0"),
    ("游泳 (蛙泳)", "7.0"),
    ("骑行 (中等)", "6.0"),
    ("椭圆机", "5.0"),
    ("划船机", "7.0"),
    ("高强度间歇训练", "12.0"),
    ("自定义", "custom")
]

strength_parts_json = json.dumps(strength_parts)
cardio_parts_json = json.dumps(cardio_parts)
cardio_met_json = json.dumps(cardio_met_options)

# ---------- 基础 HTML ----------
base_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>茧记</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: #f8fafc;
        padding: 20px 16px 40px;
        min-height: 100vh;
        max-width: 420px;
        margin: 0 auto;
    }}
    .card {{ background: white; border-radius: 20px; padding: 20px 24px; margin-bottom: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.04); }}
    .btn {{ display: block; width: 100%; padding: 14px; background: #2563eb; color: white; border: none; border-radius: 60px; font-size: 16px; font-weight: 600; text-align: center; cursor: pointer; text-decoration: none; transition: transform 0.1s; }}
    .btn:active {{ transform: scale(0.97); }}
    .btn-danger {{ background: #ef4444; }}
    .btn-success {{ background: #22c55e; }}
    .btn-secondary {{ background: #6b7280; }}
    .input-group {{ margin-bottom: 14px; }}
    .input-group label {{ display: block; font-size: 14px; color: #334155; margin-bottom: 4px; font-weight: 500; }}
    .input-group input, .input-group select {{
        width: 100%;
        padding: 12px;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        font-size: 16px;
        background: #f1f5f9;
        outline: none;
        transition: border-color 0.2s;
    }}
    .input-group input:focus, .input-group select:focus {{ border-color: #2563eb; }}
    .back-link {{ display: block; text-align: center; margin-top: 20px; color: #2563eb; text-decoration: none; font-size: 14px; }}
    .brand {{ text-align: center; margin-bottom: 24px; }}
    .brand h1 {{ font-size: 28px; color: #0f172a; font-weight: 700; letter-spacing: 1px; }}
    .brand p {{ color: #94a3b8; font-size: 14px; margin-top: 4px; }}
    .menu-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }}
    .menu-item {{ background: white; border-radius: 16px; padding: 16px 8px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.04); cursor: pointer; text-decoration: none; transition: transform 0.1s; display: block; }}
    .menu-item:active {{ transform: scale(0.94); }}
    .menu-item .icon {{ font-size: 28px; display: block; margin-bottom: 4px; }}
    .menu-item .label {{ font-size: 12px; color: #334155; font-weight: 500; }}
    .badge {{ display: inline-block; padding: 2px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; background: #dcfce7; color: #16a34a; }}
    .stat-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f1f5f9; }}
    .stat-row:last-child {{ border-bottom: none; }}
    .stat-label {{ color: #475569; }}
    .stat-value {{ font-weight: 600; color: #0f172a; }}
    .footer {{ text-align: center; font-size: 12px; color: #94a3b8; margin-top: 24px; }}
    .avatar-img {{ width: 48px; height: 48px; border-radius: 50%; object-fit: cover; background: #e2e8f0; }}
    .user-row {{ display: flex; align-items: center; gap: 12px; }}
    .user-name {{ font-weight: 600; color: #0f172a; font-size: 16px; }}
    .user-status {{ font-size: 12px; color: #94a3b8; }}
    .toast {{ position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background: #0f172a; color: white; padding: 10px 20px; border-radius: 12px; font-size: 14px; z-index: 9999; display: none; }}
    .switch-mode {{ display: flex; gap: 12px; margin-bottom: 16px; }}
    .switch-mode button {{ flex: 1; padding: 10px; border: 2px solid #e2e8f0; background: white; border-radius: 12px; font-size: 14px; font-weight: 500; cursor: pointer; }}
    .switch-mode button.active {{ border-color: #2563eb; background: #eff6ff; color: #2563eb; }}
    .hidden {{ display: none; }}
    .calendar-grid {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; margin-top: 12px; }}
    .day-cell {{ text-align: center; padding: 10px 0; border-radius: 12px; background: #f1f5f9; font-size: 14px; font-weight: 500; color: #0f172a; }}
    .day-cell.trained {{ background: #2563eb; color: white; }}
    .day-cell.empty {{ background: transparent; }}
    .day-cell.weekend {{ color: #94a3b8; }}
    .month-nav {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
    .month-nav span {{ font-weight: 600; color: #0f172a; }}
    .month-nav button {{ background: none; border: none; font-size: 20px; cursor: pointer; padding: 0 12px; }}
    .group-item {{ display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }}
    .group-item input {{ flex: 1; padding: 8px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 14px; }}
    .group-item .remove-btn {{ background: #ef4444; color: white; border: none; border-radius: 6px; padding: 4px 10px; font-size: 12px; cursor: pointer; }}
    .add-btn {{ background: #22c55e; color: white; border: none; border-radius: 8px; padding: 6px 12px; font-size: 14px; cursor: pointer; margin-top: 4px; }}
    .add-btn-small {{ background: #22c55e; color: white; border: none; border-radius: 6px; padding: 4px 10px; font-size: 12px; cursor: pointer; }}
    .remove-btn-red {{ background: #ef4444; color: white; border: none; border-radius: 6px; padding: 4px 10px; font-size: 12px; cursor: pointer; }}
    .block-container {{ margin-bottom: 16px; padding: 12px; background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0; }}
</style>
</head>
<body>
<div id="toast" class="toast"></div>
<script>
    const SUPABASE_URL = '{supabase_url}';
    const SUPABASE_ANON_KEY = '{supabase_anon_key}';
    const WECHAT_FIXED_PASSWORD = 'wechat123';
    const STRENGTH_PARTS = {strength_parts_json};
    const CARDIO_PARTS = {cardio_parts_json};
    const CARDIO_MET_OPTIONS = {cardio_met_json};
    const WECHAT_OPENID = '{wechat_openid}';
    const AVATAR = '{avatar}';
    const NICKNAME = '{nickname}';

    let accessToken = null;
    let userId = null;

    function showToast(msg, duration = 2000) {{
        const toast = document.getElementById('toast');
        toast.textContent = msg;
        toast.style.display = 'block';
        setTimeout(() => {{ toast.style.display = 'none'; }}, duration);
    }}

    async function autoLogin() {{
        if (!WECHAT_OPENID) {{
            showToast('缺少用户标识');
            return false;
        }}
        const email = WECHAT_OPENID + '@wechat.com';
        try {{
            let resp = await fetch(SUPABASE_URL + '/auth/v1/token?grant_type=password', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'apikey': SUPABASE_ANON_KEY }},
                body: JSON.stringify({{ email, password: WECHAT_FIXED_PASSWORD }})
            }});
            let data = await resp.json();
            if (data.access_token) {{
                accessToken = data.access_token;
                userId = data.user.id;
                if (AVATAR && NICKNAME) {{
                    await fetch(SUPABASE_URL + '/rest/v1/profiles', {{
                        method: 'PATCH',
                        headers: {{
                            'Content-Type': 'application/json',
                            'apikey': SUPABASE_ANON_KEY,
                            'Authorization': 'Bearer ' + accessToken,
                            'Prefer': 'return=representation'
                        }},
                        body: JSON.stringify({{ avatar_url: AVATAR, nickname: NICKNAME }})
                    }});
                }}
                return true;
            }} else {{
                resp = await fetch(SUPABASE_URL + '/auth/v1/signup', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json', 'apikey': SUPABASE_ANON_KEY }},
                    body: JSON.stringify({{ email, password: WECHAT_FIXED_PASSWORD }})
                }});
                data = await resp.json();
                if (data.access_token) {{
                    accessToken = data.access_token;
                    userId = data.user.id;
                    await fetch(SUPABASE_URL + '/rest/v1/profiles', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                            'apikey': SUPABASE_ANON_KEY,
                            'Authorization': 'Bearer ' + accessToken,
                            'Prefer': 'return=representation'
                        }},
                        body: JSON.stringify({{ user_id: userId, weight: 70, height: 175, avatar_url: AVATAR, nickname: NICKNAME }})
                    }});
                    return true;
                }}
            }}
        }} catch (e) {{
            console.error('登录失败:', e);
            showToast('自动登录失败，请重试');
            return false;
        }}
        return false;
    }}

    async function supabaseRequest(method, path, body = null) {{
        const url = SUPABASE_URL + path;
        const headers = {{
            'Content-Type': 'application/json',
            'apikey': SUPABASE_ANON_KEY,
            'Authorization': 'Bearer ' + accessToken
        }};
        const options = {{ method, headers }};
        if (body) options.body = JSON.stringify(body);
        const resp = await fetch(url, options);
        return resp.json();
    }}

    function initUser() {{
        const avatarEl = document.getElementById('userAvatar');
        const nameEl = document.getElementById('userName');
        if (avatarEl) {{
            if (AVATAR) avatarEl.src = AVATAR;
            else avatarEl.src = '';
        }}
        if (nameEl) {{
            nameEl.textContent = NICKNAME || '微信用户';
        }}
    }}

    window.onload = async function() {{
        initUser();
        if (!accessToken) {{
            const ok = await autoLogin();
            if (!ok) {{
                showToast('登录失败，部分功能不可用');
            }} else {{
                if (window.refreshData) window.refreshData();
            }}
        }} else {{
            if (window.refreshData) window.refreshData();
        }}
    }};
</script>
"""

def render(html):
    st.html(html)

# ---------- 首页 ----------
if tab == "home":
    html = base_html + f"""
    <div class="brand"><h1>🦋 茧记</h1><p>记录 · 蜕变</p></div>
    <div class="card">
        <div class="user-row">
            <img id="userAvatar" class="avatar-img" src="" alt="头像">
            <div>
                <div id="userName" class="user-name">微信用户</div>
                <div class="user-status">已登录</div>
            </div>
            <span class="badge" style="margin-left:auto;">在线</span>
        </div>
    </div>
    <div class="menu-grid">
        <a href="?webview=1&tab=settings&wechat_openid={wechat_openid}&avatar={avatar}&nickname={nickname}" class="menu-item">
            <span class="icon">⚙️</span><span class="label">个人设置</span>
        </a>
        <a href="?webview=1&tab=calendar&wechat_openid={wechat_openid}&avatar={avatar}&nickname={nickname}" class="menu-item">
            <span class="icon">📅</span><span class="label">训练日历</span>
        </a>
        <a href="?webview=1&tab=training&wechat_openid={wechat_openid}&avatar={avatar}&nickname={nickname}" class="menu-item">
            <span class="icon">🏋️</span><span class="label">训练记录</span>
        </a>
        <a href="?webview=1&tab=report&wechat_openid={wechat_openid}&avatar={avatar}&nickname={nickname}" class="menu-item">
            <span class="icon">📊</span><span class="label">今日战报</span>
        </a>
    </div>
    <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <span style="font-weight:600; color:#0f172a;">📋 今日训练</span>
            <span id="todayCount" style="font-size:13px; color:#2563eb; background:#eff6ff; padding:2px 14px; border-radius:30px;">加载中...</span>
        </div>
        <div id="todayList" style="text-align:center; color:#94a3b8; padding:16px 0;">今天还没有训练记录</div>
    </div>
    <div class="footer">数据安全加密 · Supabase 动力</div>
    <script>
        window.refreshData = async function() {{
            if (!accessToken) return;
            try {{
                const today = new Date().toISOString().slice(0,10);
                const resp = await supabaseRequest('GET', '/rest/v1/workouts?user_id=eq.' + userId + '&date=eq.' + today);
                const count = resp.length;
                document.getElementById('todayCount').textContent = count + ' 项';
                const list = document.getElementById('todayList');
                if (count > 0) {{
                    let html = '';
                    resp.forEach(w => {{
                        html += `<div style="padding:4px 0;">• ${{w.body_part}} ${{w.exercise}}：${{w.set_count || 0}}组</div>`;
                    }});
                    list.innerHTML = html;
                }} else {{
                    list.textContent = '今天还没有训练记录，开始吧 💪';
                }}
            }} catch(e) {{
                console.error(e);
            }}
        }};
    </script>
    """

# ---------- 个人设置 ----------
elif tab == "settings":
    html = base_html + f"""
    <div class="brand"><h1>⚙️ 个人设置</h1><p>管理您的身体数据</p></div>
    <div class="card">
        <form id="profileForm">
            <div class="input-group"><label>体重 (kg)</label><input type="number" id="weight" step="0.5" min="30"></div>
            <div class="input-group"><label>身高 (cm)</label><input type="number" id="height" step="1" min="100"></div>
            <button type="button" class="btn" onclick="saveProfile()">保存身体数据</button>
        </form>
    </div>
    <div class="card">
        <h3 style="font-size:16px; color:#0f172a; margin-bottom:12px;">📲 微信推送设置</h3>
        <div class="input-group"><label>PushPlus Token</label><input type="text" id="pushToken" placeholder="请前往 pushplus.plus 获取"></div>
        <label style="display:flex; align-items:center; gap:8px; font-size:14px; color:#334155; margin:8px 0 14px;">
            <input type="checkbox" id="pushEnabled" checked> 开启每日推送
        </label>
        <button type="button" class="btn" onclick="savePushSettings()">保存推送设置</button>
    </div>
    <a href="?webview=1&wechat_openid={wechat_openid}&avatar={avatar}&nickname={nickname}" class="back-link">← 返回首页</a>
    <div class="footer">数据安全加密</div>
    <script>
        async function loadProfile() {{
            if (!accessToken) return;
            try {{
                const resp = await supabaseRequest('GET', '/rest/v1/profiles?user_id=eq.' + userId);
                if (resp.length) {{
                    const p = resp[0];
                    document.getElementById('weight').value = p.weight || 70;
                    document.getElementById('height').value = p.height || 175;
                }}
            }} catch(e) {{ console.error(e); }}
        }}
        async function saveProfile() {{
            if (!accessToken) {{ showToast('请先登录'); return; }}
            const weight = parseFloat(document.getElementById('weight').value);
            const height = parseFloat(document.getElementById('height').value);
            try {{
                await supabaseRequest('PATCH', '/rest/v1/profiles?user_id=eq.' + userId, {{ weight, height }});
                showToast('保存成功');
            }} catch(e) {{
                console.error(e);
                showToast('保存失败');
            }}
        }}
        async function loadPushSettings() {{
            if (!accessToken) return;
            try {{
                const resp = await supabaseRequest('GET', '/rest/v1/user_push_settings?user_id=eq.' + userId);
                if (resp.length) {{
                    document.getElementById('pushToken').value = resp[0].pushplus_token || '';
                    document.getElementById('pushEnabled').checked = resp[0].is_enabled;
                }}
            }} catch(e) {{ console.error(e); }}
        }}
        async function savePushSettings() {{
            if (!accessToken) {{ showToast('请先登录'); return; }}
            const token = document.getElementById('pushToken').value.trim();
            const enabled = document.getElementById('pushEnabled').checked;
            try {{
                await supabaseRequest('POST', '/rest/v1/user_push_settings', {{
                    user_id: userId,
                    pushplus_token: token,
                    is_enabled: enabled
                }});
                showToast('推送设置已保存');
            }} catch(e) {{
                console.error(e);
                showToast('保存失败');
            }}
        }}
        window.refreshData = function() {{
            loadProfile();
            loadPushSettings();
        }};
        setTimeout(() => {{
            if (accessToken) {{
                loadProfile();
                loadPushSettings();
            }}
        }}, 500);
    </script>
    """

# ---------- 训练日历 ----------
elif tab == "calendar":
    html = base_html + f"""
    <div class="brand"><h1>📅 训练日历</h1><p id="monthYear">2026年7月</p></div>
    <div class="card" id="calendarContainer">
        <div class="month-nav">
            <button id="prevMonth">◀</button>
            <span id="currentMonth">2026年7月</span>
            <button id="nextMonth">▶</button>
        </div>
        <div id="calendarGrid" class="calendar-grid"></div>
        <div style="margin-top: 16px; text-align: center;">
            <span style="font-size:14px; color:#475569;">本月出勤：<span id="attendanceCount">0</span> 天</span>
        </div>
    </div>
    <a href="?webview=1&wechat_openid={wechat_openid}&avatar={avatar}&nickname={nickname}" class="back-link">← 返回首页</a>
    <div class="footer">绿色日期表示有训练记录</div>
    <script>
        let currentYear = 2026, currentMonth = 6;
        const monthNames = ['一月','二月','三月','四月','五月','六月','七月','八月','九月','十月','十一月','十二月'];
        const weekDays = ['日','一','二','三','四','五','六'];

        async function loadCalendar(year, month) {{
            if (!accessToken) {{
                showToast('请先登录');
                return;
            }}
            const start = new Date(year, month, 1).toISOString().slice(0,10);
            const end = new Date(year, month+1, 0).toISOString().slice(0,10);
            try {{
                const resp = await supabaseRequest('GET', `/rest/v1/workouts?user_id=eq.${{userId}}&date=gte.${{start}}&date=lte.${{end}}&select=date`);
                const trainedDates = new Set(resp.map(w => w.date));
                renderCalendar(year, month, trainedDates);
            }} catch(e) {{
                console.error('加载日历失败:', e);
                showToast('加载日历失败，请重试');
            }}
        }}

        function renderCalendar(year, month, trainedDates) {{
            const firstDay = new Date(year, month, 1).getDay();
            const daysInMonth = new Date(year, month+1, 0).getDate();
            const grid = document.getElementById('calendarGrid');
            let html = weekDays.map(d => `<div class="day-cell weekend">${{d}}</div>`).join('');
            for (let i = 0; i < firstDay; i++) {{
                html += '<div class="day-cell empty"></div>';
            }}
            let trainedCount = 0;
            for (let d = 1; d <= daysInMonth; d++) {{
                const dateStr = new Date(year, month, d).toISOString().slice(0,10);
                const trained = trainedDates.has(dateStr);
                if (trained) trainedCount++;
                html += `<div class="day-cell ${{trained ? 'trained' : ''}}">${{d}}</div>`;
            }}
            grid.innerHTML = html;
            document.getElementById('currentMonth').textContent = year + '年' + monthNames[month];
            document.getElementById('monthYear').textContent = year + '年' + monthNames[month];
            document.getElementById('attendanceCount').textContent = trainedCount;
        }}

        document.getElementById('prevMonth').addEventListener('click', function() {{
            if (currentMonth === 0) {{ currentMonth = 11; currentYear--; }} else {{ currentMonth--; }}
            loadCalendar(currentYear, currentMonth);
        }});
        document.getElementById('nextMonth').addEventListener('click', function() {{
            if (currentMonth === 11) {{ currentMonth = 0; currentYear++; }} else {{ currentMonth++; }}
            loadCalendar(currentYear, currentMonth);
        }});

        window.refreshData = function() {{
            loadCalendar(currentYear, currentMonth);
        }};
        setTimeout(() => {{
            if (accessToken) loadCalendar(currentYear, currentMonth);
        }}, 1000);
    </script>
    """

# ---------- 训练记录（重构） ----------
elif tab == "training":
    html = base_html + f"""
    <div class="brand"><h1>🏋️ 训练记录</h1><p>记录每一次进步</p></div>
    <div class="card">
        <div class="switch-mode">
            <button id="modeStrength" class="active" onclick="switchMode('strength')">💪 力量</button>
            <button id="modeCardio" onclick="switchMode('cardio')">🏃 有氧</button>
        </div>
        <form id="workoutForm">
            <!-- 力量模式 -->
            <div id="strengthFields">
                <div id="strengthBlocks"></div>
                <button type="button" class="btn btn-secondary" onclick="addStrengthBlock()">+ 添加部位</button>
            </div>
            <!-- 有氧模式 -->
            <div id="cardioFields" class="hidden">
                <div class="input-group"><label>动作</label>
                    <select id="cardioExercise">
                        {''.join([f'<option value="{e}">{e}</option>' for e in cardio_parts["有氧"]])}
                    </select>
                </div>
                <div class="input-group"><label>时长 (分钟)</label><input type="number" id="cardioDuration" value="30" min="1"></div>
                <div class="input-group"><label>强度 (MET)</label>
                    <select id="metSelect">
                        {''.join([f'<option value="{v}">{k}</option>' for k, v in cardio_met_options])}
                    </select>
                </div>
                <div class="input-group hidden" id="customMetGroup">
                    <label>自定义 MET 值</label><input type="number" id="customMet" value="8.0" step="0.1">
                </div>
            </div>
            <button type="button" class="btn" onclick="saveWorkout()" style="margin-top:12px;">保存记录</button>
        </form>
    </div>
    <a href="?webview=1&wechat_openid={wechat_openid}&avatar={avatar}&nickname={nickname}" class="back-link">← 返回首页</a>
    <div class="footer">数据将存储于 Supabase · 安全加密</div>
    <script>
        // ---------- 力量模式动态块 ----------
        let blockCount = 0;

        function addStrengthBlock() {{
            blockCount++;
            const container = document.getElementById('strengthBlocks');
            const blockId = 'block_' + blockCount;
            const partSelect = document.createElement('select');
            partSelect.id = blockId + '_part';
            partSelect.className = 'block-part';
            // 从 STRENGTH_PARTS 生成选项
            for (let p in STRENGTH_PARTS) {{
                const opt = document.createElement('option');
                opt.value = p;
                opt.textContent = p;
                partSelect.appendChild(opt);
            }}
            partSelect.onchange = function() {{ updateStrengthExercises(blockId); }};

            const exerciseSelect = document.createElement('select');
            exerciseSelect.id = blockId + '_exercise';
            exerciseSelect.className = 'block-exercise';

            const blockDiv = document.createElement('div');
            blockDiv.className = 'block-container';
            blockDiv.id = blockId;
            blockDiv.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-weight:600; font-size:14px;">部位 ${{blockCount}}</span>
                    <button type="button" class="remove-btn-red" onclick="removeBlock('${{blockId}}')">删除</button>
                </div>
                <div class="input-group"><label>部位</label></div>
                <div class="input-group"><label>动作</label></div>
                <div class="input-group"><label>组数</label>
                    <input type="number" class="block-sets" value="3" min="1" onchange="generateGroupInputs('${{blockId}}')">
                </div>
                <div id="${{blockId}}_groups"></div>
                <button type="button" class="add-btn" onclick="addGroup('${{blockId}}')">+ 添加一组</button>
            `;
            // 插入部位和动作选择器
            const partLabel = blockDiv.querySelector('.input-group:first-child');
            partLabel.appendChild(partSelect);
            const exLabel = blockDiv.querySelector('.input-group:nth-child(2)');
            exLabel.appendChild(exerciseSelect);
            // 初始化动作列表
            updateStrengthExercises(blockId);
            // 生成默认组
            generateGroupInputs(blockId);

            container.appendChild(blockDiv);
        }}

        function removeBlock(blockId) {{
            const el = document.getElementById(blockId);
            if (el) el.remove();
        }}

        function updateStrengthExercises(blockId) {{
            const partSelect = document.getElementById(blockId + '_part');
            const exSelect = document.getElementById(blockId + '_exercise');
            const part = partSelect.value;
            const exercises = STRENGTH_PARTS[part] || [];
            exSelect.innerHTML = exercises.map(e => `<option value="${{e}}">${{e}}</option>`).join('');
        }}

        function generateGroupInputs(blockId) {{
            const setsInput = document.querySelector('#' + blockId + ' .block-sets');
            const count = parseInt(setsInput.value) || 0;
            const container = document.getElementById(blockId + '_groups');
            container.innerHTML = '';
            for (let i = 0; i < count; i++) {{
                const div = document.createElement('div');
                div.className = 'group-item';
                div.innerHTML = `
                    <span style="font-weight:500; font-size:14px;">${{i+1}}.</span>
                    <input type="number" placeholder="次数" class="group-reps" value="10" min="1" style="flex:1;">
                    <input type="number" placeholder="重量(kg)" class="group-weight" value="20" step="2.5" min="0" style="flex:1;">
                `;
                container.appendChild(div);
            }}
        }}

        function addGroup(blockId) {{
            const container = document.getElementById(blockId + '_groups');
            const idx = container.children.length + 1;
            const div = document.createElement('div');
            div.className = 'group-item';
            div.innerHTML = `
                <span style="font-weight:500; font-size:14px;">${{idx}}.</span>
                <input type="number" placeholder="次数" class="group-reps" value="10" min="1" style="flex:1;">
                <input type="number" placeholder="重量(kg)" class="group-weight" value="20" step="2.5" min="0" style="flex:1;">
                <button type="button" class="remove-btn" onclick="this.parentElement.remove()">✕</button>
            `;
            container.appendChild(div);
        }}

        // ---------- 切换模式 ----------
        function switchMode(mode) {{
            document.getElementById('modeStrength').classList.toggle('active', mode === 'strength');
            document.getElementById('modeCardio').classList.toggle('active', mode === 'cardio');
            document.getElementById('strengthFields').classList.toggle('hidden', mode !== 'strength');
            document.getElementById('cardioFields').classList.toggle('hidden', mode !== 'cardio');
        }}

        // ---------- MET 自定义 ----------
        document.getElementById('metSelect').addEventListener('change', function() {{
            const customGroup = document.getElementById('customMetGroup');
            if (this.value === 'custom') {{
                customGroup.classList.remove('hidden');
            }} else {{
                customGroup.classList.add('hidden');
            }}
        }});

        // ---------- 保存训练记录 ----------
        async function saveWorkout() {{
            if (!accessToken) {{
                showToast('请先登录');
                return;
            }}
            const mode = document.getElementById('modeStrength').classList.contains('active') ? 'strength' : 'cardio';
            let records = [];

            if (mode === 'strength') {{
                const blocks = document.querySelectorAll('.block-container');
                if (blocks.length === 0) {{
                    showToast('请至少添加一个部位');
                    return;
                }}
                for (let block of blocks) {{
                    const part = block.querySelector('.block-part').value;
                    const exercise = block.querySelector('.block-exercise').value;
                    const setsInput = block.querySelector('.block-sets');
                    const sets = parseInt(setsInput.value) || 0;
                    const repsInputs = block.querySelectorAll('.group-reps');
                    const weightInputs = block.querySelectorAll('.group-weight');
                    let details = [];
                    for (let i = 0; i < repsInputs.length; i++) {{
                        const reps = parseInt(repsInputs[i].value) || 0;
                        const weight = parseFloat(weightInputs[i].value) || 0;
                        if (reps > 0) details.push(`${{reps}}次×${{weight}}kg`);
                    }}
                    if (details.length === 0) continue;
                    records.push({{
                        user_id: userId,
                        date: new Date().toISOString().slice(0,10),
                        body_part: part,
                        exercise: exercise,
                        set_count: details.length,
                        details: details.join('; '),
                        cardio_duration: null,
                        met_value: null
                    }});
                }}
            }} else {{
                const exercise = document.getElementById('cardioExercise').value;
                const duration = parseInt(document.getElementById('cardioDuration').value) || 0;
                const metSelect = document.getElementById('metSelect');
                let met = parseFloat(metSelect.value);
                if (metSelect.value === 'custom') {{
                    met = parseFloat(document.getElementById('customMet').value);
                }}
                if (duration <= 0) {{
                    showToast('请输入有效时长');
                    return;
                }}
                records.push({{
                    user_id: userId,
                    date: new Date().toISOString().slice(0,10),
                    body_part: '有氧',
                    exercise: exercise,
                    set_count: 0,
                    details: '',
                    cardio_duration: duration,
                    met_value: met
                }});
            }}

            if (records.length === 0) {{
                showToast('请至少输入一条有效记录');
                return;
            }}

            try {{
                let success = true;
                for (let rec of records) {{
                    const resp = await supabaseRequest('POST', '/rest/v1/workouts', rec);
                    if (!resp.length) success = false;
                }}
                if (success) {{
                    showToast('保存成功！');
                }} else {{
                    showToast('部分记录保存失败，请检查');
                }}
            }} catch(e) {{
                console.error(e);
                showToast('保存异常，请重试');
            }}
        }}

        // ---------- 初始化 ----------
        addStrengthBlock();
    </script>
    """

# ---------- 今日战报 ----------
elif tab == "report":
    html = base_html + f"""
    <div class="brand"><h1>📊 今日战报</h1><p id="reportDate">{datetime.now().strftime("%Y年%m月%d日")}</p></div>
    <div class="card" id="reportContent">
        <div style="text-align:center; color:#94a3b8; padding:20px;">加载中...</div>
    </div>
    <a href="?webview=1&wechat_openid={wechat_openid}&avatar={avatar}&nickname={nickname}" class="back-link">← 返回首页</a>
    <div class="footer">数据基于您的训练记录生成</div>
    <script>
        async function loadReport() {{
            if (!accessToken) {{
                document.getElementById('reportContent').innerHTML = '<div style="text-align:center;padding:20px;">请先登录</div>';
                return;
            }}
            const today = new Date().toISOString().slice(0,10);
            try {{
                const workouts = await supabaseRequest('GET', '/rest/v1/workouts?user_id=eq.' + userId + '&date=eq.' + today);
                const durations = await supabaseRequest('GET', '/rest/v1/training_durations?user_id=eq.' + userId + '&date=eq.' + today);
                let totalDuration = 0;
                durations.forEach(d => totalDuration += d.duration_min || 0);
                const profileResp = await supabaseRequest('GET', '/rest/v1/profiles?user_id=eq.' + userId);
                let weight = 70;
                if (profileResp.length) weight = profileResp[0].weight || 70;

                let totalCal = 0;
                let parts = new Set(), actions = new Set();
                let detailHtml = '';
                workouts.forEach(w => {{
                    parts.add(w.body_part);
                    actions.add(w.exercise);
                    if (w.met_value) {{
                        const cal = w.met_value * weight * (w.cardio_duration / 60);
                        totalCal += cal;
                        detailHtml += `<div>• ${{w.body_part}} ${{w.exercise}}：${{w.cardio_duration}}分钟，MET=${{w.met_value}}，消耗 ~${{Math.round(cal)}}千卡</div>`;
                    }} else {{
                        const sets = w.set_count || 0;
                        const details = w.details || '';
                        const cal = 5 * weight * (sets * 2 / 60);
                        totalCal += cal;
                        detailHtml += `<div>• ${{w.body_part}} ${{w.exercise}}：${{sets}}组，${{details}}，估算 ~${{Math.round(cal)}}千卡</div>`;
                    }}
                }});

                const partsStr = Array.from(parts).join('、') || '无';
                const actionsStr = Array.from(actions).join('、') || '无';
                const durStr = totalDuration > 0 ? `${{Math.floor(totalDuration)}}分钟` : '未记录';
                const calStr = Math.round(totalCal);

                document.getElementById('reportContent').innerHTML = `
                    <div class="stat-row"><span class="stat-label">🏋️ 训练部位</span><span class="stat-value">${{partsStr}}</span></div>
                    <div class="stat-row"><span class="stat-label">📊 完成动作</span><span class="stat-value">${{actionsStr}}</span></div>
                    <div class="stat-row"><span class="stat-label">⏱️ 训练时长</span><span class="stat-value">${{durStr}}</span></div>
                    <div class="stat-row"><span class="stat-label">🔥 估算消耗</span><span class="stat-value">${{calStr}} 千卡</span></div>
                    <div style="margin-top:16px;"><h3 style="font-size:16px; color:#0f172a;">✅ 详细记录</h3>${{detailHtml || '<div style="color:#94a3b8;">今日无训练记录</div>'}}</div>
                `;
            }} catch(e) {{
                console.error(e);
                document.getElementById('reportContent').innerHTML = '<div style="text-align:center;padding:20px;">加载失败，请重试</div>';
            }}
        }}
        window.refreshData = loadReport;
        setTimeout(() => {{
            if (accessToken) loadReport();
        }}, 500);
    </script>
    """

else:
    html = base_html + "<p>页面不存在</p>"

render(html)
