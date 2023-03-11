from dataclasses import dataclass
from math import inf
from typing import List, Any, Dict

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
    free_slots: List[Any]


Schedule = Dict[Any, List[str]]


def block_sort_key(block):
    return (
        SORT_ORDER.index(block.split(",")[0])
        if block.split(",")[0] in SORT_ORDER
        else inf
    )


def pretty_print_schedule(schedule):
    output = "Schedule\n--------\n"
    for block in sorted(
        schedule.keys(),
        key=block_sort_key,
    ):
        people = schedule[block]
        output += f"{block}: "
        if len(people) > 0:
            output += ", ".join(people)
        else:
            output += "FREE"
        output += "\n"
    return output
