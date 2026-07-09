import os
import requests
from datetime import date, datetime
from supabase import create_client, Client

# ---------- 配置 ----------
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
PUSHPLUS_API = "https://www.pushplus.plus/send"

# 初始化 Supabase 客户端（使用 Service Role）
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# ---------- 位移字典（米，用于做功计算）----------
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
    "箭步蹲": 0.5, "罗马尼亚硬拉": 0.6,
    # 以下无位移，将用MET兜底
    "波比跳": 0, "壶铃摆荡": 0, "战绳": 0, "有氧跑步": 0, "跳绳": 0,
    "平板支撑": 0, "卷腹": 0, "仰卧抬腿": 0, "俄罗斯转体": 0,
    "悬垂举腿": 0, "健腹轮": 0
}

# ---------- MET 兜底字典（有氧/自重静态）----------
MET_DICT = {
    "波比跳": 8.0, "壶铃摆荡": 7.0, "战绳": 8.0, "有氧跑步": 8.0, "跳绳": 8.0,
    "平板支撑": 2.5, "卷腹": 3.0, "仰卧抬腿": 3.0, "俄罗斯转体": 3.0,
    "悬垂举腿": 4.0, "健腹轮": 4.5, "俯卧撑": 3.5
}

# ---------- 辅助函数 ----------
def get_user_push_list():
    """获取所有已启用推送且有 Token 的用户列表"""
    res = supabase.table("user_push_settings") \
        .select("user_id, pushplus_token") \
        .eq("is_enabled", True) \
        .not_.is_("pushplus_token", "null") \
        .execute()
    return res.data

def get_user_profile(user_id):
    """获取用户体重（用于计算消耗）"""
    res = supabase.table("profiles").select("weight").eq("user_id", user_id).execute()
    if res.data:
        return res.data[0].get("weight", 70)
    return 70

def get_today_workouts(user_id):
    """获取用户当天的所有训练记录"""
    today = date.today().isoformat()
    res = supabase.table("workouts") \
        .select("*") \
        .eq("user_id", user_id) \
        .eq("date", today) \
        .execute()
    return res.data

def get_today_durations(user_id):
    """获取用户当天的总训练时长（从 training_durations 表）"""
    today = date.today().isoformat()
    res = supabase.table("training_durations") \
        .select("duration_min") \
        .eq("user_id", user_id) \
        .eq("date", today) \
        .execute()
    total_min = sum(item["duration_min"] for item in res.data)
    return total_min

# ---------- 消耗计算 ----------
def calc_mechanical_calories(exercise, details, body_weight, set_count):
    """
    基于物理做功计算一组训练消耗（千卡）
    返回 None 表示无法计算，需用 MET
    """
    if not details:
        return None
    displacement = DISPLACEMENT.get(exercise, 0.0)
    if displacement == 0.0:
        return None

    total_joules = 0
    # details 格式如 "10次×20kg; 8次×25kg"
    groups = details.split('; ')
    for g in groups:
        try:
            reps, weight_part = g.split('次×')
            weight = float(weight_part.replace('kg', ''))
            reps = int(reps)
            # 自重动作特殊处理：引体向上、双杠臂屈伸
            if exercise in ["引体向上", "双杠臂屈伸"]:
                weight = body_weight * 0.9
            joules = weight * 9.8 * displacement * reps
            total_joules += joules
        except:
            continue
    if total_joules == 0:
        return 0.0
    # 人体效率22%，1千卡=4184焦耳
    kcal = total_joules / 0.22 / 4184
    return round(kcal, 2)

def estimate_calories_met(exercise, sets, body_weight, duration_min=None):
    """MET 兜底计算"""
    met = MET_DICT.get(exercise, 5.0)
    if duration_min:
        time_hours = duration_min / 60
    else:
        time_hours = (sets * 2) / 60
    return round(met * body_weight * time_hours, 1)

# ---------- 生成战报 ----------
def generate_report(user_id, workouts, total_duration, weight):
    """为单个用户生成战报文本"""
    if not workouts and total_duration == 0:
        return None  # 无数据不推送

    today = date.today().strftime("%Y-%m-%d")

    # 时长格式化
    h = int(total_duration // 60)
    m = int(total_duration % 60)
    dur_str = f"{h}小时{m}分钟" if h else f"{m}分钟"

    # 计算总消耗
    total_kcal = 0.0
    for w in workouts:
        ex = w["exercise"]
        sets = w["set_count"] or 0
        details = w["details"] or ""
        if w["met_value"] is not None:  # 有氧记录，直接使用 MET
            met = w["met_value"]
            dur = w["cardio_duration"] or 0
            total_kcal += met * weight * (dur / 60)
        else:  # 力量或无 MET 记录
            kcal = calc_mechanical_calories(ex, details, weight, sets)
            if kcal is not None:
                total_kcal += kcal
            else:
                # 兜底用 MET
                total_kcal += estimate_calories_met(ex, sets, weight, total_duration)

    total_kcal = round(total_kcal, 1)

    # 构建战报文本
    parts = list(set(w["body_part"] for w in workouts if w["body_part"]))
    actions = list(set(w["exercise"] for w in workouts if w["exercise"]))

    report = f"【{today} 训练战报】\n"
    report += f"🏋️ 训练部位：{'、'.join(parts)}\n"
    report += f"📊 完成动作：{'、'.join(actions)}\n"
    report += f"⏱️ 训练时长：{dur_str}\n"
    report += f"🔥 估算消耗：{total_kcal} 千卡\n"
    report += "✅ 详细记录：\n"
    for w in workouts:
        ex = w["exercise"]
        part = w["body_part"]
        if w["set_count"]:
            sets = int(w["set_count"])
            report += f"  - {part} {ex}：{sets}组\n"
        else:
            dur = w["cardio_duration"] or 0
            report += f"  - {part} {ex}：{dur}分钟\n"
    report += "\n🚀 继续保持，你是最棒的！"
    return report

def push_to_wechat(token, title, content):
    """通过 PushPlus 推送消息"""
    payload = {
        "token": token,
        "title": title,
        "content": content,
        "template": "txt"
    }
    try:
        resp = requests.post(PUSHPLUS_API, json=payload, timeout=10)
        if resp.status_code == 200:
            result = resp.json()
            if result.get("code") == 200:
                return True
            else:
                print(f"推送失败：{result.get('msg')}")
                return False
        else:
            print(f"HTTP 错误：{resp.status_code}")
            return False
    except Exception as e:
        print(f"推送异常：{e}")
        return False

def main():
    print(f"开始执行日报推送，时间：{datetime.now()}")

    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print("错误：缺少 Supabase 环境变量，请检查 Secrets 配置。")
        return

    users = get_user_push_list()
    if not users:
        print("没有需要推送的用户。")
        return

    print(f"共 {len(users)} 个用户需要推送。")

    for user_item in users:
        user_id = user_item["user_id"]
        token = user_item["pushplus_token"]
        print(f"处理用户：{user_id}")

        weight = get_user_profile(user_id)
        workouts = get_today_workouts(user_id)
        total_duration = get_today_durations(user_id)

        report = generate_report(user_id, workouts, total_duration, weight)
        if not report:
            print(f"用户 {user_id} 无训练数据，跳过推送。")
            continue

        title = f"💪 {date.today().strftime('%Y-%m-%d')} 训练战报"
        if push_to_wechat(token, title, report):
            print(f"用户 {user_id} 推送成功。")
        else:
            print(f"用户 {user_id} 推送失败。")

    print("日报推送完成。")

if __name__ == "__main__":
    main()
