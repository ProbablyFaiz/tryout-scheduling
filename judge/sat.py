import random
from collections import defaultdict
from copy import deepcopy

from load_data import get_judge_data, JudgeAvailability, JudgeName

from ortools.sat.python import cp_model

Round = str
Courtroom = str
Schedule = dict[Round, dict[Courtroom, list[JudgeAvailability]]]

MATCHES_PER_ROUND = {
    "Round 1 (10:45 a.m.)": 16,
    "Round 2 (12:00 p.m.)": 16,
    "Round 3 (2:00 p.m.)": 16,
    "Round of 16 (10:45 a.m.)": 8,
    "Quarterfinals (12:15 p.m.)": 4,
    "Semifinals (2:30 p.m.)": 2,
    "Final (3:45 p.m.)": 1,
}
# These are the absolute maximum, with some headroom to ensure
# we can survive drops. Just to ensure we don't end up scheduling
# like 15 people to judge the final.
MAX_JUDGES_PER_MATCH = {
    "Round 1 (10:45 a.m.)": 3,
    "Round 2 (12:00 p.m.)": 3,
    "Round 3 (2:00 p.m.)": 3,
    "Round of 16 (10:45 a.m.)": 5,
    "Quarterfinals (12:15 p.m.)": 5,
    "Semifinals (2:30 p.m.)": 7,
    "Final (3:45 p.m.)": 7,
}

GRADE_MAPPING = {
    1: 35,
    2: 30,
    3: 25,
    4: 20,
}

ROUND_ORDER = [
    "Round 1 (10:45 a.m.)",
    "Round 2 (12:00 p.m.)",
    "Round 3 (2:00 p.m.)",
    "Round of 16 (10:45 a.m.)",
    "Quarterfinals (12:15 p.m.)",
    "Semifinals (2:30 p.m.)",
    "Final (3:45 p.m.)",
]

_ALL_COURTROOM_LETTERS = [
    chr(ord("A") + i) for i in range(max(MATCHES_PER_ROUND.values()))
]
COURTROOM_LETTERS = {
    round_name: _ALL_COURTROOM_LETTERS[: MATCHES_PER_ROUND[round_name]]
    for round_name in MATCHES_PER_ROUND
}


def create_schedule(judges: list[JudgeAvailability]):
    judges = deepcopy(judges)
    for judge in judges:
        judge["grade"] = GRADE_MAPPING[judge["grade"]]
    judge_grades = {judge["name"]: judge["grade"] for judge in judges}

    full_model = initialize_full_model(judges)
    round_sum_maximization = sum(
        round_objective(round_vars, judge_grades)
        for round_vars in full_model["vars_by_round_courtroom_judge"].values()
    )
    full_model["model"].Maximize(round_sum_maximization)
    solved_schedule, objective = solve_model(full_model, judges)

    judges_by_round = defaultdict(set)
    for round_name in solved_schedule:
        for courtroom in solved_schedule[round_name]:
            for judge in solved_schedule[round_name][courtroom]:
                judges_by_round[round_name].add(judge["name"])

    full_model = initialize_full_model(judges)
    for round_name in full_model["vars_by_round_judge_courtroom"]:
        for judge_name in full_model["vars_by_round_judge_courtroom"][round_name]:
            if judge_name in judges_by_round[round_name]:
                full_model["model"].Add(
                    sum(
                        full_model["vars_by_round_judge_courtroom"][round_name][
                            judge_name
                        ].values()
                    )
                    == 1
                )
    deviation_from_average_round_score_vars = get_deviation_vars(
        judge_grades, full_model["model"], full_model["vars_by_round_courtroom_judge"]
    )
    deviation_minimization = sum(deviation_from_average_round_score_vars.values())
    full_model["model"].Minimize(deviation_minimization)
    solved_schedule, objective = solve_model(full_model, judges, max_time_in_seconds=20)
    print(pretty_print_schedule(solved_schedule))

    full_model = initialize_full_model(judges)
    for round_name in solved_schedule:
        for courtroom in solved_schedule[round_name]:
            judges_in_room = [j["name"] for j in solved_schedule[round_name][courtroom]]
            for judge_name in judges_in_room:
                full_model["model"].Add(
                    sum(
                        full_model["vars_by_round_judge_courtroom"][round_name][
                            judge_name
                        ].values()
                    )
                    == 1
                )
                # Pin all the judge assignments except for round 2 and the quarterfinals
                # to allow the solver to minimize movement between back-to-back rounds.
                # In a perfect world, we'd leave them all free, but the solver can't
                # handle that many possibilities (within my lifetime, at least).
                if round_name not in ("Round 2 (12:00 p.m.)", "Quarterfinals (12:15 p.m.)"):
                    full_model["model"].Add(
                        full_model["vars_by_round_judge_courtroom"][round_name][
                            judge_name
                        ][courtroom]
                        == 1
                    )

    deviation_from_average_round_score_vars = get_deviation_vars(
        judge_grades, full_model["model"], full_model["vars_by_round_courtroom_judge"]
    )
    deviation_minimization = sum(deviation_from_average_round_score_vars.values())
    full_model["model"].Add(deviation_minimization <= int(objective))
    judge_movement_minimization = judge_movement_objective(
        full_model["model"],
        full_model["vars_by_judge_courtroom_round"],
        full_model["vars_by_judge_round_courtroom"],
    )
    full_model["model"].Minimize(judge_movement_minimization)
    schedule, objective = solve_model(full_model, judges, max_time_in_seconds=60)
    print(pretty_print_schedule(schedule))


