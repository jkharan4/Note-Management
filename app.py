from flask import Flask, request, redirect, url_for, render_template, flash, session, send_file
from flask_session import Session
from otp import genotp
from cmail import send_mail
from stoken import endata, dndata
from io import BytesIO
# import flask_excel as excel
from openpyxl import Workbook

import mysql.connector
import re

# ---------------- DB ----------------
mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="ajayjani",
    database="notesdb"
)

# ---------------- APP ----------------
app = Flask(__name__)
# excel.init_excel(app)
app.secret_key = "code9"

app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("welcome.html")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        uname = request.form["uname"].strip()
        email = request.form["uemail"].strip()
        password = request.form["upassword"].strip()

        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute("SELECT COUNT(*) FROM users WHERE useremail=%s", (email,))
            exists = cursor.fetchone()[0]
            cursor.close()
        except Exception as e:
            print(e)
            flash("Database error")
            return redirect(url_for("register"))

        if exists:
            flash("Email already registered")
            return redirect(url_for("login"))

        server_otp = genotp()
        user_data = {
            "username": uname,
            "email": email,
            "password": password,
            "server_otp": server_otp
        }

        send_mail(
            to=email,
            subject="OTP Verification - Note App",
            body=f"Your OTP is: {server_otp}"
        )

        flash("OTP sent to your email")
        return redirect(url_for("otpverify", var_data=endata(user_data)))

    return render_template("register.html")

# ---------------- OTP VERIFY ----------------
@app.route("/otpverify/<var_data>", methods=["GET", "POST"])
def otpverify(var_data):
    if request.method == "POST":
        user_otp = request.form["userotp"].strip()

        try:
            user_data = dndata(var_data)
        except Exception:
            flash("OTP expired or invalid")
            return redirect(url_for("register"))

        if user_otp != user_data["server_otp"]:
            flash("Invalid OTP")
            return redirect(url_for("otpverify", var_data=var_data))

        cursor = mydb.cursor()
        cursor.execute(
            "INSERT INTO users (username, useremail, userpassword) VALUES (%s,%s,%s)",
            (user_data["username"], user_data["email"], user_data["password"])
        )
        mydb.commit()
        cursor.close()

        flash("Registration successful. Please login.")
        return redirect(url_for("login"))

    return render_template("otp.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["uemail"].strip()
        password = request.form["upassword"].strip()

        cursor = mydb.cursor(buffered=True)
        cursor.execute("SELECT COUNT(*) FROM users WHERE useremail=%s", (email,))
        exists = cursor.fetchone()[0]

        if exists == 1:
            cursor.execute("SELECT userpassword FROM users WHERE useremail=%s", (email,))
            db_pass = cursor.fetchone()[0]
            cursor.close()

            if db_pass == password:
                session["user"] = email
                flash("Login successful")
                return redirect(url_for("dashboard"))
            else:
                flash("Invalid password")
        else:
            flash("User not found")

        return redirect(url_for("login"))

    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if session.get("user"):
        return render_template("dashboard.html")
    flash("Please login first")
    return redirect(url_for("login"))

# ---------------- ADD NOTES ----------------
@app.route("/addnotes", methods=["GET", "POST"])
def addnotes():
    if not session.get("user"):
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form.get("title").strip()
        content = request.form.get("content").strip()

        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute("SELECT user_id FROM users WHERE useremail=%s", (session["user"],))
            user_id = cursor.fetchone()[0]

            cursor.execute(
                "INSERT INTO notesdata (notestitle, notescontent, user_id) VALUES (%s,%s,%s)",
                (title, content, user_id)
            )
            mydb.commit()
            cursor.close()
        except Exception as e:
            print(e)
            flash("Could not add note")
            return redirect(url_for("addnotes"))

        flash("Note added successfully")
    return render_template("addnotes.html")


# ---------------- UPLOAD FILE ----------------

@app.route('/uploadfile', methods=['GET', 'POST'], strict_slashes=False)  # FIX
def uploadfile():
    if not session.get("user"):
        flash("Please login first")
        return redirect(url_for("login"))

    if request.method == "POST":
        fileobj = request.files.get("Filedata")

        if not fileobj or fileobj.filename == "":
            flash("Please select a file")
            return redirect("/uploadfile")  # FIX

        fname = fileobj.filename
        filedata = fileobj.read()

        cursor = mydb.cursor(buffered=True)
        cursor.execute(
            "SELECT user_id FROM users WHERE useremail=%s",
            (session["user"],)
        )
        user_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO filesdata (filename, filecontent, user_id) VALUES (%s,%s,%s)",
            (fname, filedata, user_id)
        )
        mydb.commit()
        cursor.close()

        flash("File uploaded successfully")
        return redirect("/viewallfiles")  # FIX

    return render_template("uploadfile.html")



