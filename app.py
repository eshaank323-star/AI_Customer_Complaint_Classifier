"""
app.py
======
The Flask web application. It connects the pages (HTML templates) with the
Python logic in classifier.py, data_manager.py and charts.py.

Run it with:   python app.py
Then open:     http://127.0.0.1:5000
"""

import os
import time

from flask import (Flask, abort, flash, redirect, render_template, request,
                   url_for)

import charts
import classifier
import data_manager

# Limits used to validate the complaint form.
MAX_NAME_LENGTH = 80
MAX_TITLE_LENGTH = 120
MIN_DESCRIPTION_LENGTH = 10
MAX_DESCRIPTION_LENGTH = 2000


def clean_form_text(value):
    """Remove extra spaces and line breaks from text typed in a form."""
    return " ".join(str(value or "").split())


def validate_complaint_form(form):
    """Return a list of friendly error messages (empty list = form is valid)."""
    errors = []
    if not form["description"]:
        errors.append("Please describe your complaint. The description cannot be empty.")
    elif len(form["description"]) < MIN_DESCRIPTION_LENGTH:
        errors.append(f"Please write a little more. The description needs at least "
                      f"{MIN_DESCRIPTION_LENGTH} characters.")
    elif len(form["description"]) > MAX_DESCRIPTION_LENGTH:
        errors.append(f"The description is too long. Please keep it under "
                      f"{MAX_DESCRIPTION_LENGTH} characters.")
    if len(form["customer_name"]) > MAX_NAME_LENGTH:
        errors.append(f"The name is too long (maximum {MAX_NAME_LENGTH} characters).")
    if len(form["title"]) > MAX_TITLE_LENGTH:
        errors.append(f"The title is too long (maximum {MAX_TITLE_LENGTH} characters).")
    return errors


def create_app(test_config=None):
    """Build the Flask app. A function is used so tests can use temporary files."""
    app = Flask(__name__)
    app.config.update(
        # Needed for flash messages. Change it if you ever publish the app.
        SECRET_KEY=os.environ.get("SECRET_KEY", "class-project-secret-key"),
        CSV_PATH=data_manager.DEFAULT_CSV_PATH,
        CHART_DIR=os.path.join(app.static_folder, "charts"),
    )
    if test_config:
        app.config.update(test_config)

    @app.context_processor
    def inject_lists():
        """Make these lists available in every template (for dropdown menus)."""
        return {
            "CATEGORIES": classifier.CATEGORIES,
            "PRIORITIES": data_manager.PRIORITIES,
            "STATUSES": data_manager.STATUSES,
        }

    # ------------------------------------------------------------------
    # Page 0: your introduction / portfolio page (the first page)
    # ------------------------------------------------------------------
    @app.route("/")
    def home():
        """Open the intro page in static/intro/. If it is missing, go to the dashboard."""
        intro_page = os.path.join(app.static_folder, "intro", "index.html")
        if os.path.exists(intro_page):
            return redirect(url_for("static", filename="intro/index.html"))
        return redirect(url_for("dashboard"))

    # ------------------------------------------------------------------
    # Page 1: Dashboard
    # ------------------------------------------------------------------
    @app.route("/dashboard")
    def dashboard():
        df = data_manager.load_complaints(app.config["CSV_PATH"])
        stats = data_manager.get_statistics(df)
        chart_files = charts.create_all_charts(stats, app.config["CHART_DIR"])
        return render_template(
            "dashboard.html",
            stats=stats,
            chart_files=chart_files,
            recent=data_manager.get_recent_complaints(df, 5),
            cache_bust=int(time.time()),   # makes the browser reload new charts
        )

    # ------------------------------------------------------------------
    # Page 2: Submit a complaint
    # ------------------------------------------------------------------
    @app.route("/submit", methods=["GET", "POST"])
    def submit_complaint():
        form = {"customer_name": "", "title": "", "description": ""}
        errors = []

        if request.method == "POST":
            form = {
                "customer_name": clean_form_text(request.form.get("customer_name")),
                "title": clean_form_text(request.form.get("title")),
                "description": clean_form_text(request.form.get("description")),
            }
            errors = validate_complaint_form(form)

            if not errors:
                analysis = classifier.analyze_complaint(form["title"], form["description"])
                title = form["title"] or (form["description"][:60] + "...")
                record = data_manager.add_complaint(
                    form["customer_name"], title, form["description"],
                    analysis, app.config["CSV_PATH"])
                # Redirect so refreshing the result page does not submit twice.
                return redirect(url_for("result", complaint_id=record["Complaint ID"]))

            return render_template("submit_complaint.html", form=form, errors=errors), 400

        return render_template("submit_complaint.html", form=form, errors=errors)

    # ------------------------------------------------------------------
    # Page 3: Complaint result
    # ------------------------------------------------------------------
    @app.route("/result/<complaint_id>")
    def result(complaint_id):
        complaint = data_manager.get_complaint_by_id(complaint_id, app.config["CSV_PATH"])
        if complaint is None:
            abort(404)
        analysis = classifier.analyze_complaint(
            complaint["Complaint Title"], complaint["Complaint Description"])
        return render_template("result.html", complaint=complaint, analysis=analysis)

    # ------------------------------------------------------------------
    # Page 4: All complaints (with search and filters)
    # ------------------------------------------------------------------
    @app.route("/complaints")
    def complaints():
        search = request.args.get("q", "").strip()[:100]
        category = request.args.get("category", "All")
        priority = request.args.get("priority", "All")
        status = request.args.get("status", "All")

        df = data_manager.load_complaints(app.config["CSV_PATH"])
        filtered = data_manager.sort_newest_first(
            data_manager.filter_complaints(df, search, category, priority, status))
        return render_template(
            "complaints.html",
            complaints=filtered.to_dict("records"),
            total_count=len(df),
            shown_count=len(filtered),
            filters={"q": search, "category": category, "priority": priority, "status": status},
        )

    # ------------------------------------------------------------------
    # Page 5: Complaint details + status update
    # ------------------------------------------------------------------
    @app.route("/complaint/<complaint_id>")
    def complaint_details(complaint_id):
        complaint = data_manager.get_complaint_by_id(complaint_id, app.config["CSV_PATH"])
        if complaint is None:
            abort(404)
        return render_template("complaint_details.html", complaint=complaint)

    @app.route("/complaint/<complaint_id>/status", methods=["POST"])
    def update_status(complaint_id):
        new_status = request.form.get("status", "")
        try:
            found = data_manager.update_status(complaint_id, new_status, app.config["CSV_PATH"])
        except ValueError:
            flash("Please choose a valid status: Pending, In Progress or Resolved.", "error")
            return redirect(url_for("complaint_details", complaint_id=complaint_id))
        if not found:
            abort(404)
        flash(f"Status updated to '{new_status}'.", "success")
        return redirect(url_for("complaint_details", complaint_id=complaint_id))

    # ------------------------------------------------------------------
    # Friendly error pages
    # ------------------------------------------------------------------
    @app.errorhandler(404)
    def page_not_found(error):
        return render_template(
            "error.html", title="Page not found",
            message="We could not find that page or complaint."), 404

    @app.errorhandler(PermissionError)
    def file_in_use(error):
        return render_template(
            "error.html", title="Data file is busy",
            message="The complaints file could not be saved. If data/complaints.csv is "
                    "open in Excel, close it and try again."), 500

    return app


# Used by "python app.py" and by the Flask command line.
app = create_app()

if __name__ == "__main__":
    app.run(debug=True) 
