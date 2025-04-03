import csv
import itertools
import random
from collections import defaultdict
from copy import deepcopy

import click
from load_data import JudgeAvailability, JudgeName, get_judge_data
from ortools.sat.python import cp_model

Round = str
Courtroom = str
Schedule = dict[Round, dict[Courtroom, list[JudgeAvailability]]]

MATCHES_PER_ROUND = {
    "Round 1 (11:45 a.m.)": 12,
    "Round 2 (1:00 p.m.)": 12,
    "Round 3 (3:00 p.m.)": 12,
    "Round 4 (10:30 a.m.)": 12,
    "Quarterfinals (12:00 noon)": 4,
    "Semifinals (2:15 p.m.)": 2,
    "Final (3:30 p.m.)": 1,
}
# These are the absolute maximum, with some headroom to ensure
# we can survive drops. Just to ensure we don't end up scheduling
# like 15 people to judge the final.
MAX_JUDGES_PER_MATCH = {
    "Round 1 (11:45 a.m.)": 3,
    "Round 2 (1:00 p.m.)": 3,
    "Round 3 (3:00 p.m.)": 3,
    "Round 4 (10:30 a.m.)": 3,
    "Quarterfinals (12:00 noon)": 5,
    "Semifinals (2:15 p.m.)": 5,
    "Final (3:30 p.m.)": 7,
}

GRADE_MAPPING = {
    0: 40,
    1: 35,
    2: 30,
    3: 20,
    4: 15,
}

ROUND_ORDER = [
    "Round 1 (11:45 a.m.)",
    "Round 2 (1:00 p.m.)",
    "Round 3 (3:00 p.m.)",
    "Round 4 (10:30 a.m.)",
    "Quarterfinals (12:00 noon)",
    "Semifinals (2:15 p.m.)",
    "Final (3:30 p.m.)",
]

_ALL_COURTROOM_LETTERS = [
    chr(ord("A") + i) for i in range(max(MATCHES_PER_ROUND.values()))
]
COURTROOM_LETTERS = {
    round_name: _ALL_COURTROOM_LETTERS[: MATCHES_PER_ROUND[round_name]]
    for round_name in MATCHES_PER_ROUND
}


def create_schedule(
    judges: list[JudgeAvailability], max_time_per_stage: int
) -> Schedule:
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
    solved_schedule, dev_objective = solve_model(full_model, judges, max_time_per_stage)

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
    solved_schedule, dev_objective = solve_model(
        full_model, judges, max_time_in_seconds=max_time_per_stage
    )

    # full_model = initialize_full_model(judges)
    # setup_judge_movement_optimization(
    #     full_model,
    #     solved_schedule,
    #     dev_objective,
    #     judge_grades,
    #     [
    #         "Round 2 (2:00 p.m.)",
    #         "Round 3 (3:30 p.m.)",
    #         "Quarterfinals (12:00 noon)",
    #         "Semifinals (2:15 p.m.)",
    #     ],
    # )
    # judge_movement_minimization = judge_movement_objective(
    #     full_model["model"],
    #     full_model["vars_by_judge_courtroom_round"],
    #     full_model["vars_by_judge_round_courtroom"],
    # )
    # full_model["model"].Minimize(judge_movement_minimization)
    # mv_optimized_schedule, mv_objective = solve_model(
    #     full_model, judges, max_time_in_seconds=max_time_per_stage
    # )

    return solved_schedule


def setup_judge_movement_optimization(
    full_model,
    previous_solved_schedule: Schedule,
    objective: float,
    judge_grades: dict[JudgeName, float],
    unpinned_rounds: list[str],
):
    for round_name in previous_solved_schedule:
        for courtroom in previous_solved_schedule[round_name]:
            judges_in_room = [
                j["name"] for j in previous_solved_schedule[round_name][courtroom]
            ]
            for judge_name in judges_in_room:
                full_model["model"].Add(
                    sum(
                        full_model["vars_by_round_judge_courtroom"][round_name][
                            judge_name
                        ].values()
                    )
                    == 1
                )
                # Pin all the judge assignments except for the specified
                # to allow the solver to minimize movement between just some rounds
                # In a perfect world, we'd leave them all free, but the solver can't
                # handle that many possibilities (within my lifetime, at least).
                if round_name not in unpinned_rounds:
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
            strict=False,
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
                vars_by_judge_round_courtroom[judge["name"]][round_name][courtroom] = (
                    curr_var
                )
                vars_by_round_courtroom_judge[round_name][courtroom][judge["name"]] = (
                    curr_var
                )
                vars_by_judge_courtroom_round[judge["name"]][courtroom][round_name] = (
                    curr_var
                )
                vars_by_round_judge_courtroom[round_name][judge["name"]][courtroom] = (
                    curr_var
                )
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
    judge_movement_vars = []
    for judge in vars_by_judge_courtroom_round:
        for r1, r2 in zip(ROUND_ORDER, ROUND_ORDER[1:], strict=False):
            if r1 == "Round 3 (2:00 p.m.)" and r2 == "Round of 16 (10:45 a.m.)":
                # This is across a day boundary, so we don't care about switching
                continue
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
            judge_movement_vars.append(judge_switches_courtrooms)
    return sum(judge_movement_vars)


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
            schedule[round_name][courtroom].sort(key=lambda j: j["grade"], reverse=True)
    return schedule


