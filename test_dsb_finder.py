import contextlib
import io
import os
import subprocess
import sys
import unittest

import dsb_finder


def make_plan_page(date_title, rows):
    row_html = ""
    for cells in rows:
        tds = "".join(f'<td class="list">{c}</td>' for c in cells)
        row_html += f"<tr>{tds}</tr>"
    return f"""
    <html><body>
    <div class="mon_title">{date_title} (Seite 1 / 2)</div>
    <table class="mon_list">{row_html}</table>
    </body></html>
    """


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeSession:
    def __init__(self, pages_by_url):
        self.pages_by_url = pages_by_url
        self.headers = {}

    def get(self, url, timeout=None):
        return FakeResponse(self.pages_by_url[url])


class TestMultiPagePlanMerge(unittest.TestCase):
    def test_entries_from_all_pages_of_same_date_are_kept(self):
        """A plan split across several subst_NNN.htm pages (same mon_title
        date) must keep entries from every page, not only the last one."""
        date_title = "9.7.2026 Donnerstag"
        page1 = make_plan_page(date_title, [
            ["7d", "1", "GF", "GF", "e", "A104", "entf&auml;llt"],
        ])
        page2 = make_plan_page(date_title, [
            ["7e", "2", "DR", "LEH", "g", "A105", ""],
        ])

        url1 = "https://example.test/plan/subst_001.htm"
        url2 = "https://example.test/plan/subst_002.htm"
        json_data = [{
            "Title": "VPlan_S_m",
            "Childs": [
                {"Title": "subst_001", "Date": "08.07.2026", "Detail": url1},
                {"Title": "subst_001", "Date": "08.07.2026", "Detail": url2},
            ],
        }]
        session = FakeSession({url1: page1, url2: page2})

        results = dsb_finder.extract_timetable_info(
            json_data, session, ["7d", "7e"])

        self.assertIn(date_title, results)
        day = results[date_title]
        self.assertIn("7d", day, "7d entries from page 1 were lost")
        self.assertIn("7e", day, "7e entries from page 2 were lost")
        self.assertEqual(day["7d"][0]["period"], "1")
        self.assertEqual(day["7e"][0]["period"], "2")


class TestDebugFilesPerPage(unittest.TestCase):
    def test_each_plan_page_gets_its_own_debug_file(self):
        """Pages of one plan share the child title 'subst_001', so debug
        dumps must be disambiguated by the page name from the URL."""
        date_title = "9.7.2026 Donnerstag"
        page1 = make_plan_page(date_title, [
            ["7d", "1", "GF", "GF", "e", "A104", ""],
        ])
        page2 = make_plan_page(date_title, [
            ["7e", "2", "DR", "LEH", "g", "A105", ""],
        ])

        url1 = "https://example.test/plan/subst_001.htm?123"
        url2 = "https://example.test/plan/subst_002.htm?123"
        json_data = [{
            "Title": "VPlan_S_m",
            "Childs": [
                {"Title": "subst_001", "Date": "08.07.2026", "Detail": url1},
                {"Title": "subst_001", "Date": "08.07.2026", "Detail": url2},
            ],
        }]
        session = FakeSession({url1: page1, url2: page2})

        expected1 = "debug/html_VPlan_S_m_-_subst_001_subst_001.html"
        expected2 = "debug/html_VPlan_S_m_-_subst_001_subst_002.html"
        for path in (expected1, expected2):
            if os.path.exists(path):
                os.remove(path)

        dsb_finder.extract_timetable_info(json_data, session, ["7d", "7e"])

        self.assertTrue(os.path.exists(expected1),
                        f"missing debug dump for page 1: {expected1}")
        self.assertTrue(os.path.exists(expected2),
                        f"missing debug dump for page 2: {expected2}")
        with open(expected2, encoding="utf-8") as f:
            self.assertIn("7e", f.read())


class TestCancellationDetection(unittest.TestCase):
    """Canceled = teacher cells striked AND equal, or the Text column
    says ENTFALL/CANCELLED or similar. Same teacher without strikes is a
    subject/room change, not a cancellation."""

    def _extract_single(self, cells):
        page = make_plan_page("9.7.2026 Donnerstag", [cells])
        soup = dsb_finder.BeautifulSoup(page, "html.parser")
        entries = dsb_finder.extract_class_info(soup, ["7d", "7e"])
        self.assertEqual(len(entries), 1)
        return entries[0]

    def test_striked_equal_teachers_is_canceled(self):
        entry = self._extract_single(
            ["7e", "1", "<strike>HM</strike>", "<strike>HM</strike>",
             "<strike>m</strike>", "---", ""])
        self.assertTrue(entry.get("is_canceled", False))

    def test_same_teacher_without_strikes_is_not_canceled(self):
        entry = self._extract_single(
            ["7e", "3", "TSA", "TSA", "ntph", "E12", ""])
        self.assertFalse(entry.get("is_canceled", False))

    def test_entfall_in_text_column_is_canceled(self):
        entry = self._extract_single(
            ["7d", "7", "SZ", "SZ", "intm", "---", "intm entf&auml;llt!"])
        self.assertTrue(entry.get("is_canceled", False))


class TestSameTeacherChangeDisplay(unittest.TestCase):
    def test_same_teacher_change_shows_new_subject_and_room(self):
        """A non-canceled entry with the same teacher is a subject/room
        change; show what changed instead of 'X -> X'."""
        entry = {
            "period": "3", "class": "7e",
            "substitute": "TSA", "original_teacher": "TSA",
            "subject": "ntph", "subject_full": "Natur und Technik (Physik)",
            "room": "E12", "notes": "",
            "regular_subject_full": "Natur und Technik",
            "regular_room": "B101/C8",
            "original_teacher_full": "Dimitri Tsambrounis (Natur und Technik)",
            "substitute_full": "Dimitri Tsambrounis (Natur und Technik)",
        }
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            dsb_finder.print_summary({"9.7.2026 Donnerstag": {"7e": [entry]}})
        out = buf.getvalue()

        self.assertIn("Cambio", out)
        self.assertIn("Natur und Technik (Physik)", out)
        self.assertIn("E12", out)
        self.assertNotIn("->", out)


class TestConsoleEncoding(unittest.TestCase):
    def test_print_summary_survives_cp1252_stdout(self):
        """On Windows the console can be cp1252; emoji output must not
        crash the script with UnicodeEncodeError."""
        code = (
            "import dsb_finder as df; "
            "df.print_summary({'9.7.2026 Donnerstag': {'7d': [{"
            "'period': '1', 'subject_full': 'Kunst', 'room': 'B104', "
            "'is_canceled': True, 'notes': ''}]}})"
        )
        env = os.environ.copy()
        env.pop("PYTHONUTF8", None)
        env["PYTHONIOENCODING"] = "cp1252"

        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, env=env,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )

        self.assertEqual(
            result.returncode, 0,
            f"script crashed on cp1252 stdout:\n{result.stderr}")


if __name__ == "__main__":
    unittest.main()
