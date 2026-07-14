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


class TestSharedSlotCancellationDisplay(unittest.TestCase):
    """k/ev/eth religion groups share one slot; the regular timetable name
    ('Religion') is the same for all of them, so the output must also show
    the plan's own subject or two canceled groups look like duplicates."""

    def _entry(self, subject, subject_full, teacher):
        return {
            "period": "5", "class": "7e",
            "substitute": teacher, "original_teacher": teacher,
            "subject": subject, "subject_full": subject_full,
            "room": "---", "notes": "",
            "is_canceled": True, "cancel_reason": "ENTFALL",
            "regular_subject_full": "Religion",
            "regular_room": "A102/A201/A105",
        }

    def test_two_canceled_groups_in_shared_slot_are_distinguishable(self):
        entries = [
            self._entry("k", "Kath. Religionslehre", "DOE"),
            self._entry("eth", "Ethik", "KAG"),
        ]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            dsb_finder.print_summary({"14.7.2026 Dienstag": {"7e": entries}})
        out = buf.getvalue()

        self.assertIn("Kath. Religionslehre", out)
        self.assertIn("Ethik", out)

    def test_identical_regular_and_plan_subject_is_not_repeated(self):
        entry = self._entry("ffme", "Förderung Mathe/Englisch", "HAU")
        entry["regular_subject_full"] = "Förderung Mathe/Englisch"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            dsb_finder.print_summary({"14.7.2026 Dienstag": {"7e": [entry]}})
        out = buf.getvalue()

        self.assertEqual(out.count("Förderung Mathe/Englisch"), 1)

    def test_notification_names_the_specific_group(self):
        msg = dsb_finder.compose_notification(
            [("14.7.2026 Dienstag", "7e", self._entry("eth", "Ethik", "KAG"))],
            class_to_child={"7e": "Mateo"})
        self.assertIn("Ethik", msg)


class TestExcludedSubjects(unittest.TestCase):
    """Children only attend one group of a shared slot (k/ev/eth,
    DaZ-plus7/intf); subjects listed in the child's excluded_subjects
    must be dropped from the results before printing/saving/diffing."""

    def _entry(self, subject, subject_full):
        return {"period": "5", "subject": subject,
                "subject_full": subject_full, "is_canceled": True}

    def _results(self, class_name, entries):
        return {"14.7.2026 Dienstag": {class_name: entries}}

    def test_excluded_by_code(self):
        results = self._results("7e", [self._entry("eth", "Ethik")])
        out = dsb_finder.filter_excluded_subjects(
            results, {"7e": {"eth"}})
        self.assertEqual(out, {})

    def test_excluded_by_full_name(self):
        results = self._results("7e", [self._entry("eth", "Ethik")])
        out = dsb_finder.filter_excluded_subjects(
            results, {"7e": {"ethik"}})
        self.assertEqual(out, {})

    def test_matching_is_case_insensitive(self):
        results = self._results("7e", [self._entry("DaZ-plus7",
                                                   "Deutsch als Zweitsprache Plus 7")])
        out = dsb_finder.filter_excluded_subjects(
            results, {"7e": {"daz-plus7"}})
        self.assertEqual(out, {})

    def test_no_substring_matching(self):
        """'l' (Latein) must not exclude 'lint' (Latein Intensiv)."""
        results = self._results("7e", [self._entry("lint", "Latein Intensiv")])
        out = dsb_finder.filter_excluded_subjects(
            results, {"7e": {"l", "latein"}})
        self.assertEqual(out, results)

    def test_exclusions_are_per_class(self):
        results = {"14.7.2026 Dienstag": {
            "7d": [self._entry("eth", "Ethik")],
            "7e": [self._entry("eth", "Ethik")],
        }}
        out = dsb_finder.filter_excluded_subjects(
            results, {"7d": {"eth"}})
        self.assertEqual(list(out["14.7.2026 Dienstag"].keys()), ["7e"])

    def test_kept_entries_survive_alongside_excluded(self):
        results = self._results("7e", [
            self._entry("k", "Kath. Religionslehre"),
            self._entry("eth", "Ethik"),
        ])
        out = dsb_finder.filter_excluded_subjects(
            results, {"7e": {"eth"}})
        entries = out["14.7.2026 Dienstag"]["7e"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["subject"], "k")

    def test_no_exclusions_passes_through(self):
        results = self._results("7e", [self._entry("eth", "Ethik")])
        out = dsb_finder.filter_excluded_subjects(results, {})
        self.assertEqual(out, results)


