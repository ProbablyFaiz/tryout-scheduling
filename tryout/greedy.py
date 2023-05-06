# Goals: 1) Schedule everyone into a block and 2) use as few blocks as possible
from collections import defaultdict
from math import inf
from typing import List
from get_avail_data import get_avail_data
from helpers import (
    pretty_print_schedule,
    Availability,
    Schedule,
    MAX_PER_BLOCK,
    UNSCHEDULED_BLOCK,
)


def create_schedule(availability: List[Availability]) -> Schedule:
    # Format: key = block, value = array of names scheduled in block
    schedule = defaultdict(list)
    scheduled_per_day: dict[str, int] = defaultdict(lambda: 0)
    sorted_availability = sorted(availability, key=lambda item: len(item.free_slots))
    for person in sorted_availability:
        if len(person.free_slots) == 0:
            person.free_slots.append(UNSCHEDULED_BLOCK)
        least_available_block, least_available_block_num = None, -inf
        for block in person.free_slots:
            if block not in schedule:
                schedule[block] = []
            if len(schedule[block]) >= MAX_PER_BLOCK:
                continue
            # Schedule the person in the block with the least available spots (though > 0) to avoid fragmentation.
            block_goodness = (
                len(schedule[block])
                # Quick hack to avoid scheduling Saturday if at all possible.
                if block.split(",")[0] != "Saturday"
                else len(schedule[block]) - 99
            )
            is_least_available_block = block_goodness > least_available_block_num or (
                # Tiebreaker: prefer days with more people scheduled.
                block_goodness == least_available_block_num
                and scheduled_per_day[block] > scheduled_per_day[least_available_block]
            )
            if is_least_available_block:
                least_available_block = block
                least_available_block_num = block_goodness
        if least_available_block is None:
            least_available_block = UNSCHEDULED_BLOCK
        else:
            block_day = least_available_block.split(",")[0]
            scheduled_per_day[block_day] += 1
        schedule[least_available_block].append(person.name)
    return {
        key: value for key, value in sorted(schedule.items(), key=lambda item: item[0])
    }


if __name__ == "__main__":
    availability = get_avail_data()
    schedule = create_schedule(availability)
    print(pretty_print_schedule(schedule))
