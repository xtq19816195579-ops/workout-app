import pandas as pd
from datetime import datetime
import requests
import os
import json
from io import StringIO
from github import Github

# ---------- 配置 ----------
PUSHPLUS_TOKEN = "93133ef2ee0b402d9b185fb5b2c23d74"
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
REPO_NAME = "xtq19816195579-ops/workout-app"
DATA_FILE = "workout_log.csv"
PROFILE_FILE = "user_profile.json"

# 位移字典（米）
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
    "波比跳": 0, "壶铃摆荡": 0, "战绳": 0, "有氧跑步": 0, "跳绳": 0,
    "平板支撑": 0, "卷腹": 0, "仰卧抬腿": 0, "俄罗斯转体": 0,
    "悬垂举腿": 0, "健腹轮": 0
}

# MET 兜底
MET_DICT = {
    "波比跳": 8.0, "壶铃摆荡": 7.0, "战绳": 8.0, "有氧跑步": 8.0, "跳绳": 8.0,
    "平板支撑": 2.5, "卷腹": 3.0, "仰卧抬腿": 3.0, "俄罗斯转体": 3.0,
    "悬垂举腿": 4.0, "健腹轮": 4.5, "俯卧撑": 3.5
}

# ---------- 工具函数 ----------
def github_read(filepath):
    g = Github(GITHUB_TOKEN)
    try:
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(filepath)
        return contents.decoded_content.decode('utf-8')
    except:
        return None

def load_profile():
    raw = github_read(PROFILE_FILE)
    if raw:
        try:
            return json.loads(raw)
        except:
            pass
    return {"weight": 70, "height": 175}

def load_workout_data():
    raw = github_read(DATA_FILE)
    if raw:
        return pd.read_csv(StringIO(raw))
    return pd.DataFrame()

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

def get_displacement_for_exercise(exercise, profile):
    base = DISPLACEMENT.get(exercise, 0.0)
    if base == 0.0:
        return base
    height = profile.get("height", 175)
    if exercise in ["引体向上", "双杠臂屈伸"]:
        return round(height * 0.0025, 2)   # 身高 cm 转为米，约 25% 身高
    return base

def calc_mechanical_calories(row, body_weight, profile):
    exercise = row["动作"]
    weight_str = row["每组详情"]
    if pd.isna(weight_str) or not weight_str:
        return None
    displacement = get_displacement_for_exercise(exercise, profile)
    if displacement == 0.0:
        return None        # 无位移动作，交给 MET 兜底

    total_joules = 0
    groups = weight_str.split('; ')
    for g in groups:
        try:
            reps, weight_part = g.split('次×')   # 分离次数和重量
            weight = float(weight_part.replace('kg', ''))  # 去除'kg'并转浮点
            reps = int(reps)
            if exercise in ["引体向上", "双杠臂屈伸"]:
                weight = body_weight * 0.9   # 自重动作，负荷为体重的90%
            joules = weight * 9.8 * displacement * reps
            total_joules += joules
        except:
            continue

    if total_joules == 0:
        return 0.0
    kcal = total_joules / 0.22 / 4184
    return round(kcal, 2)

def estimate_calories_met(exercise, sets, body_weight, duration_min=None):
    met = MET_DICT.get(exercise, 5.0)
    if duration_min:
        time_hours = duration_min / 60
    else:
        time_hours = (sets * 2) / 60
    return round(met * body_weight * time_hours, 1)

# ---------- 战报生成 ----------
def generate_report():
    profile = load_profile()
    body_weight = profile.get("weight", 70)

    df = load_workout_data()
    if df.empty:
        return None

    today = datetime.now().strftime("%Y-%m-%d")
    today_df = df[df["日期"] == today]
    if today_df.empty:
        return None

    # ---------- 叠加一天多次训练的时长 ----------
    total_min = 0.0
    if "实际时长(分钟)" in today_df.columns:
        # 按记录批次去重（同一次训练的多条记录共享相同实际时长）
        duration_series = today_df.groupby("记录时间")["实际时长(分钟)"].first().dropna()
        if not duration_series.empty:
            total_min = duration_series.sum()
        else:
            total_min = today_df["组数"].sum() * 2
    else:
        total_min = today_df["组数"].sum() * 2

    h = int(total_min // 60)
    m = int(total_min % 60)
    dur_str = f"{h}小时{m}分钟" if h else f"{m}分钟"

    # ---------- 总消耗 ----------
    total_kcal = 0.0
    for _, row in today_df.iterrows():
        kcal = calc_mechanical_calories(row, body_weight, profile)
        if kcal is not None:
            total_kcal += kcal
        else:
            total_kcal += estimate_calories_met(row["动作"], row["组数"], body_weight, total_min / 60)

    total_kcal = round(total_kcal, 1)

    parts = today_df["部位"].unique()
    actions = today_df["动作"].tolist()

    report = f"【{today} 训练战报】\n"
    report += f"🏋️ 训练部位：{'、'.join(parts)}\n"
    report += f"📊 完成动作：{'、'.join(list(set(actions)))}\n"
    report += f"⏱️ 训练总时长：{dur_str}\n"
    report += f"🔥 估算消耗：{total_kcal} 千卡\n"
    report += "✅ 详细记录：\n"
    for _, row in today_df.iterrows():
        details_compressed = compress_details(row["每组详情"])
        report += f"  - {row['部位']} {row['动作']}：{int(row['组数'])}组\n"
        if details_compressed:
            report += f"    {details_compressed.replace(chr(10), chr(10) + '    ')}\n"
    report += "\n🚀 继续保持，你是最棒的！"
    return report

def push_to_wechat(content):
    if not content:
        return
    url = "http://www.pushplus.plus/send"
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": "训练战报",
        "content": content,
        "template": "txt"
    }
    resp = requests.post(url, json=data)
    print(f"推送状态：{resp.status_code}, {resp.text}")

if __name__ == "__main__":
    report = generate_report()
    if report:
        push_to_wechat(report)
    else:
        print("今日无训练记录，不推送。")
