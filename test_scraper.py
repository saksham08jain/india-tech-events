"""The event refresh must be stable when listings themselves have not changed."""
from datetime import datetime, timezone
import unittest

import scraper


class ScraperTests(unittest.TestCase):
    def test_is_tech_requires_a_real_keyword_not_a_title_fragment(self):
        self.assertTrue(scraper.is_tech("AI Security: Securing LLM Applications"))
        self.assertTrue(scraper.is_tech("8th Bharat AgriTech Expo"))
        for title in (
            "Sufi Qawwali night with Fanna-Fi-Allah",
            "MAHADEV",
            "Dev Deepawali 2026",
            "ANYMA presents AEDEN - Mumbai",
            "code to capital summit",
        ):
            with self.subTest(title=title):
                self.assertFalse(scraper.is_tech(title))

    def test_directory_event_keeps_devfolio_hackathons_without_keyword_titles(self):
        self.assertTrue(scraper.is_directory_event({"source": "devfolio", "title": "Cognition 2026"}))
        self.assertFalse(scraper.is_directory_event({"source": "allevents", "title": "Sufi Qawwali night with Fanna-Fi-Allah"}))
        self.assertTrue(scraper.is_directory_event({
            "source": "allevents", "title": "code to capital summit", "organizer": "Legal Tech Meet"
        }))

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
            {
                "title": "Sufi Qawwali night with Fanna-Fi-Allah",
                "url": "https://example.org/qawwali",
                "source": "fixture",
                "start": "2026-10-20T12:00:00+00:00",
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