"""The event refresh must be stable when listings themselves have not changed."""
from datetime import datetime, timezone
import unittest

import scraper


class ScraperTests(unittest.TestCase):
    def test_fresh_events_removes_volatile_scrape_timestamp(self):
        now = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
        records = [
            {
                "title": "Future meetup",
                "url": "https://example.org/future",
                "source": "fixture",
                "start": "2026-10-20T12:00:00+00:00",
                "scraped_at": "2026-10-15T12:00:00+00:00",
            },
            {
                "title": "Past meetup",
                "url": "https://example.org/past",
                "source": "fixture",
                "start": "2026-10-14T12:00:00+00:00",
                "scraped_at": "2026-10-15T12:00:00+00:00",
            },
        ]

        self.assertEqual(
            scraper.fresh_events(records, now=now),
            [{
                "title": "Future meetup",
                "url": "https://example.org/future",
                "source": "fixture",
                "start": "2026-10-20T12:00:00+00:00",
            }],
        )


if __name__ == "__main__":
    unittest.main()