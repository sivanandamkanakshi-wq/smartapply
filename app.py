import json
import os
import random
import secrets
import smtplib
import sqlite3
import sys
from email.message import EmailMessage
from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv
import requests

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from features.resume_ats import calculate_ats_score
from features.job_search import job_search_bp
from werkzeug.utils import secure_filename
from features.application_tracker import tracker_bp, init_tracker_db
from features.encryption import encrypt_field, decrypt_field

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "").strip() or secrets.token_hex(32)
app.config["DATABASE_PATH"] = os.path.join(BASE_DIR, "database", "SmartApply.db")
app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB total per request
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "false").strip().lower() in {"1", "true", "yes", "on"}
ALLOW_LOCAL_DB_RESET = os.getenv("ALLOW_LOCAL_DB_RESET", "false").strip().lower() in {"1", "true", "yes", "on"}

ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "webp"}
ALLOWED_DOC_EXT = {"pdf", "png", "jpg", "jpeg"}

# ---------------------------------------------------------------------------
# Google OAuth (Authlib) — enables either for real Google OAuth when
# credentials are provided or for a demo mode that works locally without
# external setup.
# ---------------------------------------------------------------------------
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
GOOGLE_DEMO_MODE = os.getenv("GOOGLE_DEMO_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}
GOOGLE_DEMO_EMAIL = os.getenv("GOOGLE_DEMO_EMAIL", "demo.google.user@example.com").strip()
GOOGLE_DEMO_NAME = os.getenv("GOOGLE_DEMO_NAME", "Google Demo User").strip()
GOOGLE_ENABLED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET) or GOOGLE_DEMO_MODE

# ---------------------------------------------------------------------------
# Gemini API (Google AI Studio) — powers AI Auto Apply. Free tier, no credit
# card: https://aistudio.google.com/apikey. Until GEMINI_API_KEY is set in
# .env, the Auto Apply page stays visible but shows a friendly setup message
# instead of erroring.
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = "gemini-2.5-flash"


