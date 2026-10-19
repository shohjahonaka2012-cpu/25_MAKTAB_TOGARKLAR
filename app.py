
import os
from functools import wraps
from hmac import compare_digest

from flask import (
    Flask, request, redirect, url_for,
    render_template_string, session, flash
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "")

if not app.secret_key:
    raise RuntimeError("Render Environment’da SECRET_KEY qo‘shing.")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

database_url = os.environ.get("DATABASE_URL", "sqlite:///school.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get(
    "RENDER", ""
) != ""

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
    club_id = db.Column(
        db.Integer, db.ForeignKey("club.id"), nullable=False
    )
    status = db.Column(db.String(30), default="Yangi")
    club = db.relationship("Club")


STYLE = """
*{box-sizing:border-box}
body{margin:0;background:#080b12;color:#f5f5f5;font:16px Arial}
header{background:#111722;padding:22px;text-align:center;border-bottom:2px solid #d6ad52}
h1,h2,h3{color:#e7c36c}
main{max-width:1000px;margin:auto;padding:20px 14px}
.card{background:#141b28;border:1px solid #4d4026;border-radius:12px;padding:17px;margin:14px 0}
input,textarea,select{display:block;width:100%;padding:12px;margin:8px 0 14px;background:#0c111b;color:white;border:1px solid #555;border-radius:7px}
button,.btn{background:#e1b957;color:#111;padding:11px 15px;border:0;border-radius:7px;font-weight:bold;cursor:pointer;text-decoration:none;display:inline-block;margin:3px}
.danger{background:#d66b6b}
a{color:#f1cf78}
small{color:#ccc}
table{width:100%;border-collapse:collapse}
td,th{padding:9px;border-bottom:1px solid #444;text-align:left}
.notice{background:#203526;padding:12px;border-radius:8px}
@media(max-width:600px){table{font-size:13px}td,th{padding:5px}}
"""


def page(title, body, **context):
    template = """
    <!doctype html><html lang="uz"><head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{{ title }} | 25-maktab</title>
    <style>""" + STYLE + """</style></head>
    <body><header><h1>25-MAKTAB</h1>
    <p>TO‘GARAKLAR MARKAZI</p>
    <a href="/">Bosh sahifa</a>
    {% if session.get('is_admin') %}
    · <a href="/admin">Admin paneli</a>
    · <a href="/admin/logout">Chiqish</a>
    {% endif %}
    </header><main>
    {% with messages=get_flashed_messages() %}
    {% for message in messages %}<p class="notice">{{ message }}</p>{% endfor %}
    {% endwith %}
    """ + body + """</main><footer style="text-align:center;padding:24px;color:#aaa">
    © 25-maktab</footer></body></html>
    """
    return render_template_string(template, title=title, **context)


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


@app.route("/")
def index():
    clubs = Club.query.order_by(Club.name).all()
    body = """
    <h2>Maktabimiz to‘garaklari</h2><div>
    {% for c in clubs %}
    <div class="card"><h3>{{ c.name }}</h3>
    <p>{{ c.description }}</p>
    <p><b>Rahbar:</b> {{ c.leader or 'Belgilanmagan' }}</p>
    <p><b>Jadval:</b> {{ c.schedule or 'Belgilanmagan' }}</p></div>
    {% else %}<p>Hozircha to‘garaklar yo‘q.</p>{% endfor %}
    </div>
    <div class="card"><h2>To‘garakka ariza berish</h2>
    <p>Saytga login qilish shart emas.</p>
    <form method="post" action="/apply">
    <label>Ism-familiya</label><input name="student_name" maxlength="120" required>
    <label>Sinf</label><input name="class_name" maxlength="30" required>
    <label>Telefon</label><input name="phone" type="tel" maxlength="30" required>
    <label>To‘garak</label><select name="club_id" required>
    <option value="">Tanlang</option>
    {% for c in clubs %}<option value="{{ c.id }}">{{ c.name }}</option>{% endfor %}
    </select><button>Ariza yuborish</button></form></div>
    """
    return page("Bosh sahifa", body, clubs=clubs)


@app.route("/apply", methods=["POST"])
def apply():
    name = request.form.get("student_name", "").strip()
    cls = request.form.get("class_name", "").strip()
    phone = request.form.get("phone", "").strip()
    club_id = request.form.get("club_id", type=int)
    club = db.session.get(Club, club_id) if club_id else None

    if not name or not cls or not phone or not club:
        flash("Barcha maydonlarni to‘ldiring.")
        return redirect(url_for("index"))

    db.session.add(Application(
        student_name=name[:120],
        class_name=cls[:30],
        phone=phone[:30],
        club_id=club.id
    ))
    db.session.commit()
    flash("Arizangiz qabul qilindi.")
    return redirect(url_for("index"))


