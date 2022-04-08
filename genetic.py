from get_avail_csv import fetch_avail_csv
from main import get_availability_from_csv, Availability

Student = str | None
Block = list[Student]
Schedule = list[Block]

CROSSOVER_PROB = 0.7
MUTATION_PROB = 0.1


class GeneticAlgorithm:
    def __init__(self):
        pass

    def valid_schedule(self, schedule: Schedule) -> bool:
        pass

    def fitness(self, schedule: Schedule) -> int:
        pass

    def mutate(self, schedule: Schedule) -> None:
        pass

    def crossover(self, schedule1: Schedule, schedule2: Schedule) -> None:
        pass


def dict_from_availability(availability: list[Availability]) -> dict[str, set[str]]:
    avail_dict = {}
    for avail in availability:
        avail_dict[avail.name] = set(avail.free_slots)
    return avail_dict


if __name__ == "__main__":
    availability = dict_from_availability(get_availability_from_csv(fetch_avail_csv()))
    print(availability)
