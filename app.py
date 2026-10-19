
import os
from flask import Flask, request, redirect, url_for, render_template_string, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

database_url = os.environ.get("DATABASE_URL", "sqlite:///school.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Club(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    leader = db.Column(db.String(120), default="")
    schedule = db.Column(db.String(120), default="")


class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(120), nullable=False)
    class_name = db.Column(db.String(30), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey("club.id"), nullable=False)
    status = db.Column(db.String(30), default="Yangi")
    club = db.relationship("Club")


HOME = """
<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>25-maktab | To‘garaklar</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#080b12;color:#f5f5f5;font-family:Arial,sans-serif}
header{padding:24px 16px;text-align:center;background:#111722;border-bottom:2px solid #d6ad52}
header h1{color:#e7c36c;margin:8px}
header p{color:#c5c7ce}
main{max-width:1000px;margin:auto;padding:22px 15px}
h2{color:#e7c36c}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}
.card{background:#141b28;border:1px solid #4d4026;border-radius:14px;padding:18px}
.card h3{color:#f1cf78}
input,select,textarea{width:100%;padding:12px;margin:7px 0 12px;border:1px solid #555;background:#0c111b;color:white;border-radius:8px}
button{background:#e1b957;color:#111;font-weight:bold;border:0;border-radius:8px;padding:12px 16px;cursor:pointer}
section{margin:30px 0}
.notice{background:#17251d;padding:12px;border-radius:8px}
footer{text-align:center;padding:25px;color:#aaa;border-top:1px solid #333}
</style>
</head>
<body>
<header>
<h1>25-MAKTAB</h1>
<p>TO‘GARAKLAR MARKAZI</p>
<p>Toshkent viloyati · Angren shahri</p>
</header>
<main>
<section>
<h2>Maktabimiz to‘garaklari</h2>
<div class="grid">
{% for club in clubs %}
<div class="card">
<h3>{{ club.name }}</h3>
<p>{{ club.description or 'Ushbu to‘garak haqida ma’lumot tez orada qo‘shiladi.' }}</p>
<p><b>Rahbar:</b> {{ club.leader or 'Hozircha belgilanmagan' }}</p>
<p><b>Jadval:</b> {{ club.schedule or 'Tez orada e’lon qilinadi' }}</p>
</div>
{% else %}
<div class="card">To‘garaklar ro‘yxati hozircha bo‘sh.</div>
{% endfor %}
</div>
</section>

<section class="card">
<h2>To‘garakka ariza berish</h2>
<p>Login yoki parol kerak emas. Ma’lumotlarni to‘ldiring.</p>
{% with messages = get_flashed_messages() %}
{% for message in messages %}<p class="notice">{{ message }}</p>{% endfor %}
{% endwith %}
<form method="post" action="/apply">
<label>O‘quvchining ism-familiyasi</label>
<input name="student_name" maxlength="120" required>
<label>Sinf</label>
<input name="class_name" maxlength="30" placeholder="Masalan: 8-A" required>
<label>Telefon raqami</label>
<input name="phone" type="tel" maxlength="30" placeholder="+998..." required>
<label>To‘garak</label>
<select name="club_id" required>
<option value="">To‘garakni tanlang</option>
{% for club in clubs %}
<option value="{{ club.id }}">{{ club.name }}</option>
{% endfor %}
</select>
<button type="submit">Ariza yuborish</button>
</form>
</section>
</main>
<footer>© 25-maktab · To‘garaklar markazi</footer>
</body>
</html>
"""


@app.route("/")
def index():
    clubs = Club.query.order_by(Club.name).all()
    return render_template_string(HOME, clubs=clubs)


@app.route("/apply", methods=["POST"])
def apply():
    name = request.form.get("student_name", "").strip()
    class_name = request.form.get("class_name", "").strip()
    phone = request.form.get("phone", "").strip()
    club_id = request.form.get("club_id", type=int)

    club = db.session.get(Club, club_id) if club_id else None

    if not name or not class_name or not phone or not club:
        flash("Iltimos, barcha maydonlarni to‘g‘ri to‘ldiring.")
        return redirect(url_for("index"))

    application = Application(
        student_name=name,
        class_name=class_name,
        phone=phone,
        club_id=club.id
    )
    db.session.add(application)
    db.session.commit()

    flash("Arizangiz qabul qilindi!")
    return redirect(url_for("index"))


@app.route("/health")
def health():
    return {"status": "ok"}


with app.app_context():
    db.create_all()

    if Club.query.count() == 0:
        db.session.add_all([
            Club(
                name="IT va dasturlash",
                description="Kompyuter savodxonligi va dasturlash.",
                schedule="Jadval belgilanmoqda"
            ),
            Club(
                name="Ingliz tili",
                description="Ingliz tilini o‘rganish va amaliy mashg‘ulotlar.",
                schedule="Jadval belgilanmoqda"
            ),
            Club(
                name="Sport",
                description="Jismoniy faollik va sport mashg‘ulotlari.",
                schedule="Jadval belgilanmoqda"
            ),
            Club(
                name="Matematika",
                description="Mantiqiy fikrlash va masalalar yechish.",
                schedule="Jadval belgilanmoqda"
            )
        ])
        db.session.commit()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
          
