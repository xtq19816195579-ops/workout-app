import streamlit as st
import json
import urllib.parse
from datetime import datetime

# 设置页面基础配置
st.set_page_config(page_title="茧记", page_icon="🦋", layout="wide")

query_params = st.query_params

# 安全拦截：非微信小程序 WebView 容器访问直接拦截
if query_params.get("webview") != "1":
    st.write("请通过微信小程序访问")
    st.stop()

# 安全提取 URL 路由传参
tab = query_params.get("tab", "home")
wechat_openid = query_params.get("wechat_openid", "")
avatar = query_params.get("avatar", "")
nickname = query_params.get("nickname", "微信用户")

# 头像与昵称兜底处理：防止空参数导致界面挂掉
display_avatar = avatar if avatar else "https://mmbiz.qpic.cn/mmbiz/icTdbqWNOwNRna42FI242Lcia07jQodd2FJGIYQfG0LAJGFxM4FbnQP6yfMxBgJ0F3YRqJCJ1aPAK2dQagdusBZg/0"
display_nickname = nickname if nickname else "微信用户"

# 对内页跳转链接参数进行标准 URL 编码，防止特殊字符断裂
safe_avatar = urllib.parse.quote(avatar)
safe_nickname = urllib.parse.quote(nickname)
nav_params = f"?webview=1&wechat_openid={wechat_openid}&avatar={safe_avatar}&nickname={safe_nickname}"

# 提取云端密钥配置
supabase_url = st.secrets["SUPABASE_URL"]
supabase_anon_key = st.secrets["SUPABASE_ANON_KEY"]

# ---------- 全局系统标准动作库 ----------
strength_parts = {
    "胸部": ["杠铃卧推", "上斜卧推", "哑铃飞鸟", "器械卧推", "夹胸", "俯卧撑"],
    "肩部": ["哑铃推举", "杠铃推举", "侧平举", "前平举", "面拉", "蝴蝶机反向飞鸟"],
    "背部": ["引体向上", "杠铃划船", "哑铃划船", "高位下拉", "坐姿划船", "硬拉"],
    "二头": ["杠铃弯举", "哑铃弯举", "锤式弯举", "集中弯举", "牧师凳弯举"],
    "三头": ["窄距卧推", "绳索下压", "哑铃臂屈伸", "双杠臂屈伸", "俯身臂屈伸"],
    "腹部": ["卷腹", "平板支撑", "仰卧抬腿", "俄罗斯转体", "悬垂举腿", "健腹轮"],
    "腿部": ["深蹲", "腿举", "腿弯举", "腿屈伸", "箭步蹲", "罗马尼亚硬拉"]
}
cardio_parts = {"有氧": ["跑步", "慢跑", "跳绳", "游泳", "骑行", "椭圆机", "划船机", "高强度间歇训练", "波比跳", "壶铃摆荡", "战绳"]}
cardio_met_options = [
    ("跑步 (8 km/h)", "8.0"), ("跑步 (10 km/h)", "10.0"), ("慢跑", "7.0"),
    ("跳绳 (中速)", "10.0"), ("跳绳 (快速)", "12.0"), ("游泳 (自由泳)", "8.0"),
    ("游泳 (蛙泳)", "7.0"), ("骑行 (中等)", "6.0"), ("椭圆机", "5.0"),
    ("划船机", "7.0"), ("高强度间歇训练", "12.0"), ("自定义", "custom")
]

cardio_opts_html = "".join([f'<option value="{e}">{e}</option>' for e in cardio_parts["有氧"]])
met_opts_html = "".join([f'<option value="{v}">{k}</option>' for k, v in cardio_met_options])
strength_json = json.dumps(strength_parts, ensure_ascii=False)