# ---------------- VIEW ALL FILES ----------------
@app.route('/viewallfiles')
def viewallfiles():
    if not session.get("user"):
        flash("Please login first")
        return redirect(url_for("login"))

    cursor = mydb.cursor(buffered=True)
    cursor.execute(
        "SELECT user_id FROM users WHERE useremail=%s",
        (session["user"],)
    )
    user_id = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT filesid, filename, created_at
        FROM filesdata
        WHERE user_id=%s
        """,
        (user_id,)
    )
    filesdata = cursor.fetchall()
    cursor.close()

    return render_template("viewallfiles.html", filesdata=filesdata)



# ---------------- VIEW FILE ----------------
# ---------------- VIEW FILE ----------------
@app.route('/viewfile/<fid>')
def viewfile(fid):
    if not session.get("user"):
        flash("Please login first")
        return redirect(url_for("login"))

    try:
        cursor = mydb.cursor(buffered=True)
        cursor.execute(
            "SELECT user_id FROM users WHERE useremail=%s",
            (session["user"],)
        )
        user_id = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT filecontent, filename
            FROM filesdata
            WHERE filesid=%s AND user_id=%s
            """,
            (fid, user_id)
        )
        file_data = cursor.fetchone()
        cursor.close()

        if not file_data:
            flash("File not found")
            return redirect(url_for("viewallfiles"))

        return send_file(
            BytesIO(file_data[0]),
            download_name=file_data[1],
            as_attachment=False
        )
    except Exception as e:
        print(e)
        flash("Could not open file")
        return redirect(url_for("viewallfiles"))



