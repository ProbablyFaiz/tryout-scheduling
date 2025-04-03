import csv
import datetime
import itertools
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scheduler.tryout.time_ranges import get_time_intervals, parse_datetime_range

UNSCHEDULED_BLOCK = "Unscheduled"
SORT_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
    UNSCHEDULED_BLOCK,
]


@dataclass
class Person:
    name: str
    email: str
    free_slots: list[str]


@dataclass
class Slot:
    name: str
    spots_multiplier: int
    rooms: list[str]


Schedule = dict[Any, list[Person]]


def block_sort_key(block):
    try:
        return parse_datetime_range(block)[0]
    except Exception:
        return datetime.datetime.max


_DAY_OF_WEEK_REGEX = re.compile(r"[A-Za-z]+?day")


def get_block_day(block: str) -> str:
    try:
        return parse_datetime_range(block)[0].strftime("%A")
    except Exception:
        res = _DAY_OF_WEEK_REGEX.search(block)
        return res.group(0) if res else ""


def pretty_print_schedule(schedule):
    output = "Schedule\n--------\n"
    for block in sorted(
        schedule.keys(),
        key=block_sort_key,
    ):
        people = schedule[block]
        output += f"{block}: "
        if len(people) > 0:
            output += ", ".join([p.name for p in people])
        else:
            output += "FREE"
        output += "\n"
    return output


def write_schedule_to_csv(
    schedule: Schedule, slots: list[Slot], output_path: Path
) -> None:
    blocks = {s.name: s for s in slots}
    with output_path.open("w") as f:
        writer = csv.writer(f)
        writer.writerow(["Block", "Slot", "Name", "Email", "Room"])
        for block in sorted(
            schedule.keys(),
            key=block_sort_key,
        ):
            people_in_block = schedule[block]
            slots_in_block = (
                get_time_intervals(block)
                if block != UNSCHEDULED_BLOCK
                else [""] * len(people_in_block)
            )
            if (block_info := blocks.get(block)) and (rooms := block_info.rooms):
                slot_room_combinations = list(
                    itertools.product(
                        slots_in_block,
                        rooms,
                    )
                )
            else:
                slot_room_combinations = [(slot, "") for slot in slots_in_block]

            for (slot, room), person in itertools.zip_longest(
                slot_room_combinations,
                people_in_block,
            ):
                email, name = (person.email, person.name) if person else ("", "")
                writer.writerow([block, slot, name, email, room])
