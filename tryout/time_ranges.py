import re
from datetime import datetime, timedelta, time


DEFAULT_YEAR = datetime.now().year


def parse_datetime_range(time_range_str: str) -> tuple[datetime, datetime]:
    tokens = [t.strip() for t in time_range_str.split(",")]
    day, month_day, time_range = tokens
    start_time, end_time = parse_time_range(time_range)
    start_datetime = datetime.combine(
        datetime.strptime(f"{month_day} {DEFAULT_YEAR}", "%B %d %Y"), start_time
    )
    end_datetime = datetime.combine(
        datetime.strptime(f"{month_day} {DEFAULT_YEAR}", "%B %d %Y"), end_time
    )
    return start_datetime, end_datetime


def parse_time_range(time_range_str: str) -> tuple[time, time]:
    """
    :param time_range_str: A time range formatted like "1:00–2:00 p.m.", "1–2 PM" or "11:00 AM–12:00 PM"
    :return:
    """
    # replace a.m. and p.m with AM and PM
    time_range_str = (
        time_range_str.replace(".", "").replace("am", "AM").replace("pm", "PM")
    )

    start_time_str, end_time_str = re.split(r"[-–—]+", time_range_str)
    start_time_str = start_time_str.strip()
    end_time_str = end_time_str.strip()

    # Check if start time has a meridiem, if not, use the meridiem from the end time
    if "AM" not in start_time_str.upper() and "PM" not in start_time_str.upper():
        am_pm = re.search(r"(AM|PM)", end_time_str, flags=re.IGNORECASE).group(0)
        start_time_str = f"{start_time_str} {am_pm}"

    minutes_time_format = "%I:%M %p"
    no_minutes_time_format = "%I %p"
    start_time = (
        datetime.strptime(start_time_str, minutes_time_format).time()
        if (":" in start_time_str)
        else datetime.strptime(start_time_str, no_minutes_time_format).time()
    )
    end_time = (
        datetime.strptime(end_time_str, minutes_time_format).time()
        if (":" in end_time_str)
        else datetime.strptime(end_time_str, no_minutes_time_format).time()
    )

    return start_time, end_time


def get_time_intervals(
    datetime_range_str: str, interval_mins: int = 15, gap_mins: int = 5
) -> list[str]:
    """Given a string like "Monday, April 24, 1–2 p.m.", return a list of time intervals formatted as
    ["Monday, April 24, 1:00–1:15 p.m.", "Monday, April 24, 1:20–1:35 p.m.", ...]
    """
    start_datetime, end_datetime = parse_datetime_range(datetime_range_str)
    interval = timedelta(minutes=interval_mins)
    gap = timedelta(minutes=gap_mins)
    current_datetime = start_datetime
    time_intervals = []
    while current_datetime + interval + gap <= end_datetime:
        start_interval = current_datetime
        end_interval = current_datetime + interval
        # Only include the period in start time if it's not the same as the end time
        start_str = (
            start_interval.strftime("%A, %B %-e, %-l:%M")
            if start_interval.strftime("%p") == end_interval.strftime("%p")
            else start_interval.strftime("%A, %B %-e, %-l:%M %p")
        )
        end_str = end_interval.strftime("%-l:%M %p")
        time_intervals.append(f"{start_str}–{end_str}")
        current_datetime += interval + gap
    return time_intervals


def datetime_range_in_range(
    sub_range: tuple[datetime, datetime], super_range: tuple[datetime, datetime]
) -> bool:
    """Check if a datetime range is within another datetime range"""
    sub_start, sub_end = sub_range
    assert sub_start <= sub_end, f"sub_start {sub_start} must be before sub_end {sub_end}"
    super_start, super_end = super_range
    assert super_start <= super_end, (
        f"super_start {super_start} must be before super_end {super_end}"
    )
    return sub_start >= super_start and sub_end <= super_end


