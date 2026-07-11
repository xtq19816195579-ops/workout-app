import streamlit as st
import json
import urllib.parse
from datetime import datetime

# 设置页面
st.set_page_config(page_title="茧记", page_icon="🦋", layout="wide")

query_params = st.query_params

# 拦截非小程序访问
if query_params.get("webview") != "1":
    st.write("请通过微信小程序访问")
    st.stop()

# 获取 URL 参数
tab = query_params.get("tab", "home")
wechat_openid = query_params.get("wechat_openid", "")
avatar = query_params.get("avatar", "")
nickname = query_params.get("nickname", "微信用户")

# 【关键修复 1】：处理默认显示
display_avatar = avatar if avatar else "https://mmbiz.qpic.cn/mmbiz/icTdbqWNOwNRna42FI242Lcia07jQodd2FJGIYQfG0LAJGFxM4FbnQP6yfMxBgJ0F3YRqJCJ1aPAK2dQagdusBZg/0"
display_nickname = nickname if nickname else "微信用户"

# 生成带参数的安全跳转链接
safe_avatar = urllib.parse.quote(avatar)
safe_nickname = urllib.parse.quote(nickname)
nav_params = f"?webview=1&wechat_openid={wechat_openid}&avatar={safe_avatar}&nickname={safe_nickname}"

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

# ---------- 全局 CSS 与 核心鉴权 JS ----------
head_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f8fafc; padding: 20px 16px 40px; min-height: 100vh; max-width: 420px; margin: 0 auto; }}
    .card {{ background: white; border-radius: 20px; padding: 20px 24px; margin-bottom: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.04); }}
    .btn {{ display: block; width: 100%; padding: 14px; background: #2563eb; color: white; border: none; border-radius: 60px; font-size: 16px; font-weight: 600; text-align: center; cursor: pointer; }}
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
        if (!WECHAT_OPENID) return null;
        try {{
            const email = WECHAT_OPENID + '@wechat.com';
            let res = await fetch(SUPABASE_URL + '/auth/v1/token?grant_type=password', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'apikey': SUPABASE_ANON_KEY }},
                body: JSON.stringify({{ email, password: 'wechat123' }})
            }});
            let data = await res.json();
            
            if (data.access_token) {{
                gbToken = data.access_token; gbUserId = data.user.id;
                return true;
            }} else {{
                res = await fetch(SUPABASE_URL + '/auth/v1/signup', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json', 'apikey': SUPABASE_ANON_KEY }},
                    body: JSON.stringify({{ email, password: 'wechat123' }})
                }});
                data = await res.json();
                if (data.access_token) {{
                    gbToken = data.access_token; gbUserId = data.user.id;
                    return true;
                }}
            }}
        }} catch(e) {{ console.error("鉴权失败", e); }}
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

# ---------- 首页 ----------
if tab == "home":
    html_body = f"""
    <div class="brand"><h1>🦋 茧记</h1><p>记录 · 蜕变</p></div>
    
    <div class="card">
        <div class="user-row">
            <img class="avatar-img" src="{display_avatar}" alt="头像">
            <div>
                <div class="user-name">{display_nickname}</div>
                <div class="user-status" id="loginStatus" style="font-size:12px; color:#94a3b8;">系统连接中...</div>
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
    
    <script>
    // 独立且自执行的业务逻辑，不依赖全局 onload
    (async function() {{
        const statusEl = document.getElementById('loginStatus');
        const listEl = document.getElementById('todayList');
        const countEl = document.getElementById('todayCount');
        
        if (!await getAuth()) {{
            statusEl.textContent = '连接失败';
            statusEl.style.color = 'red';
            listEl.textContent = '无法连接数据库';
            countEl.textContent = '错误';
            return;
        }}
        statusEl.textContent = '已连接数据库';
        statusEl.style.color = '#16a34a';

        try {{
            const today = new Date().toISOString().slice(0,10);
            const resp = await apiRequest('GET', '/rest/v1/workouts?user_id=eq.' + gbUserId + '&date=eq.' + today);
            
            if (!Array.isArray(resp)) throw new Error("API 响应异常");
            
            countEl.textContent = resp.length + ' 项';
            if (resp.length > 0) {{
                let html = '';
                resp.forEach(w => {{ html += `<div style="padding:4px 0;text-align:left;color:#333;">• ${{w.body_part}} ${{w.exercise}}：${{w.set_count || 0}}组</div>`; }});
                listEl.innerHTML = html;
            }} else {{
                listEl.textContent = '今天还没有训练记录，开始吧 💪';
            }}
        }} catch(e) {{
            listEl.textContent = '数据加载失败';
            countEl.textContent = '错误';
        }}
    }})();
    </script>
    </body></html>
    """
    st.html(head_html + html_body)

