# Goals: 1) Schedule everyone into a block and 2) use as few blocks as possible
from collections import defaultdict
from dataclasses import dataclass
from math import inf
from typing import List, Dict, Any
import csv
import re
from get_avail_csv import fetch_avail_csv

UNSCHEDULED_BLOCK = "Unscheduled"
MAX_PER_BLOCK = 3
FREE_SLOTS_PARSE_REGEX = r"[A-Za-z]+?day.+?–.+?\.m\."
# FREE_SLOTS_PARSE_REGEX = r"(?:.+?M)|(?:week of .*)"
CSV_NAME_ROW = 1
CSV_FREE_SLOTS_ROW = 4

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


Schedule = Dict[Any, List[str]]


def create_schedule(availability: List[Availability]) -> Schedule:
    schedule = {
        UNSCHEDULED_BLOCK: []
    }  # Format: key = block, value = array of names scheduled in block
    scheduled_per_day: dict[str, int] = defaultdict(lambda: 0)
    sorted_availability = sorted(availability, key=lambda item: len(item.free_slots))
    for person in sorted_availability:
        least_available_block, least_available_block_num = None, -inf
        for block in person.free_slots:
            if block not in schedule:
                schedule[block] = []
            # Schedule the person in the block with the least available spots (though > 0) to avoid fragmentation.
            if MAX_PER_BLOCK > len(schedule[block]):
                if len(schedule[block]) > least_available_block_num or (
                    len(schedule) == least_available_block_num
                    and scheduled_per_day[block]
                    > scheduled_per_day[least_available_block]
                ):
                    least_available_block, least_available_block_num = block, len(
                        schedule[block]
                    )
        if least_available_block is None:
            least_available_block = UNSCHEDULED_BLOCK
        else:
            block_day = least_available_block.split(",")[0]
            scheduled_per_day[block_day] += 1
        schedule[least_available_block].append(person.name)
    return {
        key: value for key, value in sorted(schedule.items(), key=lambda item: item[0])
    }


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
            output += f"{people[0]}"
            for person in people[1:]:
                output += f", {person}"
        else:
            output += "FREE"
        output += "\n"
    return output


if __name__ == "__main__":
    availability_from_file = get_availability_from_csv(fetch_avail_csv())
    schedule = create_schedule(availability_from_file)
    print(pretty_print_schedule(schedule))