class TestSubjectMappingNormalization(unittest.TestCase):
    def test_mixed_case_keys_are_lowercased_on_load(self):
        """Lookups lowercase the subject code, so the mapping must be
        normalized at load time to tolerate mixed-case keys in the file."""
        import json
        import tempfile
        with tempfile.NamedTemporaryFile(
                "w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump({"DaZ-plus7/intf": "DaZ Plus 7/Int. Französisch"}, f)
            path = f.name
        try:
            mapping = dsb_finder.load_subject_mapping(path)
        finally:
            os.remove(path)

        self.assertEqual(mapping.get("daz-plus7/intf"),
                         "DaZ Plus 7/Int. Französisch")


class TestCredentials(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.pop(k, None)
                       for k in ("DSB_USERNAME", "DSB_PASSWORD")}

    def tearDown(self):
        for k, v in self._saved.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)

    def test_credentials_come_from_config(self):
        cfg = {"credentials": {"username": "user1", "password": "pass1"}}
        self.assertEqual(dsb_finder.get_credentials(cfg), ("user1", "pass1"))

    def test_env_vars_override_config(self):
        os.environ["DSB_USERNAME"] = "env_user"
        os.environ["DSB_PASSWORD"] = "env_pass"
        cfg = {"credentials": {"username": "user1", "password": "pass1"}}
        self.assertEqual(dsb_finder.get_credentials(cfg),
                         ("env_user", "env_pass"))

    def test_missing_credentials_returns_none(self):
        self.assertEqual(dsb_finder.get_credentials({}), (None, None))


class TestConfigDerivedClasses(unittest.TestCase):
    def test_class_variants(self):
        self.assertEqual(dsb_finder.class_variants("8e"),
                         ["8e", "8E", "8.e", "8.E"])

    def test_target_classes_for_children(self):
        children = [{"name": "A", "class": "8d"}, {"name": "B", "class": "8e"}]
        self.assertEqual(
            dsb_finder.target_classes_for(children),
            ["8d", "8D", "8.d", "8.D", "8e", "8E", "8.e", "8.E"])

    def test_fallback_regex_uses_target_classes(self):
        """The malformed-row fallback must recognize whatever classes are
        configured, not a hardcoded '7[de]' pattern."""
        page = """
        <html><body>
        <div class="mon_title">9.7.2026 Donnerstag</div>
        <table class="mon_list">
        <tr><td>8x5ABCDEF E02</td></tr>
        </table>
        </body></html>
        """
        soup = dsb_finder.BeautifulSoup(page, "html.parser")
        entries = dsb_finder.extract_class_info(soup, ["8x"])
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["class"], "8x")
        self.assertEqual(entries[0]["period"], "5")
        self.assertEqual(entries[0]["room"], "E02")


def _entry(period, subject="Kunst", canceled=False, substitute="XX",
           original="YY"):
    return {
        "period": period, "subject": subject.lower(),
        "subject_full": subject, "regular_subject_full": subject,
        "room": "B104", "notes": "", "is_canceled": canceled,
        "substitute": substitute, "original_teacher": original,
        "substitute_full": f"Sub ({subject})",
    }


class TestNotificationDiff(unittest.TestCase):
    def test_everything_is_new_on_first_run(self):
        new = {"9.7.2026 Donnerstag": {"7d": [_entry("1"), _entry("2")]}}
        self.assertEqual(len(dsb_finder.diff_new_entries({}, new)), 2)

    def test_unchanged_results_produce_empty_diff(self):
        results = {"9.7.2026 Donnerstag": {"7d": [_entry("1")]}}
        self.assertEqual(dsb_finder.diff_new_entries(results, results), [])

    def test_only_added_entries_are_reported(self):
        old = {"9.7.2026 Donnerstag": {"7d": [_entry("1")]}}
        new = {"9.7.2026 Donnerstag": {"7d": [_entry("1"), _entry("5")]}}
        fresh = dsb_finder.diff_new_entries(old, new)
        self.assertEqual(len(fresh), 1)
        self.assertEqual(fresh[0][2]["period"], "5")


class TestNotificationMessage(unittest.TestCase):
    def test_message_names_child_subject_and_cancellation(self):
        fresh = [("9.7.2026 Donnerstag", "7d",
                  _entry("1", subject="Kunst", canceled=True))]
        msg = dsb_finder.compose_notification(
            fresh, class_to_child={"7d": "Diego"})
        self.assertIn("Diego", msg)
        self.assertIn("Kunst", msg)
        self.assertIn("CANCELADA", msg)
        self.assertIn("9.7.2026", msg)


class TestNotificationSend(unittest.TestCase):
    def test_method_none_sends_nothing(self):
        self.assertFalse(
            dsb_finder.send_notification("hola", {"method": "none"}))

    def test_ntfy_without_topic_sends_nothing(self):
        self.assertFalse(
            dsb_finder.send_notification("hola", {"method": "ntfy"}))


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


class TestRunFromAnyDirectory(unittest.TestCase):
    def test_module_finds_its_data_files_from_foreign_cwd(self):
        """'python ~/SubstituteFinder/dsb_finder.py' run from $HOME
        (Termux, cron) must find config.json and data/ next to the
        script, not relative to the caller's cwd."""
        import tempfile
        repo = os.path.dirname(os.path.abspath(__file__))
        code = (
            f"import sys; sys.path.insert(0, {repo!r}); "
            "import dsb_finder; "
            "sys.exit(0 if dsb_finder.SUBJECT_MAPPING else 1)"
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True, text=True, cwd=tmp)

        self.assertEqual(
            result.returncode, 0,
            "data/subject_mapping.json not found when cwd is elsewhere:\n"
            + result.stderr)


if __name__ == "__main__":
    unittest.main()