@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if (ADMIN_USERNAME and ADMIN_PASSWORD
            and compare_digest(username, ADMIN_USERNAME)
            and compare_digest(password, ADMIN_PASSWORD)):
            session.clear()
            session["is_admin"] = True
            return redirect(url_for("admin_dashboard"))

        flash("Admin nomi yoki parol noto‘g‘ri.")

    body = """
    <div class="card"><h2>Admin kirishi</h2>
    <form method="post">
    <label>Admin nomi</label><input name="username" required>
    <label>Parol</label><input name="password" type="password" required>
    <button>Kirish</button></form></div>
    """
    return page("Admin kirishi", body)


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    clubs = Club.query.order_by(Club.name).all()
    applications = Application.query.order_by(
        Application.id.desc()
    ).all()
    total = Application.query.count()
    body = """
    <h2>Admin paneli</h2>
    <div class="card"><h3>Statistika</h3>
    <p>To‘garaklar: {{ clubs|length }}</p>
    <p>Arizalar: {{ total }}</p></div>
    <div class="card"><h3>Yangi to‘garak qo‘shish</h3>
    <form method="post" action="/admin/clubs/add">
    <label>Nomi</label><input name="name" maxlength="120" required>
    <label>Tavsif</label><textarea name="description" maxlength="2000"></textarea>
    <label>Rahbar</label><input name="leader" maxlength="120">
    <label>Mashg‘ulot jadvali</label><input name="schedule" maxlength="120">
    <button>To‘garak qo‘shish</button></form></div>
    <h3>To‘garaklar</h3>
    {% for c in clubs %}
    <div class="card"><b>{{ c.name }}</b>
    <form method="post" action="/admin/clubs/{{ c.id }}/edit">
    <label>Nomi</label><input name="name" value="{{ c.name }}" required maxlength="120">
    <label>Tavsif</label><textarea name="description">{{ c.description }}</textarea>
    <label>Rahbar</label><input name="leader" value="{{ c.leader }}">
    <label>Jadval</label><input name="schedule" value="{{ c.schedule }}">
    <button>Saqlash</button></form>
    <form method="post" action="/admin/clubs/{{ c.id }}/delete"
    onsubmit="return confirm('To‘garak va unga tegishli arizalar o‘chirilsinmi?')">
    <button class="danger">To‘garakni o‘chirish</button></form></div>
    {% endfor %}
    <h3>O‘quvchilar arizalari</h3>
    {% for a in applications %}
    <div class="card"><b>{{ a.student_name }}</b> — {{ a.class_name }}
    <p>Telefon: {{ a.phone }}</p><p>To‘garak: {{ a.club.name }}</p>
    <p>Holat: {{ a.status }}</p>
    <form method="post" action="/admin/applications/{{ a.id }}/status">
    <select name="status">
    {% for s in ['Yangi','Tasdiqlandi','Rad etildi'] %}
    <option {% if a.status == s %}selected{% endif %}>{{ s }}</option>
    {% endfor %}</select><button>Holatni saqlash</button></form></div>
    {% else %}<p>Hozircha arizalar yo‘q.</p>{% endfor %}
    """
    return page("Admin paneli", body, clubs=clubs,
                applications=applications, total=total)


@app.route("/admin/clubs/add", methods=["POST"])
@admin_required
def add_club():
    name = request.form.get("name", "").strip()
    if not name:
        flash("To‘garak nomini kiriting.")
    else:
        db.session.add(Club(
            name=name[:120],
            description=request.form.get("description", "")[:2000],
            leader=request.form.get("leader", "")[:120],
            schedule=request.form.get("schedule", "")[:120]
        ))
        db.session.commit()
        flash("To‘garak qo‘shildi.")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/clubs/<int:club_id>/edit", methods=["POST"])
@admin_required
def edit_club(club_id):
    club = db.session.get(Club, club_id)
    if not club:
        flash("To‘garak topilmadi.")
    else:
        club.name = request.form.get("name", "").strip()[:120] or club.name
        club.description = request.form.get("description", "")[:2000]
        club.leader = request.form.get("leader", "")[:120]
        club.schedule = request.form.get("schedule", "")[:120]
        db.session.commit()
        flash("To‘garak yangilandi.")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/clubs/<int:club_id>/delete", methods=["POST"])
@admin_required
def delete_club(club_id):
    club = db.session.get(Club, club_id)
    if club:
        Application.query.filter_by(club_id=club.id).delete()
        db.session.delete(club)
        db.session.commit()
        flash("To‘garak va uning arizalari o‘chirildi.")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/applications/<int:app_id>/status", methods=["POST"])
@admin_required
def update_status(app_id):
    application = db.session.get(Application, app_id)
    status = request.form.get("status", "")
    if application and status in ("Yangi", "Tasdiqlandi", "Rad etildi"):
        application.status = status
        db.session.commit()
        flash("Ariza holati yangilandi.")
    return redirect(url_for("admin_dashboard"))


@app.route("/health")
def health():
    return {"status": "ok"}


with app.app_context():
    db.create_all()
    if Club.query.count() == 0:
        db.session.add_all([
            Club(name="IT va dasturlash",
                 description="Kompyuter va dasturlash mashg‘ulotlari."),
            Club(name="Ingliz tili",
                 description="Ingliz tilini o‘rganish."),
            Club(name="Sport",
                 description="Sport mashg‘ulotlari."),
            Club(name="Matematika",
                 description="Mantiqiy fikrlash va masalalar.")
        ])
        db.session.commit()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
        
