import csv
import datetime
import itertools
from dataclasses import dataclass
from typing import List, Any, Dict

from tryout.time_ranges import parse_datetime_range, get_time_intervals

UNSCHEDULED_BLOCK = "Unscheduled"
MAX_PER_BLOCK = 3
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
class Availability:
    name: str
    email: str
    free_slots: List[Any]


Schedule = Dict[Any, List[str]]


def block_sort_key(block):
    try:
        return parse_datetime_range(block)[0]
    except Exception:
        return datetime.datetime.max


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


def write_schedule_to_csv(schedule, output_path) -> None:
    with open(output_path, "w") as f:
        writer = csv.writer(f)
        # writer.writerow(["Block", "Slot", "Name", "Email"])
        writer.writerow(["Block", "Slot", "Name"])
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
            for slot, person in itertools.zip_longest(
                slots_in_block,
                people_in_block,
            ):
                email, name = (person.email, person.name) if person else ("", "")
                # writer.writerow([block, slot, name, email])
                writer.writerow([block, slot, name])