# ---------- 全局统一纯净 HTML / CSS 骨架 ----------
base_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f8fafc; padding: 20px 16px 40px; min-height: 100vh; max-width: 420px; margin: 0 auto; }}
    .card {{ background: white; border-radius: 20px; padding: 20px 24px; margin-bottom: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.04); }}
    .btn {{ display: block; width: 100%; padding: 14px; background: #2563eb; color: white; border: none; border-radius: 60px; font-size: 16px; font-weight: 600; text-align: center; cursor: pointer; text-decoration: none; }}
    .btn:active {{ transform: scale(0.98); }}
    .btn-secondary {{ background: #6b7280; }}
    .input-group {{ margin-bottom: 14px; }}
    .input-group label {{ display: block; font-size: 14px; color: #334155; margin-bottom: 4px; font-weight: 500; }}
    .input-group input, .input-group select {{ width: 100%; padding: 12px; border: 1px solid #e2e8f0; border-radius: 12px; font-size: 16px; background: #f1f5f9; outline: none; }}
    .back-link {{ display: block; text-align: center; margin-top: 20px; color: #2563eb; text-decoration: none; font-size: 14px; }}
    .brand {{ text-align: center; margin-bottom: 24px; }}
    .brand h1 {{ font-size: 28px; color: #0f172a; font-weight: 700; }}
    .brand p {{ color: #94a3b8; font-size: 14px; margin-top: 4px; }}
    .menu-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }}
    .menu-item {{ background: white; border-radius: 16px; padding: 16px 8px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.04); cursor: pointer; text-decoration: none; display: block; color: #333; }}
    .menu-item .icon {{ font-size: 28px; display: block; margin-bottom: 4px; }}
    .menu-item .label {{ font-size: 12px; color: #334155; font-weight: 500; }}
    .badge {{ display: inline-block; padding: 2px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; background: #dcfce7; color: #16a34a; }}
    .stat-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f1f5f9; }}
    .stat-row:last-child {{ border-bottom: none; }}
    .avatar-img {{ width: 48px; height: 48px; border-radius: 50%; object-fit: cover; background: #e2e8f0; }}
    .user-row {{ display: flex; align-items: center; gap: 12px; }}
    .user-name {{ font-weight: 600; color: #0f172a; font-size: 16px; }}
    .toast {{ position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.85); color: white; padding: 16px 24px; border-radius: 12px; font-size: 16px; z-index: 999999; display: none; text-align: center; white-space: nowrap; }}
    .switch-mode {{ display: flex; gap: 12px; margin-bottom: 16px; }}
    .switch-mode button {{ flex: 1; padding: 10px; border: 2px solid #e2e8f0; background: white; border-radius: 12px; font-size: 14px; font-weight: 500; cursor: pointer; }}
    .switch-mode button.active {{ border-color: #2563eb; background: #eff6ff; color: #2563eb; }}
    .hidden {{ display: none; }}
    .calendar-grid {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; margin-top: 12px; }}
    .day-cell {{ text-align: center; padding: 10px 0; border-radius: 12px; background: #f1f5f9; font-size: 14px; font-weight: 500; color: #0f172a; }}
    .day-cell.trained {{ background: #2563eb; color: white; }}
    .day-cell.empty {{ background: transparent; }}
    .day-cell.weekend {{ color: #94a3b8; }}
    .month-nav {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; font-weight: 600; color: #0f172a; }}
    .month-nav button {{ background: none; border: none; font-size: 20px; cursor: pointer; padding: 0 12px; }}
    .group-item {{ display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }}
    .group-item input {{ flex: 1; padding: 8px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 14px; }}
    .add-btn {{ background: #22c55e; color: white; border: none; border-radius: 8px; padding: 6px 12px; font-size: 14px; cursor: pointer; margin-top: 4px; }}
    .remove-btn, .remove-btn-red {{ background: #ef4444; color: white; border: none; border-radius: 6px; padding: 4px 10px; font-size: 12px; cursor: pointer; }}
    .block-container {{ margin-bottom: 16px; padding: 12px; background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0; }}
</style>
</head>
<body>
<div id="toast" class="toast"></div>
<script>
    // 强制隔离闭包：底层统一数据层通信，屏蔽全局作用域变量声明冲突
    const SUPABASE_URL = '{supabase_url}';
    const SUPABASE_ANON_KEY = '{supabase_anon_key}';
    const WECHAT_OPENID = '{wechat_openid}';
    let gbToken = null;
    let gbUserId = null;

    function showToast(msg) {{
        const t = document.getElementById('toast');
        t.textContent = msg; t.style.display = 'block';
        setTimeout(() => t.style.display = 'none', 2500);
    }}

    async function getAuth() {{
        if (gbToken) return true;
        if (!WECHAT_OPENID) return false;
        try {{
            const email = WECHAT_OPENID + '@wechat.com';
            const opts = {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'apikey': SUPABASE_ANON_KEY }},
                body: JSON.stringify({{ email, password: 'wechat123' }})
            }};
            let res = await fetch(SUPABASE_URL + '/auth/v1/token?grant_type=password', opts);
            let data = await res.json();
            
            if (!data.access_token) {{
                res = await fetch(SUPABASE_URL + '/auth/v1/signup', opts);
                data = await res.json();
            }}
            
            if (data.access_token) {{
                gbToken = data.access_token; 
                gbUserId = data.user.id;
                
                // 静默维护用户云端 profiles 基础字典映射
                fetch(SUPABASE_URL + '/rest/v1/profiles?user_id=eq.' + gbUserId, {{
                    method: 'PATCH',
                    headers: {{ 'Content-Type': 'application/json', 'apikey': SUPABASE_ANON_KEY, 'Authorization': 'Bearer ' + gbToken }},
                    body: JSON.stringify({{ avatar_url: '{avatar}', nickname: '{nickname}' }})
                }}).catch(e => console.log(e));
                
                return true;
            }}
        }} catch(e) {{ console.error("数据层连接挂断：", e); }}
        return false;
    }}

    async function apiRequest(method, path, body = null) {{
        if (!gbToken) await getAuth();
        const options = {{
            method,
            headers: {{ 'Content-Type': 'application/json', 'apikey': SUPABASE_ANON_KEY, 'Authorization': 'Bearer ' + gbToken }}
        }};
        if (body) options.body = JSON.stringify(body);
        const r = await fetch(SUPABASE_URL + path, options);
        return r.json();
    }}
</script>
"""

# ---------- 路由分支一：首页系统渲染 ----------
if tab == "home":
    html_body = f"""
    <div class="brand"><h1>🦋 茧记</h1><p>记录 · 蜕变</p></div>
    
    <div class="card">
        <div class="user-row">
            <img class="avatar-img" src="{display_avatar}" alt="头像">
            <div>
                <div class="user-name">{display_nickname}</div>
                <div id="loginStatus" style="font-size:12px; color:#94a3b8;">系统连接中...</div>
            </div>
            <span class="badge" style="margin-left:auto;">在线</span>
        </div>
    </div>
    
    <div class="menu-grid">
        <a href="{nav_params}&tab=settings" class="menu-item"><span class="icon">⚙️</span><span class="label">个人设置</span></a>
        <a href="{nav_params}&tab=calendar" class="menu-item"><span class="icon">📅</span><span class="label">训练日历</span></a>
        <a href="{nav_params}&tab=training" class="menu-item"><span class="icon">🏋️</span><span class="label">训练记录</span></a>
        <a href="{nav_params}&tab=report" class="menu-item"><span class="icon">📊</span><span class="label">今日战报</span></a>
    </div>
    
    <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <span style="font-weight:600; color:#0f172a;">📋 今日训练</span>
            <span id="todayCount" style="font-size:13px; color:#2563eb; background:#eff6ff; padding:2px 14px; border-radius:30px;">加载中...</span>
        </div>
        <div id="todayList" style="text-align:center; color:#94a3b8; padding:16px 0;">正在拉取数据...</div>
    </div>
    
    <div class="footer">数据安全加密 · Supabase 动力</div>
    <script>
    (async function() {{
        const statusEl = document.getElementById('loginStatus');
        const listEl = document.getElementById('todayList');
        const countEl = document.getElementById('todayCount');
        
        if (!await getAuth()) {{
            statusEl.textContent = '连接失败'; statusEl.style.color = '#ef4444';
            listEl.textContent = '无法建立云端连接'; countEl.textContent = '离线';
            return;
        }}
        statusEl.textContent = '已连接数据库'; statusEl.style.color = '#16a34a';

        try {{
            const today = new Date().toISOString().slice(0,10);
            const resp = await apiRequest('GET', '/rest/v1/workouts?user_id=eq.' + gbUserId + '&date=eq.' + today);
            
            // 安全防空校验，防止非数组引起下游遍历异常
            const safeResp = Array.isArray(resp) ? resp : [];
            countEl.textContent = safeResp.length + ' 项';
            
            if (safeResp.length > 0) {{
                let htmlStr = '';
                safeResp.forEach(w => {{ htmlStr += `<div style="padding:6px 0;text-align:left;color:#334155;border-bottom:1px dashed #f1f5f9;">• <b>${{w.body_part}}</b> ${{w.exercise}}：${{w.set_count || w.cardio_duration + '分钟'}}</div>`; }});
                listEl.innerHTML = htmlStr;
            }} else {{
                listEl.textContent = '今天还没有训练记录，开始吧 💪';
            }}
        }} catch(e) {{
            listEl.textContent = '今日日志加载失败'; countEl.textContent = '异常';
        }}
    }})();
    </script>
    </body></html>
    """
    st.html(base_html + html_body)

# ---------- 路由分支二：训练记录动态表单 ----------
elif tab == "training":
    html_body = f"""
    <div class="brand"><h1>🏋️ 训练记录</h1><p>记录每一次进步</p></div>
    <div class="card">
        <div class="switch-mode">
            <button id="modeStrength" class="active" onclick="window.switchMode('strength')">💪 力量训练</button>
            <button id="modeCardio" onclick="window.switchMode('cardio')">🏃 有氧训练</button>
        </div>
        <form id="workoutForm">
            <div id="strengthFields">
                <div id="strengthBlocks"></div>
                <button type="button" class="btn btn-secondary" onclick="window.addStrengthBlock()">+ 添加动作部位</button>
            </div>
            <div id="cardioFields" class="hidden">
                <div class="input-group"><label>有氧动作</label><select id="cardioExercise">{cardio_opts_html}</select></div>
                <div class="input-group"><label>时长 (分钟)</label><input type="number" id="cardioDuration" value="30" min="1"></div>
                <div class="input-group"><label>运动强度 (MET)</label><select id="metSelect" onchange="window.toggleMet()">{met_opts_html}</select></div>
                <div class="input-group hidden" id="customMetGroup"><label>自定义 MET 值</label><input type="number" id="customMet" value="8.0" step="0.1"></div>
            </div>
            <button type="button" class="btn" onclick="window.saveWorkout()" style="margin-top:16px;">保存训练日志</button>
        </form>
    </div>
    <a href="{nav_params}&tab=home" class="back-link">← 返回主菜单页</a>
    <script>
    (function() {{
        const STRENGTH_PARTS = {strength_json};
        let blockCount = 0;

        window.switchMode = function(mode) {{
            document.getElementById('modeStrength').classList.toggle('active', mode === 'strength');
            document.getElementById('modeCardio').classList.toggle('active', mode === 'cardio');
            document.getElementById('strengthFields').style.display = mode === 'strength' ? 'block' : 'none';
            document.getElementById('cardioFields').style.display = mode === 'cardio' ? 'block' : 'none';
        }};

        window.toggleMet = function() {{
            document.getElementById('customMetGroup').style.display = document.getElementById('metSelect').value === 'custom' ? 'block' : 'none';
        }};

        window.addStrengthBlock = function() {{
            blockCount++;
            const container = document.getElementById('strengthBlocks');
            const blockId = 'block_' + blockCount;
            let partOptions = '';
            for (let p in STRENGTH_PARTS) partOptions += `<option value="${{p}}">${{p}}</option>`;
            
            const div = document.createElement('div');
            div.className = 'block-container';
            div.id = blockId;
            div.innerHTML = `
                <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                    <b>动作模块 ${{blockCount}}</b><button type="button" class="remove-btn-red" onclick="document.getElementById('${{blockId}}').remove()">移除</button>
                </div>
                <div class="input-group"><label>目标部位</label><select class="b-part" onchange="window.updateEx('${{blockId}}')">${{partOptions}}</select></div>
                <div class="input-group"><label>训练动作</label><select class="b-ex"></select></div>
                <div class="input-group"><label>目标组数</label><input type="number" class="b-sets" value="3" min="1" onchange="window.genGroups('${{blockId}}')"></div>
                <div id="${{blockId}}_groups"></div>
                <button type="button" class="add-btn" onclick="window.addGroup('${{blockId}}')">+ 追加一组</button>
            `;
            container.appendChild(div);
            window.updateEx(blockId);
            window.genGroups(blockId);
        }};

        window.updateEx = function(blockId) {{
            const part = document.querySelector('#' + blockId + ' .b-part').value;
            document.querySelector('#' + blockId + ' .b-ex').innerHTML = (STRENGTH_PARTS[part] || []).map(e => `<option value="${{e}}">${{e}}</option>`).join('');
        }};

        window.genGroups = function(blockId) {{
            const count = parseInt(document.querySelector('#' + blockId + ' .b-sets').value) || 0;
            document.getElementById(blockId + '_groups').innerHTML = '';
            for (let i=0; i<count; i++) window.addGroup(blockId, i+1);
        }};

        window.addGroup = function(blockId, idxLabel=null) {{
            const container = document.getElementById(blockId + '_groups');
            const idx = idxLabel || (container.children.length + 1);
            const div = document.createElement('div');
            div.className = 'group-item';
            div.innerHTML = `<span>${{idx}}组.</span><input type="number" placeholder="次数" class="g-reps" value="10"><input type="number" placeholder="重量(kg)" class="g-weight" value="20"><button type="button" class="remove-btn" onclick="this.parentElement.remove()">✕</button>`;
            container.appendChild(div);
        }};

        window.saveWorkout = async function() {{
            if (!await getAuth()) return showToast('用户鉴权拒绝，保存终止');
            const isStrength = document.getElementById('modeStrength').classList.contains('active');
            let records = [];

            if (isStrength) {{
                const blocks = document.querySelectorAll('.block-container');
                if (!blocks.length) return showToast('需至少配置一个动作部位');
                blocks.forEach(b => {{
                    const part = b.querySelector('.b-part').value;
                    const ex = b.querySelector('.b-ex').value;
                    const reps = b.querySelectorAll('.g-reps');
                    const weights = b.querySelectorAll('.g-weight');
                    let details = [];
                    for(let i=0; i<reps.length; i++) if (parseInt(reps[i].value) > 0) details.push(`${{reps[i].value}}次×${{weights[i].value}}kg`);
                    if(details.length) records.push({{ user_id: gbUserId, date: new Date().toISOString().slice(0,10), body_part: part, exercise: ex, set_count: details.length, details: details.join('; '), cardio_duration: null, met_value: null }});
                }});
            }} else {{
                const ex = document.getElementById('cardioExercise').value;
                const dur = parseInt(document.getElementById('cardioDuration').value) || 0;
                let met = document.getElementById('metSelect').value === 'custom' ? parseFloat(document.getElementById('customMet').value) : parseFloat(document.getElementById('metSelect').value);
                if (dur <= 0) return showToast('请输入合理的训练时长');
                records.push({{ user_id: gbUserId, date: new Date().toISOString().slice(0,10), body_part: '有氧', exercise: ex, set_count: 0, details: '', cardio_duration: dur, met_value: met }});
            }}

            if (!records.length) return showToast('暂无合规数据可用于同步');
            let success = true;
            for (let r of records) {{
                let res = await apiRequest('POST', '/rest/v1/workouts', r);
                if (res && res.error) success = false;
            }}
            showToast(success ? '训练日志已同步成功！' : '日志保存出现局部失败');
        }};

        window.addStrengthBlock();
    }})();
    </script>
    </body></html>
    """
    st.html(base_html + html_body)

# ---------- 路由分支三：训练出勤日历系统 ----------
elif tab == "calendar":
    html_body = f"""
    <div class="brand"><h1>📅 训练日历</h1><p id="monthYear">数据加载中...</p></div>
    <div class="card">
        <div class="month-nav">
            <button id="prevMonth">◀</button>
            <span id="currentMonth">---</span>
            <button id="nextMonth">▶</button>
        </div>
        <div id="calendarGrid" class="calendar-grid"></div>
        <div style="margin-top:16px;text-align:center;font-size:14px;color:#475569;">
            本月已累计打卡：<b id="attendanceCount" style="color:#2563eb;font-size:16px;">0</b> 天
        </div>
    </div>
    <a href="{nav_params}&tab=home" class="back-link">← 返回主菜单页</a>
    <script>
    (function() {{
        let d = new Date();
        let currYear = d.getFullYear(), currMonth = d.getMonth();
        const mNames = ['一月','二月','三月','四月','五月','六月','七月','八月','九月','十月','十一月','十二月'];

        async function initCalendar() {{
            if (!await getAuth()) return showToast('未登录，日历未就绪');
            
            const firstDay = new Date(currYear, currMonth, 1).toISOString().slice(0,10);
            const lastDay = new Date(currYear, currMonth + 1, 0).toISOString().slice(0,10);
            
            try {{
                const resp = await apiRequest('GET', `/rest/v1/workouts?user_id=eq.${{gbUserId}}&date=gte.${{firstDay}}&date=lte.${{lastDay}}&select=date`);
                const safeResp = Array.isArray(resp) ? resp : [];
                const trainedSet = new Set(safeResp.map(w => w.date));
                
                renderView(trainedSet);
            }} catch(e) {{ showToast('数据打卡打标记失败'); }}
        }}

        function renderView(trainedSet) {{
            const grid = document.getElementById('calendarGrid');
            const startDay = new Date(currYear, currMonth, 1).getDay();
            const totalDays = new Date(currYear, currMonth + 1, 0).getDate();
            
            let htmlStr = ['日','一','二','三','四','五','六'].map(w => `<div class="day-cell weekend">${{w}}</div>`).join('');
            for (let i = 0; i < startDay; i++) htmlStr += '<div class="day-cell empty"></div>';
            
            let tCount = 0;
            for (let day = 1; d <= totalDays; day++) {{
                // 解决时区偏移导致日期缩进偏差
                const dateStr = `${{currYear}}-${{String(currMonth+1).padStart(2,'0')}}-${{String(day).padStart(2,'0')}}`;
                const isTrained = trainedSet.has(dateStr);
                if (isTrained) tCount++;
                htmlStr += `<div class="day-cell ${{isTrained ? 'trained' : ''}}">${{day}}</div>`;
                if(day >= totalDays) break;
            }}
            
            grid.innerHTML = htmlStr;
            document.getElementById('currentMonth').textContent = currYear + '年 ' + mNames[currMonth];
            document.getElementById('monthYear').textContent = currYear + '年 ' + mNames[currMonth];
            document.getElementById('attendanceCount').textContent = tCount;
        }}

        document.getElementById('prevMonth').onclick = () => {{
            if (currMonth === 0) {{ currMonth = 11; currYear--; }} else currMonth--;
            initCalendar();
        }};
        document.getElementById('nextMonth').onclick = () => {{
            if (currMonth === 11) {{ currMonth = 0; currYear++; }} else currMonth++;
            initCalendar();
        }};

        initCalendar();
    }})();
    </script>
    </body></html>
    """
    st.html(base_html + html_body)

# ---------- 路由分支四：今日动态智能战报 ----------
elif tab == "report":
    html_body = f"""
    <div class="brand"><h1>📊 今日战报</h1><p>{datetime.now().strftime("%Y年%m月%d日")}</p></div>
    <div class="card" id="reportContent"><div style="text-align:center; padding:20px; color:#94a3b8;">正在多维建模生成综合战报...</div></div>
    <a href="{nav_params}&tab=home" class="back-link">← 返回主菜单页</a>
    <script>
    (async function() {{
        const box = document.getElementById('reportContent');
        if (!await getAuth()) return box.innerHTML = '<div style="text-align:center;padding:20px;color:#ef4444;">系统初始化失败</div>';
        
        try {{
            const today = new Date().toISOString().slice(0,10);
            
            // 采用并发并行请求，降低网络WebView阻塞时耗
            const [workouts, profile] = await Promise.all([
                apiRequest('GET', '/rest/v1/workouts?user_id=eq.' + gbUserId + '&date=eq.' + today),
                apiRequest('GET', '/rest/v1/profiles?user_id=eq.' + gbUserId)
            ]);
            
            // 安全解构与回退字段，防止由于 'train_data' 等键值不存在产生 Python 侧的 KeyError 
            const safeWorkouts = Array.isArray(workouts) ? workouts : [];
            let weight = (Array.isArray(profile) && profile.length) ? (profile[0].weight || 70) : 70;

            let totalCal = 0, parts = new Set(), actions = new Set(), detailHtml = '';
            
            if (safeWorkouts.length > 0) {{
                safeWorkouts.forEach(w => {{
                    parts.add(w.body_part); actions.add(w.exercise);
                    if (w.met_value) {{
                        let cal = w.met_value * weight * ((w.cardio_duration || 30) / 60);
                        totalCal += cal;
                        detailHtml += `<div style="font-size:14px;padding:4px 0;color:#475569;">• 🏃有氧 [${{w.exercise}}]：时长${{w.cardio_duration}}分钟，消耗 ~${{Math.round(cal)}}kcal</div>`;
                    }} else {{
                        let sets = w.set_count || 0;
                        let cal = 5 * weight * (sets * 2 / 60); // 经典阻抗模型物理消耗转化
                        totalCal += cal;
                        detailHtml += `<div style="font-size:14px;padding:4px 0;color:#475569;">• 💪力量 [${{w.body_part}}·${{w.exercise}}]：累计${{sets}}组，消耗 ~${{Math.round(cal)}}kcal</div>`;
                    }}
                }});
            }}
            
            box.innerHTML = `
                <div class="stat-row"><span class="stat-label">🏋️ 动用集群</span><span class="stat-value">${{Array.from(parts).join('、') || '暂无'}}</span></div>
                <div class="stat-row"><span class="stat-label">📊 累计打击动作</span><span class="stat-value">${{Array.from(actions).join('、') || '暂无'}}</span></div>
                <div class="stat-row"><span class="stat-label">🔥 今日总做功消耗</span><span class="stat-value" style="color:#ef4444;font-size:18px;">${{Math.round(totalCal)}} 千卡</span></div>
                <div style="margin-top:16px;border-top:1px solid #f1f5f9;padding-top:12px;">
                    <h3 style="font-size:15px;color:#0f172a;margin-bottom:8px;">📋 详细做功能源清单</h3>
                    ${{detailHtml || '<div style="color:#94a3b8;font-size:13px;text-align:center;padding:12px;">今日尚未向服务器上报任何做功矩阵</div>'}}
                </div>
            `;
        }} catch(e) {{
            box.innerHTML = '<div style="text-align:center;padding:20px;color:#ef4444;">综合战报建模崩溃，请确认日志数据健全性</div>';
        }}
    }})();
    </script>
    </body></html>
    """
    st.html(base_html + html_body)

# ---------- 路由分支五：个人身体配置与消息设置 ----------
elif tab == "settings":
    html_body = f"""
    <div class="brand"><h1>⚙️ 个人设置</h1><p>更新基本特征与推送通道</p></div>
    <div class="card">
        <form id="profileForm">
            <div class="input-group"><label>当前体重 (kg)</label><input type="number" id="weight" step="0.1" value="70"></div>
            <div class="input-group"><label>当前身高 (cm)</label><input type="number" id="height" step="1" value="175"></div>
            <button type="button" class="btn" onclick="window.saveProfile()">覆盖更新特征档案</button>
        </form>
    </div>
    <div class="card">
        <h3 style="font-size:16px; color:#0f172a; margin-bottom:12px;">📲 微信全自动日报推送</h3>
        <div class="input-group"><label>PushPlus 通道密钥 (Token)</label><input type="text" id="pushToken" placeholder="请前往 pushplus.plus 获取"></div>
        <label style="display:flex; align-items:center; gap:8px; font-size:14px; color:#334155; margin:8px 0 14px;">
            <input type="checkbox" id="pushEnabled" checked> 开启 GitHub Actions 每晚 22:30 定时推送战报
        </label>
        <button type="button" class="btn" onclick="window.savePushSettings()">覆写通道策略</button>
    </div>
    <a href="{nav_params}&tab=home" class="back-link">← 返回主菜单页</a>
    <script>
    (async function() {{
        if (!await getAuth()) return showToast('鉴权挂断，无法初始化档案');
        
        try {{
            const [profile, push] = await Promise.all([
                apiRequest('GET', '/rest/v1/profiles?user_id=eq.' + gbUserId),
                apiRequest('GET', '/rest/v1/user_push_settings?user_id=eq.' + gbUserId)
            ]);
            
            if (Array.isArray(profile) && profile.length) {{
                document.getElementById('weight').value = profile[0].weight || 70;
                document.getElementById('height').value = profile[0].height || 175;
            }}
            if (Array.isArray(push) && push.length) {{
                document.getElementById('pushToken').value = push[0].pushplus_token || '';
                document.getElementById('pushEnabled').checked = push[0].is_enabled;
            }}
        }} catch(e) {{ console.error(e); }}

        window.saveProfile = async function() {{
            const weight = parseFloat(document.getElementById('weight').value);
            const height = parseFloat(document.getElementById('height').value);
            await apiRequest('PATCH', '/rest/v1/profiles?user_id=eq.' + gbUserId, {{ weight, height }});
            showToast('档案字典更新成功');
        }};

        window.savePushSettings = async function() {{
            const token = document.getElementById('pushToken').value.trim();
            const enabled = document.getElementById('pushEnabled').checked;
            // 采用 upsert 进行单用户唯一记录覆盖写入
            await apiRequest('POST', '/rest/v1/user_push_settings', {{ user_id: gbUserId, pushplus_token: token, is_enabled: enabled }});
            showToast('微信自动化推送策略已同步');
        }};
    }})();
    </script>
    </body></html>
    """
    st.html(base_html + html_body)
