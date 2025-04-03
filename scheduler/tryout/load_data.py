import csv
import os
import re
from io import StringIO

import requests
from dotenv import load_dotenv

from scheduler.tryout.utils import Person

FREE_SLOTS_PARSE_REGEX = r"[A-Za-z]+?day.+?–.+?\.m\."
# FREE_SLOTS_PARSE_REGEX = r"(?:.+?M)|(?:week of .*)"


def fetch_avail_csv() -> tuple[StringIO, StringIO]:
    load_dotenv()

    avail_csv_path = os.getenv("AVAIL_CSV_PATH")
    avail_response = requests.get(avail_csv_path)
    avail_response.encoding = avail_response.apparent_encoding

    slot_csv_path = os.getenv("SLOTS_CSV_PATH")
    slot_response = requests.get(slot_csv_path)
    slot_response.encoding = slot_response.apparent_encoding

    return StringIO(avail_response.text), StringIO(slot_response.text)


def get_availability_from_csv(avail_file, slot_file) -> tuple[list[Person], list[str]]:
    availability: list[Person] = []
    avail_file_reader = csv.reader(avail_file)
    next(avail_file_reader, None)  # Skip header row
    for avail_row in avail_file_reader:
        slots_regex_match = re.findall(FREE_SLOTS_PARSE_REGEX, avail_row[4])
        avail_object = Person(
            email=avail_row[1],
            name=avail_row[2],
            free_slots=[slot.strip(" ,") for slot in slots_regex_match],
        )
        availability.append(avail_object)
    slot_file_reader = csv.reader(slot_file)
    next(slot_file_reader, None)  # Skip header row
    slots: list[str] = [s[0] for s in slot_file_reader]
    return availability, slots


def get_avail_data():
    avail_csv, slot_csv = fetch_avail_csv()
    return get_availability_from_csv(avail_csv, slot_csv)
