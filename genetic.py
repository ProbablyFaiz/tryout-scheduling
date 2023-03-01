from collections import defaultdict
from copy import deepcopy
from random import random, choice, choices, randint
from typing import Iterable

from get_avail_csv import fetch_avail_csv
from greedy import get_availability_from_csv, Availability, block_sort_key


class HList(list):
    def __init__(self, *args):
        if len(args) == 1 and isinstance(args[0], Iterable):
            args = args[0]
        super().__init__(args)

    def __hash__(self):
        return hash(e for e in self)


# Represents the absence of anyone scheduled in a slot
Nobody = None
Student = str | Nobody
Slot = str
Block = tuple[Slot, HList[Student]]
Schedule = HList[Block]

MAX_STUDENTS_PER_SLOT = 3
CROSSOVER_PROB = 0.1
MUTATION_PROB = 0.2
POPULATION_SIZE = 500
NUM_ELITES = POPULATION_SIZE // 20
NUM_RANDOM = POPULATION_SIZE // 20
NUM_GENERATIONS = 1000


class GeneticAlgorithm:
    # We use a set here so we can check for a slot in O(1) time
    student_availability: dict[Student, set[Slot]]
    slot_availability: dict[Slot, list[Student]]
    population: list[Schedule]

    def __init__(self, availability: list[Availability]):
        self.student_availability = self.student_availability_dict(availability)
        self.slot_availability = self.slot_availability_dict(availability)
        self.population = self.initial_population()
        best_schedule = max(self.population, key=self.fitness)
        print(self.fitness(best_schedule, verbose=True))

    def run(self) -> Schedule:
        best_schedule = None
        for i in range(NUM_GENERATIONS):
            self.population = self.next_generation()
            if i % 50 == 0:
                best_schedule = max(self.population, key=self.fitness)
                print(self.fitness(best_schedule, verbose=True))
        return best_schedule

    def next_generation(self) -> list[Schedule]:
        pop_fitness_map = {
            schedule: self.fitness(schedule) for schedule in self.population
        }
        fitness_baseline = min(pop_fitness_map.values()) * 2

        new_population = []

        num_children = POPULATION_SIZE - NUM_ELITES - NUM_RANDOM
        # Select parents of next generation, weighting by parent fitness
        parents = iter(
            choices(
                self.population,
                weights=[
                    self.fitness(schedule) - fitness_baseline
                    for schedule in self.population
                ],
                k=num_children * 2,
            )
        )

        for parent1 in parents:
            parent2 = next(parents)
            new_population.append(self.crossover(parent1, parent2))
        # And mutate the new population
        for schedule in new_population:
            self.mutate(schedule)

        # Add the random schedules
        new_population.extend(self.random_schedule() for _ in range(NUM_RANDOM))
        # Select elites to preserve
        new_population.extend(
            sorted(self.population, key=self.fitness, reverse=True)[:NUM_ELITES]
        )
        return new_population

    def fitness(self, schedule: Schedule, verbose=False) -> int:
        scheduled_students = set()
        num_duplicate_scheduled = 0
        num_blocks_used = 0
        for (slot, students) in schedule:
            block_used = False
            for student in students:
                if student is Nobody:
                    continue
                block_used = True
                if student in scheduled_students:
                    num_duplicate_scheduled += 1
                scheduled_students.add(student)
            if block_used:
                num_blocks_used += 1
        num_unscheduled = len(self.student_availability) - len(scheduled_students)
        fitness_score = -(
            # Add a penalty of 2 if there are any unscheduled
            num_unscheduled * 2
            # + 2 * int(num_unscheduled > 0)
            + num_blocks_used
            + num_duplicate_scheduled
        )
        if verbose:
            print(
                f"{num_duplicate_scheduled} duplicate, {num_unscheduled} unscheduled,"
                f" {num_blocks_used} blocks used"
            )
            print(f"Fitness score: {fitness_score}")
        return fitness_score

    def mutate(self, schedule: Schedule) -> Schedule:
        new_schedule = deepcopy(schedule)
        for (slot, students) in new_schedule:
            for i in range(len(students)):
                if random() < MUTATION_PROB:
                    students[i] = choice(self.slot_availability[slot])
                # elif random() < MUTATION_PROB and students[i] is not Nobody:
                #     swap_made = False
                #     for (other_slot, other_students) in new_schedule:
                #         if other_slot != slot and other_slot in self.student_availability[students[i]]:
                #             for j in range(len(other_students)):
                #                 if other_students[j] is Nobody:
                #                     other_students[j] = students[i]
                #                     students[i] = Nobody
                #                     swap_made = True
                #                     break
                #         if swap_made:
                #             break
        return new_schedule

    def crossover(self, schedule1: Schedule, schedule2: Schedule) -> Schedule:
        new_schedule = deepcopy(schedule1)
        for i in range(len(new_schedule)):
            if random() < CROSSOVER_PROB:
                new_schedule[i:] = deepcopy(schedule2[i:])
                break
        return new_schedule

    def initial_population(self) -> list[Schedule]:
        population = []
        for _ in range(POPULATION_SIZE):
            population.append(self.random_schedule())
        return population

    def random_schedule(self) -> Schedule:
        schedule = HList()
        for slot in self.slot_availability:
            schedule.append(
                (
                    slot,
                    HList(
                        choices(self.slot_availability[slot], k=MAX_STUDENTS_PER_SLOT)
                    ),
                )
            )
        return schedule

    def student_availability_dict(
        self, availability: list[Availability]
    ) -> dict[Student, set[Slot]]:
        avail_dict = {}
        for avail in availability:
            avail_dict[avail.name] = set(avail.free_slots)
        return avail_dict

    def slot_availability_dict(
        self,
        availability: list[Availability],
    ) -> dict[Slot, list[Student]]:
        """
        Returns a dictionary mapping each slot to a list of students who can be scheduled in that slot.
        :param availability:
        :return:
        """
        avail_dict = defaultdict(list)
        for avail in availability:
            for slot in avail.free_slots:
                avail_dict[slot].append(avail.name)
        # Allow blocks to be empty
        for students in avail_dict.values():
            students.append(Nobody)
        return avail_dict

    def pretty_print_schedule(self, schedule: Schedule) -> None:
        student_count = 0
        schedule.sort(key=lambda b: block_sort_key(b[0]))
        for (slot, students) in schedule:
            non_empty_students = [s for s in students if s is not Nobody]
            student_count += len(non_empty_students)
            student_str = ", ".join(non_empty_students) or "FREE"
            print(f"{slot} - {student_str}")
        print(f"Duplicate schedules: {student_count - len(self.student_availability)}")


if __name__ == "__main__":
    availability = get_availability_from_csv(fetch_avail_csv())
    genetic = GeneticAlgorithm(availability)
    result_schedule = genetic.run()
    genetic.pretty_print_schedule(result_schedule)
