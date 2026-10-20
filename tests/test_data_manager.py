"""Tests for data_manager.py (uses temporary files, never your real data)."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

import data_manager as dm
from classifier import analyze_complaint


class DataManagerTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = os.path.join(self.temp_dir.name, "data", "complaints.csv")

    def tearDown(self):
        self.temp_dir.cleanup()

    def add(self, name="Test User", title="Title", text="I was charged twice for my order"):
        return dm.add_complaint(name, title, text, analyze_complaint(title, text), self.csv_path)


class TestCsvCreationAndAppending(DataManagerTestCase):
    def test_csv_is_created_with_correct_columns(self):
        df = dm.load_complaints(self.csv_path)
        self.assertTrue(os.path.exists(self.csv_path))
        self.assertEqual(list(df.columns), dm.COLUMNS)
        self.assertEqual(len(df), 0)

    def test_adding_complaints_appends_and_keeps_old_records(self):
        first = self.add(name="Alice", text="My parcel has not arrived")
        second = self.add(name="Bob", text="The application keeps crashing")
        df = dm.load_complaints(self.csv_path)
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]["Customer Name"], "Alice")
        self.assertEqual(df.iloc[1]["Customer Name"], "Bob")
        self.assertNotEqual(first["Complaint ID"], second["Complaint ID"])

    def test_saved_record_has_all_fields(self):
        record = self.add()
        self.assertEqual(record["Status"], "Pending")
        self.assertEqual(record["Source"], "User")
        self.assertEqual(record["Predicted Category"], "Billing")
        self.assertEqual(record["Assigned Team"], "Billing Support Team")
        self.assertTrue(record["Submission Date"])

    def test_missing_name_and_title_get_safe_defaults(self):
        record = self.add(name="", title="")
        self.assertEqual(record["Customer Name"], "Anonymous")
        self.assertEqual(record["Complaint Title"], "Untitled complaint")

    def test_commas_quotes_and_new_lines_are_saved_safely(self):
        text = 'He said, "Hello", then left,\nand never came back'
        self.add(text=text)
        df = dm.load_complaints(self.csv_path)
        self.assertEqual(df.iloc[0]["Complaint Description"], text)


class TestIds(DataManagerTestCase):
    def test_ids_are_unique_and_increasing(self):
        ids = [self.add()["Complaint ID"] for _ in range(5)]
        self.assertEqual(len(set(ids)), 5)
        self.assertEqual(ids[0], "CMP-0001")
        self.assertEqual(ids[-1], "CMP-0005")

    def test_new_id_continues_after_highest_existing(self):
        dm.ensure_csv_exists(self.csv_path)
        pd.DataFrame([{"Complaint ID": "CMP-0020"}]).to_csv(self.csv_path, index=False)
        self.assertEqual(self.add()["Complaint ID"], "CMP-0021")

    def test_duplicate_ids_in_file_are_repaired(self):
        dm.ensure_csv_exists(self.csv_path)
        rows = [{"Complaint ID": "CMP-0001", "Complaint Description": "first"},
                {"Complaint ID": "CMP-0001", "Complaint Description": "second"},
                {"Complaint ID": "", "Complaint Description": "third"}]
        pd.DataFrame(rows).to_csv(self.csv_path, index=False)
        df = dm.load_complaints(self.csv_path)
        self.assertEqual(df["Complaint ID"].nunique(), 3)
        self.assertEqual(len(df), 3)            # nothing was deleted


class TestBadFiles(DataManagerTestCase):
    def test_missing_values_are_filled(self):
        dm.ensure_csv_exists(self.csv_path)
        with open(self.csv_path, "w", encoding="utf-8") as file:
            file.write("Complaint ID,Complaint Description,Status,Priority\nCMP-0001,,Strange,Odd\n")
        df = dm.load_complaints(self.csv_path)
        self.assertEqual(df.iloc[0]["Status"], "Pending")
        self.assertEqual(df.iloc[0]["Priority"], "Medium")
        self.assertEqual(df.iloc[0]["Customer Name"], "Anonymous")
        self.assertEqual(list(df.columns), dm.COLUMNS)

    def test_empty_file_does_not_crash(self):
        dm.ensure_csv_exists(self.csv_path)
        open(self.csv_path, "w").close()
        self.assertEqual(len(dm.load_complaints(self.csv_path)), 0)

    def test_damaged_file_is_backed_up(self):
        dm.ensure_csv_exists(self.csv_path)
        with open(self.csv_path, "w", encoding="utf-8") as file:
            file.write('a,b\n"unclosed quote,1\n1,2,3,4,5,6\n')
        df = dm.load_complaints(self.csv_path)       # must not crash
        self.assertEqual(list(df.columns), dm.COLUMNS)


class TestStatusUpdate(DataManagerTestCase):
    def test_update_status(self):
        record = self.add()
        self.assertTrue(dm.update_status(record["Complaint ID"], "Resolved", self.csv_path))
        self.assertEqual(dm.get_complaint_by_id(record["Complaint ID"], self.csv_path)["Status"], "Resolved")

    def test_update_only_changes_one_complaint(self):
        first, second = self.add(), self.add()
        dm.update_status(first["Complaint ID"], "In Progress", self.csv_path)
        self.assertEqual(dm.get_complaint_by_id(second["Complaint ID"], self.csv_path)["Status"], "Pending")

    def test_invalid_status_is_rejected(self):
        record = self.add()
        with self.assertRaises(ValueError):
            dm.update_status(record["Complaint ID"], "Done", self.csv_path)

    def test_unknown_id_returns_false(self):
        self.assertFalse(dm.update_status("CMP-9999", "Resolved", self.csv_path))

    def test_get_unknown_complaint_returns_none(self):
        self.assertIsNone(dm.get_complaint_by_id("CMP-9999", self.csv_path))


class TestFilteringAndStatistics(DataManagerTestCase):
    def setUp(self):
        super().setUp()
        self.add(name="Alice", title="Double payment", text="I was charged twice for my order")
        self.add(name="Bob", title="App problem", text="The application keeps crashing")
        self.add(name="Carol", title="Late parcel", text="My parcel has not arrived")
        dm.update_status("CMP-0003", "Resolved", self.csv_path)
        self.df = dm.load_complaints(self.csv_path)

    def test_filter_by_category(self):
        result = dm.filter_complaints(self.df, category="Technical")
        self.assertEqual(list(result["Customer Name"]), ["Bob"])

    def test_filter_by_priority(self):
        result = dm.filter_complaints(self.df, priority="High")
        self.assertEqual(list(result["Customer Name"]), ["Bob"])

    def test_filter_by_status(self):
        result = dm.filter_complaints(self.df, status="Resolved")
        self.assertEqual(list(result["Customer Name"]), ["Carol"])

    def test_search_is_not_case_sensitive(self):
        self.assertEqual(len(dm.filter_complaints(self.df, search="PARCEL")), 1)
        self.assertEqual(len(dm.filter_complaints(self.df, search="cmp-0002")), 1)

    def test_search_with_special_characters_does_not_crash(self):
        self.assertEqual(len(dm.filter_complaints(self.df, search="(*[")), 0)

    def test_combined_filters(self):
        result = dm.filter_complaints(self.df, search="bob", category="Technical", status="Pending")
        self.assertEqual(len(result), 1)
        self.assertEqual(len(dm.filter_complaints(self.df, search="bob", category="Billing")), 0)

    def test_unknown_filter_value_is_ignored(self):
        self.assertEqual(len(dm.filter_complaints(self.df, category="Nonsense")), 3)

    def test_statistics(self):
        stats = dm.get_statistics(self.df)
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["high_priority"], 1)
        self.assertEqual(stats["resolved"], 1)
        self.assertEqual(stats["pending"], 2)
        self.assertEqual(stats["category_counts"]["Billing"], 1)
        self.assertEqual(stats["resolved_percent"], 33.3)

    def test_statistics_with_no_data(self):
        stats = dm.get_statistics(dm.create_empty_dataframe())
        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["resolved_percent"], 0.0)
        self.assertEqual(sum(stats["category_counts"].values()), 0)

    def test_recent_complaints_newest_first(self):
        df = dm.load_complaints(self.csv_path)
        df["Submission Date"] = ["2026-01-01 10:00", "2026-03-01 10:00", "2026-02-01 10:00"]
        recent = dm.get_recent_complaints(df, 2)
        self.assertEqual([r["Customer Name"] for r in recent], ["Bob", "Carol"])


if __name__ == "__main__":
    unittest.main()
