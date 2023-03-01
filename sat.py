from collections import defaultdict

from helpers import (
    block_sort_key,
    Availability,
    Schedule,
    MAX_PER_BLOCK,
    UNSCHEDULED_BLOCK,
    pretty_print_schedule,
)
from get_avail_data import get_avail_data
from ortools.sat.python import cp_model


def create_schedule(availability: list[Availability]) -> Schedule:
    model = cp_model.CpModel()
    schedule_vars = {}
    for person in availability:
        for block in person.free_slots:
            if block not in schedule_vars:
                schedule_vars[block] = []
            schedule_vars[block].append(model.NewBoolVar(f"{person.name} in {block}"))
    for block in schedule_vars:
        model.Add(sum(schedule_vars[block]) <= MAX_PER_BLOCK)
    for person in availability:
        model.Add(
            sum(
                schedule_vars[block][i]
                for block in person.free_slots
                for i in range(len(schedule_vars[block]))
            )
            == 1
        )
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    if status == cp_model.OPTIMAL:
        schedule = defaultdict(list)
        for block in schedule_vars:
            for i in range(len(schedule_vars[block])):
                if solver.Value(schedule_vars[block][i]):
                    schedule[block].append(availability[i].name)
        return {
            key: value
            for key, value in sorted(schedule.items(), key=lambda item: item[0])
        }
    else:
        return {UNSCHEDULED_BLOCK: [person.name for person in availability]}


def main():
    availability = get_avail_data()
    schedule = create_schedule(availability)
    print(pretty_print_schedule(schedule))


if __name__ == "__main__":
    main()
