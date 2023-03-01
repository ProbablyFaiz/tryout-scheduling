import csv
import re
from typing import List

import requests
import os
from dotenv import load_dotenv
from io import StringIO

from helpers import (
    Availability,
    UNSCHEDULED_BLOCK,
)

FREE_SLOTS_PARSE_REGEX = r"[A-Za-z]+?day.+?–.+?\.m\."
# FREE_SLOTS_PARSE_REGEX = r"(?:.+?M)|(?:week of .*)"
CSV_NAME_ROW = 1
CSV_FREE_SLOTS_ROW = 4


def fetch_avail_csv() -> StringIO:
    load_dotenv()
    avail_csv_path = os.getenv("AVAIL_CSV_PATH")
    r = requests.get(avail_csv_path)
    r.encoding = r.apparent_encoding
    return StringIO(r.text)


def get_availability_from_csv(avail_file) -> List[Availability]:
    availability: List[Availability] = []
    avail_file_reader = csv.reader(avail_file)
    next(avail_file_reader, None)  # Skip header row
    for avail_row in avail_file_reader:
        slots_regex_match = re.findall(
            FREE_SLOTS_PARSE_REGEX, avail_row[CSV_FREE_SLOTS_ROW]
        )
        avail_object = Availability(
            name=avail_row[CSV_NAME_ROW].strip(),
            free_slots=[slot.strip(" ,") for slot in slots_regex_match],
        )
        if len(avail_object.free_slots) == 0:
            avail_object.free_slots.append(UNSCHEDULED_BLOCK)
        availability.append(avail_object)
    return availability


def get_avail_data():
    return get_availability_from_csv(fetch_avail_csv())
