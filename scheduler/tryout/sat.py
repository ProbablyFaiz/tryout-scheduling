from collections import defaultdict
from typing import Any

import rl.utils.io
from ortools.sat.python import cp_model

from scheduler.tryout.load_data import get_avail_data
from scheduler.tryout.time_ranges import get_time_intervals, parse_datetime_range
from scheduler.tryout.utils import (
    UNSCHEDULED_BLOCK,
    Person,
    Schedule,
    Slot,
    pretty_print_schedule,
    write_schedule_to_csv,
)


def create_schedule(availability: list[Person], slots: list[Slot]) -> Schedule:
    person_model = create_base_model(availability, slots)
    # We want to schedule as many people as possible, but to prefer
    # the people who filled out the form first, all else being equal.
    person_goodness = {}
    for i, person in enumerate(availability):
        if len(person.free_slots) == 0:
            person.name += " (NA)"
        boost = (len(availability) - i) / (len(availability) ** 2)
        person_goodness[person.email] = 1 + boost
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
    for v, (person_email, _) in person_model["var_info"]:
        if solver.Value(v) == 1:
            names.add(person_email)
    print(f"Num people scheduled: {len(names)}")

    new_availability = [a for a in availability if a.email in names]
    block_model = create_base_model(new_availability, slots)
    # Require all people to be scheduled.
    for p_vars in block_model["person_vars"].values():
        block_model["model"].Add(sum(p_vars) == 1)
    block_badness = {}
    blocks = list(block_model["block_vars"].keys())
    blocks.sort(key=lambda b: parse_datetime_range(b)[0])
    for i, block in enumerate(blocks):
        # The later a block is, the worse it is.
        block_badness[block] = 1 + i / len(blocks)

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


def create_base_model(availability: list[Person], slots: list[Slot]) -> dict[str, Any]:
    slots_by_name = {s.name: s for s in slots}
    print(slots_by_name)
    model = cp_model.CpModel()
    block_vars = defaultdict(list)
    person_vars = defaultdict(list)
    block_used_vars = {}
    var_info = []
    for person in availability:
        for block in person.free_slots:
            person_block_var = model.NewBoolVar(f"{person.email} in {block}")
            block_vars[block].append(person_block_var)
            person_vars[person.email].append(person_block_var)
            var_info.append((person_block_var, (person.email, block)))
    for block in block_vars:
        block_used_var = model.NewBoolVar(f"{block} used")
        block_used_vars[block] = block_used_var
        model.AddBoolOr(block_vars[block]).OnlyEnforceIf(block_used_var)
        model.AddBoolAnd([v.Not() for v in block_vars[block]]).OnlyEnforceIf(
            block_used_var.Not()
        )
    # At most MAX_PER_BLOCK people per block.
    for block in block_vars:
        block_size = (
            len(get_time_intervals(block)) * slots_by_name[block].spots_multiplier
        )
        model.Add(sum(block_vars[block]) <= block_size)
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
    schedule = {block: [] for block in {block for _, (_, block) in var_info}}
    schedule[UNSCHEDULED_BLOCK] = []
    scheduled_emails = set()
    people_by_email = {p.email: p for p in availability}
    for var, (person_email, block) in var_info:
        if solver.Value(var):
            person = people_by_email[person_email]
            schedule[block].append(person)
            scheduled_emails.add(person_email)
    for person in availability:
        if person.email not in scheduled_emails:
            schedule[UNSCHEDULED_BLOCK].append(person)
    return schedule


def main():
    availability, slots = get_avail_data()
    schedule = create_schedule(availability, slots)
    print(pretty_print_schedule(schedule))
    write_schedule_to_csv(
        schedule, slots, rl.utils.io.get_data_path("tryout_schedule.csv")
    )


if __name__ == "__main__":
    main()