def solve_model(full_model, judges, max_time_in_seconds=10):
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_time_in_seconds
    status = solver.Solve(full_model["model"])
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print(
            f"Schedule found! Objective value: {solver.ObjectiveValue()} ({solver.StatusName(status)})"
        )
        return (
            get_schedule_from_solution(
                solver, full_model["vars_by_round_courtroom_judge"], judges
            ),
            solver.ObjectiveValue(),
        )
    else:
        print("No schedule found :(")


def get_deviation_vars(judge_grades, model, vars_by_round_courtroom_judge):
    deviation_from_average_round_score_vars = {}
    for round_name, num_matches in MATCHES_PER_ROUND.items():
        max_match_score = max(GRADE_MAPPING.values()) * MAX_JUDGES_PER_MATCH[round_name]
        sum_round_score_var = model.NewIntVar(
            0,
            max_match_score * num_matches,
            f"Total score for {round_name}",
        )
        model.Add(
            sum_round_score_var
            == sum(
                match_objective(match, judge_grades)
                for match in vars_by_round_courtroom_judge[round_name].values()
            )
        )
        average_round_score_var = model.NewIntVar(
            0,
            max_match_score,
            f"Average score for {round_name}",
        )
        # We need to use CpModel.AddDivisionEquality for the average
        model.AddDivisionEquality(
            average_round_score_var,
            sum_round_score_var,
            num_matches,
        )
        deviation_vars = [
            model.NewIntVar(
                0,
                max_match_score**2,
                f"Deviation from average for {round_name} — {courtroom}",
            )
            for courtroom in COURTROOM_LETTERS[round_name]
        ]
        for dev_var, match in zip(
            deviation_vars,
            vars_by_round_courtroom_judge[round_name].values(),
        ):
            variance = match_objective(match, judge_grades) - average_round_score_var
            # We have to add this mediating abs variable because AddMultiplicationEquality
            # blows up if we try to multiply negative numbers
            abs_variance = model.NewIntVar(
                0,
                max_match_score**2,
                f"Absolute variance from average for {random.random()}",
            )
            model.AddAbsEquality(abs_variance, variance)
            model.AddMultiplicationEquality(
                dev_var,
                abs_variance,
                abs_variance,
            )
        deviation_from_average_round_score_vars[round_name] = model.NewIntVar(
            0,
            max_match_score**2 * num_matches,
            f"Deviation from average for {round_name}",
        )
        model.Add(
            sum(deviation_vars) == deviation_from_average_round_score_vars[round_name]
        )
    return deviation_from_average_round_score_vars


def initialize_full_model(judges):
    model = cp_model.CpModel()
    # Vars by judge and then round
    vars_by_judge_round_courtroom = defaultdict(lambda: defaultdict(dict))
    # Vars by round and then courtroom
    vars_by_round_courtroom_judge = defaultdict(lambda: defaultdict(dict))
    vars_by_judge_courtroom_round = defaultdict(lambda: defaultdict(dict))
    vars_by_round_judge_courtroom = defaultdict(lambda: defaultdict(dict))
    for judge in judges:
        for round_name in ROUND_ORDER:
            for courtroom in COURTROOM_LETTERS[round_name]:
                # A variable that represents whether a judge is in a courtroom in a given round.
                curr_var = model.NewBoolVar(
                    f"{judge['name']} in {round_name} — {courtroom}"
                )
                if round_name not in judge["free_slots"]:
                    model.Add(curr_var == 0)
                vars_by_judge_round_courtroom[judge["name"]][round_name][
                    courtroom
                ] = curr_var
                vars_by_round_courtroom_judge[round_name][courtroom][
                    judge["name"]
                ] = curr_var
                vars_by_judge_courtroom_round[judge["name"]][courtroom][
                    round_name
                ] = curr_var
                vars_by_round_judge_courtroom[round_name][judge["name"]][
                    courtroom
                ] = curr_var
            # A judge can be in one courtroom per round at most.
            model.AddAtMostOne(
                vars_by_judge_round_courtroom[judge["name"]][round_name].values()
            )
    for round_name, limit in MAX_JUDGES_PER_MATCH.items():
        for courtroom in COURTROOM_LETTERS[round_name]:
            # A courtroom can have at most `limit` judges for a round.
            model.Add(
                sum(vars_by_round_courtroom_judge[round_name][courtroom].values())
                <= limit
            )
    full_model = {
        "model": model,
        "vars_by_judge_round_courtroom": vars_by_judge_round_courtroom,
        "vars_by_round_courtroom_judge": vars_by_round_courtroom_judge,
        "vars_by_judge_courtroom_round": vars_by_judge_courtroom_round,
        "vars_by_round_judge_courtroom": vars_by_round_judge_courtroom,
    }
    return full_model


