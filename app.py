from flask import Flask, request, jsonify, render_template, session, redirect
from database import get_db, init_db, load_session, save_session
from datetime import datetime
import os
import re

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "dev_key")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "1234")

init_db()


# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------- CHATBOT ----------------
@app.route("/chat", methods=["POST"])
def chat():
    user_id = request.json.get("user_id", "default")
    message = request.json["message"]

    s = load_session(user_id)
    msg = message.lower()

    # Greeting
    if msg in ["hi", "hello"]:
        return jsonify({"reply": "Hi! Type 'book' to schedule an appointment."})

    # Cancel
    if msg == "cancel":
        s = {"step": 0, "data": {}}
        save_session(user_id, s)
        return jsonify({"reply": "Booking cancelled."})

    # Already booked
    if s["step"] == "done":
        if "book" in msg:
            s = {"step": 1, "data": {}}
            save_session(user_id, s)
            return jsonify({"reply": "Starting new booking...\nWhat is your name?"})
        return jsonify({"reply": "✅ Already booked. Type 'book' to create another."})

    # FLOW
    if str(s["step"]) == "0":
        s["step"] = 1
        save_session(user_id, s)
        return jsonify({"reply": "What is your name?"})

    elif str(s["step"]) == "1":
        s["data"]["name"] = message
        s["step"] = 2
        save_session(user_id, s)
        return jsonify({"reply": "Enter your phone number:"})

    elif str(s["step"]) == "2":
        if not message.isdigit() or len(message) < 10:
            return jsonify({"reply": "❌ Enter valid phone number"})

        s["data"]["phone"] = message
        s["step"] = 3
        save_session(user_id, s)
        return jsonify({"reply": "Enter date (DD-MM-YYYY):"})

    elif str(s["step"]) == "3":
        try:
            date_obj = datetime.strptime(message, "%d-%m-%Y")
            s["data"]["date"] = date_obj.strftime("%d-%m-%Y")
            s["step"] = 4
            save_session(user_id, s)
            return jsonify({"reply": "Enter time (HH:MM):"})
        except:
            return jsonify({"reply": "❌ Use DD-MM-YYYY format"})

    elif str(s["step"]) == "4":
        if not re.match(r"^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$", message):
            return jsonify({"reply": "❌ Use valid HH:MM format"})

        s["data"]["time"] = message

        db = get_db()
        cursor = db.cursor()

        # Prevent double booking
        cursor.execute(
            "SELECT * FROM appointments WHERE date=%s AND time=%s",
            (s["data"]["date"], s["data"]["time"])
        )

        if cursor.fetchone():
            cursor.close()
            db.close()
            return jsonify({"reply": "❌ Slot already booked"})

        cursor.execute(
            "INSERT INTO appointments (name, phone, date, time, status) VALUES (%s, %s, %s, %s, 'Pending')",
            (
                s["data"]["name"],
                s["data"]["phone"],
                s["data"]["date"],
                s["data"]["time"]
            )
        )

        db.commit()
        cursor.close()
        db.close()

        s["step"] = "done"
        save_session(user_id, s)

        return jsonify({"reply": "✅ Appointment booked!"})

    return jsonify({"reply": "Error"})


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == ADMIN_USER and request.form["password"] == ADMIN_PASS:
            session["admin"] = True
            return redirect("/admin")
        return "Invalid credentials"

    return render_template("login.html")


# ---------------- ADMIN ----------------
@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    q = request.args.get("q")
    status = request.args.get("status")

    if status == "pending":
        cursor.execute("SELECT * FROM appointments WHERE status='Pending' ORDER BY id DESC")
    elif q:
        cursor.execute(
            "SELECT * FROM appointments WHERE name ILIKE %s OR phone ILIKE %s ORDER BY id DESC",
            (f"%{q}%", f"%{q}%")
        )
    else:
        cursor.execute("SELECT * FROM appointments ORDER BY id DESC")

    data = cursor.fetchall()
    cursor.close()
    db.close()

    return render_template("admin.html", appointments=data)


# ---------------- COMPLETE ----------------
@app.route("/complete/<int:id>")
def complete(id):
    if not session.get("admin"):
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("UPDATE appointments SET status='Completed' WHERE id=%s", (id,))
    db.commit()

    cursor.close()
    db.close()

    return redirect("/admin")


# ---------------- DELETE ----------------
@app.route("/delete/<int:id>")
def delete(id):
    if not session.get("admin"):
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("DELETE FROM appointments WHERE id=%s", (id,))
    db.commit()

    cursor.close()
    db.close()

    return redirect("/admin")


# ---------------- EDIT ----------------
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    if not session.get("admin"):
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    if request.method == "POST":
        date = request.form["date"]
        time = request.form["time"]

        cursor.execute(
            "UPDATE appointments SET date=%s, time=%s WHERE id=%s",
            (date, time, id)
        )
        db.commit()

        cursor.close()
        db.close()
        return redirect("/admin")

    cursor.execute("SELECT * FROM appointments WHERE id=%s", (id,))
    data = cursor.fetchone()

    cursor.close()
    db.close()

    return render_template("edit.html", data=data)


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/login")


# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)