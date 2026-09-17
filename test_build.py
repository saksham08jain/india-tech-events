"""Generated navigation must work under the GitHub Pages project path."""
import json
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from unittest.mock import patch

import build


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs).get("href", ""))


class BuildTests(unittest.TestCase):
    def test_page_externalRegistrationLink_isUnchanged(self):
        for url in ("https://example.org/register", "//example.org/register"):
            with self.subTest(url=url), tempfile.TemporaryDirectory() as tmp:
                site = Path(tmp)
                with patch.object(build, "SITE", site):
                    build.page("Event", "", f'<a href="{url}">Register</a>', "event/test.html")
                parser = Links()
                parser.feed((site / "event/test.html").read_text())
                self.assertIn(url, parser.links)
                self.assertIn("../", parser.links)
                self.assertIn("../communities.html", parser.links)

    def test_main_cityPreview_allEventsReachableUnderProjectPath(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data, site = root / "data", root / "docs"
            data.mkdir()
            events = [{"title": f"Event {i}", "city": "bengaluru",
                       "start": "2099-01-01T12:00:00+00:00", "url": "https://example.org/event",
                       "source": "fixture"} for i in range(13)]
            (data / "events.json").write_text(json.dumps(events))
            (data / "communities.json").write_text("[]")
            with patch.object(build, "DATA", data), patch.object(build, "SITE", site):
                build.main()
            base = "https://example.test/india-tech-events/"
            pending, seen = ["index.html"], set()
            while pending:
                path = pending.pop()
                if path in seen:
                    continue
                seen.add(path)
                parser = Links()
                parser.feed((site / path).read_text())
                for href in parser.links:
                    url = urljoin(base + path, href)
                    if urlsplit(url).netloc != "example.test":
                        continue
                    self.assertTrue(url.startswith(base), f"Link escapes project: {path} -> {href}")
                    target = urlsplit(url).path.removeprefix("/india-tech-events/") or "index.html"
                    self.assertTrue((site / target).is_file(), f"Missing target: {path} -> {target}")
                    pending.append(target)
            self.assertIn("city/bengaluru.html", seen)
            self.assertTrue({f"event/event-{i}.html" for i in range(13)} <= seen)


if __name__ == "__main__":
    unittest.main()
