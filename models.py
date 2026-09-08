from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP


db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(Integer, primary_key=True)
    full_name = db.Column(Text, nullable=False)
    email = db.Column(Text, nullable=False, unique=True)
    password = db.Column(Text, nullable=False)
    mobile_number = db.Column(Text)
    auth_provider = db.Column(Text, server_default="local")
    api_token = db.Column(Text)
    created_at = db.Column(TIMESTAMP(timezone=False), server_default=db.text("CURRENT_TIMESTAMP"))


class Profile(db.Model):
    __tablename__ = "profiles"

    user_id = db.Column(Integer, ForeignKey("users.id"), primary_key=True)
    full_name = db.Column(Text)
    photo_path = db.Column(Text)
    gender = db.Column(Text)
    dob = db.Column(Text)
    age = db.Column(Text)
    nationality = db.Column(Text)
    marital_status = db.Column(Text)
    blood_group = db.Column(Text)
    aadhaar_number = db.Column(Text)
    pan_number = db.Column(Text)
    mobile_number = db.Column(Text)
    alt_mobile_number = db.Column(Text)
    email = db.Column(Text)
    alt_email = db.Column(Text)
    perm_house_no = db.Column(Text)
    perm_street = db.Column(Text)
    perm_area = db.Column(Text)
    perm_city = db.Column(Text)
    perm_district = db.Column(Text)
    perm_state = db.Column(Text)
    perm_country = db.Column(Text)
    perm_pincode = db.Column(Text)
    same_as_permanent = db.Column(Integer, server_default="0")
    curr_house_no = db.Column(Text)
    curr_street = db.Column(Text)
    curr_area = db.Column(Text)
    curr_city = db.Column(Text)
    curr_district = db.Column(Text)
    curr_state = db.Column(Text)
    curr_country = db.Column(Text)
    curr_pincode = db.Column(Text)
    career_objective = db.Column(Text)
    education_json = db.Column(Text)
    technical_skills_json = db.Column(Text)
    soft_skills_json = db.Column(Text)
    experience_type = db.Column(Text)
    exp_company_name = db.Column(Text)
    exp_job_role = db.Column(Text)
    exp_start_date = db.Column(Text)
    exp_end_date = db.Column(Text)
    exp_total_experience = db.Column(Text)
    exp_responsibilities = db.Column(Text)
    internship_json = db.Column(Text)
    projects_json = db.Column(Text)
    certifications_json = db.Column(Text)
    achievements_json = db.Column(Text)
    languages_json = db.Column(Text)
    social_json = db.Column(Text)
    job_pref_json = db.Column(Text)
    documents_json = db.Column(Text)
    hobbies = db.Column(Text)
    interests = db.Column(Text)
    references_json = db.Column(Text)
    declaration = db.Column(Integer, server_default="0")
    security_question = db.Column(Text)
    security_answer = db.Column(Text)
    profile_completion = db.Column(Integer, server_default="0")
    created_at = db.Column(TIMESTAMP(timezone=False), server_default=db.text("CURRENT_TIMESTAMP"))
    updated_at = db.Column(TIMESTAMP(timezone=False), server_default=db.text("CURRENT_TIMESTAMP"))


class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, nullable=False)
    job_title = db.Column(Text, nullable=False)
    company = db.Column(Text, nullable=False)
    status = db.Column(Text, nullable=False, server_default="applied")
    applied_date = db.Column(Text, nullable=False)
    notes = db.Column(Text)
    created_at = db.Column(Text, server_default=db.text("CURRENT_TIMESTAMP"))