def generate_auto_apply_content(profile_summary, job_title, company, job_description):
    """Calls the Gemini API to produce a match analysis + tailored cover
    letter for the given job, based on the user's saved profile. Returns
    (result_text, error_message) — exactly one of which is None."""
    if not GEMINI_API_KEY:
        return None, "AI Auto Apply isn't set up yet. Add a GEMINI_API_KEY to your .env file to enable it."

    prompt = f"""You are a career assistant helping a job seeker apply to a role.

Candidate profile:
- Name: {profile_summary.get('name') or 'the candidate'}
- Career objective: {profile_summary.get('career_objective') or 'Not provided'}
- Experience level: {profile_summary.get('experience_type') or 'Not provided'}
- Most recent role: {profile_summary.get('exp_job_role') or 'Not provided'}
- Technical skills: {', '.join(profile_summary.get('technical_skills') or []) or 'Not provided'}
- Soft skills: {', '.join(profile_summary.get('soft_skills') or []) or 'Not provided'}
- Projects: {', '.join(profile_summary.get('projects') or []) or 'Not provided'}

Target job:
- Title: {job_title or 'Not specified'}
- Company: {company or 'Not specified'}
- Description:
{job_description}

Write a response in two clearly labeled sections using these exact headings:

MATCH ANALYSIS
A short bulleted list of how the candidate's skills/experience align with this job, and one or two honest gaps if relevant.

COVER LETTER
A concise, professional cover letter (roughly 150-200 words) tailored to this job, written in the candidate's voice, ready to copy and send."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    try:
        response = requests.post(
            url,
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        return text, None
    except Exception as exc:
        print(f"[GEMINI ERROR] {exc}")
        return None, "Something went wrong generating your application. Please try again in a moment."


oauth = None
if GOOGLE_ENABLED and GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    try:
        from authlib.integrations.flask_client import OAuth
    except ImportError:
        OAuth = None

    if OAuth is not None:
        oauth = OAuth(app)
        oauth.register(
            name="google",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )


def get_or_create_google_demo_user():
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM users WHERE email = ?", (GOOGLE_DEMO_EMAIL,)).fetchone()

    if not user:
        random_password = generate_password_hash(os.urandom(16).hex())
        conn.execute(
            "INSERT INTO users (full_name, email, password, mobile_number, auth_provider) VALUES (?, ?, ?, NULL, 'google')",
            (GOOGLE_DEMO_NAME, GOOGLE_DEMO_EMAIL, random_password),
        )
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (GOOGLE_DEMO_EMAIL,)).fetchone()

    conn.close()
    ensure_profile_exists(user["id"], user)
    return user


def ensure_profile_exists(user_id, user=None):
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row
    existing = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
    if not existing:
        if user is None:
            user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.execute(
            "INSERT INTO profiles (user_id, full_name, email, documents_json, education_json, technical_skills_json, soft_skills_json, internship_json, projects_json, certifications_json, achievements_json, languages_json, social_json, job_pref_json, references_json, profile_completion, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (
                user_id,
                user["full_name"] if user else "",
                user["email"] if user else "",
                "{}",
                "{}",
                "[]",
                "[]",
                "{}",
                "[]",
                "[]",
                "{}",
                "[]",
                "{}",
                "{}",
                "[]",
                0,
            ),
        )
        conn.commit()
    conn.close()


def init_db():
    os.makedirs(os.path.dirname(app.config["DATABASE_PATH"]), exist_ok=True)
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            mobile_number TEXT,
            auth_provider TEXT DEFAULT 'local',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    for statement in (
        "ALTER TABLE users ADD COLUMN mobile_number TEXT",
        "ALTER TABLE users ADD COLUMN auth_provider TEXT DEFAULT 'local'",
        "ALTER TABLE users ADD COLUMN api_token TEXT",
    ):
        try:
            conn.execute(statement)
        except sqlite3.OperationalError:
            pass

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT, photo_path TEXT, gender TEXT, dob TEXT, age TEXT,
            nationality TEXT, marital_status TEXT, blood_group TEXT,
            aadhaar_number TEXT, pan_number TEXT,
            mobile_number TEXT, alt_mobile_number TEXT, email TEXT, alt_email TEXT,
            perm_house_no TEXT, perm_street TEXT, perm_area TEXT, perm_city TEXT,
            perm_district TEXT, perm_state TEXT, perm_country TEXT, perm_pincode TEXT,
            same_as_permanent INTEGER DEFAULT 0,
            curr_house_no TEXT, curr_street TEXT, curr_area TEXT, curr_city TEXT,
            curr_district TEXT, curr_state TEXT, curr_country TEXT, curr_pincode TEXT,
            career_objective TEXT,
            education_json TEXT, technical_skills_json TEXT, soft_skills_json TEXT,
            experience_type TEXT, exp_company_name TEXT, exp_job_role TEXT,
            exp_start_date TEXT, exp_end_date TEXT, exp_total_experience TEXT,
            exp_responsibilities TEXT, internship_json TEXT, projects_json TEXT,
            certifications_json TEXT, achievements_json TEXT, languages_json TEXT,
            social_json TEXT, job_pref_json TEXT, documents_json TEXT,
            hobbies TEXT, interests TEXT, references_json TEXT,
            declaration INTEGER DEFAULT 0,
            security_question TEXT, security_answer TEXT,
            profile_completion INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    conn.commit()
    conn.close()


def reset_local_db():
    if os.path.exists(app.config["DATABASE_PATH"]):
        os.remove(app.config["DATABASE_PATH"])
    init_db()


def mask_mobile_number(value):
    if not value:
        return "your registered mobile number"
    if len(value) <= 4:
        return "*" * len(value)
    return "*" * (len(value) - 4) + value[-4:]


def normalize_mobile_number(mobile_number):
    if not mobile_number:
        return ""

    cleaned = "".join(ch for ch in str(mobile_number) if ch.isdigit())
    if not cleaned:
        return ""

    if cleaned.startswith("0"):
        cleaned = cleaned[1:]

    if len(cleaned) == 10 and cleaned[0] in "6789":
        return f"+91{cleaned}"
    if cleaned.startswith("91") and len(cleaned) == 12:
        return f"+{cleaned}"
    if cleaned.startswith("1") and len(cleaned) == 11:
        return f"+{cleaned}"
    return f"+{cleaned}"


def is_valid_indian_mobile_number(mobile_number):
    if not mobile_number:
        return False

    cleaned = "".join(ch for ch in str(mobile_number) if ch.isdigit())
    if not cleaned:
        return False

    if cleaned.startswith("0"):
        cleaned = cleaned[1:]

    if cleaned.startswith("91") and len(cleaned) == 12:
        return True
    if cleaned.startswith("1") and len(cleaned) == 11:
        return True

    return len(cleaned) == 10 and cleaned[0] in "6789"


def send_sms_otp(mobile_number, otp_code):
    if os.getenv("OTP_DEMO_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}:
        print(f"[OTP DEMO] SMS OTP for {mobile_number}: {otp_code}")
        return True

    provider = os.getenv("SMS_PROVIDER", "msg91").strip().lower()
    if provider in {"email", "smtp"}:
        recipient = os.getenv("OTP_RECIPIENT_NUMBER", "").strip() or mobile_number
        return send_email_otp(recipient, otp_code)

    if not mobile_number:
        print("[OTP DEBUG] no mobile number provided")
        return False

    if not is_valid_indian_mobile_number(mobile_number):
        print(f"[OTP DEBUG] invalid Indian mobile number: {mobile_number}")
        return False

    api_key = os.getenv("MSG91_API_KEY", "").strip()
    sender_id = os.getenv("MSG91_SENDER_ID", "").strip()
    if not api_key or not sender_id:
        print("[OTP DEBUG] MSG91 credentials are not configured — cannot send real SMS")
        return False

    recipient = mobile_number
    if os.getenv("OTP_RECIPIENT_NUMBER_OVERRIDE", "false").strip().lower() in {"1", "true", "yes", "on"}:
        recipient = os.getenv("OTP_RECIPIENT_NUMBER", "").strip() or mobile_number

    phone_number = normalize_mobile_number(recipient)
    try:
        response = requests.post(
            "https://api.msg91.com/api/v5/otp",
            json={
                "mobile": phone_number,
                "authkey": api_key,
                "template_id": "",
                "otp": otp_code,
                "sender": sender_id,
            },
            timeout=10,
        )
        response.raise_for_status()
        return True
    except Exception as exc:
        print(f"MSG91 SMS error: {exc}")
        return False


def send_email_otp(email_address, otp_code):
    if os.getenv("OTP_DEMO_MODE", "false").lower() == "true":
        print(f"[OTP DEMO] Email OTP for {email_address}: {otp_code}")
        return True

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM")

    if not all([smtp_host, smtp_port, smtp_username, smtp_password, smtp_from]):
        print(f"[OTP DEBUG] email={email_address} otp={otp_code}")
        return False

    msg = EmailMessage()
    msg["Subject"] = "SmartApply verification code"
    msg["From"] = smtp_from
    msg["To"] = email_address
    msg.set_content(
        f"Your SmartApply verification code is {otp_code}.\n\n"
        "Enter this code on the password reset page to verify your account."
    )

    try:
        with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        return True
    except Exception as exc:
        print(f"Email OTP error: {exc}")
        return False


def send_otp_to_user(email, mobile_number, otp_code):
    if os.getenv("SMS_PROVIDER", "msg91").strip().lower() in {"email", "smtp"}:
        if send_email_otp(email, otp_code):
            return "email", True
        return None, False
    if mobile_number and send_sms_otp(mobile_number, otp_code):
        return "mobile", True
    if send_email_otp(email, otp_code):
        return "email", True
    return None, False


def allowed_file(filename, allowed_ext):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_ext


def save_upload(file_storage, user_id, field_name, allowed_ext):
    """Saves an uploaded file under static/uploads/<user_id>/ and returns the
    web-accessible path, or None if no valid file was submitted."""
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename, allowed_ext):
        return None

    user_folder = os.path.join(app.config["UPLOAD_FOLDER"], str(user_id))
    os.makedirs(user_folder, exist_ok=True)

    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    safe_name = secure_filename(f"{field_name}.{ext}")
    disk_path = os.path.join(user_folder, safe_name)
    file_storage.save(disk_path)

    return f"uploads/{user_id}/{safe_name}"


def delete_upload(web_path):
    """Deletes a previously-saved upload from disk given its web-accessible
    path (e.g. 'uploads/3/photo.jpg'). Safe to call even if the file is
    already gone."""
    if not web_path:
        return
    disk_path = os.path.join(app.static_folder, web_path)
    try:
        if os.path.isfile(disk_path):
            os.remove(disk_path)
    except OSError as exc:
        print(f"[DELETE UPLOAD ERROR] {exc}")


def load_json_field(raw_value, default):
    if not raw_value:
        return default
    try:
        return json.loads(raw_value)
    except (TypeError, ValueError):
        return default


def calculate_profile_completion(profile_row):
    """Rough completion score across the major sections of the one-time
    profile, so the dashboard progress bar reflects real data."""
    if not profile_row:
        return 0

    checks = [
        bool(profile_row["full_name"]),
        bool(profile_row["photo_path"]),
        bool(profile_row["dob"]),
        bool(profile_row["mobile_number"]),
        bool(profile_row["perm_city"]),
        bool(profile_row["career_objective"]),
        bool(load_json_field(profile_row["education_json"], {})),
        bool(load_json_field(profile_row["technical_skills_json"], [])),
        bool(load_json_field(profile_row["projects_json"], [])),
        bool(load_json_field(profile_row["social_json"], {})),
        bool(load_json_field(profile_row["job_pref_json"], {})),
        bool(load_json_field(profile_row["documents_json"], {}).get("resume_path"))
        if load_json_field(profile_row["documents_json"], {})
        else False,
    ]
    return round((sum(1 for c in checks if c) / len(checks)) * 100)


init_db()
app.register_blueprint(tracker_bp)
init_tracker_db(app)
app.register_blueprint(job_search_bp)


@app.route("/")
def index():
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return render_template("index.html", total_users=total_users)


@app.route("/home")
def home():
    if "user_id" not in session:
        flash("Please log in to continue.")
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please log in to continue.")
        return redirect(url_for("login"))

    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    profile = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (session["user_id"],)).fetchone()
    conn.close()

    if not user:
        session.clear()
        flash("Your session has expired. Please log in again.")
        return redirect(url_for("login"))

    if profile:
        profile_completion = profile["profile_completion"] or calculate_profile_completion(profile)
        display_name = profile["full_name"] or user["full_name"]
        photo_path = profile["photo_path"]
    else:
        fields = [user["full_name"], user["email"], user["mobile_number"]]
        profile_completion = round((sum(1 for f in fields if f) / len(fields)) * 100)
        display_name = user["full_name"]
        photo_path = None

    return render_template(
        "home.html",
        full_name=display_name,
        email=user["email"],
        profile_completion=profile_completion,
        photo_path=photo_path,
        has_profile=bool(profile),
    )


@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        flash("Please log in to continue.")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row

    existing = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    if request.method == "POST":
        f = request.form

        # ---- Personal / contact / address -------------------------------
        same_as_permanent = 1 if f.get("same_as_permanent") == "on" else 0
        if same_as_permanent:
            curr = {k: f.get(f"perm_{k}", "") for k in
                    ["house_no", "street", "area", "city", "district", "state", "country", "pincode"]}
        else:
            curr = {k: f.get(f"curr_{k}", "") for k in
                    ["house_no", "street", "area", "city", "district", "state", "country", "pincode"]}

        # ---- Education ----------------------------------------------------
        education = {
            "ssc": {"school": f.get("ssc_school", ""), "board": f.get("ssc_board", ""),
                    "year": f.get("ssc_year", ""), "score": f.get("ssc_score", "")},
            "intermediate": {"college": f.get("inter_college", ""), "board": f.get("inter_board", ""),
                              "stream": f.get("inter_stream", ""), "year": f.get("inter_year", ""),
                              "score": f.get("inter_score", "")},
            "diploma": {"college": f.get("diploma_college", ""), "branch": f.get("diploma_branch", ""),
                        "year": f.get("diploma_year", ""), "score": f.get("diploma_score", "")},
            "graduation": {"college": f.get("grad_college", ""), "university": f.get("grad_university", ""),
                           "degree": f.get("grad_degree", ""), "branch": f.get("grad_branch", ""),
                           "current_year": f.get("grad_current_year", ""), "score": f.get("grad_score", ""),
                           "year": f.get("grad_year", "")},
            "post_graduation": {"college": f.get("pg_college", ""), "university": f.get("pg_university", ""),
                                 "degree": f.get("pg_degree", ""), "branch": f.get("pg_branch", ""),
                                 "year": f.get("pg_year", ""), "score": f.get("pg_score", "")},
        }

        technical_skills = f.getlist("technical_skills")
        other_tech_skill = f.get("other_tech_skill", "").strip()
        if other_tech_skill:
            technical_skills.append(other_tech_skill)

        soft_skills = f.getlist("soft_skills")

        # ---- Experience / internship --------------------------------------
        internship = {
            "company": f.get("intern_company", ""), "role": f.get("intern_role", ""),
            "duration": f.get("intern_duration", ""), "technologies": f.get("intern_technologies", ""),
            "description": f.get("intern_description", ""),
        }

        # ---- Repeatable: projects & certifications -------------------------
        projects = []
        for title, desc, tech, team, role, duration, github, demo in zip(
            f.getlist("project_title"), f.getlist("project_description"),
            f.getlist("project_technologies"), f.getlist("project_team_size"),
            f.getlist("project_role"), f.getlist("project_duration"),
            f.getlist("project_github"), f.getlist("project_demo"),
        ):
            if title.strip():
                projects.append({"title": title, "description": desc, "technologies": tech,
                                  "team_size": team, "role": role, "duration": duration,
                                  "github": github, "demo": demo})

        certifications = []
        for name, org, issue_date, cert_id, link in zip(
            f.getlist("cert_name"), f.getlist("cert_org"), f.getlist("cert_issue_date"),
            f.getlist("cert_id"), f.getlist("cert_link"),
        ):
            if name.strip():
                certifications.append({"name": name, "organization": org, "issue_date": issue_date,
                                        "cert_id": cert_id, "link": link})

        achievements = {
            "academic": f.get("achv_academic", ""), "technical": f.get("achv_technical", ""),
            "hackathons": f.get("achv_hackathons", ""), "workshops": f.get("achv_workshops", ""),
            "paper_presentations": f.get("achv_papers", ""), "awards": f.get("achv_awards", ""),
        }

        languages = f.getlist("languages")
        other_language = f.get("other_language", "").strip()
        if other_language:
            languages.append(other_language)

        social = {
            "linkedin": f.get("social_linkedin", ""), "github": f.get("social_github", ""),
            "portfolio": f.get("social_portfolio", ""), "hackerrank": f.get("social_hackerrank", ""),
            "leetcode": f.get("social_leetcode", ""), "codechef": f.get("social_codechef", ""),
            "codeforces": f.get("social_codeforces", ""),
        }

        job_pref = {
            "role": f.get("pref_role", ""), "industry": f.get("pref_industry", ""),
            "location": f.get("pref_location", ""), "expected_salary": f.get("pref_salary", ""),
            "employment_type": f.getlist("employment_type"), "notice_period": f.get("pref_notice_period", ""),
            "willing_to_relocate": f.get("pref_relocate", "No"),
        }

        references_list = []
        for name, designation, company, contact, ref_email in zip(
            f.getlist("ref_name"), f.getlist("ref_designation"), f.getlist("ref_company"),
            f.getlist("ref_contact"), f.getlist("ref_email"),
        ):
            if name.strip():
                references_list.append({"name": name, "designation": designation, "company": company,
                                         "contact": contact, "email": ref_email})

        # ---- File uploads ----------------------------------------------------
        existing_docs = load_json_field(existing["documents_json"], {}) if existing else {}
        existing_photo = existing["photo_path"] if existing else None

        new_photo = save_upload(request.files.get("photo"), user_id, "photo", ALLOWED_IMAGE_EXT)
        remove_photo_requested = f.get("remove_photo") == "1"

        if new_photo:
            # A fresh photo was uploaded — it replaces whatever was there.
            if existing_photo and existing_photo != new_photo:
                delete_upload(existing_photo)
            photo_path = new_photo
        elif remove_photo_requested:
            # User explicitly removed their photo and did not upload a new one.
            if existing_photo:
                delete_upload(existing_photo)
            photo_path = None
        else:
            photo_path = existing_photo

        doc_fields = {
            "resume_path": ("resume", ALLOWED_DOC_EXT),
            "aadhaar_path": ("aadhaar_doc", ALLOWED_DOC_EXT),
            "pan_path": ("pan_doc", ALLOWED_DOC_EXT),
            "ssc_cert_path": ("ssc_cert", ALLOWED_DOC_EXT),
            "inter_cert_path": ("inter_cert", ALLOWED_DOC_EXT),
            "degree_cert_path": ("degree_cert", ALLOWED_DOC_EXT),
            "experience_cert_path": ("experience_cert", ALLOWED_DOC_EXT),
        }
        documents = dict(existing_docs)
        for doc_key, (field_name, allowed_ext) in doc_fields.items():
            saved = save_upload(request.files.get(field_name), user_id, field_name, allowed_ext)
            if saved:
                documents[doc_key] = saved

        declaration = 1 if f.get("declaration") == "on" else 0

        row_values = {
            "user_id": user_id,
            "full_name": f.get("full_name", "").strip(),
            "photo_path": photo_path,
            "gender": f.get("gender", ""),
            "dob": f.get("dob", ""),
            "age": f.get("age", ""),
            "nationality": f.get("nationality", ""),
            "marital_status": f.get("marital_status", ""),
            "blood_group": f.get("blood_group", ""),
            # ---- Encrypted before storage — see features/encryption.py ----
            "aadhaar_number": encrypt_field(f.get("aadhaar_number", "")),
            "pan_number": encrypt_field(f.get("pan_number", "")),
            "mobile_number": f.get("mobile_number", "").strip(),
            "alt_mobile_number": f.get("alt_mobile_number", ""),
            "email": f.get("email", "").strip() or (user["email"] if user else ""),
            "alt_email": f.get("alt_email", ""),
            "perm_house_no": f.get("perm_house_no", ""), "perm_street": f.get("perm_street", ""),
            "perm_area": f.get("perm_area", ""), "perm_city": f.get("perm_city", ""),
            "perm_district": f.get("perm_district", ""), "perm_state": f.get("perm_state", ""),
            "perm_country": f.get("perm_country", ""), "perm_pincode": f.get("perm_pincode", ""),
            "same_as_permanent": same_as_permanent,
            "curr_house_no": curr["house_no"], "curr_street": curr["street"],
            "curr_area": curr["area"], "curr_city": curr["city"],
            "curr_district": curr["district"], "curr_state": curr["state"],
            "curr_country": curr["country"], "curr_pincode": curr["pincode"],
            "career_objective": f.get("career_objective", ""),
            "education_json": json.dumps(education),
            "technical_skills_json": json.dumps(technical_skills),
            "soft_skills_json": json.dumps(soft_skills),
            "experience_type": f.get("experience_type", "Fresher"),
            "exp_company_name": f.get("exp_company_name", ""),
            "exp_job_role": f.get("exp_job_role", ""),
            "exp_start_date": f.get("exp_start_date", ""),
            "exp_end_date": f.get("exp_end_date", ""),
            "exp_total_experience": f.get("exp_total_experience", ""),
            "exp_responsibilities": f.get("exp_responsibilities", ""),
            "internship_json": json.dumps(internship),
            "projects_json": json.dumps(projects),
            "certifications_json": json.dumps(certifications),
            "achievements_json": json.dumps(achievements),
            "languages_json": json.dumps(languages),
            "social_json": json.dumps(social),
            "job_pref_json": json.dumps(job_pref),
            "documents_json": json.dumps(documents),
            "hobbies": f.get("hobbies", ""),
            "interests": f.get("interests", ""),
            "references_json": json.dumps(references_list),
            "declaration": declaration,
            "security_question": f.get("security_question", ""),
            # ---- Encrypted before storage — see features/encryption.py ----
            "security_answer": encrypt_field(f.get("security_answer", "")),
        }

        columns = list(row_values.keys())
        placeholders = ", ".join("?" for _ in columns)
        updates = ", ".join(f"{c} = excluded.{c}" for c in columns if c != "user_id")

        conn.execute(
            f"""
            INSERT INTO profiles ({", ".join(columns)}, updated_at)
            VALUES ({placeholders}, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET {updates}, updated_at = CURRENT_TIMESTAMP
            """,
            list(row_values.values()),
        )
        conn.commit()

        saved_row = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        completion = calculate_profile_completion(saved_row)
        conn.execute("UPDATE profiles SET profile_completion = ? WHERE user_id = ?", (completion, user_id))
        conn.commit()
        conn.close()

        flash("Profile saved successfully.")
        return redirect(url_for("profile"))

    # ---- GET: prefill from existing profile (if any) ------------------------
    conn.close()

    empty_education = {"ssc": {}, "intermediate": {}, "diploma": {}, "graduation": {}, "post_graduation": {}}
    data = {
        "education": empty_education, "technical_skills": [], "soft_skills": [], "internship": {},
        "projects": [], "certifications": [], "achievements": {}, "languages": [],
        "social": {}, "job_pref": {}, "documents": {}, "references_list": [],
    }
    profile_completion = 0
    if existing:
        data.update(dict(existing))
        # ---- Decrypted for display — see features/encryption.py ----
        data["aadhaar_number"] = decrypt_field(existing["aadhaar_number"])
        data["pan_number"] = decrypt_field(existing["pan_number"])
        data["security_answer"] = decrypt_field(existing["security_answer"])
        loaded_education = load_json_field(existing["education_json"], {})
        data["education"] = {**empty_education, **loaded_education}
        data["technical_skills"] = load_json_field(existing["technical_skills_json"], [])
        data["soft_skills"] = load_json_field(existing["soft_skills_json"], [])
        data["internship"] = load_json_field(existing["internship_json"], {})
        data["projects"] = load_json_field(existing["projects_json"], [])
        data["certifications"] = load_json_field(existing["certifications_json"], [])
        data["achievements"] = load_json_field(existing["achievements_json"], {})
        data["languages"] = load_json_field(existing["languages_json"], [])
        data["social"] = load_json_field(existing["social_json"], {})
        data["job_pref"] = load_json_field(existing["job_pref_json"], {})
        data["documents"] = load_json_field(existing["documents_json"], {})
        data["references_list"] = load_json_field(existing["references_json"], [])
        profile_completion = existing["profile_completion"] or calculate_profile_completion(existing)
    else:
        data["email"] = user["email"] if user else ""
        data["full_name"] = user["full_name"] if user else ""
        data["mobile_number"] = user["mobile_number"] if user else ""

    return render_template(
        "profile.html",
        data=data,
        has_profile=bool(existing),
        profile_completion=profile_completion,
    )


@app.route("/resume-manager", methods=["GET", "POST"])
def resume_manager():
    if "user_id" not in session:
        flash("Please log in to continue.")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row

    existing = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()

    if not existing:
        conn.close()
        flash("Please complete your profile first, then come back to manage your resume.")
        return redirect(url_for("profile"))

    if request.method == "POST":
        f = request.form
        existing_docs = load_json_field(existing["documents_json"], {})
        documents = dict(existing_docs)

        # ---- Resume (with explicit remove support, like the photo field) ----
        new_resume = save_upload(request.files.get("resume"), user_id, "resume", ALLOWED_DOC_EXT)
        remove_resume_requested = f.get("remove_resume") == "1"

        if new_resume:
            if documents.get("resume_path") and documents["resume_path"] != new_resume:
                delete_upload(documents["resume_path"])
            documents["resume_path"] = new_resume
        elif remove_resume_requested:
            if documents.get("resume_path"):
                delete_upload(documents["resume_path"])
            documents.pop("resume_path", None)

        # ---- Other documents (Aadhaar, PAN, certificates) --------------------
        other_doc_fields = {
            "aadhaar_path": ("aadhaar_doc", ALLOWED_DOC_EXT),
            "pan_path": ("pan_doc", ALLOWED_DOC_EXT),
            "ssc_cert_path": ("ssc_cert", ALLOWED_DOC_EXT),
            "inter_cert_path": ("inter_cert", ALLOWED_DOC_EXT),
            "degree_cert_path": ("degree_cert", ALLOWED_DOC_EXT),
            "experience_cert_path": ("experience_cert", ALLOWED_DOC_EXT),
        }
        for doc_key, (field_name, allowed_ext) in other_doc_fields.items():
            saved = save_upload(request.files.get(field_name), user_id, field_name, allowed_ext)
            if saved:
                if documents.get(doc_key) and documents[doc_key] != saved:
                    delete_upload(documents[doc_key])
                documents[doc_key] = saved

        conn.execute(
            "UPDATE profiles SET documents_json = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (json.dumps(documents), user_id),
        )
        conn.commit()

        saved_row = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        completion = calculate_profile_completion(saved_row)
        conn.execute("UPDATE profiles SET profile_completion = ? WHERE user_id = ?", (completion, user_id))
        conn.commit()
        conn.close()

        flash("Resume updated successfully.")
        return redirect(url_for("resume_manager"))

    # ---- GET: build the same `data` shape the template's Jinja needs --------
    empty_education = {"ssc": {}, "intermediate": {}, "diploma": {}, "graduation": {}, "post_graduation": {}}
    data = {
        "education": load_json_field(existing["education_json"], empty_education),
        "technical_skills": load_json_field(existing["technical_skills_json"], []),
        "soft_skills": load_json_field(existing["soft_skills_json"], []),
        "experience_type": existing["experience_type"],
        "internship": load_json_field(existing["internship_json"], {}),
        "projects": load_json_field(existing["projects_json"], []),
        "certifications": load_json_field(existing["certifications_json"], []),
        "languages": load_json_field(existing["languages_json"], []),
        "documents": load_json_field(existing["documents_json"], {}),
    }
    data["education"] = {**empty_education, **data["education"]}

    ats_score = 0
    resume_path = data["documents"].get("resume_path")
    if resume_path:
        resume_disk_path = os.path.join(app.static_folder, resume_path)
        ats_score = calculate_ats_score(resume_disk_path, data["technical_skills"])

    conn.close()
    return render_template("resume_manager.html", data=data, ats_score=ats_score)


@app.route("/auto-apply", methods=["GET", "POST"])
def auto_apply():
    if "user_id" not in session:
        flash("Please log in to continue.")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row
    existing = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()

    if not existing:
        flash("Please complete your profile first, then come back to use Auto Apply.")
        return redirect(url_for("profile"))

    result = None
    job_title = ""
    company = ""
    job_description = ""

    if request.method == "POST":
        job_title = request.form.get("job_title", "").strip()
        company = request.form.get("company", "").strip()
        job_description = request.form.get("job_description", "").strip()

        if not job_description:
            flash("Please paste the job description first.")
        else:
            technical_skills = load_json_field(existing["technical_skills_json"], [])
            soft_skills = load_json_field(existing["soft_skills_json"], [])
            projects = load_json_field(existing["projects_json"], [])

            profile_summary = {
                "name": existing["full_name"],
                "career_objective": existing["career_objective"],
                "experience_type": existing["experience_type"],
                "exp_job_role": existing["exp_job_role"],
                "technical_skills": technical_skills,
                "soft_skills": soft_skills,
                "projects": [p.get("title") for p in projects if p.get("title")],
            }

            result, error = generate_auto_apply_content(profile_summary, job_title, company, job_description)
            if error:
                flash(error)

    return render_template(
        "auto_apply.html",
        result=result,
        job_title=job_title,
        company=company,
        job_description=job_description,
        gemini_enabled=bool(GEMINI_API_KEY),
    )


@app.route("/extension", methods=["GET", "POST"])
def extension_setup():
    """Shows the personal API token used by the SmartApply browser extension
    to fetch this user's profile data for auto-filling job application
    forms. POST regenerates the token (invalidating the old one)."""
    if "user_id" not in session:
        flash("Please log in to continue.")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row

    if request.method == "POST":
        new_token = secrets.token_hex(24)
        conn.execute("UPDATE users SET api_token = ? WHERE id = ?", (new_token, user_id))
        conn.commit()
        flash("New extension token generated. Update it in the extension popup.")

    user = conn.execute("SELECT api_token FROM users WHERE id = ?", (user_id,)).fetchone()
    token = user["api_token"] if user else None

    if not token:
        token = secrets.token_hex(24)
        conn.execute("UPDATE users SET api_token = ? WHERE id = ?", (token, user_id))
        conn.commit()

    conn.close()
    return render_template("extension_setup.html", token=token)


@app.route("/security")
def security_info():
    if "user_id" not in session:
        flash("Please log in to continue.")
        return redirect(url_for("login"))
    return render_template("security.html")


@app.route("/api/profile-data", methods=["GET", "OPTIONS"])
def api_profile_data():
    if request.method == "OPTIONS":
        resp = app.response_class(status=204)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        return resp
    """Read-only API for the browser extension. Authenticated via a bearer
    token (not the session cookie), since this is called from content
    scripts running on third-party job sites."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else ""

    if not token:
        response = {"error": "Missing API token"}
        resp = app.response_class(json.dumps(response), status=401, mimetype="application/json")
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp

    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT id, full_name, email FROM users WHERE api_token = ?", (token,)).fetchone()

    if not user:
        conn.close()
        resp = app.response_class(json.dumps({"error": "Invalid API token"}), status=401, mimetype="application/json")
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp

    profile = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user["id"],)).fetchone()
    conn.close()

    if not profile:
        payload = {
            "full_name": user["full_name"], "email": user["email"],
            "mobile_number": "", "alt_mobile_number": "", "alt_email": "",
            "perm_house_no": "", "perm_street": "", "perm_area": "", "perm_city": "",
            "perm_district": "", "perm_state": "", "perm_country": "", "perm_pincode": "",
            "dob": "", "gender": "", "nationality": "",
            "linkedin": "", "github": "", "portfolio": "",
            "career_objective": "", "exp_job_role": "", "exp_company_name": "",
            "exp_total_experience": "", "technical_skills": [],
        }
    else:
        social = load_json_field(profile["social_json"], {})
        payload = {
            "full_name": profile["full_name"] or user["full_name"],
            "email": profile["email"] or user["email"],
            "mobile_number": profile["mobile_number"] or "",
            "alt_mobile_number": profile["alt_mobile_number"] or "",
            "alt_email": profile["alt_email"] or "",
            "perm_house_no": profile["perm_house_no"] or "",
            "perm_street": profile["perm_street"] or "",
            "perm_area": profile["perm_area"] or "",
            "perm_city": profile["perm_city"] or "",
            "perm_district": profile["perm_district"] or "",
            "perm_state": profile["perm_state"] or "",
            "perm_country": profile["perm_country"] or "",
            "perm_pincode": profile["perm_pincode"] or "",
            "dob": profile["dob"] or "",
            "gender": profile["gender"] or "",
            "nationality": profile["nationality"] or "",
            "linkedin": social.get("linkedin", ""),
            "github": social.get("github", ""),
            "portfolio": social.get("portfolio", ""),
            "career_objective": profile["career_objective"] or "",
            "exp_job_role": profile["exp_job_role"] or "",
            "exp_company_name": profile["exp_company_name"] or "",
            "exp_total_experience": profile["exp_total_experience"] or "",
            "technical_skills": load_json_field(profile["technical_skills_json"], []),
        }

    resp = app.response_class(json.dumps(payload), status=200, mimetype="application/json")
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))


