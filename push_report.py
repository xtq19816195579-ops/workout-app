import os
import json
import requests
from datetime import date, datetime
from supabase import create_client, Client
import pandas as pd

# ---------- 配置 ----------
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
PUSHPLUS_API = "https://www.pushplus.plus/send"

# 初始化 Supabase 客户端（使用 Service Role）
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# MET 值映射（若动作库中有则用，否则使用默认值）
MET_MAP = {
    "跑步 (8 km/h)": 8.0,
    "跑步 (10 km/h)": 10.0,
    "慢跑": 7.0,
    "跳绳 (中速)": 10.0,
    "跳绳 (快速)": 12.0,
    "游泳 (自由泳)": 8.0,
    "游泳 (蛙泳)": 7.0,
    "骑行 (中等)": 6.0,
    "椭圆机": 5.0,
    "划船机": 7.0,
    "高强度间歇训练": 12.0,
    # 其他动作可在表中直接存储 met_value，这里仅做兜底
}

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
    return 70  # 默认体重

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

def calculate_calories(exercise, met_value, duration_min, weight_kg):
    """
    计算消耗（千卡）
    公式：消耗 = MET × 体重(kg) × 时长(小时)
    """
    if not met_value:
        met_value = MET_MAP.get(exercise, 5.0)  # 默认 MET=5
    hours = duration_min / 60
    return met_value * weight_kg * hours

def generate_report(user_id, workouts, total_duration, weight):
    """生成个性化战报文本"""
    if not workouts and total_duration == 0:
        return None  # 无训练数据，不推送

    lines = []
    lines.append(f"📅 {date.today().strftime('%Y-%m-%d')} 训练日报")
    lines.append("")
    if total_duration > 0:
        lines.append(f"⏱️ 总训练时长：{total_duration:.1f} 分钟")
    else:
        lines.append("⏱️ 未记录训练时长（可能计时器未使用）")

    total_cal = 0
    if workouts:
        lines.append("")
        lines.append("🏋️ 训练明细：")
        for w in workouts:
            ex = w["exercise"]
            part = w["body_part"]
            if w["met_value"] is not None:  # 有氧
                dur = w["cardio_duration"]
                met = w["met_value"]
                cal = calculate_calories(ex, met, dur, weight)
                total_cal += cal
                lines.append(f"  • {part} - {ex}：{dur} 分钟，MET={met}，消耗 ~{cal:.0f} 千卡")
            else:  # 力量
                sets = w["set_count"]
                details = w["details"] or "未填"
                lines.append(f"  • {part} - {ex}：{sets} 组，{details}")
                # 力量训练消耗粗略估算（可选），可忽略
    if total_cal > 0:
        lines.append("")
        lines.append(f"🔥 总消耗：约 {total_cal:.0f} 千卡")
    else:
        # 若无有氧，可提示
        pass

    return "\n".join(lines)

def push_to_wechat(token, title, content):
    """通过 PushPlus 推送消息"""
    payload = {
        "token": token,
        "title": title,
        "content": content,
        "template": "txt"  # 纯文本
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

    users = get_user_push_list()
    if not users:
        print("没有需要推送的用户。")
        return

    print(f"共 {len(users)} 个用户需要推送。")

    for user_item in users:
        user_id = user_item["user_id"]
        token = user_item["pushplus_token"]
        print(f"处理用户：{user_id}")

        # 获取数据
        weight = get_user_profile(user_id)
        workouts = get_today_workouts(user_id)
        total_duration = get_today_durations(user_id)

        # 生成战报
        report = generate_report(user_id, workouts, total_duration, weight)
        if not report:
            print(f"用户 {user_id} 无训练数据，跳过推送。")
            continue

        # 推送
        title = f"💪 {date.today().strftime('%Y-%m-%d')} 训练战报"
        success = push_to_wechat(token, title, report)
        if success:
            print(f"用户 {user_id} 推送成功。")
        else:
            print(f"用户 {user_id} 推送失败。")

    print("日报推送完成。")

if __name__ == "__main__":
    main()
