from math import inf

# Goals: 1) Schedule everyone into a block and 2) use as few blocks as possible

MAX_PER_BLOCK = 3


def create_schedule(availability):
    schedule = {}  # Format: key = block, value = array of names scheduled in block
    sorted_availability = sorted(availability, key=lambda item: len(item["availability"]))
    for person in sorted_availability:
        least_available_block, least_available_block_num = None, -inf
        for block in person["availability"]:
            if block not in schedule:
                schedule[block] = []
            if MAX_PER_BLOCK > len(schedule[block]) > least_available_block_num:
                least_available_block, least_available_block_num = block, len(schedule[block])
        if least_available_block is None:
            print(f"Unable to schedule person {person['name']}. Either impossible or my algorithm is bad.")
            exit(1)
        schedule[least_available_block].append(person["name"])
    return {key: value for key, value in sorted(schedule.items(), key=lambda item: item[0])}


sample_availability = [
    {"name": "Edwin", "availability": [3, 4, 6, 7]},
    {"name": "Juan", "availability": [0, 3, 4, 5, 6]},
    {"name": "Eric", "availability": [3, 4, 6]}
]
print(create_schedule(sample_availability))
