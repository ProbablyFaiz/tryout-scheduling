import csv
import os
from typing import TypedDict

import requests

from dotenv import load_dotenv


JudgeName = str


class JudgeAvailability(TypedDict):
    name: JudgeName
    email: str
    grade: int
    moot_exp: bool
    free_slots: list[str]


def get_judge_data():
    load_dotenv()
    judge_csv_path = os.getenv("JUDGE_CSV_PATH")
    r = requests.get(judge_csv_path)
    judges = list(csv.DictReader(r.text.splitlines()))
    for judge in judges:
        judge["grade"] = int(judge["grade"])
        judge["moot_exp"] = judge["moot_exp"] == "Yes"
        slots = judge["day1"].split(", ") + judge["day2"].split(", ")
        judge["free_slots"] = [
            slot
            for slot in slots
            if slot not in ("None", "")
        ]
    return judges


if __name__ == "__main__":
    print(get_judge_data()[0])
