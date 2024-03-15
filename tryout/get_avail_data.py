import csv
import re
from typing import List, Tuple

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


def fetch_avail_csv() -> Tuple[StringIO, StringIO]:
    load_dotenv()
    avail_csv_path = os.getenv("AVAIL_CSV_PATH")
    r = requests.get(avail_csv_path)
    r.encoding = r.apparent_encoding
    slot_csv_path = os.getenv("SLOTS_CSV_PATH")
    r2 = requests.get(slot_csv_path)
    r2.encoding = r2.apparent_encoding
    return StringIO(r.text), StringIO(r2.text)


def get_availability_from_csv(
    avail_file, slot_file
) -> Tuple[List[Availability], List[str]]:
    availability: List[Availability] = []
    avail_file_reader = csv.reader(avail_file)
    next(avail_file_reader, None)  # Skip header row
    for avail_row in avail_file_reader:
        slots_regex_match = re.findall(FREE_SLOTS_PARSE_REGEX, avail_row[4])
        avail_object = Availability(
            email=avail_row[1],
            name=avail_row[2],
            free_slots=[slot.strip(" ,") for slot in slots_regex_match],
        )
        availability.append(avail_object)
    slot_file_reader = csv.reader(slot_file)
    next(slot_file_reader, None)  # Skip header row
    slots: List[str] = [s[0] for s in slot_file_reader]
    return availability, slots


def get_avail_data():
    avail_csv, slot_csv = fetch_avail_csv()
    return get_availability_from_csv(avail_csv, slot_csv)
