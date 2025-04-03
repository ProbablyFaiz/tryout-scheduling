# Goals: 1) Schedule everyone into a block and 2) use as few blocks as possible
import math
from collections import defaultdict

import helpers
import load_data
from helpers import (
    UNSCHEDULED_BLOCK,
    Person,
    Schedule,
)

MAX_PER_BLOCK = 6


def create_schedule(availability: list[Person], blocks: list[str]) -> Schedule:
    schedule: dict[str, list[Person]] = defaultdict(list)
    scheduled_per_day: dict[str, int] = defaultdict(lambda: 0)

    # Sort by availability, so that people with the fewest slots marked are scheduled first.
    availability = sorted(availability, key=lambda person: len(person.free_slots))

    for person in availability:
        # Filter to only blocks with space
        candidate_blocks = [
            block for block in person.free_slots if len(schedule[block]) < MAX_PER_BLOCK
        ]
        # Select a block that has space but is closest to being full, to encourage compact scheduling.
        # Tiebreaker: select the day with the most people already scheduled.
        # Second tiebreaker: select the earliest block.
        best_available_block = max(
            candidate_blocks,
            key=lambda block: (
                len(schedule[block]),
                scheduled_per_day[helpers.get_block_day(block)],
                helpers.parse_datetime_range(block)[0],
            ),
            default=UNSCHEDULED_BLOCK,
        )
        schedule[best_available_block].append(person)
        scheduled_per_day[helpers.get_block_day(best_available_block)] += 1

    return dict(
        sorted(
            schedule.items(),
            key=lambda item: blocks.index(item[0]) if item[0] in blocks else math.inf,
        )
    )


if __name__ == "__main__":
    availability, blocks = load_data.get_avail_data()
    schedule = create_schedule(availability, blocks)
    print(helpers.pretty_print_schedule(schedule))
    helpers.write_schedule_to_csv(schedule, "schedule.csv")
    print("Wrote schedule to schedule.csv")
