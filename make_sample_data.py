"""
make_sample_data.py
===================
Creates the fictional sample complaints in data/sample_complaints.csv
and data/complaints.csv. Run it any time you want to reset the demo data:

    python make_sample_data.py

WARNING: this REPLACES data/complaints.csv, so any complaints you submitted
yourself will be removed.
"""

import os

import pandas as pd

import classifier
from data_manager import COLUMNS, BASE_DIR

# (name, title, description, status, date)
SAMPLES = [
    ("Aarav Mehta", "Charged twice for one order",
     "I was charged twice for my order #4521. Please refund the extra payment as soon as possible.",
     "In Progress", "2026-09-21 10:15"),
    ("Sara Ali", "Question about invoice",
     "How do I download my invoice for last month? Just a general question, no rush.",
     "Resolved", "2026-09-22 14:30"),
    ("Daniel Brown", "Wrong amount on my bill",
     "The amount on my monthly bill is higher than the price I was told. Please check the charges.",
     "Pending", "2026-09-25 09:05"),
    ("Priya Nair", "Unauthorized transaction",
     "There is an unauthorized transaction on my credit card linked to my account. Please look into this urgently.",
     "In Progress", "2026-09-27 16:45"),
    ("Omar Farooq", "Refund not credited",
     "I returned my item two weeks ago but the refund has still not been credited to my account.",
     "Resolved", "2026-09-28 11:20"),
    ("Neha Kapoor", "App keeps crashing",
     "The application keeps crashing every time I open the payment page.",
     "In Progress", "2026-09-30 08:50"),
    ("John Smith", "Cannot log in",
     "I cannot log in to my account. It says my password is wrong even after resetting it. I need access urgently.",
     "Pending", "2026-10-02 19:10"),
    ("Fatima Khan", "Website loads slowly",
     "The website is a little slow when I open the product page. It is a minor issue.",
     "Resolved", "2026-10-03 13:00"),
    ("Rahul Verma", "Error message on profile page",
     "I get an error message when I try to update my profile settings. Please fix this bug.",
     "Pending", "2026-10-05 10:40"),
    ("Emily Clark", "Software update fails",
     "The latest software update fails to install on my laptop.",
     "Resolved", "2026-10-06 15:25"),
    ("Kabir Singh", "Parcel not arrived",
     "My parcel has not arrived and the tracking page has shown the same status for ten days.",
     "Pending", "2026-10-07 12:35"),
    ("Anita Desai", "Package damaged",
     "My package arrived damaged and one item is missing from the box.",
     "Resolved", "2026-10-08 17:05"),
    ("Liam Wilson", "Delivery was very late",
     "My order was delayed again and again. This is the third time this month. Please escalate.",
     "In Progress", "2026-10-09 09:30"),
    ("Zara Hussain", "Change delivery address",
     "I would like to know whether I can change the delivery address for my next order.",
     "Resolved", "2026-10-09 18:15"),
    ("Michael Lee", "Unhelpful support staff",
     "The customer support staff was unhelpful and rude when I called about my problem.",
     "Pending", "2026-10-10 11:55"),
    ("Sneha Iyer", "No reply to my emails",
     "I sent three emails to your support team and received no reply for two weeks.",
     "In Progress", "2026-10-11 14:20"),
    ("Chris Evans", "Feedback on service",
     "I just wanted to give some feedback. The agent who helped me was very friendly.",
     "Resolved", "2026-10-12 10:10"),
    ("Ayesha Siddiqui", "Internet is completely down",
     "The internet service has been completely down since morning and our whole office cannot work. This is an emergency.",
     "Pending", "2026-10-13 07:45"),
    ("Hannah Wright", "Staff behaviour at the counter",
     "The staff member at the service counter ignored me for twenty minutes and showed a bad attitude.",
     "Resolved", "2026-10-13 16:00"),
    ("", "Not sure where this belongs",
     "Hello, I have a problem but I am not sure what to write here.",
     "Pending", "2026-10-14 09:00"),
]


def build_rows():
    rows = []
    for number, (name, title, description, status, date) in enumerate(SAMPLES, start=1):
        result = classifier.analyze_complaint(title, description)
        rows.append({
            "Complaint ID": f"CMP-{number:04d}",
            "Customer Name": name or "Anonymous",
            "Complaint Title": title,
            "Complaint Description": description,
            "Predicted Category": result["category"],
            "Priority": result["priority"],
            "Assigned Team": result["team"],
            "Status": status,
            "Submission Date": date,
            "Source": "Sample",
        })
    return pd.DataFrame(rows, columns=COLUMNS)


if __name__ == "__main__":
    data_folder = os.path.join(BASE_DIR, "data")
    os.makedirs(data_folder, exist_ok=True)
    table = build_rows()
    table.to_csv(os.path.join(data_folder, "sample_complaints.csv"), index=False, encoding="utf-8-sig")
    table.to_csv(os.path.join(data_folder, "complaints.csv"), index=False, encoding="utf-8-sig")
    print(f"Created {len(table)} sample complaints in the data folder.")
