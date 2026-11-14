from datetime import datetime
import sqlite3
from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)
DB_NAME = "water.db"


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS intake_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount_ml INTEGER NOT NULL,
                log_date TEXT NOT NULL,
                log_time TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                daily_goal_ml INTEGER NOT NULL
            )
        """)
        # Set default goal to 2500 ml if not already set
        conn.execute(
            "INSERT OR IGNORE INTO settings (id, daily_goal_ml) VALUES (1, 2500)"
        )
        conn.commit()


@app.route("/", methods=["GET"])
def index():
    today = datetime.now().strftime("%Y-%m-%d")

    with get_db_connection() as conn:
        goal_row = conn.execute(
            "SELECT daily_goal_ml FROM settings WHERE id = 1"
        ).fetchone()
        daily_goal = goal_row["daily_goal_ml"]

        logs = conn.execute(
            "SELECT id, amount_ml, log_time FROM intake_logs WHERE log_date = ? ORDER BY id DESC",
            (today,),
        ).fetchall()

    total_intake = sum(row["amount_ml"] for row in logs)
    percentage = (
        min(round((total_intake / daily_goal) * 100), 100)
        if daily_goal > 0
        else 0
    )
    remaining = max(daily_goal - total_intake, 0)

    return render_template(
        "index.html",
        logs=logs,
        total_intake=total_intake,
        daily_goal=daily_goal,
        percentage=percentage,
        remaining=remaining,
        today=today,
    )


@app.route("/add", methods=["POST"])
def add_water():
    try:
        amount = int(request.form.get("amount", 0))
        if amount > 0:
            now = datetime.now()
            log_date = now.strftime("%Y-%m-%d")
            log_time = now.strftime("%I:%M %p")

            with get_db_connection() as conn:
                conn.execute(
                    "INSERT INTO intake_logs (amount_ml, log_date, log_time) VALUES (?, ?, ?)",
                    (amount, log_date, log_time),
                )
                conn.commit()
    except ValueError:
        pass

    return redirect(url_for("index"))


@app.route("/delete/<int:log_id>", methods=["POST"])
def delete_log(log_id):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM intake_logs WHERE id = ?", (log_id,))
        conn.commit()
    return redirect(url_for("index"))


@app.route("/goal", methods=["POST"])
def update_goal():
    try:
        new_goal = int(request.form.get("daily_goal", 2500))
        if new_goal >= 100:
            with get_db_connection() as conn:
                conn.execute(
                    "UPDATE settings SET daily_goal_ml = ? WHERE id = 1",
                    (new_goal,),
                )
                conn.commit()
    except ValueError:
        pass
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
