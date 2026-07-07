import pandas as pd
from datetime import datetime
import requests
import os
from io import StringIO
from github import Github

# ---------- 配置 ----------
PUSHPLUS_TOKEN = "93133ef2ee0b402d9b185fb5b2c23d74"   # 替换！！！
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]  # GitHub Actions 会自动提供
REPO_NAME = "xtq19816195579-ops/workout-app"
FILE_PATH = "workout_log.csv"

# 简易 MET 值（用于估算卡路里）
MET_DICT = {
    "杠铃卧推": 5.0, "上斜卧推": 5.0, "哑铃飞鸟": 4.0, "器械卧推": 4.5,
    "夹胸": 4.0, "俯卧撑": 3.5, "哑铃推举": 4.5, "杠铃推举": 5.0,
    "侧平举": 3.5, "前平举": 3.5, "面拉": 4.0, "蝴蝶机反向飞鸟": 4.0,
    "引体向上": 6.0, "杠铃划船": 5.5, "哑铃划船": 5.0, "高位下拉": 5.0,
    "坐姿划船": 5.0, "硬拉": 6.5, "杠铃弯举": 4.5, "哑铃弯举": 4.0,
    "锤式弯举": 4.0, "集中弯举": 4.0, "牧师凳弯举": 4.0,
    "窄距卧推": 5.0, "绳索下压": 4.5, "哑铃臂屈伸": 4.0,
    "双杠臂屈伸": 5.5, "俯身臂屈伸": 4.0,
    "卷腹": 3.0, "平板支撑": 2.5, "仰卧抬腿": 3.0, "俄罗斯转体": 3.0,
    "悬垂举腿": 4.0, "健腹轮": 4.5,
    "深蹲": 6.0, "腿举": 5.0, "腿弯举": 4.0, "腿屈伸": 4.0,
    "箭步蹲": 5.0, "罗马尼亚硬拉": 6.0,
    "波比跳": 8.0, "壶铃摆荡": 7.0, "战绳": 8.0, "有氧跑步": 8.0, "跳绳": 8.0
}

def load_workout_data():
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    try:
        contents = repo.get_contents(FILE_PATH)
        csv_text = contents.decoded_content.decode('utf-8')
        df = pd.read_csv(StringIO(csv_text))
        return df
    except:
        return pd.DataFrame()

def estimate_calories(exercise, sets, reps_per_set=10, weight=20, met_dict=MET_DICT):
    """简单估算：MET × 体重 × 时间（小时），每组计2分钟，体重默认70kg"""
    met = met_dict.get(exercise, 5.0)
    time_hours = (sets * 2) / 60
    calories = met * 70 * time_hours
    return round(calories, 1)

def generate_report():
    df = load_workout_data()
    if df.empty:
        return None

    today = datetime.now().strftime("%Y-%m-%d")
    today_df = df[df["日期"] == today]
    if today_df.empty:
        return None

    total_sets = today_df["组数"].sum()
    actions = today_df["动作"].tolist()
    parts = today_df["部位"].unique()

    total_cal = 0
    for _, row in today_df.iterrows():
        total_cal += estimate_calories(row["动作"], row["组数"])

    total_min = total_sets * 2
    h = int(total_min // 60)
    m = int(total_min % 60)
    dur_str = f"{h}小时{m}分钟" if h else f"{m}分钟"

    report = f"【{today} 训练战报】\n"
    report += f"🏋️ 训练部位：{'、'.join(parts)}\n"
    report += f"📊 完成动作：{'、'.join(list(set(actions)))}\n"
    report += f"🔥 估算消耗：{total_cal:.1f} 千卡\n"
    report += f"⏱️ 训练时长：约{dur_str}\n"
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
