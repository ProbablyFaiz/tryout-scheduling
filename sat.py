import random
from collections import defaultdict

from helpers import (
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
    block_vars = defaultdict(list)
    person_vars = defaultdict(list)
    block_used_vars = {}
    var_info = {}

    for person in availability:
        if len(person.free_slots) == 0:
            person.name = f"{person.name} (NA)"
        for block in person.free_slots:
            person_block_var = model.NewBoolVar(f"{person.name} in {block}")
            block_vars[block].append(person_block_var)
            person_vars[person.name].append(person_block_var)
            var_info[person_block_var] = (person.name, block)

    for block in block_vars:
        block_used_var = model.NewBoolVar(f"{block} used")
        block_used_vars[block] = block_used_var
        model.AddBoolOr(block_vars[block]).OnlyEnforceIf(block_used_var)
        model.AddBoolAnd([v.Not() for v in block_vars[block]]).OnlyEnforceIf(
            block_used_var.Not()
        )

    # At most MAX_PER_BLOCK people per block.
    for block in block_vars:
        model.Add(sum(block_vars[block]) <= MAX_PER_BLOCK)
    # Each person is scheduled in at most one block.
    for person, p_vars in person_vars.items():
        model.Add(
            sum(p_vars) <= 1,
        )
    
    # Maximize the number of people scheduled.
    model.Maximize(sum(
        sum(p_vars) for p_vars in person_vars.values()
    ))


    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    print(f"Status: {solver.StatusName(status)}")
    for block in block_used_vars:
        print(f"{block}: {solver.Value(block_used_vars[block])}")

    return solved_to_schedule(solver, var_info, availability)


def solved_to_schedule(solver, var_info, availability):
    schedule = {
        block: [] for block in set(block for person, block in var_info.values())
    }
    schedule[UNSCHEDULED_BLOCK] = []
    scheduled_names = set()
    for var in var_info:
        if solver.Value(var):
            person, block = var_info[var]
            schedule[block].append(person)
            scheduled_names.add(person)
    for person in availability:
        if person.name not in scheduled_names:
            schedule[UNSCHEDULED_BLOCK].append(person.name)
    return {
        key: value for key, value in sorted(schedule.items(), key=lambda item: item[0])
    }


def main():
    random.seed(0)
    availability = get_avail_data()
    # Randomly select half the people
    # availability = random.sample(availability, len(availability) // 2)
    schedule = create_schedule(availability)
    print(pretty_print_schedule(schedule))


if __name__ == "__main__":
    main()
