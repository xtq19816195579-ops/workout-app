import os
import requests
from datetime import datetime
from supabase import create_client, Client

# ---------- 配置 ----------
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
PUSHPLUS_TOKEN = os.environ["PUSHPLUS_TOKEN"]

# 你自己的邮箱（用于定位 user_id）
YOUR_EMAIL = "你的注册邮箱@example.com"   # ⚠️ 替换为你的实际邮箱

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# ---------- 位移字典 ----------
DISPLACEMENT = {
    "杠铃卧推": 0.5, "上斜卧推": 0.5, "哑铃飞鸟": 0.4, "器械卧推": 0.5,
    "夹胸": 0.3, "俯卧撑": 0.3, "哑铃推举": 0.4, "杠铃推举": 0.4,
    "侧平举": 0.3, "前平举": 0.3, "面拉": 0.3, "蝴蝶机反向飞鸟": 0.3,
    "引体向上": 0.4, "杠铃划船": 0.5, "哑铃划船": 0.5, "高位下拉": 0.5,
    "坐姿划船": 0.4, "硬拉": 0.6, "杠铃弯举": 0.3, "哑铃弯举": 0.3,
    "锤式弯举": 0.3, "集中弯举": 0.3, "牧师凳弯举": 0.3,
    "窄距卧推": 0.4, "绳索下压": 0.3, "哑铃臂屈伸": 0.3,
    "双杠臂屈伸": 0.4, "俯身臂屈伸": 0.3,
    "深蹲": 0.6, "腿举": 0.5, "腿弯举": 0.4, "腿屈伸": 0.4,
    "箭步蹲": 0.5, "罗马尼亚硬拉": 0.6
}

# ---------- 用户查找（修复 .users 错误）----------
def get_user_id(email):
    try:
        res = supabase.auth.admin.list_users()
        # res 是一个列表，每个元素是一个用户字典
        for user in res:
            if user.email == email:
                return user.id
    except Exception as e:
        print(f"获取用户列表失败: {e}")
    return None

# ---------- 数据读取 ----------
def load_today_workouts(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    res = supabase.table("workouts").select("*").eq("user_id", user_id).eq("date", today).execute()
    return res.data

def load_today_durations(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    res = supabase.table("training_durations").select("duration_min").eq("user_id", user_id).eq("date", today).execute()
    total = sum(row["duration_min"] for row in res.data)
    return total

# ---------- 消耗计算 ----------
def compress_details(detail_str):
    if not detail_str:
        return ""
    groups = detail_str.split('; ')
    order_map = {}
    count_map = {}
    for idx, g in enumerate(groups):
        try:
            reps, weight = g.split('次×')
            weight = weight.rstrip('kg')
        except:
            continue
        key = (reps, weight)
        if key not in order_map:
            order_map[key] = idx
            count_map[key] = 0
        count_map[key] += 1
    sorted_keys = sorted(order_map.keys(), key=lambda k: order_map[k])
    lines = []
    for reps, weight in sorted_keys:
        cnt = count_map[(reps, weight)]
        lines.append(f"{cnt}组×{reps}次×{weight}kg" if cnt > 1 else f"1组×{reps}次×{weight}kg")
    return '\n'.join(lines)

def calc_strength_calories(exercise, details, body_weight=70):
    displacement = DISPLACEMENT.get(exercise, 0.0)
    if displacement == 0.0 or not details:
        return 0.0
    total_joules = 0
    groups = details.split('; ')
    for g in groups:
        try:
            reps, weight_part = g.split('次×')
            weight = float(weight_part.replace('kg', ''))
            reps = int(reps)
            if exercise in ["引体向上", "双杠臂屈伸"]:
                weight = body_weight * 0.9
            joules = weight * 9.8 * displacement * reps
            total_joules += joules
        except:
            continue
    if total_joules == 0:
        return 0.0
    return round(total_joules / 0.22 / 4184, 2)

def calc_cardio_calories(duration_min, met_value, body_weight=70):
    if not duration_min or not met_value:
        return 0.0
    return round(met_value * body_weight * (duration_min / 60), 2)

# ---------- 生成战报 ----------
def generate_report():
    user_id = get_user_id(YOUR_EMAIL)
    if not user_id:
        print("未找到该邮箱对应的用户")
        return None

    workouts = load_today_workouts(user_id)
    if not workouts:
        return None

    total_duration = load_today_durations(user_id)
    if total_duration == 0:
        strength_sets = sum(row['set_count'] for row in workouts if not row.get('cardio_duration'))
        cardio_dur = sum(row['cardio_duration'] for row in workouts if row.get('cardio_duration'))
        total_duration = strength_sets * 2 + cardio_dur

    h = int(total_duration // 60)
    m = int(total_duration % 60)
    dur_str = f"{h}小时{m}分钟" if h else f"{m}分钟"

    total_kcal = 0.0
    parts = set()
    actions = []
    detailed_lines = []
    for row in workouts:
        parts.add(row['body_part'])
        actions.append(row['exercise'])
        if row.get('cardio_duration'):
            cal = calc_cardio_calories(row['cardio_duration'], row['met_value'])
            detailed_lines.append(f"  - {row['body_part']} {row['exercise']}：{row['cardio_duration']} 分钟 (MET {row['met_value']})")
        else:
            cal = calc_strength_calories(row['exercise'], row['details'])
            detail_compressed = compress_details(row['details'])
            detailed_lines.append(f"  - {row['body_part']} {row['exercise']}：{int(row['set_count'])}组")
            if detail_compressed:
                detailed_lines.append(f"    {detail_compressed.replace(chr(10), chr(10) + '    ')}")
        total_kcal += cal

    total_kcal = round(total_kcal, 1)

    report = f"【{datetime.now().strftime('%Y-%m-%d')} 训练战报】\n"
    report += f"🏋️ 训练部位：{'、'.join(parts)}\n"
    report += f"📊 完成动作：{'、'.join(list(set(actions)))}\n"
    report += f"⏱️ 训练总时长：{dur_str}\n"
    report += f"🔥 估算消耗：{total_kcal} 千卡\n"
    report += "✅ 详细记录：\n"
    report += "\n".join(detailed_lines)
    report += "\n🚀 继续保持，你是最棒的！"
    return report

def push_to_wechat(content):
    if not content:
        return
    url = "http://www.pushplus.plus/send"
    data = {"token": PUSHPLUS_TOKEN, "title": "训练战报", "content": content, "template": "txt"}
    resp = requests.post(url, json=data)
    print(f"推送状态：{resp.status_code}, {resp.text}")

if __name__ == "__main__":
    report = generate_report()
    if report:
        push_to_wechat(report)
    else:
        print("今日无训练记录，不推送。")
