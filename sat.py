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


class VarArraySolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Print intermediate solutions."""

    def __init__(self, var_info, availability):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__var_info = var_info
        self.__availability = availability
        self.__solution_count = 0

    def on_solution_callback(self):
        self.__solution_count += 1
        print(f"Solution #{self.__solution_count}: {self.ObjectiveValue()}")
        print(pretty_print_schedule(solved_to_schedule(self, self.__var_info, self.__availability)))

    def solution_count(self):
        return self.__solution_count

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

    person_goodness = {}
    for i, person in enumerate(availability):
        person_goodness[person.name] = 2 - i / len(availability)

    # We want to maximize the sum of the goodness of the people scheduled.
    # The idea being to schedule as many people as possible, but to prefer
    # the people who filled out the form first.
    model.Maximize(sum(sum(person_vars[p]) * person_goodness[p] for p in person_vars))

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    print(f"Status: {solver.StatusName(status)}")
    print(f"Objective value: {solver.ObjectiveValue()}, Num people: {len(availability)}")

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
    availability = get_avail_data()
    # Randomly select half the people
    # availability = random.sample(availability, len(availability) // 2)
    schedule = create_schedule(availability)
    print(pretty_print_schedule(schedule))


if __name__ == "__main__":
    main()
