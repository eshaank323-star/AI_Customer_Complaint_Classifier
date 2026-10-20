# AI-Based Customer Complaint Classifier

Prepared by **Eshaan Khan** for **Programming Project (ILS)**.

## 1. Project Description

This is a beginner-friendly web application. A customer types a complaint, and the
app will:

1. suggest a **category** (Billing, Technical, Delivery or Service),
2. suggest a **priority** (High, Medium or Low) and explain why,
3. recommend the **support team** that should handle it,
4. save the complaint in a CSV file and show analytics on a dashboard.

> **Honest note:** this version does **not** use trained machine learning.
> It uses simple, readable **keyword rules** written in Python (`classifier.py`).
> The results are suggestions and are **not guaranteed to be correct**.
> No internet connection or paid service is needed.

## 2. Features

- **Intro page** (your own introduction, photo and portfolio) that links to the project.
- **Dashboard:** total, high-priority, pending and resolved counts, three charts, recent complaints.
- **Submit Complaint form** with friendly error messages (empty description, too short, too long).
- **Automatic classification** into four categories using keyword rules (not case-sensitive).
- **Automatic priority** with a written reason.
- **Support team recommendation** (Billing Support Team, Technical Support Team, Delivery Support Team, Customer Service Team).
- **Complaint management:** saved in `data/complaints.csv`, unique IDs, statuses Pending / In Progress / Resolved.
- **Charts** (Matplotlib + Seaborn): by category, by priority, and a status pie chart.
- **Search and filters** by category, priority and status.
- **Sample data:** 20 fictional complaints marked `Sample`; your own are marked `User`.

## 3. Technologies Used

Python, Pandas, NumPy, Matplotlib, Seaborn, Flask, HTML and CSS.

## 4. Prerequisites

- Windows 10 or 11 (Mac and Linux also work).
- **Python 3.9 or newer** from https://www.python.org/downloads/
  (during installation tick **"Add Python to PATH"**).
- Check it works: open Command Prompt and type `python --version`.

## 5. Folder Structure

```text
customer_complaint_classifier/
├── app.py                  Flask routes (the web pages)
├── classifier.py           Keyword rules: category, priority, support team
├── data_manager.py         Reads/writes the CSV with Pandas, search, filters, statistics
├── charts.py               Draws the charts with Matplotlib and Seaborn
├── make_sample_data.py     Re-creates the sample dataset
├── requirements.txt
├── README.md
├── data/
│   ├── complaints.csv          The data the app uses
│   └── sample_complaints.csv   Untouched copy of the sample data
├── templates/              base, dashboard, submit_complaint, result,
│                           complaints, complaint_details, error, macros
├── static/
│   ├── css/style.css
│   ├── charts/             Chart images are created here automatically
│   └── intro/              Your first page (introduction, photo, portfolio)
└── tests/                  Automated tests
```

## 6. Setup (Windows, step by step)

1. Unzip the project and open the folder `customer_complaint_classifier`.
2. Click the folder address bar, type `cmd` and press Enter (Command Prompt opens in that folder).
3. Create a virtual environment:
   ```
   python -m venv venv
   ```
4. Activate it:
   ```
   venv\Scripts\activate
   ```
   You will see `(venv)` at the start of the line.
   (If PowerShell blocks this, use Command Prompt, or run
   `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.)
5. Install the packages:
   ```
   pip install -r requirements.txt
   ```

## 7. How to Run

```
python app.py
```

Open your browser and go to **http://127.0.0.1:5000**

- You will first see your **introduction page**. Click **Start Project** to open the dashboard.
- Press `Ctrl + C` in the Command Prompt to stop the app.

## 8. Linking Your Own Introduction / Photo / Portfolio Page

The first page lives in the folder `static/intro/`. A sample page is included so the
project runs out of the box; **replace it with your own page**:

1. Copy your page files (HTML, CSS, photo, etc.) into `static/intro/`.
2. Name your main page `index.html`. Keep your CSS and photo files in the same folder
   and use **relative paths** (for example `<img src="photo.jpg">`).
3. Add this link where you want the project to start (for example a button):
   ```html
   <a href="/dashboard">Start Project</a>
   ```
4. Run `python app.py` and open http://127.0.0.1:5000. It opens `static/intro/index.html`.

The **Portfolio** link in the project's menu brings you back to this page.
If `static/intro/index.html` does not exist, the app opens the dashboard directly.

## 9. How the Rules Work

**Category:** each keyword found in the title and description adds points (phrases such as
"charged twice" add more). The category with the most points wins. A tie goes to the
category listed first. If nothing matches, the complaint goes to the default category
**Service** and the result page says so.

**Priority:**
- **High:** urgent requests, account access problems, repeated failures, serious service
  interruptions, possible fraud.
- **Low:** clearly minor issues, feedback, or simple questions (without a real problem).
- **Medium:** everything else.

All keywords are lists at the top of `classifier.py`, so you can read and change them.
Because the rules only look at words, mistakes are possible. For example, "The delivery
staff was rude" may be sorted as Service instead of Delivery.

**Upgrading later:** `classify_category()` is a separate function. A trained model can
replace its inside later without changing the rest of the project.

## 10. Run the Automated Tests

```
python -m unittest discover -s tests -t .
```

The tests cover classification, priority, team mapping, empty and invalid input, unknown
complaints, CSV creation and appending, duplicate IDs, status updates, search, filters
and an empty dashboard. They use temporary files, so your real data is never changed.

## 11. Reset or Replace the Sample Dataset

- **Reset to the original samples** (this removes your own submitted complaints):
  ```
  python make_sample_data.py
  ```
  or copy `data\sample_complaints.csv` over `data\complaints.csv`.
- **Start with an empty dashboard:** delete `data\complaints.csv` and restart the app.
  An empty file with the correct headings is created automatically.
- **Use your own data:** keep these column headings in this order:
  `Complaint ID, Customer Name, Complaint Title, Complaint Description, Predicted Category, Priority, Assigned Team, Status, Submission Date, Source`
  (`Source` is `Sample` or `User`). Missing columns and empty values are repaired automatically.

## 12. Common Errors and Troubleshooting

| Problem | Solution |
|---|---|
| `'python' is not recognized` | Reinstall Python and tick "Add Python to PATH", or try `py` instead of `python`. |
| `No module named flask` (or pandas, seaborn...) | Activate the virtual environment (`venv\Scripts\activate`) and run `pip install -r requirements.txt` again. |
| `Address already in use` / port 5000 busy | Close the other program, or change the last line of `app.py` to `app.run(debug=True, port=5001)` and open `http://127.0.0.1:5001`. |
| "Data file is busy" page | `data/complaints.csv` is open in Excel. Close it and try again. |
| Charts look old | Refresh the page (`Ctrl + F5`). Charts are re-drawn each time the dashboard opens. |
| Intro page shows no photo | Check the photo file is inside `static/intro/` and the name in your HTML matches exactly. |
| Strange characters in Excel | Save/open the CSV as UTF-8. The app already writes it with UTF-8 (BOM). |
| A damaged CSV | The app keeps a backup named `complaints.csv.damaged_<time>.bak` and starts a fresh file. |

## 13. Limitations

- Keyword rules cannot understand meaning, spelling mistakes or sarcasm.
- CSV storage is suitable for a student project, not for many users at the same time.
- The status page has no login, so anyone who opens the app can change a status.