@app.route("/reset-local-db")
def reset_local_db_route():
    if not ALLOW_LOCAL_DB_RESET:
        return "Not found", 404
    reset_local_db()
    flash("Local database reset successfully. You can register again.")
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        mobile_number = request.form.get("mobile_number", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not full_name or not email or not mobile_number or not password or not confirm:
            flash("Please fill in all fields.")
            return render_template("register.html", google_enabled=GOOGLE_ENABLED)

        if password != confirm:
            flash("Passwords do not match.")
            return render_template("register.html", google_enabled=GOOGLE_ENABLED)

        if not is_valid_indian_mobile_number(mobile_number):
            flash("Please enter a valid 10-digit mobile number.")
            return render_template("register.html", google_enabled=GOOGLE_ENABLED)

        normalized_mobile = normalize_mobile_number(mobile_number)

        conn = sqlite3.connect(app.config["DATABASE_PATH"])
        conn.row_factory = sqlite3.Row
        existing_user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        existing_mobile = conn.execute(
            "SELECT id FROM users WHERE mobile_number = ?",
            (normalized_mobile,),
        ).fetchone()

        if existing_user:
            conn.close()
            flash("An account with this email already exists.")
            return render_template("register.html", google_enabled=GOOGLE_ENABLED)

        if existing_mobile:
            conn.close()
            flash("An account with this mobile number already exists.")
            return render_template("register.html", google_enabled=GOOGLE_ENABLED)

        try:
            conn.execute(
                "INSERT INTO users (full_name, email, password, mobile_number, auth_provider) VALUES (?, ?, ?, ?, 'local')",
                (full_name, email, generate_password_hash(password), normalized_mobile),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            flash("An account with this email or mobile number already exists.")
            return render_template("register.html", google_enabled=GOOGLE_ENABLED)
        except Exception as exc:
            conn.close()
            print(f"[REGISTER ERROR] {exc}")
            flash("Something went wrong while creating your account. Please try again.")
            return render_template("register.html", google_enabled=GOOGLE_ENABLED)
        finally:
            conn.close()

        flash("Account created successfully. Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html", google_enabled=GOOGLE_ENABLED)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember")

        if not email or not password:
            flash("Please enter both email and password.")
            return render_template("login.html", google_enabled=GOOGLE_ENABLED)

        conn = sqlite3.connect(app.config["DATABASE_PATH"])
        conn.row_factory = sqlite3.Row
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["full_name"]
            session.permanent = bool(remember)

            flash(f"Welcome back, {user['full_name']}!")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.")
        return render_template("login.html", google_enabled=GOOGLE_ENABLED)

    return render_template("login.html", google_enabled=GOOGLE_ENABLED)


@app.route("/auth/google/login")
def google_login():
    if not GOOGLE_ENABLED:
        flash("Google Login is coming soon.")
        return redirect(url_for("login"))

    if GOOGLE_DEMO_MODE:
        user = get_or_create_google_demo_user()
        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["full_name"]
        flash(f"Welcome, {user['full_name']}!")
        return redirect(url_for("dashboard"))

    if oauth is None:
        flash("Google login is not configured on this server.")
        return redirect(url_for("login"))

    redirect_uri = GOOGLE_REDIRECT_URI or request.url_root.strip("/") + url_for("google_callback")
    return oauth.google.authorize_redirect(
        redirect_uri,
        prompt="consent",
        access_type="offline",
        include_granted_scopes="false",
    )


@app.route("/auth/google/callback")
def google_callback():
    if GOOGLE_DEMO_MODE:
        user = get_or_create_google_demo_user()
        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["full_name"]
        flash(f"Welcome, {user['full_name']}!")
        return redirect(url_for("dashboard"))

    if not GOOGLE_ENABLED or oauth is None:
        flash("Google login is not configured on this server.")
        return redirect(url_for("login"))

    token = oauth.google.authorize_access_token()
    user_info = token.get("userinfo")
    if not user_info:
        flash("Google login failed. Please try again.")
        return redirect(url_for("login"))

    email = (user_info.get("email") or "").strip().lower()
    full_name = user_info.get("name") or email.split("@")[0]

    if not email:
        flash("Google did not share an email address. Please try again.")
        return redirect(url_for("login"))

    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if not user:
        random_password = generate_password_hash(os.urandom(16).hex())
        conn.execute(
            "INSERT INTO users (full_name, email, password, mobile_number, auth_provider) VALUES (?, ?, ?, NULL, 'google')",
            (full_name, email, random_password),
        )
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    conn.close()

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["full_name"]

    flash(f"Welcome, {user['full_name']}!")
    return redirect(url_for("dashboard"))


@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        step = request.form.get("step", "send")
        email = request.form.get("email", "").strip().lower()

        if step == "send":
            if not email:
                flash("Please enter your email.")
                return render_template("forgot_password.html", otp_sent=False, email="")

            conn = sqlite3.connect(app.config["DATABASE_PATH"])
            conn.row_factory = sqlite3.Row
            user = conn.execute("SELECT email, mobile_number FROM users WHERE email = ?", (email,)).fetchone()
            conn.close()

            if not user:
                flash("No account was found with that email.")
                return render_template("forgot_password.html", otp_sent=False, email=email)

            otp_code = f"{random.randint(100000, 999999)}"
            session["otp_code"] = otp_code
            session["otp_email"] = user["email"]
            session["otp_mobile"] = user["mobile_number"] or ""

            channel, sent = send_otp_to_user(user["email"], user["mobile_number"], otp_code)

            if channel == "mobile":
                flash("OTP sent successfully to your registered mobile number.")
            elif channel == "email":
                flash("OTP sent to your registered email address.")
            else:
                flash("We couldn't send the OTP right now. Please try again shortly.")

            return render_template(
                "forgot_password.html",
                otp_sent=True,
                email=user["email"],
                masked_mobile=mask_mobile_number(user["mobile_number"]),
            )

        otp_code = request.form.get("otp", "").strip()
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not otp_code or not new_password or not confirm_password:
            flash("Please fill in all fields.")
            return render_template(
                "forgot_password.html",
                otp_sent=True,
                email=session.get("otp_email", ""),
                masked_mobile=mask_mobile_number(session.get("otp_mobile", "")),
            )

        if otp_code != session.get("otp_code"):
            flash("Invalid OTP. Please try again.")
            return render_template(
                "forgot_password.html",
                otp_sent=True,
                email=session.get("otp_email", ""),
                masked_mobile=mask_mobile_number(session.get("otp_mobile", "")),
            )

        if new_password != confirm_password:
            flash("Passwords do not match.")
            return render_template(
                "forgot_password.html",
                otp_sent=True,
                email=session.get("otp_email", ""),
                masked_mobile=mask_mobile_number(session.get("otp_mobile", "")),
            )

        conn = sqlite3.connect(app.config["DATABASE_PATH"])
        conn.execute(
            "UPDATE users SET password = ? WHERE email = ?",
            (generate_password_hash(new_password), session.get("otp_email")),
        )
        conn.commit()
        conn.close()

        session.pop("otp_code", None)
        session.pop("otp_email", None)
        session.pop("otp_mobile", None)

        flash("Password reset successful. Please log in with your new password.")
        return redirect(url_for("login"))

    return render_template("forgot_password.html", otp_sent=False, email="")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}
    app.run(host="0.0.0.0", port=port, debug=debug)