# ---------------- DOWNLOAD FILE ----------------
# ---------------- DOWNLOAD FILE ----------------
@app.route('/downloadfile/<fid>')
def downloadfile(fid):
    if not session.get("user"):
        flash("Please login first")
        return redirect(url_for("login"))

    try:
        cursor = mydb.cursor(buffered=True)
        cursor.execute(
            "SELECT user_id FROM users WHERE useremail=%s",
            (session["user"],)
        )
        user_id = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT filecontent, filename
            FROM filesdata
            WHERE filesid=%s AND user_id=%s
            """,
            (fid, user_id)
        )
        file_data = cursor.fetchone()
        cursor.close()

        if not file_data:
            flash("File not found")
            return redirect(url_for("viewallfiles"))

        return send_file(
            BytesIO(file_data[0]),
            download_name=file_data[1],
            as_attachment=True
        )
    except Exception as e:
        print(e)
        flash("Could not download file")
        return redirect(url_for("viewallfiles"))



# ---------------- DELETE FILE ----------------
# ---------------- DELETE FILE ----------------
@app.route('/deletefile/<fid>')
def deletefile(fid):
    if not session.get("user"):
        flash("Please login first")
        return redirect(url_for("login"))

    try:
        cursor = mydb.cursor(buffered=True)
        cursor.execute(
            "SELECT user_id FROM users WHERE useremail=%s",
            (session["user"],)
        )
        user_id = cursor.fetchone()[0]

        cursor.execute(
            """
            DELETE FROM filesdata
            WHERE filesid=%s AND user_id=%s
            """,
            (fid, user_id)
        )
        mydb.commit()
        cursor.close()

        flash("File deleted successfully")
        return redirect(url_for("viewallfiles"))
    except Exception as e:
        print(e)
        flash("Could not delete file")
        return redirect(url_for("viewallfiles"))


# ---------------- VIEW ALL NOTES ----------------
@app.route("/viewnotes")
def viewnotes():
    if not session.get("user"):
        return redirect(url_for("login"))

    cursor = mydb.cursor(buffered=True)
    cursor.execute("SELECT user_id FROM users WHERE useremail=%s", (session["user"],))
    user_id = cursor.fetchone()[0]

    cursor.execute(
    """
    SELECT notesid, notestitle, notescontent, created_at
    FROM notesdata
    WHERE user_id=%s
    """,
    (user_id,)
    )

    notesdata = cursor.fetchall()
    cursor.close()

    return render_template("viewnotes.html", notesdata=notesdata)

# ---------------- DELETE NOTE ----------------
@app.route("/deletenotes/<nid>")
def deletenotes(nid):
    if not session.get("user"):
        return redirect(url_for("login"))

    cursor = mydb.cursor(buffered=True)
    cursor.execute("SELECT user_id FROM users WHERE useremail=%s", (session["user"],))
    user_id = cursor.fetchone()[0]

    cursor.execute(
        "DELETE FROM notesdata WHERE notesid=%s AND user_id=%s",
        (nid, user_id)
    )
    mydb.commit()
    cursor.close()

    flash("Note deleted")
    return redirect(url_for("viewnotes"))

# ---------------- UPDATE NOTE ----------------
@app.route("/updatenotes/<nid>", methods=["GET", "POST"])
def updatenotes(nid):
    if not session.get("user"):
        return redirect(url_for("login"))

    cursor = mydb.cursor(buffered=True)
    cursor.execute("SELECT user_id FROM users WHERE useremail=%s", (session["user"],))
    user_id = cursor.fetchone()[0]

    cursor.execute(
    """
    SELECT notesid, notestitle, notescontent
    FROM notesdata
    WHERE notesid=%s AND user_id=%s
    """,
    (nid, user_id)
    )

    note = cursor.fetchone()

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]

        cursor.execute(
            "UPDATE notesdata SET notestitle=%s, notescontent=%s WHERE notesid=%s AND user_id=%s",
            (title, content, nid, user_id)
        )
        mydb.commit()
        cursor.close()

        flash("Note updated")
        return redirect(url_for("updatenotes", nid=nid))

    cursor.close()
    return render_template("updatenotes.html", note=note)


# ---------------- SEARCH (RESTORED) ----------------
@app.route("/search", methods=["POST"])
def search():
    if not session.get("user"):
        return redirect(url_for("login"))

    search_value = request.form["search_value"]
    pattern = re.compile("^[A-Za-z0-9]")

    if not pattern.match(search_value):
        flash("Invalid search")
        return redirect(url_for("viewnotes"))

    cursor = mydb.cursor(buffered=True)
    cursor.execute("SELECT user_id FROM users WHERE useremail=%s", (session["user"],))
    user_id = cursor.fetchone()[0]

    cursor.execute(
        "SELECT * FROM notesdata WHERE user_id=%s AND notestitle LIKE %s",
        (user_id, search_value + "%")
    )
    results = cursor.fetchall()
    cursor.close()

    return render_template("viewnotes.html", notesdata=results)

# ---------------- EXCEL EXPORT ----------------
from openpyxl import Workbook
from io import BytesIO
from flask import send_file

@app.route('/getexceldata')
def getexceldata():
    if not session.get("user"):
        flash("Please login first")
        return redirect(url_for("login"))

    try:
        cursor = mydb.cursor(buffered=True)
        cursor.execute(
            "SELECT user_id FROM users WHERE useremail=%s",
            (session["user"],)
        )
        user_id = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT notesid, notestitle, notescontent, created_at
            FROM notesdata
            WHERE user_id=%s
            """,
            (user_id,)
        )
        notesdata = cursor.fetchall()
        cursor.close()

        # Create Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "Notes"

        # Header
        ws.append(["Note ID", "Title", "Content", "Created At"])

        # Data
        for row in notesdata:
            ws.append(list(row))

        # Save to memory
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        return send_file(
            output,
            download_name="notesdata.xlsx",
            as_attachment=True,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        print("EXCEL EXPORT ERROR:", e)
        flash("Could not generate Excel")
        return redirect(url_for("dashboard"))


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out successfully")
    return redirect(url_for("login"))

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