# ---------- 训练记录 ----------
elif tab == "training":
    html_body = f"""
    <div class="brand"><h1>🏋️ 训练记录</h1><p>记录每一次进步</p></div>
    <div class="card">
        <div class="switch-mode">
            <button id="modeStrength" class="active" onclick="switchMode('strength')">💪 力量</button>
            <button id="modeCardio" onclick="switchMode('cardio')">🏃 有氧</button>
        </div>
        <form id="workoutForm">
            <div id="strengthFields">
                <div id="strengthBlocks"></div>
                <button type="button" class="btn btn-secondary" onclick="addStrengthBlock()">+ 添加部位</button>
            </div>
            <div id="cardioFields" class="hidden">
                <div class="input-group"><label>动作</label><select id="cardioExercise">{cardio_opts_html}</select></div>
                <div class="input-group"><label>时长 (分钟)</label><input type="number" id="cardioDuration" value="30" min="1"></div>
                <div class="input-group"><label>强度 (MET)</label><select id="metSelect" onchange="toggleMet()">{met_opts_html}</select></div>
                <div class="input-group hidden" id="customMetGroup"><label>自定义 MET</label><input type="number" id="customMet" value="8.0" step="0.1"></div>
            </div>
            <button type="button" class="btn" onclick="saveWorkout()" style="margin-top:12px;">保存记录</button>
        </form>
    </div>
    <a href="{nav_params}&tab=home" class="back-link">← 返回首页</a>
    
    <script>
        const STRENGTH_PARTS = {strength_json};
        let blockCount = 0;

        function switchMode(mode) {{
            document.getElementById('modeStrength').classList.toggle('active', mode === 'strength');
            document.getElementById('modeCardio').classList.toggle('active', mode === 'cardio');
            document.getElementById('strengthFields').style.display = mode === 'strength' ? 'block' : 'none';
            document.getElementById('cardioFields').style.display = mode === 'cardio' ? 'block' : 'none';
        }}
        function toggleMet() {{
            document.getElementById('customMetGroup').style.display = document.getElementById('metSelect').value === 'custom' ? 'block' : 'none';
        }}

        function addStrengthBlock() {{
            blockCount++;
            const container = document.getElementById('strengthBlocks');
            const blockId = 'block_' + blockCount;
            let partOpts = '';
            for (let p in STRENGTH_PARTS) partOpts += `<option value="${{p}}">${{p}}</option>`;
            
            const div = document.createElement('div');
            div.className = 'block-container';
            div.id = blockId;
            div.innerHTML = `
                <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                    <b>部位 ${{blockCount}}</b>
                    <button type="button" class="remove-btn-red" onclick="document.getElementById('${{blockId}}').remove()">删除</button>
                </div>
                <div class="input-group"><label>部位</label><select class="b-part" onchange="updateEx('${{blockId}}')">${{partOpts}}</select></div>
                <div class="input-group"><label>动作</label><select class="b-ex"></select></div>
                <div class="input-group"><label>组数</label><input type="number" class="b-sets" value="3" min="1" onchange="genGroups('${{blockId}}')"></div>
                <div id="${{blockId}}_groups"></div>
                <button type="button" class="add-btn" onclick="addGroup('${{blockId}}')">+ 添加一组</button>
            `;
            container.appendChild(div);
            updateEx(blockId);
            genGroups(blockId);
        }}

        function updateEx(blockId) {{
            const part = document.querySelector('#' + blockId + ' .b-part').value;
            document.querySelector('#' + blockId + ' .b-ex').innerHTML = (STRENGTH_PARTS[part] || []).map(e => `<option value="${{e}}">${{e}}</option>`).join('');
        }}

        function genGroups(blockId) {{
            const count = parseInt(document.querySelector('#' + blockId + ' .b-sets').value) || 0;
            document.getElementById(blockId + '_groups').innerHTML = '';
            for (let i=0; i<count; i++) addGroup(blockId, i+1);
        }}

        function addGroup(blockId, idxLabel=null) {{
            const container = document.getElementById(blockId + '_groups');
            const idx = idxLabel || (container.children.length + 1);
            const div = document.createElement('div');
            div.className = 'group-item';
            div.innerHTML = `<span>${{idx}}.</span><input type="number" placeholder="次数" class="g-reps" value="10"><input type="number" placeholder="重量(kg)" class="g-weight" value="20"><button type="button" class="remove-btn" onclick="this.parentElement.remove()">✕</button>`;
            container.appendChild(div);
        }}

        async function saveWorkout() {{
            if (!await getAuth()) return showToast('未登录，无法保存');
            const isStrength = document.getElementById('modeStrength').classList.contains('active');
            let records = [];

            if (isStrength) {{
                const blocks = document.querySelectorAll('.block-container');
                if (!blocks.length) return showToast('请至少添加一个部位');
                blocks.forEach(b => {{
                    const part = b.querySelector('.b-part').value;
                    const ex = b.querySelector('.b-ex').value;
                    const reps = b.querySelectorAll('.g-reps');
                    const weights = b.querySelectorAll('.g-weight');
                    let details = [];
                    for(let i=0; i<reps.length; i++) if (reps[i].value > 0) details.push(`${{reps[i].value}}次×${{weights[i].value}}kg`);
                    if(details.length) records.push({{ user_id: gbUserId, date: new Date().toISOString().slice(0,10), body_part: part, exercise: ex, set_count: details.length, details: details.join('; '), cardio_duration: null, met_value: null }});
                }});
            }} else {{
                const ex = document.getElementById('cardioExercise').value;
                const dur = parseInt(document.getElementById('cardioDuration').value) || 0;
                let met = document.getElementById('metSelect').value === 'custom' ? parseFloat(document.getElementById('customMet').value) : parseFloat(document.getElementById('metSelect').value);
                if (dur <= 0) return showToast('请输入有效时长');
                records.push({{ user_id: gbUserId, date: new Date().toISOString().slice(0,10), body_part: '有氧', exercise: ex, set_count: 0, details: '', cardio_duration: dur, met_value: met }});
            }}

            if (!records.length) return showToast('无有效记录');
            let success = true;
            for (let r of records) {{
                let res = await apiRequest('POST', '/rest/v1/workouts', r);
                if (res.error) success = false;
            }}
            showToast(success ? '保存成功！' : '部分保存失败');
        }}

        // 初始化一列力量训练
        addStrengthBlock();
    </script>
    </body></html>
    """
    st.html(head_html + html_body)

