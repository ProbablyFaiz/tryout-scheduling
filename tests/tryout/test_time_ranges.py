from datetime import datetime, time

import pytest

from scheduler.tryout.time_ranges import (
    datetime_range_in_range,
    get_time_intervals,
    parse_datetime_range,
    parse_time_range,
)

_ASSUME_YEAR = 2024


class TestTimeRanges:
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

    @pytest.mark.parametrize("time_range_str,expected", PARSE_TIME_RANGE_TEST_CASES)
    def test_parse_time_range(self, time_range_str, expected):
        start_time, end_time = parse_time_range(time_range_str)
        assert start_time == expected[0]
        assert end_time == expected[1]

    @pytest.mark.parametrize(
        "datetime_range_str,expected", PARSE_DATETIME_RANGE_TEST_CASES
    )
    def test_parse_datetime_range(self, datetime_range_str, expected):
        start_datetime, end_datetime = parse_datetime_range(datetime_range_str)
        assert start_datetime == expected[0], datetime_range_str
        assert end_datetime == expected[1], datetime_range_str

    @pytest.mark.parametrize("datetime_range_str,expected", DATETIME_RANGE_TEST_CASES)
    def test_get_time_intervals(self, datetime_range_str, expected):
        output = get_time_intervals(datetime_range_str, _ASSUME_YEAR)
        assert all(a == b for a, b in zip(output, expected, strict=False)), (
            datetime_range_str,
            expected,
            output,
        )

    def test_datetime_range_in_range(self):
        # Test case where sub_range is completely within super_range
        sub_range = (datetime(2023, 1, 1, 12, 0), datetime(2023, 1, 1, 13, 0))
        super_range = (datetime(2023, 1, 1, 11, 0), datetime(2023, 1, 1, 14, 0))
        assert datetime_range_in_range(sub_range, super_range)

        # Test case where sub_range is exactly the same as super_range
        sub_range = (datetime(2023, 1, 1, 11, 0), datetime(2023, 1, 1, 14, 0))
        super_range = (datetime(2023, 1, 1, 11, 0), datetime(2023, 1, 1, 14, 0))
        assert datetime_range_in_range(sub_range, super_range)

        # Test case where sub_range extends beyond super_range
        sub_range = (datetime(2023, 1, 1, 10, 0), datetime(2023, 1, 1, 13, 0))
        super_range = (datetime(2023, 1, 1, 11, 0), datetime(2023, 1, 1, 14, 0))
        assert not datetime_range_in_range(sub_range, super_range)

        # Test case where sub_range starts at super_range start but ends after
        sub_range = (datetime(2023, 1, 1, 11, 0), datetime(2023, 1, 1, 15, 0))
        super_range = (datetime(2023, 1, 1, 11, 0), datetime(2023, 1, 1, 14, 0))
        assert not datetime_range_in_range(sub_range, super_range)
