import csv
import os
from typing import NewType, TypedDict

import requests
from dotenv import load_dotenv

JudgeName = NewType("JudgeName", str)
Slot = NewType("Slot", str)


class JudgeAvailability(TypedDict):
    name: JudgeName
    email: str
    grade: int
    moot_exp: bool
    free_slots: list[Slot]


def get_judge_data():
    load_dotenv()
    judge_csv_path = os.getenv("JUDGE_CSV_PATH")
    r = requests.get(judge_csv_path)
    r.encoding = "utf-8"
    lines = r.text.splitlines()
    lines = [ln for ln in lines if ln.replace(",", "").strip()]
    judges = list(csv.DictReader(lines))
    for judge in judges:
        judge["grade"] = (
            int(judge["grade"]) if judge.get("grade") else int(judge["grades"])
        )
        judge["moot_exp"] = judge["moot_exp"] == "Yes"
        slots = judge["day1"].split(", ") + judge["day2"].split(", ")
        judge["free_slots"] = [Slot(slot) for slot in slots if slot not in ("None", "")]
    return judges


if __name__ == "__main__":
    print(get_judge_data()[0])
