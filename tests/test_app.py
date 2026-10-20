"""Tests for the Flask pages (uses a temporary CSV file and chart folder)."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data_manager as dm
from app import create_app


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = os.path.join(self.temp_dir.name, "complaints.csv")
        self.app = create_app({
            "TESTING": True,
            "CSV_PATH": self.csv_path,
            "CHART_DIR": os.path.join(self.temp_dir.name, "charts"),
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def submit(self, **fields):
        data = {"customer_name": "Tester", "title": "Charge problem",
                "description": "I was charged twice for my order, please help"}
        data.update(fields)
        return self.client.post("/submit", data=data)


class TestPagesOpen(AppTestCase):
    def test_dashboard_with_no_complaints(self):
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No complaints have been saved yet", response.data)
        self.assertIn(b"Total Complaints", response.data)
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir.name, "charts", "category_chart.png")))

    def test_every_page_opens(self):
        for url in ["/dashboard", "/submit", "/complaints"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_home_redirects_to_intro_or_dashboard(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)

    def test_unknown_pages_give_404(self):
        self.assertEqual(self.client.get("/nothing-here").status_code, 404)
        self.assertEqual(self.client.get("/complaint/CMP-9999").status_code, 404)
        self.assertEqual(self.client.get("/result/CMP-9999").status_code, 404)


class TestSubmission(AppTestCase):
    def test_empty_description_shows_friendly_error(self):
        response = self.submit(description="")
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"description cannot be empty", response.data)
        self.assertEqual(len(dm.load_complaints(self.csv_path)), 0)

    def test_spaces_only_description_is_rejected(self):
        self.assertEqual(self.submit(description="     ").status_code, 400)

    def test_too_short_description_is_rejected(self):
        response = self.submit(description="Help")
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"at least 10 characters", response.data)

    def test_too_long_description_is_rejected(self):
        self.assertEqual(self.submit(description="a " * 1500).status_code, 400)

    def test_form_keeps_typed_text_after_error(self):
        response = self.submit(customer_name="Keep Me", description="")
        self.assertIn(b"Keep Me", response.data)

    def test_valid_submission_is_saved_and_shows_result(self):
        response = self.submit()
        self.assertEqual(response.status_code, 302)
        page = self.client.get(response.headers["Location"])
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Billing Support Team", page.data)
        self.assertIn(b"not guaranteed", page.data)
        df = dm.load_complaints(self.csv_path)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["Predicted Category"], "Billing")

    def test_missing_title_and_name_are_filled(self):
        self.submit(customer_name="", title="")
        row = dm.load_complaints(self.csv_path).iloc[0]
        self.assertEqual(row["Customer Name"], "Anonymous")
        self.assertTrue(row["Complaint Title"].startswith("I was charged twice"))

    def test_html_in_input_is_escaped(self):
        self.submit(description="<script>alert(1)</script> my parcel has not arrived")
        page = self.client.get("/complaint/CMP-0001")
        self.assertNotIn(b"<script>alert(1)</script>", page.data)

    def test_second_submission_does_not_overwrite_first(self):
        self.submit(customer_name="First")
        self.submit(customer_name="Second")
        self.assertEqual(list(dm.load_complaints(self.csv_path)["Customer Name"]), ["First", "Second"])


class TestListingAndStatus(AppTestCase):
    def setUp(self):
        super().setUp()
        self.submit(customer_name="Alice", description="I was charged twice for my order")
        self.submit(customer_name="Bob", description="The application keeps crashing")

    def test_all_complaints_page_lists_records(self):
        page = self.client.get("/complaints")
        self.assertIn(b"Alice", page.data)
        self.assertIn(b"Bob", page.data)

    def test_search_and_filters_on_page(self):
        page = self.client.get("/complaints?q=alice")
        self.assertIn(b"Alice", page.data)
        self.assertNotIn(b"Bob", page.data)
        page = self.client.get("/complaints?category=Technical&priority=High")
        self.assertIn(b"Bob", page.data)
        self.assertNotIn(b"Alice", page.data)

    def test_no_match_message(self):
        page = self.client.get("/complaints?q=zzzzzz")
        self.assertIn(b"No complaints match", page.data)

    def test_status_update(self):
        response = self.client.post("/complaint/CMP-0001/status", data={"status": "Resolved"},
                                    follow_redirects=True)
        self.assertIn(b"Status updated", response.data)
        self.assertEqual(dm.get_complaint_by_id("CMP-0001", self.csv_path)["Status"], "Resolved")

    def test_invalid_status_is_rejected(self):
        response = self.client.post("/complaint/CMP-0001/status", data={"status": "Banana"},
                                    follow_redirects=True)
        self.assertIn(b"valid status", response.data)
        self.assertEqual(dm.get_complaint_by_id("CMP-0001", self.csv_path)["Status"], "Pending")

    def test_status_update_for_unknown_id_gives_404(self):
        response = self.client.post("/complaint/CMP-9999/status", data={"status": "Resolved"})
        self.assertEqual(response.status_code, 404)

    def test_dashboard_counts_update(self):
        page = self.client.get("/dashboard")
        self.assertIn(b"Recent Complaints", page.data)
        self.assertIn(b"Alice", page.data)


if __name__ == "__main__":
    unittest.main()
