from flask import Flask, request, jsonify, render_template, session, redirect
from database import get_db, init_db
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secure_random_key_123"

# Initialize database
init_db()

# Temporary session storage
user_sessions = {}


# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------- CHATBOT ----------------
@app.route("/chat", methods=["POST"])
def chat():
    user_id = request.json.get("user_id", "default")
    message = request.json["message"]

    if user_id not in user_sessions:
        user_sessions[user_id] = {"step": 0, "data": {}}

    s = user_sessions[user_id]

    # ✅ If already booked
    if s["step"] == "done":
        if "book" in message.lower():
            s["step"] = 0
            s["data"] = {}
            return jsonify({"reply": "Starting new booking...\nWhat is your name?"})
        else:
            return jsonify({
                "reply": "✅ Appointment already booked.\nType 'book' to create another."
            })

    # ---------------- FLOW ----------------
    if s["step"] == 0:
        s["step"] = 1
        return jsonify({"reply": "What is your name?"})

    elif s["step"] == 1:
        s["data"]["name"] = message
        s["step"] = 2
        return jsonify({"reply": "Enter your phone number:"})

    elif s["step"] == 2:
        s["data"]["phone"] = message
        s["step"] = 3
        return jsonify({"reply": "Enter appointment date (DD-MM-YYYY):"})

    elif s["step"] == 3:
        try:
            date_obj = datetime.strptime(message, "%d-%m-%Y")
            s["data"]["date"] = date_obj.strftime("%d-%m-%Y")
            s["step"] = 4
            return jsonify({"reply": "Enter time (HH:MM):"})
        except:
            return jsonify({"reply": "❌ Use DD-MM-YYYY format"})

    elif s["step"] == 4:
        s["data"]["time"] = message

        db = get_db()
        cursor = db.cursor()

        # 🚫 Prevent double booking
        cursor.execute(
            "SELECT * FROM appointments WHERE date=? AND time=?",
            (s["data"]["date"], s["data"]["time"])
        )

        if cursor.fetchone():
            return jsonify({"reply": "❌ Slot already booked. Choose another time."})

        # ✅ Insert
        cursor.execute(
            "INSERT INTO appointments (name, phone, date, time, status) VALUES (?, ?, ?, ?, 'Pending')",
            (
                s["data"]["name"],
                s["data"]["phone"],
                s["data"]["date"],
                s["data"]["time"],
            )
        )

        db.commit()
        db.close()

        s["step"] = "done"

        return jsonify({"reply": "✅ Appointment booked successfully!"})

    return jsonify({"reply": "Error"})


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "1234":
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

    cursor.execute("SELECT * FROM appointments")
    data = cursor.fetchall()

    db.close()

    return render_template("admin.html", appointments=data)


# ---------------- COMPLETE ----------------
@app.route("/complete/<int:id>")
def complete(id):
    if not session.get("admin"):
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("UPDATE appointments SET status='Completed' WHERE id=?", (id,))
    db.commit()
    db.close()

    return redirect("/admin")


# ---------------- DELETE ----------------
@app.route("/delete/<int:id>")
def delete(id):
    if not session.get("admin"):
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("DELETE FROM appointments WHERE id=?", (id,))
    db.commit()
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
            "UPDATE appointments SET date=?, time=? WHERE id=?",
            (date, time, id)
        )
        db.commit()
        db.close()

        return redirect("/admin")

    cursor.execute("SELECT * FROM appointments WHERE id=?", (id,))
    data = cursor.fetchone()

    db.close()

    return render_template("edit.html", data=data)


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/login")


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()