if __name__ == "__main__":
    PARSE_TIME_RANGE_TEST_CASES = [
        ("1:00–2:00 p.m.", (time(13, 0), time(14, 0))),
        ("11:00 AM–12:00 PM", (time(11, 0), time(12, 0))),
        ("3:00–4:00 p.m.", (time(15, 0), time(16, 0))),
        ("11:00 AM-2:00 p.m.", (time(11, 0), time(14, 0))),
        ("2 PM–3 PM", (time(14, 0), time(15, 0))),
        ("2–3 PM", (time(14, 0), time(15, 0))),
    ]

    PARSE_DATETIME_RANGE_TEST_CASES = [
        (
            "Monday, April 24, 1–2 p.m.",
            (
                datetime(datetime.now().year, 4, 24, 13, 0),
                datetime(datetime.now().year, 4, 24, 14, 0),
            ),
        ),
        (
            "Tuesday, May 2, 11 a.m.–12 p.m.",
            (
                datetime(datetime.now().year, 5, 2, 11, 0),
                datetime(datetime.now().year, 5, 2, 12, 0),
            ),
        ),
        (
            "Friday, June 16, 11 a.m.–12 p.m.",
            (
                datetime(datetime.now().year, 6, 16, 11, 0),
                datetime(datetime.now().year, 6, 16, 12, 0),
            ),
        ),
        (
            "Saturday, July 1, 10 a.m.–2 p.m.",
            (
                datetime(datetime.now().year, 7, 1, 10, 0),
                datetime(datetime.now().year, 7, 1, 14, 0),
            ),
        ),
    ]

    DATETIME_RANGE_TEST_CASES = [
        (
            "Monday, April 24, 1–2 p.m.",
            [
                "Monday, April 24, 1:00–1:15 PM",
                "Monday, April 24, 1:20–1:35 PM",
                "Monday, April 24, 1:40–1:55 PM",
            ],
        ),
        (
            "Tuesday, May 2, 11 a.m.–12 p.m.",
            [
                "Tuesday, May 2, 11:00–11:15 AM",
                "Tuesday, May 2, 11:20–11:35 AM",
                "Tuesday, May 2, 11:40–11:55 AM",
            ],
        ),
        (
            "Saturday, July 1, 10 a.m.–2 p.m.",
            [
                "Saturday, July 1, 10:00–10:15 AM",
                "Saturday, July 1, 10:20–10:35 AM",
                "Saturday, July 1, 10:40–10:55 AM",
                "Saturday, July 1, 11:00–11:15 AM",
                "Saturday, July 1, 11:20–11:35 AM",
                "Saturday, July 1, 11:40–11:55 AM",
                "Saturday, July 1, 12:00–12:15 PM",
                "Saturday, July 1, 12:20–12:35 PM",
                "Saturday, July 1, 12:40–12:55 PM",
                "Saturday, July 1, 1:00–1:15 PM",
                "Saturday, July 1, 1:20–1:35 PM",
                "Saturday, July 1, 1:40–1:55 PM",
            ],
        ),
        (
            "Tuesday, August 15, 11 a.m.–1 p.m.",
            [
                "Tuesday, August 15, 11:00–11:15 AM",
                "Tuesday, August 15, 11:20–11:35 AM",
                "Tuesday, August 15, 11:40–11:55 AM",
                "Tuesday, August 15, 12:00–12:15 PM",
                "Tuesday, August 15, 12:20–12:35 PM",
                "Tuesday, August 15, 12:40–12:55 PM",
            ],
        ),
        (
            "Sunday, September 24, 6–7 p.m.",
            [
                "Sunday, September 24, 6:00–6:15 PM",
                "Sunday, September 24, 6:20–6:35 PM",
                "Sunday, September 24, 6:40–6:55 PM",
            ],
        ),
        (
            "Monday, October 2, 12–2 p.m.",
            [
                "Monday, October 2, 12:00–12:15 PM",
                "Monday, October 2, 12:20–12:35 PM",
                "Monday, October 2, 12:40–12:55 PM",
                "Monday, October 2, 1:00–1:15 PM",
                "Monday, October 2, 1:20–1:35 PM",
                "Monday, October 2, 1:40–1:55 PM",
            ],
        ),
    ]

    for time_range_str, expected in PARSE_TIME_RANGE_TEST_CASES:
        start_time, end_time = parse_time_range(time_range_str)
        assert start_time == expected[0]
        assert end_time == expected[1]
    print("\033[92m" + "Time range parsing tests passed!" + "\033[0m")

    for datetime_range_str, expected in PARSE_DATETIME_RANGE_TEST_CASES:
        start_datetime, end_datetime = parse_datetime_range(datetime_range_str)
        assert start_datetime == expected[0], datetime_range_str
        assert end_datetime == expected[1], datetime_range_str
    print("\033[92m" + "Datetime range parsing tests passed!" + "\033[0m")
    

    for datetime_range_str, expected in DATETIME_RANGE_TEST_CASES:
        output = get_time_intervals(datetime_range_str)
        assert all([a == b for a, b in zip(output, expected)]), (
            datetime_range_str,
            expected,
            output,
        )
    print("\033[92m" + "Datetime interval creation tests passed!" + "\033[0m")