# ---------- 今日战报 ----------
elif tab == "report":
    html_body = f"""
    <div class="brand"><h1>📊 今日战报</h1><p>{datetime.now().strftime("%Y年%m月%d日")}</p></div>
    <div class="card" id="reportContent"><div style="text-align:center; padding:20px;">正在生成战报...</div></div>
    <a href="{nav_params}&tab=home" class="back-link">← 返回首页</a>
    <script>
    (async function() {{
        const box = document.getElementById('reportContent');
        if (!await getAuth()) return box.innerHTML = '<div style="text-align:center;padding:20px;">鉴权失败</div>';
        
        try {{
            const today = new Date().toISOString().slice(0,10);
            const workouts = await apiRequest('GET', '/rest/v1/workouts?user_id=eq.' + gbUserId + '&date=eq.' + today);
            const profile = await apiRequest('GET', '/rest/v1/profiles?user_id=eq.' + gbUserId);
            
            let weight = (Array.isArray(profile) && profile.length) ? (profile[0].weight || 70) : 70;
            let totalCal = 0, parts = new Set(), actions = new Set(), detailHtml = '';
            
            if (Array.isArray(workouts) && workouts.length) {{
                workouts.forEach(w => {{
                    parts.add(w.body_part); actions.add(w.exercise);
                    if (w.met_value) {{
                        let cal = w.met_value * weight * (w.cardio_duration / 60);
                        totalCal += cal;
                        detailHtml += `<div>• ${{w.body_part}} ${{w.exercise}}：${{w.cardio_duration}}分钟，消耗 ~${{Math.round(cal)}}千卡</div>`;
                    }} else {{
                        let cal = 5 * weight * ((w.set_count || 0) * 2 / 60);
                        totalCal += cal;
                        detailHtml += `<div>• ${{w.body_part}} ${{w.exercise}}：${{w.set_count}}组，消耗 ~${{Math.round(cal)}}千卡</div>`;
                    }}
                }});
            }}
            
            box.innerHTML = `
                <div class="stat-row"><span class="stat-label">🏋️ 训练部位</span><span class="stat-value">${{Array.from(parts).join('、') || '无'}}</span></div>
                <div class="stat-row"><span class="stat-label">📊 完成动作</span><span class="stat-value">${{Array.from(actions).join('、') || '无'}}</span></div>
                <div class="stat-row"><span class="stat-label">🔥 估算消耗</span><span class="stat-value" style="color:#ef4444;">${{Math.round(totalCal)}} 千卡</span></div>
                <div style="margin-top:16px;"><h3 style="font-size:16px; margin-bottom:8px;">✅ 详细记录</h3>${{detailHtml || '<div style="color:#94a3b8;">今日无训练记录</div>'}}</div>
            `;
        }} catch(e) {{
            box.innerHTML = '<div style="text-align:center;padding:20px;">生成失败</div>';
        }}
    }})();
    </script>
    </body></html>
    """
    st.html(head_html + html_body)

# ---------- 其他页面简写 (日历/设置) 为了演示已简化，可按相同模式扩展 ----------
else:
    st.html(head_html + f"""
    <div class="brand"><h1>建设中...</h1></div>
    <a href="{nav_params}&tab=home" class="back-link">← 返回首页</a>
    </body></html>
    """)
