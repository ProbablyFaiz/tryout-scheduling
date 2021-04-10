# Goals: 1) Schedule everyone into a block and 2) use as few blocks as possible
from dataclasses import dataclass
from math import inf
from typing import List, Dict, Any
import csv
import re

MAX_PER_BLOCK = 3
FREE_SLOTS_PARSE_REGEX = r".+?M"
CSV_NAME_ROW = 1
CSV_FREE_SLOTS_ROW = 4


@dataclass
class Availability:
    name: str
    free_slots: List[Any]


def get_availability_from_csv(file_name) -> List[Availability]:
    availability: List[Availability] = []
    with open(file_name) as avail_file:
        avail_file_reader = csv.reader(avail_file)
        next(avail_file_reader, None)  # Skip header row
        for avail_row in avail_file_reader:
            slots_regex_match = re.findall(FREE_SLOTS_PARSE_REGEX, avail_row[CSV_FREE_SLOTS_ROW])
            availability.append(Availability(
                name=avail_row[CSV_NAME_ROW].strip(),
                free_slots=[slot.strip(" ,") for slot in slots_regex_match]
            ))
    return availability


def create_schedule(availability: List[Availability]) -> Dict[Any, List[str]]:
    schedule = {}  # Format: key = block, value = array of names scheduled in block
    sorted_availability = sorted(availability, key=lambda item: len(item.free_slots))
    for person in sorted_availability:
        least_available_block, least_available_block_num = None, -inf
        for block in person.free_slots:
            if block not in schedule:
                schedule[block] = []
            # Schedule the person in the block with the least available spots (though > 0) to avoid fragmentation.
            if MAX_PER_BLOCK > len(schedule[block]) > least_available_block_num:
                least_available_block, least_available_block_num = block, len(schedule[block])
        if least_available_block is None:
            print(f"Unable to schedule person {person.name}. Either impossible or my algorithm is bad.")
            exit(1)
        schedule[least_available_block].append(person.name)
    return {key: value for key, value in sorted(schedule.items(), key=lambda item: item[0])}


def pretty_print_schedule(schedule):
    output = "Schedule\n" \
             "--------\n"
    for block, people in schedule.items():
        output += f"{block}: "
        if len(people) > 0:
            output += f"{people[0]}"
            for person in people[1:]:
                output += f", {person}"
        else:
            output += "FREE"
        output += "\n"
    return output


availability_from_file = get_availability_from_csv("moot-tryout-avail.csv")
schedule = create_schedule(availability_from_file)
print(pretty_print_schedule(schedule))