def pretty_print_schedule(schedule: Schedule):
    output = ""
    rounds = sorted(schedule.keys(), key=lambda r: ROUND_ORDER.index(r))
    for round_name in rounds:
        output += f"{round_name}:\n"
        for courtroom in schedule[round_name]:
            judge_names = ", ".join(j["name"] for j in schedule[round_name][courtroom])
            score = sum([j["grade"] for j in schedule[round_name][courtroom]])
            output += f"\t{courtroom}: {judge_names} ({score})\n"
    return output


def write_schedule_to_csv(
    schedule: Schedule, judges: list[JudgeAvailability], filename: str
):
    # Format:
    # Round 1
    # Courtroom A, Courtroom B, Courtroom C
    # Judge A1, Judge B1, Judge C1
    # Judge A2, Judge B2, Judge C2
    # ...
    # Round 2
    # ...
    with open(filename, "w") as f:
        writer = csv.writer(f)
        for round_name in schedule:
            writer.writerow([round_name])
            round_headers = list(schedule[round_name].keys()) + ["Unscheduled"]
            writer.writerow(round_headers)
            max_num_judges = max(
                MAX_JUDGES_PER_MATCH[round_name],
                max(
                    len(schedule[round_name][courtroom])
                    for courtroom in schedule[round_name]
                ),
            )
            judges_in_round = {
                judge["email"]
                for judge in itertools.chain.from_iterable(
                    schedule[round_name].values()
                )
            }
            judges_signed_up = {
                judge["email"] for judge in judges if round_name in judge["free_slots"]
            }
            judges_not_used = judges_signed_up - judges_in_round
            judges_not_used = [
                judge for judge in judges if judge["email"] in judges_not_used
            ]
            judges_not_used.sort(key=lambda j: j["grade"])
            # split judges_not_used into groups of max_num_judges
            judges_not_used = [
                judges_not_used[i : i + max_num_judges]
                for i in range(0, len(judges_not_used), max_num_judges)
            ]

            for i in range(max_num_judges):
                row = []
                for courtroom in schedule[round_name]:
                    if i < len(schedule[round_name][courtroom]):
                        row.append(schedule[round_name][courtroom][i]["name"])
                    else:
                        row.append("")
                # Add unscheduled judges
                for judges_not_used_group in judges_not_used:
                    if i < len(judges_not_used_group):
                        row.append(judges_not_used_group[i]["name"])
                    else:
                        row.append("")
                writer.writerow(row)
            writer.writerow([])


def print_judge_summary(judges: list[JudgeAvailability]) -> str:
    """Outputs the number of available judges for each round

    E.g.:
    Round 1: 10
    Round 2: 8
    ...
    """
    output = "Judges available per round:"
    for round_name in ROUND_ORDER:
        num_judges = len(
            [judge for judge in judges if round_name in judge["free_slots"]]
        )
        output += f"\n{round_name}: {num_judges}"
    return output


def write_unscheduled_to_csv(
    schedule: Schedule, judges: list[JudgeAvailability], filename: str
):
    unscheduled_by_judge: dict[str, list[str]] = defaultdict(list)
    for round_name in schedule:
        judges_in_round = {
            j["email"]
            for j in itertools.chain.from_iterable(schedule[round_name].values())
        }
        judges_signed_up = {j["email"] for j in judges if round_name in j["free_slots"]}
        for email in judges_signed_up - judges_in_round:
            unscheduled_by_judge[email].append(round_name)

    with open(filename, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Email", "Unscheduled Rounds"])
        judge_lookup = {j["email"]: j["name"] for j in judges}
        for email, rounds in sorted(
            unscheduled_by_judge.items(), key=lambda x: judge_lookup[x[0]]
        ):
            if rounds:  # Only write if they have unscheduled rounds
                writer.writerow([judge_lookup[email], email, ", ".join(rounds)])


@click.command()
@click.option(
    "--max_time_per_stage",
    "-t",
    default=30,
    help="Maximum time (in seconds) to spend on each stage of the optimization",
)
def main(max_time_per_stage):
    judges = get_judge_data()
    print(print_judge_summary(judges))
    schedule = create_schedule(judges, max_time_per_stage=max_time_per_stage)
    print(pretty_print_schedule(schedule))
    write_schedule_to_csv(schedule, judges, "schedule.csv")
    write_unscheduled_to_csv(schedule, judges, "unscheduled.csv")


if __name__ == "__main__":
    main()
