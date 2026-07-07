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
DURATION_FILE = "training_durations.csv"

# 位移字典（米），仅力量动作使用
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
    # 有氧动作不在此处
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
        df = pd.read_csv(StringIO(raw))
        # 确保新列存在
        for col in ["有氧时长(分钟)", "MET值"]:
            if col not in df.columns:
                df[col] = None
        return df
    return pd.DataFrame()

def load_total_duration():
    """返回今日从计时器累计的总训练时长（分钟）"""
    raw = github_read(DURATION_FILE)
    if not raw:
        return 0.0
    df = pd.read_csv(StringIO(raw))
    today = datetime.now().strftime("%Y-%m-%d")
    today_df = df[df["日期"] == today]
    if today_df.empty:
        return 0.0
    return today_df["时长(分钟)"].sum()

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
        return round(height * 0.0025, 2)
    return base

def calc_strength_calories(row, body_weight, profile):
    """力量动作基于做功模型"""
    exercise = row["动作"]
    weight_str = row["每组详情"]
    if pd.isna(weight_str) or not weight_str:
        return 0.0
    displacement = get_displacement_for_exercise(exercise, profile)
    if displacement == 0.0:
        return 0.0  # 无位移力量动作？理论上不应该，但可以返回0
    total_joules = 0
    groups = weight_str.split('; ')
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
    kcal = total_joules / 0.22 / 4184
    return round(kcal, 2)

def calc_cardio_calories(row, body_weight):
    """有氧运动基于 MET 模型，使用记录中的时长和MET值"""
    duration_min = row["有氧时长(分钟)"]
    met = row["MET值"]
    if pd.isna(duration_min) or pd.isna(met):
        return 0.0
    time_hours = duration_min / 60
    kcal = met * body_weight * time_hours
    return round(kcal, 2)

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

    # 总时长（来自计时器）
    total_duration = load_total_duration()
    if total_duration == 0.0:
        # 回退：力量动作组数估算 + 有氧动作直接取时长累加
        strength_sets = today_df[today_df["有氧时长(分钟)"].isna()]["组数"].sum()
        cardio_dur = today_df["有氧时长(分钟)"].dropna().sum()
        total_duration = strength_sets * 2 + cardio_dur

    h = int(total_duration // 60)
    m = int(total_duration % 60)
    dur_str = f"{h}小时{m}分钟" if h else f"{m}分钟"

    # 分别计算消耗
    total_kcal = 0.0
    for _, row in today_df.iterrows():
        if pd.notna(row["有氧时长(分钟)"]):  # 有氧动作
            total_kcal += calc_cardio_calories(row, body_weight)
        else:  # 力量动作
            total_kcal += calc_strength_calories(row, body_weight, profile)

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
        if pd.notna(row["有氧时长(分钟)"]):  # 有氧
            report += f"  - {row['部位']} {row['动作']}：{row['有氧时长(分钟)']} 分钟 (MET {row['MET值']})\n"
        else:
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
