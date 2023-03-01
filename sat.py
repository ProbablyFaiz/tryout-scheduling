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
    person_model = create_base_model(availability)
    person_goodness = {}
    for i, person in enumerate(availability):
        person_goodness[person.name] = 2 - i / (len(availability) ** 2)
    # We want to maximize the sum of the goodness of the people scheduled.
    # The idea being to schedule as many people as possible, but to prefer
    # the people who filled out the form first.
    person_model["model"].Maximize(
        sum(
            sum(p_vars) * person_goodness[p]
            for p, p_vars in person_model["person_vars"].items()
        )
    )
    solver = cp_model.CpSolver()
    status = solver.Solve(person_model["model"])
    print(f"Status: {solver.StatusName(status)}")
    print(f"Objective value: {solver.ObjectiveValue()}")
    # Extract list of people scheduled in blocks
    names = set()
    for v in person_model["var_info"]:
        if solver.Value(v) == 1:
            names.add(person_model["var_info"][v][0])
    print(f"Num people scheduled: {len(names)}")

    new_availability = [a for a in availability if a.name in names]
    block_model = create_base_model(new_availability)
    # Require all people to be scheduled.
    for p_vars in block_model["person_vars"].values():
        block_model["model"].Add(sum(p_vars) == 1)
    block_badness = {}
    for block in block_model["block_vars"]:
        block_badness[block] = (
            1 + 1 / len(block_model["block_vars"]) if "Saturday" in block else 1
        )

    # We want to minimize the number of blocks used.
    block_model["model"].Minimize(
        sum(
            b_var * block_badness[b]
            for b, b_var in block_model["block_used_vars"].items()
        )
    )
    solver = cp_model.CpSolver()
    status = solver.Solve(block_model["model"])
    print(f"Status: {solver.StatusName(status)}")
    print(f"Objective value: {solver.ObjectiveValue()}")
    return solved_to_schedule(solver, block_model["var_info"], availability)


def create_base_model(availability):
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
    for p_vars in person_vars.values():
        model.Add(
            sum(p_vars) <= 1,
        )
    return {
        "model": model,
        "person_vars": person_vars,
        "block_vars": block_vars,
        "block_used_vars": block_used_vars,
        "var_info": var_info,
    }


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
    availability = get_avail_data()
    schedule = create_schedule(availability)
    print(pretty_print_schedule(schedule))


if __name__ == "__main__":
    main()
