from collections import defaultdict
from datetime import date
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


def compute_person_goodness(availability: list[Person]) -> dict[str, float]:
    """Compute goodness scores for each person, favoring earlier form submissions."""
    person_goodness = {}
    for i, person in enumerate(availability):
        if not person.free_slots:
            person.name += " (NA)"
        boost = (len(availability) - i) / (len(availability) ** 2)
        person_goodness[person.email] = 1 + boost
    return person_goodness


def compute_block_badness(blocks: list[str]) -> dict[str, float]:
    """Compute badness scores for blocks, with later blocks being worse."""
    blocks = sorted(blocks, key=lambda b: parse_datetime_range(b)[0])
    return {block: 1 + i / len(blocks) for i, block in enumerate(blocks)}


def compute_day_badness(days: list[date]) -> dict[date, float]:
    """Compute badness scores for days, with later days being worse."""
    days = sorted(days)
    return {day: 1 + i / len(days) for i, day in enumerate(days)}


def create_schedule(availability: list[Person], slots: list[Slot]) -> Schedule:
    block_model = create_base_model(availability, slots)
    # Require all people to be scheduled.
    for p_vars in block_model["person_vars"].values():
        block_model["model"].Add(sum(p_vars) == 1)

    person_goodness = compute_person_goodness(availability)
    block_badness = compute_block_badness(list(block_model["block_vars"].keys()))
    day_badness = compute_day_badness(list(block_model["day_used_vars"].keys()))

    block_model["model"].Minimize(
        -sum(
            sum(p_vars) * person_goodness[p]
            for p, p_vars in block_model["person_vars"].items()
        )
        * 1000
        + sum(
            d_var * day_badness[d] for d, d_var in block_model["day_used_vars"].items()
        )
        * 100
        + sum(
            b_var * block_badness[b]
            for b, b_var in block_model["block_used_vars"].items()
        )
    )

    solver = cp_model.CpSolver()
    status = solver.Solve(block_model["model"])
    print(f"Status: {solver.StatusName(status)}")
    print(f"Objective value: {solver.ObjectiveValue()}")
    return solved_to_schedule(solver, block_model["var_info"], availability)


def get_block_day(block: str) -> date:
    return parse_datetime_range(block)[0].date()


def create_base_model(availability: list[Person], slots: list[Slot]) -> dict[str, Any]:
    slots_by_name = {s.name: s for s in slots}
    print(slots_by_name)
    model = cp_model.CpModel()
    block_vars = defaultdict(list)
    person_vars = defaultdict(list)
    block_used_vars: dict[str, Any] = {}
    day_used_vars: dict[date, Any] = {}
    var_info = []
    for person in availability:
        for block in person.free_slots:
            person_block_var = model.NewBoolVar(f"{person.email} in {block}")
            block_vars[block].append(person_block_var)
            person_vars[person.email].append(person_block_var)
            var_info.append((person_block_var, (person.email, block)))
        # Allow a person to be scheduled at most once.
        model.Add(sum(person_vars[person.email]) <= 1)
    for block in block_vars:
        block_used_var = model.NewBoolVar(f"{block} used")
        block_used_vars[block] = block_used_var
        model.AddBoolOr(block_vars[block]).OnlyEnforceIf(block_used_var)
        model.AddBoolAnd([v.Not() for v in block_vars[block]]).OnlyEnforceIf(
            block_used_var.Not()
        )

    blocks_by_day = defaultdict(list)
    for block in block_vars:
        blocks_by_day[get_block_day(block)].append(block)

    for day in blocks_by_day:
        day_used_var = model.NewBoolVar(f"{day} used")
        day_used_vars[day] = day_used_var
        block_used_vars_for_day = [block_used_vars[b] for b in blocks_by_day[day]]
        model.AddBoolOr(block_used_vars_for_day).OnlyEnforceIf(day_used_var)
        model.AddBoolAnd([v.Not() for v in block_used_vars_for_day]).OnlyEnforceIf(
            day_used_var.Not()
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
        "day_used_vars": day_used_vars,
        "var_info": var_info,
    }


def solved_to_schedule(solver, var_info, availability: list[Person]) -> Schedule:
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
