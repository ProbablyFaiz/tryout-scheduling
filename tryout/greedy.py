# Goals: 1) Schedule everyone into a block and 2) use as few blocks as possible
import re
from collections import defaultdict

from load_data import get_avail_data
from helpers import (
    pretty_print_schedule,
    Availability,
    Schedule,
    MAX_PER_BLOCK,
    UNSCHEDULED_BLOCK,
)


Block = str
Name = str

_DAY_OF_WEEK_REGEX = re.compile(r"[A-Za-z]+?day")


def create_schedule(availability: list[Availability]) -> Schedule:
    schedule: dict[Block, list[Name]] = defaultdict(list)
    scheduled_per_day: dict[str, int] = defaultdict(lambda: 0)

    # Sort by availability, so that people with the fewest slots marked are scheduled first.
    availability = sorted(availability, key=lambda item: len(item.free_slots))

    for person in availability:
        candidate_blocks = [
            block for block in person.free_slots if len(schedule[block]) < MAX_PER_BLOCK
        ]
        # Select a block that has space but is closest to being full, to encourage compact scheduling.
        # Tiebreaker: select the day with the most people already scheduled.
        best_available_block = max(
            candidate_blocks,
            key=lambda block: (
                len(schedule[block]),
                scheduled_per_day[_get_block_day(block)],
            ),
            default=UNSCHEDULED_BLOCK,
        )
        schedule[best_available_block].append(person.name)
        scheduled_per_day[_get_block_day(best_available_block)] += 1
    return {
        key: value for key, value in sorted(schedule.items(), key=lambda item: item[0])
    }


def _get_block_day(block: Block) -> str:
    res = _DAY_OF_WEEK_REGEX.search(block)
    return res.group(0) if res else ""


if __name__ == "__main__":
    availability = get_avail_data()
    schedule = create_schedule(availability)
    print(pretty_print_schedule(schedule))
