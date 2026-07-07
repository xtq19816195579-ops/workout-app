import pandas as pd
from datetime import datetime
import requests
import os
import json
from io import StringIO
from github import Github

# ---------- 配置 ----------
PUSHPLUS_TOKEN = "93133ef2ee0b402d9b185fb5b2c23d74"   # 你的 PushPlus token
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
REPO_NAME = "xtq19816195579-ops/workout-app"
DATA_FILE = "workout_log.csv"
PROFILE_FILE = "user_profile.json"

# ---------- 位移字典（米）----------
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
    "悬垂举腿": 4.0, "健腹轮": 4.5, "俯卧撑": 3.5  # 俯卧撑也设为MET兜底
}

# ---------- 通用读取 ----------
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
    return {"weight": 70}

def load_workout_data():
    raw = github_read(DATA_FILE)
    if raw:
        return pd.read_csv(StringIO(raw))
    return pd.DataFrame()

# ---------- 消耗计算 ----------
def calc_mechanical_calories(row, body_weight):
    """基于物理做功计算一组训练消耗（千卡），返回None表示无法计算，需用MET"""
    exercise = row["动作"]
    weight_str = row["每组详情"]
    if pd.isna(weight_str) or not weight_str:
        return None

    displacement = DISPLACEMENT.get(exercise, 0.0)
    if displacement == 0.0:  # 无位移动作，用MET
        return None

    total_joules = 0
    groups = weight_str.split('; ')
    for g in groups:
        try:
            reps, weight_part = g.split('次×')
            weight = float(weight_part.replace('kg', ''))
            reps = int(reps)
            # 自重动作特殊处理
            if exercise in ["引体向上", "双杠臂屈伸"]:
                weight = body_weight * 0.9  # 约90%体重
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

    # 训练时长：优先使用实际时长
    if "实际时长(分钟)" in today_df.columns:
        actual_durations = today_df["实际时长(分钟)"].dropna()
        if not actual_durations.empty:
            total_min = actual_durations.iloc[0]  # 同一次训练共享同一时长
        else:
            total_min = today_df["组数"].sum() * 2
    else:
        total_min = today_df["组数"].sum() * 2

    h = int(total_min // 60)
    m = int(total_min % 60)
    dur_str = f"{h}小时{m}分钟" if h else f"{m}分钟"

    # 总消耗：优先做功模型，否则MET兜底
    total_kcal = 0.0
    for _, row in today_df.iterrows():
        exercise = row["动作"]
        sets = row["组数"]
        kcal = calc_mechanical_calories(row, body_weight)
        if kcal is not None:
            total_kcal += kcal
        else:
            # 有氧/无位移动作，使用MET（传入实际时长的小时数）
            total_kcal += estimate_calories_met(exercise, sets, body_weight, total_min / 60)

    total_kcal = round(total_kcal, 1)

    parts = today_df["部位"].unique()
    actions = today_df["动作"].tolist()

    report = f"【{today} 训练战报】\n"
    report += f"🏋️ 训练部位：{'、'.join(parts)}\n"
    report += f"📊 完成动作：{'、'.join(list(set(actions)))}\n"
    report += f"⏱️ 训练时长：{dur_str}\n"
    report += f"🔥 估算消耗：{total_kcal} 千卡（基于体重{body_weight}kg及做功模型）\n"
    report += "✅ 详细记录：\n"
    for _, row in today_df.iterrows():
        report += f"  - {row['部位']} {row['动作']}：{int(row['组数'])}组\n"
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