def round_objective(
    round_vars: dict[Courtroom, dict[JudgeName, cp_model.IntVar]],
    judge_grades: dict[JudgeName, float],
):
    return sum(match_objective(match, judge_grades) for match in round_vars.values())


def match_objective(
    match_vars: dict[JudgeName, cp_model.IntVar], judge_grades: dict[JudgeName, float]
):
    return sum(match_vars[judge] * judge_grades[judge] for judge in match_vars)


def judge_movement_objective(
    model: cp_model.CpModel,
    vars_by_judge_courtroom_round: dict[
        JudgeName, dict[Courtroom, dict[Round, cp_model.IntVar]]
    ],
    vars_by_judge_round_courtroom: dict[
        JudgeName, dict[Round, dict[Courtroom, cp_model.IntVar]]
    ],
):
    judge_switches_vars = []
    for judge in vars_by_judge_courtroom_round:
        for r1, r2 in zip(ROUND_ORDER, ROUND_ORDER[1:]):
            judge_switches_courtrooms = model.NewBoolVar(
                f"{judge} in {r1} and {r2} and in different courtrooms"
            )
            requirements_for_switch = []

            # First, the judge has to be in both rounds
            both_rounds_aux_var = model.NewBoolVar(f"{judge} in {r1} and {r2}")
            model.Add(
                sum(vars_by_judge_round_courtroom[judge][r1].values())
                + sum(vars_by_judge_round_courtroom[judge][r2].values())
                >= 2
            ).OnlyEnforceIf(both_rounds_aux_var)
            model.Add(
                sum(vars_by_judge_round_courtroom[judge][r1].values())
                + sum(vars_by_judge_round_courtroom[judge][r2].values())
                < 2
            ).OnlyEnforceIf(both_rounds_aux_var.Not())
            requirements_for_switch.append(both_rounds_aux_var)

            # Second, the judge has to be in different courtrooms
            for courtroom in set(vars_by_judge_round_courtroom[judge][r1]) & set(
                vars_by_judge_round_courtroom[judge][r2]
            ):
                different_courtrooms_aux_var = model.NewBoolVar(
                    f"{judge} in {r1} and {r2} and in different courtrooms ({courtroom})"
                )
                model.Add(
                    vars_by_judge_round_courtroom[judge][r1][courtroom]
                    + vars_by_judge_round_courtroom[judge][r2][courtroom]
                    <= 1
                ).OnlyEnforceIf(different_courtrooms_aux_var)
                model.Add(
                    vars_by_judge_round_courtroom[judge][r1][courtroom]
                    + vars_by_judge_round_courtroom[judge][r2][courtroom]
                    > 1
                ).OnlyEnforceIf(different_courtrooms_aux_var.Not())
                requirements_for_switch.append(different_courtrooms_aux_var)
            model.AddBoolAnd(requirements_for_switch).OnlyEnforceIf(
                judge_switches_courtrooms
            )
            model.AddBoolOr([r.Not() for r in requirements_for_switch]).OnlyEnforceIf(
                judge_switches_courtrooms.Not()
            )
            judge_switches_vars.append(judge_switches_courtrooms)
    return sum(judge_switches_vars)


def get_schedule_from_solution(
    solver: cp_model.CpSolver,
    vars_by_round_courtroom_judge: dict[
        Round, dict[Courtroom, dict[JudgeName, cp_model.IntVar]]
    ],
    judges: list[JudgeAvailability],
) -> Schedule:
    schedule = {}
    for round_name in vars_by_round_courtroom_judge:
        schedule[round_name] = {}
        for courtroom in vars_by_round_courtroom_judge[round_name]:
            schedule[round_name][courtroom] = []
            for judge in judges:
                judge_var = vars_by_round_courtroom_judge[round_name][courtroom].get(
                    judge["name"]
                )
                if judge_var is not None and solver.Value(judge_var):
                    schedule[round_name][courtroom].append(judge)
    return schedule


def pretty_print_schedule(schedule: Schedule):
    output = ""
    rounds = sorted(schedule.keys(), key=lambda r: ROUND_ORDER.index(r))
    for round_name in rounds:
        output += f"{round_name}:\n"
        for courtroom in schedule[round_name]:
            judge_names = ", ".join(
                [
                    j["name"]
                    for j in sorted(
                        schedule[round_name][courtroom],
                        key=lambda j: j["grade"],
                        reverse=True,
                    )
                ]
            )
            score = sum([j["grade"] for j in schedule[round_name][courtroom]])
            output += f"\t{courtroom}: {judge_names} ({score})\n"
    return output


def main():
    judges = get_judge_data()
    create_schedule(judges)


if __name__ == "__main__":
    main()
