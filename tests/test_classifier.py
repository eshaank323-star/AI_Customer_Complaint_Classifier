"""Tests for classifier.py. Run all tests with:  python -m unittest discover -s tests -t ."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from classifier import (DEFAULT_CATEGORY, analyze_complaint, assign_priority,
                        classify_category, clean_text, get_support_team)


def category_of(text):
    return classify_category(text)["category"]


class TestCategory(unittest.TestCase):
    def test_billing_example(self):
        self.assertEqual(category_of("I was charged twice for my order"), "Billing")

    def test_technical_example(self):
        self.assertEqual(category_of("The application keeps crashing"), "Technical")

    def test_delivery_example(self):
        self.assertEqual(category_of("My parcel has not arrived"), "Delivery")

    def test_service_example(self):
        self.assertEqual(category_of("The customer support staff was unhelpful"), "Service")

    def test_uppercase_and_mixed_case(self):
        self.assertEqual(category_of("I WAS CHARGED TWICE FOR MY ORDER"), "Billing")
        self.assertEqual(category_of("tHe ApPlIcAtIoN kEePs CrAsHiNg"), "Technical")

    def test_curly_apostrophe_and_punctuation(self):
        self.assertEqual(category_of("I can\u2019t log in!!!"), "Technical")

    def test_multiple_keywords_most_matches_wins(self):
        # Billing words: payment. Technical words: app, crashing, page.
        self.assertEqual(category_of("The app is crashing on the payment page"), "Technical")

    def test_whole_words_only(self):
        # 'apple' must not match the keyword 'app'
        result = classify_category("I like apple juice")
        self.assertTrue(result["used_default"])

    def test_unknown_complaint_uses_default(self):
        result = classify_category("Hello, something is not right")
        self.assertEqual(result["category"], DEFAULT_CATEGORY)
        self.assertTrue(result["used_default"])

    def test_empty_and_none_input(self):
        self.assertEqual(category_of(""), DEFAULT_CATEGORY)
        self.assertEqual(category_of(None), DEFAULT_CATEGORY)

    def test_tie_goes_to_first_category(self):
        # 'invoice' (Billing) and 'password' (Technical) each score 1 -> Billing is listed first
        result = classify_category("invoice password")
        self.assertEqual(result["scores"]["Billing"], result["scores"]["Technical"])
        self.assertEqual(result["category"], "Billing")


class TestPriority(unittest.TestCase):
    def test_urgent_is_high(self):
        self.assertEqual(assign_priority("Please fix this urgently")[0], "High")

    def test_account_access_is_high(self):
        self.assertEqual(assign_priority("I can't log in to my account")[0], "High")

    def test_repeated_failure_is_high(self):
        self.assertEqual(assign_priority("The app keeps crashing")[0], "High")
        self.assertEqual(assign_priority("It failed multiple times")[0], "High")

    def test_serious_interruption_is_high(self):
        self.assertEqual(assign_priority("Our internet is completely down")[0], "High")

    def test_not_urgent_is_not_high(self):
        priority, _ = assign_priority("This is not urgent, I have a small issue")
        self.assertEqual(priority, "Low")

    def test_minor_is_low(self):
        self.assertEqual(assign_priority("The page is a bit slow, minor issue")[0], "Low")

    def test_general_question_is_low(self):
        self.assertEqual(assign_priority("How do I change my email address?")[0], "Low")

    def test_question_with_real_problem_is_not_low(self):
        priority, _ = assign_priority("How do I get a refund? I was charged by mistake")
        self.assertEqual(priority, "Medium")

    def test_normal_problem_is_medium(self):
        self.assertEqual(assign_priority("My package arrived damaged")[0], "Medium")

    def test_reason_is_always_given(self):
        for text in ["urgent!", "just a question", "my parcel is late", ""]:
            priority, reason = assign_priority(text)
            self.assertIn(priority, ["High", "Medium", "Low"])
            self.assertTrue(len(reason) > 10)


class TestTeamAndAnalysis(unittest.TestCase):
    def test_team_mapping(self):
        self.assertEqual(get_support_team("Billing"), "Billing Support Team")
        self.assertEqual(get_support_team("Technical"), "Technical Support Team")
        self.assertEqual(get_support_team("Delivery"), "Delivery Support Team")
        self.assertEqual(get_support_team("Service"), "Customer Service Team")

    def test_unknown_category_team(self):
        self.assertEqual(get_support_team("Nonsense"), "Customer Service Team")

    def test_analyze_complaint_result(self):
        result = analyze_complaint("Charged twice", "I was charged twice for my order")
        self.assertEqual(result["category"], "Billing")
        self.assertEqual(result["team"], "Billing Support Team")
        self.assertIn("not guaranteed", result["disclaimer"])
        self.assertTrue(result["matched_keywords"])

    def test_analyze_unclear_complaint(self):
        result = analyze_complaint("", "Hello there")
        self.assertTrue(result["used_default_category"])
        self.assertEqual(result["team"], "Customer Service Team")

    def test_clean_text(self):
        self.assertEqual(clean_text("  Can't   LOG-in!  "), "cant log in")


if __name__ == "__main__":
    unittest.main()
