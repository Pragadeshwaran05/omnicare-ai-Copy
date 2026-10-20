from services.doctor_ai_assistant import ask_doctor_ai
from services.medical_document_processor import process_medical_document
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client
from dotenv import load_dotenv
from utils.supabase_client import supabase
from services.medical_conflict_detector import detect_medical_conflicts
from services.health_trend_analyzer import get_trend_analysis_data
import os
import qrcode
import io
import base64

import uuid
import secrets
# ---------------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# ---------------------------------------------------------

load_dotenv()


# ---------------------------------------------------------
# FLASK APP
# ---------------------------------------------------------

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "temporary-development-secret"
)

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
print("URL loaded:", bool(SUPABASE_URL))
print("KEY loaded:", bool(SUPABASE_KEY))
# Normal Supabase client
supabase_admin: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# Admin / service-role client

# ---------------------------------------------------------
# HOME
# ---------------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------------------------------------------------
# PATIENT REGISTER
# ---------------------------------------------------------

@app.route("/patient/register", methods=["GET", "POST"])
def patient_register():

    if request.method == "POST":

        # Get form data
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        date_of_birth = request.form.get("date_of_birth", "")
        blood_group = request.form.get("blood_group", "")
        gender = request.form.get("gender", "")
        address = request.form.get("address", "").strip()

        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")


        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not all([
            full_name,
            email,
            phone,
            date_of_birth,
            blood_group,
            gender,
            address,
            password,
            confirm_password
        ]):
            flash(
                "Please fill in all required fields.",
                "error"
            )

            return render_template(
                "auth/patient_register.html"
            )


        # Check password
        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return render_template(
                "auth/patient_register.html"
            )


        # Minimum password length
        if len(password) < 6:

            flash(
                "Password must contain at least 6 characters.",
                "error"
            )

            return render_template(
                "auth/patient_register.html"
            )


        # -------------------------------------------------
        # CHECK WHETHER EMAIL ALREADY EXISTS
        # -------------------------------------------------

        try:

            existing_patient = (
                supabase
                .table("patients")
                .select("id")
                .eq("email", email)
                .execute()
            )


            if existing_patient.data:

                flash(
                    "An account with this email already exists.",
                    "error"
                )

                return render_template(
                    "auth/patient_register.html"
                )


        except Exception as e:

            print("Email check error:", e)

            flash(
                "Unable to check your account. Please try again.",
                "error"
            )

            return render_template(
                "auth/patient_register.html"
            )


        # -------------------------------------------------
        # HASH PASSWORD
        # -------------------------------------------------

        password_hash = generate_password_hash(password)


        # -------------------------------------------------
        # INSERT PATIENT
        # -------------------------------------------------

        patient_data = {

            "full_name": full_name,

            "email": email,

            "phone": phone,

            "date_of_birth": date_of_birth,

            "blood_group": blood_group,

            "gender": gender,

            "address": address,

            "password_hash": password_hash
        }


        try:

            response = (
                supabase
                .table("patients")
                .insert(patient_data)
                .execute()
            )


            if response.data:

                flash(
                    "Registration successful! Please login.",
                    "success"
                )

                return redirect(
                    url_for("patient_login")
                )


            flash(
                "Registration failed. Please try again.",
                "error"
            )

            return render_template(
                "auth/patient_register.html"
            )


        except Exception as e:

            print("Registration error:", e)

            flash(
                "Something went wrong while creating your account.",
                "error"
            )

            return render_template(
                "auth/patient_register.html"
            )


    # GET request
    return render_template(
        "auth/patient_register.html"
    )


# ---------------------------------------------------------
# PATIENT LOGIN
# ---------------------------------------------------------

@app.route("/patient/login", methods=["GET", "POST"])
def patient_login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )


        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not email or not password:

            flash(
                "Please enter your email and password.",
                "error"
            )

            return render_template(
                "auth/patient_login.html"
            )


        # -------------------------------------------------
        # FIND PATIENT
        # -------------------------------------------------

        try:

            response = (
                supabase
                .table("patients")
                .select("*")
                .eq("email", email)
                .limit(1)
                .execute()
            )


            if not response.data:

                flash(
                    "Invalid email or password.",
                    "error"
                )

                return render_template(
                    "auth/patient_login.html"
                )


            patient = response.data[0]


        except Exception as e:

            print("Login database error:", e)

            flash(
                "Unable to login right now. Please try again.",
                "error"
            )

            return render_template(
                "auth/patient_login.html"
            )


        # -------------------------------------------------
        # CHECK PASSWORD
        # -------------------------------------------------

        if not check_password_hash(
            patient["password_hash"],
            password
        ):

            flash(
                "Invalid email or password.",
                "error"
            )

            return render_template(
                "auth/patient_login.html"
            )


        # -------------------------------------------------
        # CREATE SESSION
        # -------------------------------------------------

        session["patient_id"] = patient["id"]

        session["patient_name"] = patient["full_name"]

        session["patient_email"] = patient["email"]


        flash(
            "Login successful!",
            "success"
        )


        return redirect(
            url_for("patient_dashboard")
        )


    # GET request
    return render_template(
        "auth/patient_login.html"
    )


# ---------------------------------------------------------
# PATIENT DASHBOARD
# ---------------------------------------------------------

@app.route("/patient/dashboard")
def patient_dashboard():

    # Check login
    if "patient_id" not in session:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("patient_login")
        )


    # Get current patient
    try:

        response = (
            supabase
            .table("patients")
            .select(
                "id, full_name, email, phone, "
                "date_of_birth, blood_group, "
                "gender, address, created_at"
            )
            .eq("id", session["patient_id"])
            .limit(1)
            .execute()
        )


        if not response.data:

            session.clear()

            flash(
                "Patient account not found.",
                "error"
            )

            return redirect(
                url_for("patient_login")
            )


        patient = response.data[0]


    except Exception as e:

        print("Dashboard error:", e)

        flash(
            "Unable to load your profile.",
            "error"
        )

        return redirect(
            url_for("patient_login")
        )


    return render_template(
        "patient/dashboard.html",
        patient=patient
    )


# ---------------------------------------------------------
# PATIENT LOGOUT
# ---------------------------------------------------------

@app.route("/patient/logout")
def patient_logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("home")
    )

# ==========================================
# PATIENT PAGES
# ==========================================



@app.route("/patient/access-requests")
def patient_access_requests():

    if "patient_id" not in session:
        flash("Please login to access your account.", "error")
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    try:

        # =====================================================
        # 1. GET ACCESS REQUESTS FOR THIS PATIENT
        # =====================================================

        response = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("patient_id", patient_id)
            .order("requested_at", desc=True)
            .execute()
        )

        access_requests = response.data or []

        # =====================================================
        # 2. GET ALL DOCTOR IDs
        # =====================================================

        doctor_ids = list({
            access.get("doctor_id")
            for access in access_requests
            if access.get("doctor_id")
        })

        doctors_map = {}

        # =====================================================
        # 3. GET DOCTOR DETAILS
        # =====================================================

        if doctor_ids:

            doctor_response = (
                supabase_admin
                .table("doctors")
                .select("*")
                .in_("id", doctor_ids)
                .execute()
            )

            for doctor in doctor_response.data or []:
                doctors_map[str(doctor["id"])] = doctor

        # =====================================================
        # 4. ADD DOCTOR / HOSPITAL INFORMATION
        # =====================================================

        for access in access_requests:

            doctor = doctors_map.get(
                str(access.get("doctor_id"))
            )

            if doctor:

                # Doctor name
                access["doctor_name"] = (
                    doctor.get("full_name")
                    or doctor.get("name")
                    or doctor.get("doctor_name")
                    or "Doctor"
                )

                # Hospital name
                access["hospital_name"] = (
                    doctor.get("hospital_name")
                    or doctor.get("hospital")
                    or doctor.get("clinic_name")
                    or "Not provided"
                )

                # Hospital address
                access["hospital_address"] = (
                    doctor.get("hospital_address")
                    or doctor.get("address")
                    or doctor.get("clinic_address")
                    or "Not provided"
                )

            else:

                access["doctor_name"] = "Doctor"
                access["hospital_name"] = "Not provided"
                access["hospital_address"] = "Not provided"

            # =================================================
            # 5. FORMAT REQUESTED DATE
            # =================================================

            requested_at = access.get("requested_at")

            if requested_at:

                try:

                    from datetime import datetime

                    dt = datetime.fromisoformat(
                        requested_at.replace("Z", "+00:00")
                    )

                    access["requested_at_display"] = dt.strftime(
                        "%d %b %Y, %I:%M %p"
                    )

                except Exception:

                    access["requested_at_display"] = requested_at

            else:

                access["requested_at_display"] = "Not available"

            # =================================================
            # 6. FORMAT APPROVED DATE
            # =================================================

            approved_at = access.get("approved_at")

            if approved_at:

                try:

                    from datetime import datetime

                    dt = datetime.fromisoformat(
                        approved_at.replace("Z", "+00:00")
                    )

                    access["approved_at_display"] = dt.strftime(
                        "%d %b %Y, %I:%M %p"
                    )

                except Exception:

                    access["approved_at_display"] = approved_at

            else:

                access["approved_at_display"] = None

            # =================================================
            # 7. FORMAT EXPIRY DATE
            # =================================================

            expires_at = access.get("expires_at")

            if expires_at:

                try:

                    from datetime import datetime

                    dt = datetime.fromisoformat(
                        expires_at.replace("Z", "+00:00")
                    )

                    access["expires_at_display"] = dt.strftime(
                        "%d %b %Y, %I:%M %p"
                    )

                except Exception:

                    access["expires_at_display"] = expires_at

            else:

                access["expires_at_display"] = None

        # =====================================================
        # DEBUG
        # =====================================================

        print("=" * 70)
        print("PATIENT ACCESS REQUESTS")
        print("=" * 70)
        print("Patient ID:", patient_id)
        print("Total Requests:", len(access_requests))

        for access in access_requests:

            print(
                "Doctor:",
                access.get("doctor_name")
            )

            print(
                "Hospital:",
                access.get("hospital_name")
            )

            print(
                "Address:",
                access.get("hospital_address")
            )

            print(
                "Status:",
                access.get("status")
            )

            print(
                "Access Type:",
                access.get("access_type")
            )

            print("-" * 70)

        # =====================================================
        # 8. SEND DATA TO TEMPLATE
        # =====================================================

        return render_template(
            "patient/access_requests.html",
            access_requests=access_requests
        )

    except Exception as e:

        print("=" * 70)
        print("PATIENT ACCESS REQUESTS ERROR")
        print("=" * 70)
        print("Patient ID:", patient_id)
        print("Error:", repr(e))
        print("=" * 70)

        return render_template(
            "patient/access_requests.html",
            access_requests=[],
            error="Unable to load access requests."
        )
@app.route("/patient/approve-access/<request_id>", methods=["POST"])
def patient_approve_access(request_id):

    if "patient_id" not in session:
        flash("Please login to continue.", "error")
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    # Get selected access type
    access_type = request.form.get("access_type", "temporary").strip().lower()

    # Allow only these values
    allowed_types = {
        "one_time",
        "temporary",
        "permanent"
    }

    if access_type not in allowed_types:
        flash("Invalid access type selected.", "error")
        return redirect(url_for("patient_access_requests"))

    try:

        # -----------------------------------------------------
        # 1. CHECK REQUEST BELONGS TO THIS PATIENT
        # -----------------------------------------------------

        existing = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("id", request_id)
            .eq("patient_id", patient_id)
            .eq("status", "pending")
            .execute()
        )

        if not existing.data:
            flash(
                "Access request not found.",
                "error"
            )
            return redirect(
                url_for("patient_access_requests")
            )

        # -----------------------------------------------------
        # 2. CURRENT TIME
        # -----------------------------------------------------

        now = datetime.now(timezone.utc)

        # -----------------------------------------------------
        # 3. SET EXPIRATION
        # -----------------------------------------------------

        expires_at = None

        if access_type == "temporary":

            # Temporary access = 4 hours
            expires_at = (
                now + timedelta(hours=4)
            ).isoformat()

        elif access_type == "one_time":

            # One-time access
            # No fixed time expiration.
            # It will be revoked after the consultation/action
            # is completed.
            expires_at = None

        elif access_type == "permanent":

            # Permanent access
            # No expiration unless patient revokes it.
            expires_at = None

        # -----------------------------------------------------
        # 4. UPDATE ACCESS REQUEST
        # -----------------------------------------------------

        update_data = {
            "status": "active",
            "access_type": access_type,
            "approved_at": now.isoformat(),
            "expires_at": expires_at
        }

        response = (
            supabase_admin
            .table("access_requests")
            .update(update_data)
            .eq("id", request_id)
            .eq("patient_id", patient_id)
            .execute()
        )

        # -----------------------------------------------------
        # 5. SUCCESS MESSAGE
        # -----------------------------------------------------

        if access_type == "temporary":

            flash(
                "Access granted for 4 hours.",
                "success"
            )

        elif access_type == "one_time":

            flash(
                "One-time access granted to the doctor.",
                "success"
            )

        elif access_type == "permanent":

            flash(
                "Permanent access granted to the doctor.",
                "success"
            )

    except Exception as e:

        print("=" * 70)
        print("APPROVE ACCESS ERROR")
        print("=" * 70)
        print("Patient ID:", patient_id)
        print("Request ID:", request_id)
        print("Access Type:", access_type)
        print("Error:", repr(e))
        print("=" * 70)

        flash(
            "Unable to approve the access request.",
            "error"
        )

    return redirect(
        url_for("patient_access_requests")
    )
@app.route("/patient/reject-access/<request_id>", methods=["POST"])
def patient_reject_access(request_id):

    if "patient_id" not in session:
        flash("Please login to continue.", "error")
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    try:
        # Make sure this request belongs to the logged-in patient
        existing = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("id", request_id)
            .eq("patient_id", patient_id)
            .eq("status", "pending")
            .execute()
        )

        if not existing.data:
            flash("Access request not found.", "error")
            return redirect(url_for("patient_access_requests"))

        # Reject the request
        response = (
            supabase_admin
            .table("access_requests")
            .update({
                "status": "rejected"
            })
            .eq("id", request_id)
            .eq("patient_id", patient_id)
            .execute()
        )

        flash(
            "Access request rejected.",
            "success"
        )

    except Exception as e:
        print("REJECT ACCESS ERROR:", repr(e))

        flash(
            "Unable to reject the access request.",
            "error"
        )

    return redirect(url_for("patient_access_requests"))

@app.route("/patient/revoke-access/<request_id>", methods=["POST"])
def patient_revoke_access(request_id):

    if "patient_id" not in session:
        flash("Please login to continue.", "error")
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    try:

        # ---------------------------------------------------------
        # Verify that this access request belongs to this patient
        # and is currently active
        # ---------------------------------------------------------

        existing = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("id", request_id)
            .eq("patient_id", patient_id)
            .eq("status", "active")
            .execute()
        )

        if not existing.data:

            flash(
                "Active access request not found.",
                "error"
            )

            return redirect(
                url_for("patient_doctor_access")
            )


        # ---------------------------------------------------------
        # Revoke access
        # ---------------------------------------------------------

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        (
            supabase_admin
            .table("access_requests")
            .update({
                "status": "revoked",
                "revoked_at": now.isoformat()
            })
            .eq("id", request_id)
            .eq("patient_id", patient_id)
            .execute()
        )


        flash(
            "Doctor access has been revoked successfully.",
            "success"
        )


    except Exception as e:

        print("=" * 60)
        print("REVOKE ACCESS ERROR")
        print("=" * 60)
        print("Patient ID:", patient_id)
        print("Request ID:", request_id)
        print("Error:", repr(e))
        print("=" * 60)

        flash(
            "Unable to revoke doctor access.",
            "error"
        )


    return redirect(
        url_for("patient_doctor_access")
    )
# ==========================================
# PATIENT - HEALTH TIMELINE
# ==========================================

@app.route("/patient/health-timeline")
def health_timeline():

    # Require patient login
    if "patient_id" not in session:
        flash("Please login to view your health timeline.", "error")
        return redirect(url_for("patient_login"))

    # Always use the logged-in patient's ID
    patient_id = session["patient_id"]

    try:
        response = (
            supabase_admin
            .table("health_timeline_events")
            .select(
                "id, patient_id, medical_record_id, event_date, "
                "event_type, provider_name, hospital_name, "
                "diagnosis, clinical_findings, investigations, "
                "medications, follow_up, clinical_summary, "
                "ai_processed"
            )
            .eq("patient_id", patient_id)
            .order("event_date", desc=True)
            .execute()
        )

        timeline_events = response.data or []

        return render_template(
            "patient/patient_health_timeline.html",
            timeline_events=timeline_events
        )

    except Exception as e:
        print("PATIENT HEALTH TIMELINE ERROR:", str(e))

        flash(
            "Unable to load your health timeline. Please try again.",
            "error"
        )

        return render_template(
            "patient/patient_health_timeline.html",
            timeline_events=[],
            timeline_error=True
        )

@app.route("/patient/doctor-access")
def patient_doctor_access():

    if "patient_id" not in session:
        flash("Please login to continue.", "error")
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    try:

        # =====================================================
        # 1. GET ACCESS REQUESTS
        # =====================================================

        response = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("patient_id", patient_id)
            .order("requested_at", desc=True)
            .execute()
        )

        access_requests = response.data or []

        print("\n" + "=" * 70)
        print("PATIENT ACCESS REQUESTS")
        print("=" * 70)
        print("Patient ID:", patient_id)
        print("Access Requests:")
        print(access_requests)


        # =====================================================
        # 2. GET DOCTOR IDS
        # =====================================================

        doctor_ids = []

        for access in access_requests:

            doctor_id = access.get("doctor_id")

            if doctor_id:
                doctor_ids.append(str(doctor_id))

        doctor_ids = list(set(doctor_ids))

        print("Doctor IDs:", doctor_ids)


        # =====================================================
        # 3. GET DOCTORS
        # =====================================================

        doctors_map = {}

        if doctor_ids:

            # First try normal "id" column
            doctor_response = (
                supabase_admin
                .table("doctors")
                .select("*")
                .in_("id", doctor_ids)
                .execute()
            )

            doctors = doctor_response.data or []

            print("Doctors found using id:", doctors)

            for doctor in doctors:

                doctor_id = doctor.get("id")

                if doctor_id:
                    doctors_map[str(doctor_id)] = doctor


        # =====================================================
        # 4. ADD DISPLAY INFORMATION
        # =====================================================

        for access in access_requests:

            doctor_id = access.get("doctor_id")

            doctor = doctors_map.get(
                str(doctor_id)
            )


            # -------------------------------------------------
            # DEFAULT VALUES
            # -------------------------------------------------

            access["doctor_name"] = "Doctor"
            access["hospital_name"] = "Not provided"
            access["hospital_address"] = "Not provided"


            # -------------------------------------------------
            # DOCTOR FOUND
            # -------------------------------------------------

            if doctor:

                access["doctor_name"] = (
                    doctor.get("full_name")
                    or doctor.get("doctor_name")
                    or doctor.get("name")
                    or "Doctor"
                )

                access["hospital_name"] = (
                    doctor.get("hospital_name")
                    or doctor.get("hospital")
                    or doctor.get("clinic_name")
                    or "Not provided"
                )

                access["hospital_address"] = (
                    doctor.get("hospital_address")
                    or doctor.get("address")
                    or doctor.get("clinic_address")
                    or "Not provided"
                )


            # =================================================
            # 5. REQUESTED DATE
            # =================================================

            requested_at = access.get("requested_at")

            print("Requested At:", requested_at)

            if requested_at:

                try:

                    dt = datetime.fromisoformat(
                        str(requested_at).replace(
                            "Z",
                            "+00:00"
                        )
                    )

                    access["requested_at_display"] = dt.strftime(
                        "%d %b %Y, %I:%M %p"
                    )

                except Exception as date_error:

                    print(
                        "DATE FORMAT ERROR:",
                        repr(date_error)
                    )

                    access["requested_at_display"] = str(
                        requested_at
                    )

            else:

                access["requested_at_display"] = "Not available"


            # =================================================
            # 6. DEBUG
            # =================================================

            print("----------------------------------------")
            print("Request ID:", access.get("id"))
            print("Doctor ID:", access.get("doctor_id"))
            print("Doctor Name:", access.get("doctor_name"))
            print("Hospital:", access.get("hospital_name"))
            print(
                "Hospital Address:",
                access.get("hospital_address")
            )
            print(
                "Requested:",
                access.get("requested_at_display")
            )
            print("Status:", access.get("status"))
            print(
                "Access Type:",
                access.get("access_type")
            )


        print("=" * 70)


        # =====================================================
        # 7. RENDER
        # =====================================================

        return render_template(
            "patient/access_requests.html",
            access_requests=access_requests
        )


    except Exception as e:

        print("\n" + "=" * 70)
        print("PATIENT DOCTOR ACCESS ERROR")
        print("=" * 70)
        print("Patient ID:", patient_id)
        print("Error:", repr(e))
        print("=" * 70)

        return render_template(
            "patient/access_requests.html",
            access_requests=[],
            error="Unable to load access requests."
        )


from datetime import date

from datetime import date


@app.route("/patient/profile", methods=["GET", "POST"])
def patient_profile():

    # 1. Require patient login
    if "patient_id" not in session:
        flash("Please login to access your profile.", "error")
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    try:
        # 2. Load this patient's existing personal information
        patient_response = (
            supabase_admin
            .table("patients")
            .select("*")
            .eq("id", patient_id)
            .limit(1)
            .execute()
        )

        if not patient_response.data:
            flash("Patient account not found.", "error")
            return redirect(url_for("patient_login"))

        patient = patient_response.data[0]

        # 3. Load this patient's emergency profile
        emergency_response = (
            supabase_admin
            .table("patient_emergency_profiles")
            .select("*")
            .eq("patient_id", patient_id)
            .limit(1)
            .execute()
        )

        emergency_profile = (
            emergency_response.data[0]
            if emergency_response.data
            else {}
        )

        if request.method == "POST":

            # 4. Validate personal details
            full_name = request.form.get("name", "").strip()
            dob = request.form.get("date_of_birth", "").strip()
            gender = request.form.get("gender", "").strip()
            blood_group = request.form.get("blood_group", "").strip()
            phone = request.form.get("phone", "").strip()
            email = request.form.get("email", "").strip().lower()
            address = request.form.get("address", "").strip()

            if not full_name:
                flash("Full name is required.", "error")
                return redirect(url_for("patient_profile"))

            if dob:
                try:
                    parsed_dob = date.fromisoformat(dob)
                    if parsed_dob > date.today():
                        raise ValueError
                except ValueError:
                    flash("Enter a valid date of birth.", "error")
                    return redirect(url_for("patient_profile"))

            # 5. Update existing patients table
            personal_data = {
                "full_name": full_name,
                "date_of_birth": dob or None,
                "gender": gender or None,
                "blood_group": blood_group or None,
                "phone": phone or None,
                "email": email or None,
                "address": address or None
            }

            # 6. Collect emergency and medical information
            def form_text(field_name):
                return request.form.get(field_name, "").strip() or None

            height_text = form_text("height_cm")
            weight_text = form_text("weight_kg")

            try:
                height_cm = float(height_text) if height_text else None
                weight_kg = float(weight_text) if weight_text else None

                if height_cm is not None and not 1 <= height_cm <= 300:
                    raise ValueError("Height must be between 1 and 300 cm.")

                if weight_kg is not None and not 1 <= weight_kg <= 700:
                    raise ValueError("Weight must be between 1 and 700 kg.")

            except ValueError:
                flash("Enter valid height and weight values.", "error")
                return redirect(url_for("patient_profile"))

            emergency_data = {
                "patient_id": patient_id,
                "height_cm": height_cm,
                "weight_kg": weight_kg,
                "allergies": form_text("allergies"),
                "chronic_conditions": form_text("chronic_conditions"),
                "current_medications": form_text("current_medications"),
                "emergency_contact_name": form_text("emergency_contact_name"),
                "emergency_relationship": form_text("emergency_relationship"),
                "emergency_contact_phone": form_text("emergency_contact_phone"),
                "alternate_contact_phone": form_text("alternate_contact_phone"),
                "emergency_address": form_text("emergency_address"),
                "emergency_notes": form_text("emergency_notes"),
                "updated_at": date.today().isoformat()
            }

            try:
                # Update only the logged-in patient's row.
                (
                    supabase_admin
                    .table("patients")
                    .update(personal_data)
                    .eq("id", patient_id)
                    .execute()
                )

                # Insert or update this patient's emergency profile.
                (
                    supabase_admin
                    .table("patient_emergency_profiles")
                    .upsert(
                        emergency_data,
                        on_conflict="patient_id"
                    )
                    .execute()
                )

                flash("Profile and emergency information saved.", "success")
                return redirect(url_for("patient_profile"))

            except Exception as save_error:
                print("PATIENT PROFILE SAVE ERROR:", repr(save_error))
                flash("Unable to save profile. Please try again.", "error")
                return redirect(url_for("patient_profile"))

        # 7. Combine the two records for the template.
        # Keep both name keys for compatibility with existing HTML.
        patient["name"] = patient.get("full_name", "")
        patient.update(emergency_profile)

        # Use the ISO date format expected by <input type="date">.
        if patient.get("date_of_birth"):
            patient["date_of_birth"] = str(
                patient["date_of_birth"]
            )[:10]

        return render_template(
            "patient/patient_profile.html",
            patient=patient,
            today=date.today().isoformat()
        )

    except Exception as error:
        print("PATIENT PROFILE ERROR:", repr(error))
        flash("Unable to load your profile information.", "error")
        return redirect(url_for("patient_dashboard"))







# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("patient_login"))


# =========================================================
# PATIENT - UPLOAD MEDICAL RECORD
# =========================================================
@app.route("/patient/upload-records", methods=["GET", "POST"])
def patient_upload_records():

    if "patient_id" not in session:
        flash("Please login to access your health records.", "error")
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    # =========================
    # GET → SHOW UPLOAD PAGE
    # =========================
    if request.method == "GET":
        return render_template(
            "patient/patient_upload_records.html"
        )

    # =========================
    # POST → PROCESS UPLOAD
    # =========================

    record_type = request.form.get("record_type", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    uploaded_file = request.files.get("medical_file")

    # =========================
    # VALIDATION
    # =========================

    if not record_type:
        flash("Please select the record type.", "error")
        return redirect(url_for("patient_upload_records"))

    if not title:
        flash("Please enter a record title.", "error")
        return redirect(url_for("patient_upload_records"))

    if not uploaded_file or uploaded_file.filename == "":
        flash("Please select a medical file.", "error")
        return redirect(url_for("patient_upload_records"))

    # =========================
    # ALLOWED EXTENSIONS
    # =========================

    allowed_extensions = {
        "pdf", "png", "jpg", "jpeg", "webp"
    }

    original_filename = uploaded_file.filename

    extension = (
        original_filename.rsplit(".", 1)[-1].lower()
    )

    if extension not in allowed_extensions:
        flash(
            "Only PDF, PNG, JPG, JPEG and WEBP files are allowed.",
            "error"
        )
        return redirect(url_for("patient_upload_records"))

    # =========================
    # PATIENT-SPECIFIC PATH
    # =========================

    unique_name = secrets.token_hex(16) + "." + extension

    storage_path = f"{patient_id}/{unique_name}"

    try:

        # =====================================================
        # 1. READ ORIGINAL FILE
        # =====================================================

        file_bytes = uploaded_file.read()

        if not file_bytes:
            flash("The uploaded file is empty.", "error")
            return redirect(
                url_for("patient_upload_records")
            )

        content_type = (
            uploaded_file.content_type
            or "application/octet-stream"
        )

        # =====================================================
        # 2. UPLOAD ORIGINAL FILE TO SUPABASE STORAGE
        # =====================================================

        storage_response = (
            supabase_admin
            .storage
            .from_("medical-records")
            .upload(
                storage_path,
                file_bytes,
                {
                    "content-type": content_type
                }
            )
        )

        print("Storage upload:", storage_response)

        # =====================================================
        # 3. SAVE ORIGINAL RECORD TO DATABASE
        # =====================================================

        record_data = {
            "patient_id": patient_id,
            "record_type": record_type,
            "title": title,
            "description": description,
            "file_name": original_filename,
            "file_path": storage_path,
            "file_url": None
        }

        db_response = (
            supabase_admin
            .table("medical_records")
            .insert(record_data)
            .execute()
        )

        # =====================================================
        # 4. CHECK DATABASE SAVE
        # =====================================================

        if not db_response.data:

            try:
                (
                    supabase_admin
                    .storage
                    .from_("medical-records")
                    .remove([storage_path])
                )
            except Exception:
                pass

            flash(
                "Record could not be saved.",
                "error"
            )

            return redirect(
                url_for("patient_upload_records")
            )

        # =====================================================
        # 5. GET MEDICAL RECORD ID
        # =====================================================

        medical_record = db_response.data[0]

        medical_record_id = medical_record.get("id")

        if not medical_record_id:

            print("WARNING: Medical record ID was not returned.")

            flash(
                "Record was uploaded, but its ID could not be determined.",
                "error"
            )

            return redirect(
                url_for("patient_health_records")
            )

        print("=" * 70)
        print("MEDICAL RECORD SAVED")
        print("=" * 70)
        print("Patient ID:", patient_id)
        print("Medical Record ID:", medical_record_id)
        print("File:", original_filename)
        print("=" * 70)

        # =====================================================
        # 6. AI MEDICAL DOCUMENT PROCESSING
        # =====================================================

        try:

            print("=" * 70)
            print("STARTING AI MEDICAL DOCUMENT PROCESSING")
            print("=" * 70)

            extracted_data = process_medical_document(
                file_bytes=file_bytes,
                filename=original_filename,
                content_type=content_type
            )

            print("AI EXTRACTION RESULT:")
            print(extracted_data)

            # =================================================
            # 7. SAVE AI RESULT TO HEALTH TIMELINE
            # =================================================

            timeline_data = {
                "patient_id": patient_id,
                "medical_record_id": medical_record_id,

                "event_date": extracted_data.get(
                    "event_date"
                ),

                "event_type": extracted_data.get(
                    "event_type",
                    "other"
                ),

                "provider_name": extracted_data.get(
                    "provider_name"
                ),

                "hospital_name": extracted_data.get(
                    "hospital_name"
                ),

                "diagnosis": extracted_data.get(
                    "diagnosis"
                ),

                "clinical_findings": extracted_data.get(
                    "clinical_findings"
                ),

                "investigations": extracted_data.get(
                    "investigations",
                    []
                ),

                "medications": extracted_data.get(
                    "medications",
                    []
                ),

                "follow_up": extracted_data.get(
                    "follow_up"
                ),

                "clinical_summary": extracted_data.get(
                    "clinical_summary"
                ),

                "ai_processed": True
            }

            timeline_response = (
                supabase_admin
                .table("health_timeline_events")
                .insert(timeline_data)
                .execute()
            )

            if timeline_response.data:

                print("=" * 70)
                print("AI TIMELINE EVENT CREATED")
                print("=" * 70)
                print(
                    "Timeline Event ID:",
                    timeline_response.data[0].get("id")
                )
                print("Patient ID:", patient_id)
                print(
                    "Medical Record ID:",
                    medical_record_id
                )
                print("=" * 70)

            else:

                print(
                    "WARNING: AI extraction succeeded, "
                    "but timeline event was not saved."
                )

        except Exception as ai_error:

            # =================================================
            # AI FAILURE SHOULD NOT DELETE ORIGINAL RECORD
            # =================================================

            print("=" * 70)
            print("AI MEDICAL PROCESSING ERROR")
            print("=" * 70)
            print("Patient ID:", patient_id)
            print(
                "Medical Record ID:",
                medical_record_id
            )
            print(
                "File:",
                original_filename
            )
            print(
                "AI Error:",
                repr(ai_error)
            )
            print("=" * 70)

            # Original medical record is still safely stored.
            # AI can be processed again later.

        # =====================================================
        # 8. SUCCESS
        # =====================================================

        flash(
            "Medical record uploaded successfully!",
            "success"
        )

        return redirect(
            url_for("patient_health_records")
        )

    except Exception as e:

        print("=" * 60)
        print("UPLOAD RECORD ERROR")
        print("=" * 60)
        print("Patient ID:", patient_id)
        print("Error:", repr(e))
        print("=" * 60)

        flash(
            f"Upload failed: {str(e)}",
            "error"
        )

        return redirect(
            url_for("patient_upload_records")
        )


# =========================================================
# PATIENT - MY HEALTH RECORDS
# =========================================================

@app.route("/patient/records")
def patient_records():

    # Make sure patient is logged in
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    try:
        # Fetch ONLY this patient's records
        response = (
            supabase
            .table("medical_records")
            .select("*")
            .eq("patient_id", patient_id)
            .order("created_at", desc=True)
            .execute()
        )

        records = response.data or []

        return render_template(
            "patient/patient_records.html",
            records=records
        )

    except Exception as e:

        print("Error loading patient records:", e)

        flash(
            "Unable to load your health records.",
            "error"
        )

        return render_template(
            "patient/patient_records.html",
            records=[]
        )

@app.route("/patient/health-records")
def patient_health_records():

    # -----------------------------------------------------
    # CHECK PATIENT LOGIN
    # -----------------------------------------------------

    if "patient_id" not in session:
        flash("Please login to access your health records.", "error")
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    try:

        # -------------------------------------------------
        # FETCH ONLY THIS PATIENT'S RECORDS
        # -------------------------------------------------

        response = (
            supabase_admin
            .table("medical_records")
            .select("*")
            .eq("patient_id", patient_id)
            .order("id", desc=True)
            .execute()
        )

        records = response.data or []

        # -------------------------------------------------
        # CREATE SIGNED URL FOR EACH FILE
        # -------------------------------------------------

        for record in records:

            file_path = record.get("file_path")

            if file_path:

                try:

                    signed_response = (
                        supabase_admin
                        .storage
                        .from_("medical-records")
                        .create_signed_url(
                            file_path,
                            3600
                        )
                    )

                    # Supabase response
                    if signed_response:

                        record["file_url"] = (
                            signed_response.get("signedURL")
                            or signed_response.get("signedUrl")
                        )

                except Exception as url_error:

                    print(
                        "Signed URL error:",
                        repr(url_error)
                    )

                    record["file_url"] = None

        # -------------------------------------------------
        # DISPLAY RECORDS
        # -------------------------------------------------

        return render_template(
            "patient/patient_health_records.html",
            records=records
        )

    except Exception as e:

        print("=" * 60)
        print("HEALTH RECORDS ERROR")
        print("=" * 60)
        print("Patient ID:", patient_id)
        print("Error:", repr(e))
        print("=" * 60)

        return render_template(
            "patient/patient_health_records.html",
            records=[],
            error="Unable to load your health records."
        )

@app.route("/doctor/register", methods=["GET", "POST"])
def doctor_register():

    if request.method == "POST":

        full_name = request.form.get("full_name", "").strip()
        medical_registration_number = request.form.get("medical_registration_number", "").strip()
        specialization = request.form.get("specialization", "").strip()
        hospital_name = request.form.get("hospital_name", "").strip()
        hospital_address = request.form.get("hospital_address", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        terms = request.form.get("terms")

        # -------------------------------------------------
        # SERVER-SIDE DEBUGGING & LOGGING
        # -------------------------------------------------
        print("=" * 60)
        print("DEBUG - DOCTOR REGISTRATION FORM DATA:")
        print(f"  full_name:                   '{full_name}'")
        print(f"  medical_registration_number: '{medical_registration_number}'")
        print(f"  specialization:              '{specialization}'")
        print(f"  hospital_name:               '{hospital_name}'")
        print(f"  hospital_address:            '{hospital_address}'")
        print(f"  email:                       '{email}'")
        print(f"  phone:                       '{phone}'")
        print(f"  terms:                       '{terms}'")
        print("=" * 60)

        # -------------------------------------------------
        # SERVER-SIDE VALIDATION
        # -------------------------------------------------
        if not medical_registration_number:
            flash("Medical registration number is required.", "error")
            return render_template("auth/doctor_register.html")

        if not all([
            full_name,
            medical_registration_number,
            specialization,
            hospital_name,
            hospital_address,
            email,
            phone,
            password,
            confirm_password
        ]):
            flash("Please fill in all required fields.", "error")
            return render_template("auth/doctor_register.html")

        if not terms:
            flash("Please confirm that you are a registered medical professional.", "error")
            return render_template("auth/doctor_register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("auth/doctor_register.html")

        if len(password) < 6:
            flash("Password must contain at least 6 characters.", "error")
            return render_template("auth/doctor_register.html")

        # -------------------------------------------------
        # CHECK IF EMAIL OR REGISTRATION NUMBER ALREADY EXISTS
        # -------------------------------------------------
        try:
            existing_email = (
                supabase_admin
                .table("doctors")
                .select("id")
                .eq("email", email)
                .limit(1)
                .execute()
            )
            if existing_email.data:
                flash("An account with this email already exists.", "error")
                return render_template("auth/doctor_register.html")

            existing_reg = (
                supabase_admin
                .table("doctors")
                .select("id")
                .eq("medical_registration_number", medical_registration_number)
                .limit(1)
                .execute()
            )
            if existing_reg.data:
                flash("A doctor with this medical registration number already exists.", "error")
                return render_template("auth/doctor_register.html")
        except Exception as e:
            print("Doctor duplicate check error:", e)

        # -------------------------------------------------
        # INSERT DOCTOR INTO SUPABASE
        # -------------------------------------------------
        doctor_data = {
            "full_name": full_name,
            "medical_registration_number": medical_registration_number,
            "specialization": specialization,
            "hospital_name": hospital_name,
            "hospital_address": hospital_address,
            "email": email,
            "phone": phone,
            "password": password
        }

        try:
            response = (
                supabase_admin
                .table("doctors")
                .insert(doctor_data)
                .execute()
            )

            if response.data:
                flash("Doctor registration successful! Please login.", "success")
                return redirect(url_for("doctor_login"))

            flash("Registration failed. Please try again.", "error")
            return render_template("auth/doctor_register.html")

        except Exception as e:
            print("Doctor registration insert error:", e)
            flash("Unable to create doctor account right now. Please try again.", "error")
            return render_template("auth/doctor_register.html")

    return render_template("auth/doctor_register.html")


@app.route("/doctor/login", methods=["GET", "POST"])
def doctor_login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter your email and password.", "error")
            return render_template("auth/doctor_login.html")

        try:
            result = (
                supabase_admin
                .table("doctors")
                .select("*")
                .eq("email", email)
                .eq("password", password)
                .limit(1)
                .execute()
            )

            if result.data:
                doctor = result.data[0]

                session["doctor_id"] = doctor["id"]
                session["doctor_name"] = doctor["full_name"]
                session["doctor_email"] = doctor["email"]

                flash("Login successful!", "success")
                return redirect(url_for("doctor_dashboard"))

            flash("Invalid email or password.", "error")

        except Exception as e:
            print("Doctor login error:", e)
            flash("Unable to login right now. Please try again.", "error")

    return render_template("auth/doctor_login.html")




# ============================================================
# DOCTOR DASHBOARD & PORTAL ROUTES
# ============================================================

@app.route("/doctor/dashboard")
def doctor_dashboard():

    # Check doctor login
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = session.get("doctor_id")

    try:
        doctor_response = (
            supabase_admin
            .table("doctors")
            .select("*")
            .eq("id", doctor_id)
            .single()
            .execute()
        )
        doctor = doctor_response.data
    except Exception as e:
        print("Error fetching doctor details:", e)
        doctor = {
            "full_name": session.get("doctor_name", "Doctor"),
            "specialization": "Medical Specialist",
            "medical_registration_number": "Registered"
        }

    if not doctor:
        session.clear()
        return redirect(url_for("doctor_login"))

    return render_template(
        "doctor/doctor_dashboard.html",
        doctor=doctor
    )


@app.route("/doctor/access")
def doctor_access():
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))
    return render_template("doctor/guest_patient.html")


@app.route(
    "/doctor/guest-workspace/<uuid:guest_patient_id>/upload",
    methods=["GET", "POST"]
)
def doctor_guest_upload_records(guest_patient_id):

    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    guest_id = str(guest_patient_id)
    doctor_id = session["doctor_id"]

    # Verify this doctor has access to this guest.
    try:
        access = (
            supabase_admin.table("guest_patient_access")
            .select("id")
            .eq("guest_patient_id", guest_id)
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .limit(1)
            .execute()
        )

        if not access.data:
            flash("Guest patient access denied.", "error")
            return redirect(url_for("doctor_guest_patient"))

    except Exception as e:
        print("GUEST ACCESS CHECK ERROR:", repr(e))
        flash("Unable to verify guest access.", "error")
        return redirect(url_for("doctor_guest_patient"))

    if request.method == "GET":
        return render_template(
            "doctor/guest_upload_records.html",
            guest_patient_id=guest_id
        )

    record_type = request.form.get("record_type", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    uploaded_file = request.files.get("medical_file")

    if not record_type or not title:
        flash("Please enter the record type and title.", "error")
        return redirect(
            url_for(
                "doctor_guest_upload_records",
                guest_patient_id=guest_id
            )
        )

    if not uploaded_file or not uploaded_file.filename:
        flash("Please select a medical file.", "error")
        return redirect(
            url_for(
                "doctor_guest_upload_records",
                guest_patient_id=guest_id
            )
        )

    original_filename = secure_filename(uploaded_file.filename)
    allowed_extensions = {"pdf", "png", "jpg", "jpeg", "webp"}

    if (
        "." not in original_filename
        or original_filename.rsplit(".", 1)[-1].lower()
        not in allowed_extensions
    ):
        flash("Only PDF, PNG, JPG, JPEG and WEBP files are allowed.", "error")
        return redirect(
            url_for(
                "doctor_guest_upload_records",
                guest_patient_id=guest_id
            )
        )

    extension = original_filename.rsplit(".", 1)[-1].lower()
    unique_name = secrets.token_hex(16) + "." + extension

    # Guest files never use a registered patient's patient_id.
    storage_path = f"guests/{guest_id}/{unique_name}"

    file_bytes = uploaded_file.read()
    if not file_bytes:
        flash("The selected file is empty.", "error")
        return redirect(
            url_for(
                "doctor_guest_upload_records",
                guest_patient_id=guest_id
            )
        )

    content_type = (
        uploaded_file.content_type or "application/octet-stream"
    )

    try:
        supabase_admin.storage.from_("medical-records").upload(
            storage_path,
            file_bytes,
            {"content-type": content_type}
        )

        record_response = (
            supabase_admin.table("guest_medical_records")
            .insert({
                "guest_patient_id": guest_id,
                "uploaded_by_doctor_id": doctor_id,
                "record_type": record_type,
                "title": title,
                "description": description,
                "file_name": original_filename,
                "file_path": storage_path,
                "file_url": None
            })
            .execute()
        )

        if not record_response.data:
            raise RuntimeError("Guest record metadata was not saved.")

        guest_record = record_response.data[0]

        # Use the existing AI extraction service.
        extracted = process_medical_document(
            file_bytes,
            original_filename,
            content_type
        )

        # Do not guess the extraction schema. Inspect the actual output
        # before mapping extracted fields into the guest timeline.
        print("GUEST DOCUMENT EXTRACTION RESULT:", repr(extracted))

        flash(
            "Medical record uploaded. Check the Flask terminal for the "
            "extraction result before enabling timeline mapping.",
            "success"
        )

        return redirect(
            url_for(
                "doctor_guest_workspace",
                guest_patient_id=guest_id
            )
        )

    except Exception as e:
        print("GUEST UPLOAD ERROR:", repr(e))
        flash("Unable to upload or process the guest medical record.", "error")
        return redirect(
            url_for(
                "doctor_guest_upload_records",
                guest_patient_id=guest_id
            )
        )


@app.route("/doctor/guest-patient/create", methods=["POST"])
def create_guest_patient():
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = session["doctor_id"]

    full_name = request.form.get("full_name", "").strip()
    date_of_birth = request.form.get("date_of_birth", "").strip() or None
    gender = request.form.get("gender", "").strip() or None

    if not full_name:
        flash("Please enter the guest patient's name.", "error")
        return redirect(url_for("doctor_guest_patient"))

    guest_id = str(uuid.uuid4())
    guest_code = "GUEST-" + secrets.token_hex(4).upper()

    try:
        result = (
            supabase_admin
            .table("guest_patients")
            .insert({
                "id": guest_id,
                "guest_code": guest_code,
                "created_by_doctor_id": doctor_id,
                "full_name": full_name,
                "date_of_birth": date_of_birth,
                "gender": gender,
                "status": "active"
            })
            .execute()
        )

        if not result.data:
            raise RuntimeError("Guest patient was not created.")

        (
            supabase_admin
            .table("guest_patient_access")
            .insert({
                "guest_patient_id": guest_id,
                "doctor_id": doctor_id,
                "status": "active"
            })
            .execute()
        )

        flash(f"Guest patient created: {guest_code}", "success")

        return redirect(
            url_for(
                "doctor_guest_workspace",
                guest_patient_id=guest_id
            )
        )

    except Exception as e:
        print("CREATE GUEST PATIENT ERROR:", repr(e))
        flash("Unable to create the guest patient.", "error")
        return redirect(url_for("doctor_guest_patient"))




@app.route("/doctor/guest-patient")
def doctor_guest_patient():
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = str(session["doctor_id"]).strip()

    try:
        response = (
            supabase_admin
            .table("guest_patients")
            .select("*")
            .eq("created_by_doctor_id", doctor_id)
            .execute()
        )

        guests = response.data or []

        print("GUEST LIST COUNT:", len(guests))

        return render_template(
            "doctor/guest_patient.html",
            guests=guests
        )

    except Exception as e:
        import traceback
        print("GUEST PATIENT LIST ERROR:", repr(e))
        traceback.print_exc()

        flash("Unable to load guest patients. Check Flask terminal.", "error")
        return render_template(
            "doctor/guest_patient.html",
            guests=[]
        )





@app.route("/doctor/medical-records")
def doctor_medical_records():
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))
    return render_template("doctor/medical_records.html")


@app.route("/doctor/ai-assistant")
def doctor_ai_assistant():
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))
    return render_template("doctor/doctor_ai_assistant.html")


@app.route("/doctor/consultations")
def doctor_consultations():
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))
    return render_template("doctor/doctor_consultations.html")


@app.route("/doctor/access-audit")
def doctor_access_audit():
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))
    return render_template("doctor/doctor_access_audit.html")


@app.route("/doctor/profile")
def doctor_profile():
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = session.get("doctor_id")

    try:
        doctor_response = (
            supabase_admin
            .table("doctors")
            .select("*")
            .eq("id", doctor_id)
            .single()
            .execute()
        )
        doctor = doctor_response.data
    except Exception:
        doctor = {
            "full_name": session.get("doctor_name", "Doctor"),
            "specialization": "Medical Specialist",
            "medical_registration_number": "Registered"
        }

    return render_template("doctor/doctor_profile.html", doctor=doctor)


@app.route("/doctor/settings")
def doctor_settings():
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))
    return render_template("doctor/doctor_settings.html")
# ---------------------------------------------------------
# RUN APPLICATION
# ---------------------------------------------------------
@app.route("/patient/qr-health-id", endpoint="patient_health_card")
def patient_health_card():

    if "patient_id" not in session:
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    try:

        # =================================================
        # GET PATIENT INFORMATION
        # =================================================

        response = (
            supabase_admin
            .table("patients")
            .select("*")
            .eq("id", patient_id)
            .single()
            .execute()
        )

        patient = response.data

        if not patient:
            flash(
                "Patient information not found.",
                "error"
            )

            return redirect(
                url_for("patient_dashboard")
            )

        # =================================================
        # CREATE SHORT PATIENT-FRIENDLY HEALTH ID
        # =================================================
        #
        # Example:
        # OMC-P1025
        #
        # If your database already has a health_id column,
        # use that value instead.
        #

        health_id = patient.get("health_id")

        if not health_id:

            # Create a short ID using patient database ID
            health_id = f"OMC-P{str(patient_id)[-4:].upper()}"
            (
              supabase_admin
              .table("patients")
              .update({
              "health_id": health_id
               })
              .eq("id", patient_id)
              .execute()
            )
        # =================================================
        # GENERATE REAL QR CODE
        # =================================================
        #
        # IMPORTANT:
        # The QR does NOT contain medical records.
        #
        # It only contains a secure OmniCare identifier.
        #

        qr_data = request.host_url.rstrip('/') + url_for("public_patient_info", patient_id=patient_id)

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=4
        )

        qr.add_data(qr_data)
        qr.make(fit=True)

        qr_image = qr.make_image(
            fill_color="#24105f",
            back_color="white"
        )

        # =================================================
        # CONVERT QR IMAGE TO BASE64
        # =================================================

        qr_buffer = io.BytesIO()

        qr_image.save(
            qr_buffer,
            format="PNG"
        )

        qr_buffer.seek(0)

        qr_code = base64.b64encode(
            qr_buffer.getvalue()
        ).decode("utf-8")

        # =================================================
        # RENDER HEALTH CARD
        # =================================================

        return render_template(
            "patient/patient_health_card.html",

            # Patient information
            patient=patient,

            # Short patient-friendly ID
            health_id=health_id,

            # Real QR image
            qr_code=qr_code
        )

    except Exception as e:

        print("=" * 60)
        print("HEALTH CARD ERROR")
        print("=" * 60)
        print("Patient ID:", patient_id)
        print("Error:", repr(e))
        print("=" * 60)

        flash(
            "Unable to load your Health Card.",
            "error"
        )

        return redirect(
            url_for("patient_dashboard")
        )


# =========================================================
# PUBLIC PATIENT INFO (QR SCAN PAGE)
# =========================================================
@app.route("/patient-info/<patient_id>", endpoint="public_patient_info")
def public_patient_info(patient_id):

    try:
        response = (
            supabase_admin
            .table("patients")
            .select("*")
            .eq("id", patient_id)
            .single()
            .execute()
        )

        patient = response.data

    except Exception as e:
        print("Public Patient Info Fetch Error:", e)
        patient = None

    if not patient:
        return render_template("patient/patient_not_found.html"), 404

    # Determine Health ID
    health_id = patient.get("health_id")
    if not health_id:
        health_id = f"OMC-P{str(patient_id)[-4:].upper()}"

    # Calculate age if DOB exists and age is missing
    age = patient.get("age")
    if not age and patient.get("date_of_birth"):
        try:
            from datetime import datetime, date
            dob_str = str(patient.get("date_of_birth"))
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            today = date.today()
            calculated_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            age = f"{calculated_age} Years"
        except Exception:
            age = None
    elif age and str(age).isdigit():
        age = f"{age} Years"

    # Format Date of Birth if available
    formatted_dob = patient.get("date_of_birth")
    if formatted_dob:
        try:
            from datetime import datetime
            dt = datetime.strptime(str(formatted_dob), "%Y-%m-%d")
            formatted_dob = dt.strftime("%d/%m/%Y")
        except Exception:
            pass

    return render_template(
        "patient/public_patient_info.html",
        patient=patient,
        health_id=health_id,
        calculated_age=age,
        formatted_dob=formatted_dob
    )
@app.route("/doctor/request-access/<patient_id>", methods=["POST"])
def doctor_request_access(patient_id):

    # Check doctor login
    if "doctor_id" not in session:
        flash("Please login as a doctor.", "error")
        return redirect(url_for("doctor_login"))

    doctor_id = session["doctor_id"]

    # Keep the Health ID after returning to Patient Access
    health_id = request.form.get("health_id", "").strip()

    try:

        # -----------------------------------------
        # CHECK EXISTING REQUEST
        # -----------------------------------------

        existing = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("patient_id", patient_id)
            .eq("doctor_id", doctor_id)
            .in_("status", ["pending", "active"])
            .execute()
        )

        if existing.data:

            existing_status = existing.data[0].get("status")

            if existing_status == "active":

                flash(
                    "You already have active access to this patient's medical records.",
                    "info"
                )

            else:

                flash(
                    "Access request is already waiting for patient approval.",
                    "info"
                )

            return redirect(
                url_for(
                    "doctor_patient_access",
                    health_id=health_id
                )
            )


        # -----------------------------------------
        # CREATE NEW ACCESS REQUEST
        # -----------------------------------------

        response = (
            supabase_admin
            .table("access_requests")
            .insert({
                "patient_id": patient_id,
                "doctor_id": doctor_id,
                "status": "pending",
                "access_method": "approval"
            })
            .execute()
        )


        # -----------------------------------------
        # SUCCESS
        # -----------------------------------------

        if response.data:

            flash(
                "✓ Access request sent successfully. Waiting for patient approval.",
                "success"
            )

        else:

            flash(
                "Unable to create access request.",
                "error"
            )


    except Exception as e:

        print("=" * 60)
        print("ACCESS REQUEST ERROR")
        print("=" * 60)
        print("Patient ID:", patient_id)
        print("Doctor ID:", doctor_id)
        print("Error:", repr(e))
        print("=" * 60)

        flash(
            "Something went wrong while requesting access.",
            "error"
        )


    # -----------------------------------------
    # RETURN TO PATIENT ACCESS
    # -----------------------------------------

    return redirect(
        url_for(
            "doctor_patient_access",
            health_id=health_id
        )
    )

@app.route("/doctor/patient-access", methods=["GET"])
def doctor_patient_access():

    # Doctor must be logged in
    if "doctor_id" not in session:
        flash("Please login as a doctor.", "error")
        return redirect(url_for("doctor_login"))

    health_id = request.args.get("health_id", "").strip()

    patient = None
    error = None

    # Search only when Health ID is entered
    if health_id:

        try:
            response = (
                supabase_admin
                .table("patients")
                .select("*")
                .eq("health_id", health_id)
                .single()
                .execute()
            )

            patient = response.data

            if not patient:
                error = "Patient not found."

        except Exception as e:
            print("PATIENT ACCESS SEARCH ERROR:", repr(e))
            error = "Unable to search for the patient."

    return render_template(
        "doctor/patient_access.html",
        patient=patient,
        error=error,
        health_id=health_id
    )

# ============================================================
# DOCTOR - PATIENT WORKSPACE
# ============================================================

import random
def generate_health_id():
    while True:

        number = random.randint(1000, 999999)

        health_id = f"OMC-P{number}"

        response = (
            supabase_admin
            .table("patients")
            .select("id")
            .eq("health_id", health_id)
            .execute()
        )

        if not response.data:
            return health_id

@app.route("/doctor/patient-records/<patient_id>")
def doctor_patient_records(patient_id):

    # Doctor must be logged in
    if "doctor_id" not in session:
        flash("Please login as a doctor.", "error")
        return redirect(url_for("doctor_login"))

    doctor_id = session["doctor_id"]

    try:
        # -----------------------------------------
        # CHECK ACTIVE ACCESS
        # -----------------------------------------

        access_response = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("patient_id", patient_id)
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .execute()
        )

        access_requests = access_response.data or []

        if not access_requests:
            flash(
                "You do not have active access to this patient's records.",
                "error"
            )
            return redirect(url_for(
                "doctor_patient_access"
            ))

        access = access_requests[0]

        # -----------------------------------------
        # CHECK EXPIRATION
        # -----------------------------------------

        expires_at = access.get("expires_at")

        if expires_at:
            expiry_time = datetime.fromisoformat(
                expires_at.replace("Z", "+00:00")
            )

            if datetime.now(timezone.utc) >= expiry_time:

                # Mark access as expired
                (
                    supabase_admin
                    .table("access_requests")
                    .update({
                        "status": "expired"
                    })
                    .eq("id", access["id"])
                    .execute()
                )

                flash(
                    "This temporary access has expired.",
                    "error"
                )

                return redirect(url_for(
                    "doctor_patient_access"
                ))

        # -----------------------------------------
        # GET PATIENT
        # -----------------------------------------

        patient_response = (
            supabase_admin
            .table("patients")
            .select("*")
            .eq("id", patient_id)
            .single()
            .execute()
        )

        patient = patient_response.data

        if not patient:
            flash("Patient not found.", "error")
            return redirect(url_for(
                "doctor_patient_access"
            ))

        # -----------------------------------------
        # GET MEDICAL RECORDS
        # -----------------------------------------

        records_response = (
            supabase_admin
            .table("medical_records")
            .select("*")
            .eq("patient_id", patient_id)
            .order("created_at", desc=True)
            .execute()
        )

        records = records_response.data or []

        return render_template(
            "doctor/patient_medical_records.html",
            patient=patient,
            records=records,
            access=access
        )

    except Exception as e:

        print("DOCTOR PATIENT RECORDS ERROR:", repr(e))

        flash(
            "Unable to load patient medical records.",
            "error"
        )

        return redirect(url_for(
            "doctor_patient_access"
        ))
    
# =========================================================
# DOCTOR - PATIENT WORKSPACE
# =========================================================
@app.route("/doctor/patient-workspace/<patient_id>")
def doctor_patient_workspace(patient_id):

    # -----------------------------------------------------
    # CHECK DOCTOR LOGIN
    # -----------------------------------------------------

    if "doctor_id" not in session:
        flash(
            "Please login as a doctor.",
            "error"
        )

        return redirect(
            url_for("doctor_login")
        )

    doctor_id = session["doctor_id"]

    try:

        # -------------------------------------------------
        # 1. CHECK ACTIVE ACCESS
        # -------------------------------------------------

        access_response = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("patient_id", patient_id)
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .execute()
        )

        access_requests = access_response.data or []

        if not access_requests:

            flash(
                "You do not have active access to this patient's medical records.",
                "error"
            )

            return redirect(
                url_for("doctor_my_patients")
            )

        access = access_requests[0]

        # -------------------------------------------------
        # 2. CHECK EXPIRATION
        # -------------------------------------------------

        expires_at = access.get("expires_at")

        if expires_at:

            expiry_time = datetime.fromisoformat(
                expires_at.replace("Z", "+00:00")
            )

            current_time = datetime.now(timezone.utc)

            if current_time >= expiry_time:

                # Mark access as expired
                (
                    supabase_admin
                    .table("access_requests")
                    .update({
                        "status": "expired"
                    })
                    .eq("id", access["id"])
                    .execute()
                )

                flash(
                    "This patient's temporary access has expired.",
                    "error"
                )

                return redirect(
                    url_for("doctor_my_patients")
                )

        # -------------------------------------------------
        # 3. GET PATIENT
        # -------------------------------------------------

        patient_response = (
            supabase_admin
            .table("patients")
            .select("*")
            .eq("id", patient_id)
            .single()
            .execute()
        )

        patient = patient_response.data

        if not patient:

            flash(
                "Patient not found.",
                "error"
            )

            return redirect(
                url_for("doctor_my_patients")
            )

        # -------------------------------------------------
        # 4. GET PATIENT MEDICAL RECORDS
        # -------------------------------------------------

        records_response = (
            supabase_admin
            .table("medical_records")
            .select("*")
            .eq("patient_id", patient_id)
            .order("uploaded_at", desc=True)
            .execute()
        )

        records = records_response.data or []

        # -------------------------------------------------
        # 5. GET AI HEALTH TIMELINE EVENTS
        # -------------------------------------------------

        timeline_response = (
            supabase_admin
            .table("health_timeline_events")
            .select("*")
            .eq("patient_id", patient_id)
            .order("event_date", desc=True)
            .execute()
        )

        timeline_events = timeline_response.data or []

        # -------------------------------------------------
        # 6. DETECT MEDICAL CONFLICTS
        # -------------------------------------------------

        conflicts = detect_medical_conflicts(
            timeline_events
        )

        # -------------------------------------------------
        # 7. BUILD CONFLICT SUMMARY
        # -------------------------------------------------

        conflict_summary = {
            "total": len(conflicts),

            "high": sum(
                1
                for conflict in conflicts
                if conflict.get("severity") == "high"
            ),

            "medium": sum(
                1
                for conflict in conflicts
                if conflict.get("severity") == "medium"
            ),

            "low": sum(
                1
                for conflict in conflicts
                if conflict.get("severity") == "low"
            )
        }

        # -------------------------------------------------
        # 8. DEBUG INFORMATION
        # -------------------------------------------------

        print("=" * 70)
        print("DOCTOR PATIENT WORKSPACE")
        print("=" * 70)

        print(
            "Patient ID:",
            patient_id
        )

        print(
            "Doctor ID:",
            doctor_id
        )

        print(
            "Medical Records:",
            len(records)
        )

        print(
            "AI Timeline Events:",
            len(timeline_events)
        )

        print(
            "Medical Conflicts:",
            len(conflicts)
        )

        print(
            "High Conflicts:",
            conflict_summary["high"]
        )

        print(
            "Medium Conflicts:",
            conflict_summary["medium"]
        )

        print(
            "Low Conflicts:",
            conflict_summary["low"]
        )

        # -------------------------------------------------
        # 9. PRINT DETECTED CONFLICTS
        # -------------------------------------------------

        if conflicts:

            print("-" * 70)
            print("DETECTED MEDICAL CONFLICTS")
            print("-" * 70)

            for conflict in conflicts:

                print(
                    "Conflict Type:",
                    conflict.get("conflict_type")
                )

                print(
                    "Severity:",
                    conflict.get("severity")
                )

                print(
                    "Title:",
                    conflict.get("title")
                )

                print(
                    "Description:",
                    conflict.get("description")
                )

                print(
                    "Medication:",
                    conflict.get("medication_name")
                )

                # -----------------------------------------
                # PRINT SOURCE RECORDS
                # -----------------------------------------

                source_records = conflict.get("records") or []

                if source_records:

                    print("Source Records:")

                    for source in source_records:

                        print(
                            "  Date:",
                            source.get("event_date")
                        )

                        print(
                            "  Doctor:",
                            source.get("provider_name")
                        )

                        print(
                            "  Hospital:",
                            source.get("hospital_name")
                        )

                        print(
                            "  Record ID:",
                            source.get("medical_record_id")
                        )

                        print(
                            "  Dose:",
                            source.get("dose")
                        )

                        print(
                            "  Frequency:",
                            source.get("frequency")
                        )

                        print(
                            "  Duration:",
                            source.get("duration")
                        )

                        print(
                            "  Instructions:",
                            source.get("instructions")
                        )

                        print("-" * 40)

                print("-" * 70)

        else:

            print(
                "No medical conflicts detected."
            )

        print("=" * 70)

        # -------------------------------------------------
        # 9B. COMPUTE HEALTH TREND DATA
        # -------------------------------------------------
        patient_name = (
            patient.get("full_name")
            or patient.get("name")
            or "Patient"
        )

        trend_data = get_trend_analysis_data(
            timeline_events=timeline_events,
            medical_records=records,
            patient_name=patient_name
        )

        # -------------------------------------------------
        # 10. OPEN PATIENT WORKSPACE
        # -------------------------------------------------

        return render_template(
            "doctor/patient_workspace.html",

            patient=patient,

            records=records,

            timeline_events=timeline_events,

            conflicts=conflicts,

            conflict_summary=conflict_summary,

            access=access,

            trend_data=trend_data
        )

    except Exception as e:

        print("=" * 70)
        print("DOCTOR PATIENT WORKSPACE ERROR")
        print("=" * 70)

        print(
            "Patient ID:",
            patient_id
        )

        print(
            "Doctor ID:",
            doctor_id
        )

        print(
            "Error:",
            repr(e)
        )

        print("=" * 70)

        flash(
            "Unable to load patient workspace.",
            "error"
        )

        return redirect(
            url_for("doctor_my_patients")
        )
# ============================================================
# DOCTOR - VIEW ORIGINAL MEDICAL RECORD
# ============================================================

@app.route("/doctor/patient-record/<patient_id>/<record_id>")
def doctor_view_medical_record(patient_id, record_id):

    print("\n" + "=" * 80)
    print("DOCTOR VIEW ORIGINAL MEDICAL RECORD")
    print("=" * 80)

    # --------------------------------------------------------
    # 1. CHECK DOCTOR LOGIN
    # --------------------------------------------------------

    if "doctor_id" not in session:

        print("❌ Doctor is not logged in")

        flash(
            "Please login as a doctor.",
            "error"
        )

        return redirect(
            url_for("doctor_login")
        )

    doctor_id = session["doctor_id"]

    print("Doctor ID :", doctor_id)
    print("Patient ID:", patient_id)
    print("Record ID :", record_id)


    try:

        # ----------------------------------------------------
        # 2. CHECK ACTIVE ACCESS
        # ----------------------------------------------------

        print("\n[1] Checking doctor access...")

        access_response = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("patient_id", patient_id)
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .execute()
        )

        access_requests = access_response.data or []

        print(
            "Active access records:",
            len(access_requests)
        )

        if not access_requests:

            print("❌ NO ACTIVE ACCESS")

            flash(
                "You do not have active access to this patient's medical records.",
                "error"
            )

            return redirect(
                url_for("doctor_my_patients")
            )

        access = access_requests[0]

        print("✅ Active access found")
        print("Access ID:", access.get("id"))
        print("Access Type:", access.get("access_type"))
        print("Expires At:", access.get("expires_at"))


        # ----------------------------------------------------
        # 3. CHECK EXPIRATION
        # ----------------------------------------------------

        expires_at = access.get("expires_at")

        if expires_at:

            print("\n[2] Checking access expiration...")

            expiry_time = datetime.fromisoformat(
                expires_at.replace("Z", "+00:00")
            )

            current_time = datetime.now(timezone.utc)

            print("Current UTC:", current_time)
            print("Expiry UTC :", expiry_time)

            if current_time >= expiry_time:

                print("❌ ACCESS EXPIRED")

                (
                    supabase_admin
                    .table("access_requests")
                    .update({
                        "status": "expired"
                    })
                    .eq("id", access["id"])
                    .execute()
                )

                flash(
                    "This patient's temporary access has expired.",
                    "error"
                )

                return redirect(
                    url_for("doctor_my_patients")
                )

            print("✅ Access is still valid")


        # ----------------------------------------------------
        # 4. GET MEDICAL RECORD
        # ----------------------------------------------------

        print("\n[3] Getting medical record...")

        record_response = (
            supabase_admin
            .table("medical_records")
            .select("*")
            .eq("id", record_id)
            .eq("patient_id", patient_id)
            .execute()
        )

        records_found = record_response.data or []

        print(
            "Matching records:",
            len(records_found)
        )

        if not records_found:

            print("❌ MEDICAL RECORD NOT FOUND")

            print(
                "Record ID:",
                record_id
            )

            print(
                "Patient ID:",
                patient_id
            )

            flash(
                "Medical record not found.",
                "error"
            )

            return redirect(
                url_for(
                    "doctor_patient_workspace",
                    patient_id=patient_id
                )
            )

        record = records_found[0]

        print("✅ Medical record found")

        print(
            "Record title:",
            record.get("title")
        )

        print(
            "Record type:",
            record.get("record_type")
        )

        print(
            "Record ID:",
            record.get("id")
        )


        # ----------------------------------------------------
        # 5. GET FILE PATH
        # ----------------------------------------------------

        print("\n[4] Getting storage file path...")

        file_path = record.get("file_path")

        print(
            "Raw file_path:",
            repr(file_path)
        )

        if not file_path:

            print("❌ file_path IS EMPTY")

            flash(
                "Original medical file is not available.",
                "error"
            )

            return redirect(
                url_for(
                    "doctor_patient_workspace",
                    patient_id=patient_id
                )
            )


        # ----------------------------------------------------
        # 6. CLEAN STORAGE PATH
        #
        # If the database accidentally contains:
        #
        # medical-records/patient/file.pdf
        #
        # the storage API needs:
        #
        # patient/file.pdf
        # ----------------------------------------------------

        bucket_name = "medical-records"

        if file_path.startswith(
            bucket_name + "/"
        ):

            file_path = file_path[
                len(bucket_name) + 1:
            ]

        print(
            "Storage file path:",
            repr(file_path)
        )


        # ----------------------------------------------------
        # 7. CREATE SIGNED URL
        # ----------------------------------------------------

        print("\n[5] Creating Supabase signed URL...")

        signed_response = (
            supabase_admin
            .storage
            .from_(bucket_name)
            .create_signed_url(
                file_path,
                300
            )
        )

        print(
            "Signed URL response:",
            repr(signed_response)
        )


        # ----------------------------------------------------
        # 8. EXTRACT SIGNED URL
        # ----------------------------------------------------

        signed_url = None

        # Some supabase-py versions return a dictionary directly
        if isinstance(
            signed_response,
            dict
        ):

            signed_url = (
                signed_response.get("signedURL")
                or signed_response.get("signedUrl")
                or signed_response.get("signed_url")
            )

        # Some versions wrap the response
        elif hasattr(
            signed_response,
            "data"
        ):

            signed_data = signed_response.data

            print(
                "Signed response data:",
                repr(signed_data)
            )

            if isinstance(
                signed_data,
                dict
            ):

                signed_url = (
                    signed_data.get("signedURL")
                    or signed_data.get("signedUrl")
                    or signed_data.get("signed_url")
                )

            elif isinstance(
                signed_data,
                str
            ):

                signed_url = signed_data


        # ----------------------------------------------------
        # 9. VERIFY SIGNED URL
        # ----------------------------------------------------

        print(
            "\nExtracted signed URL:",
            repr(signed_url)
        )

        if not signed_url:

            print("\n❌ SIGNED URL WAS NOT GENERATED")

            print(
                "Bucket:",
                bucket_name
            )

            print(
                "File path:",
                file_path
            )

            flash(
                "Unable to generate a secure URL for the original medical record.",
                "error"
            )

            return redirect(
                url_for(
                    "doctor_patient_workspace",
                    patient_id=patient_id
                )
            )


        # ----------------------------------------------------
        # 10. SUCCESS
        # ----------------------------------------------------

        print("\n✅ SIGNED URL GENERATED SUCCESSFULLY")

        print(
            "Opening original medical record..."
        )

        print("=" * 80)

        return redirect(
            signed_url
        )


    except Exception as e:

        print("\n" + "=" * 80)
        print("❌ VIEW ORIGINAL MEDICAL RECORD ERROR")
        print("=" * 80)

        print(
            "Patient ID:",
            patient_id
        )

        print(
            "Doctor ID:",
            doctor_id
        )

        print(
            "Record ID:",
            record_id
        )

        print(
            "Error type:",
            type(e).__name__
        )

        print(
            "Error:",
            repr(e)
        )

        print("=" * 80)

        flash(
            "Unable to open the original medical record.",
            "error"
        )

        return redirect(
            url_for(
                "doctor_patient_workspace",
                patient_id=patient_id
            )
        )

# =========================================================
# DOCTOR - MY PATIENTS
# =========================================================

# =========================================================
# DOCTOR - MY PATIENTS
# =========================================================

@app.route("/doctor/my-patients")
def doctor_my_patients():

    # -----------------------------------------------------
    # 1. CHECK DOCTOR LOGIN
    # -----------------------------------------------------

    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = session["doctor_id"]

    patients = []

    try:

        print("\n" + "=" * 70)
        print("DOCTOR MY PATIENTS")
        print("=" * 70)

        print("Doctor ID:", doctor_id)

        # -------------------------------------------------
        # 2. GET ACTIVE ACCESS REQUESTS
        # -------------------------------------------------

        access_response = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .order("approved_at", desc=True)
            .execute()
        )

        access_requests = access_response.data or []

        print("Active access requests:", len(access_requests))
        print("Access data:", access_requests)

        # -------------------------------------------------
        # 3. PROCESS EACH AUTHORIZED PATIENT
        # -------------------------------------------------

        for access in access_requests:

            patient_id = access.get("patient_id")

            print("\nPatient ID from access:", patient_id)

            if not patient_id:
                continue

            # -------------------------------------------------
            # 4. CHECK EXPIRATION
            # -------------------------------------------------

            expires_at = access.get("expires_at")
            access_type = access.get("access_type") or "temporary"

            if expires_at:

                try:

                    expiry_time = datetime.fromisoformat(
                        expires_at.replace("Z", "+00:00")
                    )

                    current_time = datetime.now(timezone.utc)

                    if current_time >= expiry_time:

                        print(
                            "Access expired for patient:",
                            patient_id
                        )

                        (
                            supabase_admin
                            .table("access_requests")
                            .update({
                                "status": "expired"
                            })
                            .eq("id", access["id"])
                            .execute()
                        )

                        continue

                except Exception as expiry_error:

                    print(
                        "EXPIRY CHECK ERROR:",
                        repr(expiry_error)
                    )

            # -------------------------------------------------
            # 5. GET PATIENT
            # -------------------------------------------------

            patient_response = (
                supabase_admin
                .table("patients")
                .select("*")
                .eq("id", patient_id)
                .limit(1)
                .execute()
            )

            patient_data = patient_response.data or []

            print(
                "Patient returned:",
                patient_data
            )

            if not patient_data:
                print(
                    "Patient not found:",
                    patient_id
                )
                continue

            patient = patient_data[0]

            # -------------------------------------------------
            # 6. ADD ACCESS INFORMATION
            # -------------------------------------------------

            patient["patient_id"] = patient.get("id")

            patient["access_id"] = access.get("id")

            patient["access_type"] = access_type

            patient["access_status"] = "active"

            patient["approved_at"] = access.get(
                "approved_at"
            )

            patient["expires_at"] = expires_at

            patient["requested_at"] = access.get(
                "requested_at"
            )

            patients.append(patient)

        # -------------------------------------------------
        # 7. FINAL RESULT
        # -------------------------------------------------

        print("\nAuthorized patients:", len(patients))

        print("=" * 70)

        return render_template(
            "doctor/my_patients.html",
            patients=patients,
            error=None
        )

    except Exception as e:

        print("\n" + "=" * 70)
        print("❌ DOCTOR MY PATIENTS ERROR")
        print("=" * 70)

        print("Doctor ID:", doctor_id)

        print("Error type:", type(e).__name__)

        print("Error:", repr(e))

        print("=" * 70)

        return render_template(
            "doctor/my_patients.html",
            patients=[],
            error="Unable to load your authorized patients."
        )

# ============================================================
# DOCTOR - AI HEALTH ASSISTANT
# ============================================================

@app.route(
    "/doctor/patient-workspace/<patient_id>/ai-assistant",
    methods=["POST"]
)
def doctor_patient_ai_assistant(patient_id):

    # --------------------------------------------------------
    # 1. CHECK DOCTOR LOGIN
    # --------------------------------------------------------

    if "doctor_id" not in session:

        return {
            "success": False,
            "message": "Doctor login required."
        }, 401


    doctor_id = session["doctor_id"]


    try:

        # ----------------------------------------------------
        # 2. CHECK ACTIVE PATIENT ACCESS
        # ----------------------------------------------------

        access_response = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("patient_id", patient_id)
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .execute()
        )

        access_requests = (
            access_response.data or []
        )


        if not access_requests:

            return {
                "success": False,
                "message":
                    "You do not have active access "
                    "to this patient's records."
            }, 403


        access = access_requests[0]


        # ----------------------------------------------------
        # 3. CHECK EXPIRATION
        # ----------------------------------------------------

        expires_at = access.get(
            "expires_at"
        )


        if expires_at:

            expiry_time = datetime.fromisoformat(
                expires_at.replace(
                    "Z",
                    "+00:00"
                )
            )


            current_time = datetime.now(
                timezone.utc
            )


            if current_time >= expiry_time:

                (
                    supabase_admin
                    .table("access_requests")
                    .update({
                        "status": "expired"
                    })
                    .eq(
                        "id",
                        access["id"]
                    )
                    .execute()
                )


                return {
                    "success": False,
                    "message":
                        "This patient's access has expired."
                }, 403


        # ----------------------------------------------------
        # 4. GET ONLY THIS PATIENT'S TIMELINE
        # ----------------------------------------------------

        timeline_response = (
            supabase_admin
            .table("health_timeline_events")
            .select("*")
            .eq(
                "patient_id",
                patient_id
            )
            .order(
                "event_date",
                desc=True
            )
            .execute()
        )


        timeline_events = (
            timeline_response.data or []
        )


        # ----------------------------------------------------
        # 5. GET QUESTION
        # ----------------------------------------------------

        data = request.get_json(
            silent=True
        ) or {}


        question = (
            data.get("question", "")
            .strip()
        )


        if not question:

            return {
                "success": False,
                "message":
                    "Please enter a question."
            }, 400


        # ----------------------------------------------------
        # 6. ASK GEMINI
        # ----------------------------------------------------

        answer = ask_doctor_ai(
            question,
            timeline_events
        )


        # ----------------------------------------------------
        # 7. RETURN ANSWER
        # ----------------------------------------------------

        return {

            "success": True,

            "answer": answer,

            "event_count":
                len(timeline_events)

        }


    except Exception as e:

        print("=" * 70)
        print("DOCTOR AI ASSISTANT ERROR")
        print("=" * 70)

        print(
            "Patient ID:",
            patient_id
        )

        print(
            "Doctor ID:",
            doctor_id
        )

        print(
            "Error:",
            repr(e)
        )

        print("=" * 70)


        return {

            "success": False,

            "message":
                "Unable to process the AI request."

        }, 500

# ============================================================
# DOCTOR AI - SOURCE RECORDS
# ============================================================
# ============================================================
# DOCTOR AI - SOURCE RECORDS
# ============================================================
# ============================================================
# DOCTOR AI SOURCE RECORDS
# ============================================================

@app.route(
    "/doctor/patient-workspace/<patient_id>/ai-sources",
    methods=["GET"]
)
def doctor_patient_ai_sources(patient_id):

    # --------------------------------------------------------
    # 1. CHECK DOCTOR LOGIN
    # --------------------------------------------------------

    if "doctor_id" not in session:

        return {
            "success": False,
            "message": "Doctor login required."
        }, 401

    doctor_id = session["doctor_id"]

    try:

        # ----------------------------------------------------
        # 2. VERIFY ACTIVE ACCESS
        # ----------------------------------------------------

        access_response = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("patient_id", patient_id)
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .execute()
        )

        access_requests = (
            access_response.data or []
        )

        if not access_requests:

            return {
                "success": False,
                "message": (
                    "You do not have active "
                    "access to this patient."
                )
            }, 403

        access = access_requests[0]

        # ----------------------------------------------------
        # 3. CHECK EXPIRATION
        # ----------------------------------------------------

        expires_at = access.get(
            "expires_at"
        )

        if expires_at:

            expiry_time = datetime.fromisoformat(
                expires_at.replace(
                    "Z",
                    "+00:00"
                )
            )

            current_time = datetime.now(
                timezone.utc
            )

            if current_time >= expiry_time:

                (
                    supabase_admin
                    .table("access_requests")
                    .update({
                        "status": "expired"
                    })
                    .eq(
                        "id",
                        access["id"]
                    )
                    .execute()
                )

                return {
                    "success": False,
                    "message": (
                        "Patient access has expired."
                    )
                }, 403

        # ----------------------------------------------------
        # 4. GET TIMELINE EVENTS
        # ----------------------------------------------------

        timeline_response = (
            supabase_admin
            .table("health_timeline_events")
            .select(
                """
                id,
                medical_record_id,
                event_date,
                event_type,
                provider_name,
                hospital_name
                """
            )
            .eq(
                "patient_id",
                patient_id
            )
            .order(
                "event_date",
                desc=True
            )
            .execute()
        )

        timeline_events = (
            timeline_response.data or []
        )

        # ----------------------------------------------------
        # 5. BUILD SOURCE LIST
        # ----------------------------------------------------

        sources = []

        seen_records = set()

        for event in timeline_events:

            medical_record_id = (
                event.get(
                    "medical_record_id"
                )
            )

            if not medical_record_id:
                continue

            if medical_record_id in seen_records:
                continue

            seen_records.add(
                medical_record_id
            )

            # ------------------------------------------------
            # IMPORTANT:
            # Build the original-record URL safely.
            # ------------------------------------------------

            try:

                
                    view_url = url_for(
    "doctor_view_medical_record",
    patient_id=patient_id,
    record_id=medical_record_id
)

                    print(
    "SOURCE RECORD:",
    medical_record_id,
    "VIEW URL:",
    view_url
)


            except Exception as url_error:

                print(
                    "SOURCE URL ERROR:",
                    repr(url_error)
                )

                view_url = None

            sources.append({

                "medical_record_id":
                    medical_record_id,

                "event_date":
                    event.get(
                        "event_date"
                    ),

                "event_type":
                    event.get(
                        "event_type"
                    ),

                "provider_name":
                    event.get(
                        "provider_name"
                    ),

                "hospital_name":
                    event.get(
                        "hospital_name"
                    ),

                "view_url":
                    view_url
            })

        # ----------------------------------------------------
        # 6. DEBUG
        # ----------------------------------------------------

        print("=" * 70)
        print("DOCTOR AI SOURCES")
        print("=" * 70)

        print(
            "Patient ID:",
            patient_id
        )

        print(
            "Doctor ID:",
            doctor_id
        )

        print(
            "Timeline Events:",
            len(timeline_events)
        )

        print(
            "Source Records:",
            len(sources)
        )

        for source in sources:

            print(
                "Record ID:",
                source.get(
                    "medical_record_id"
                )
            )

            print(
                "Event:",
                source.get(
                    "event_type"
                )
            )

            print(
                "Date:",
                source.get(
                    "event_date"
                )
            )

            print(
                "View URL:",
                source.get(
                    "view_url"
                )
            )

        print("=" * 70)

        # ----------------------------------------------------
        # 7. RETURN JSON
        # ----------------------------------------------------

        return {
            "success": True,
            "sources": sources
        }

    except Exception as e:

        # ----------------------------------------------------
        # PRINT REAL ERROR
        # ----------------------------------------------------

        print("=" * 70)
        print("DOCTOR AI SOURCE ERROR")
        print("=" * 70)

        print(
            "Patient ID:",
            patient_id
        )

        print(
            "Doctor ID:",
            doctor_id
        )

        print(
            "ERROR TYPE:",
            type(e).__name__
        )

        print(
            "ERROR:",
            repr(e)
        )

        print("=" * 70)

        return {
            "success": False,
            "message": (
                "Unable to load source records."
            )
        }, 500


# ============================================================
# DOCTOR - PATIENT WORKSPACE TREND DATA API
# ============================================================

@app.route(
    "/doctor/patient-workspace/<patient_id>/trend-data",
    methods=["POST"]
)
def doctor_patient_trend_data(patient_id):
    """
    Secure server-side endpoint for retrieving filtered health trend
    measurements, charts, summaries, and AI observations.
    """
    # --------------------------------------------------------
    # 1. CHECK DOCTOR LOGIN
    # --------------------------------------------------------
    if "doctor_id" not in session:
        return {
            "success": False,
            "message": "Doctor login required."
        }, 401

    doctor_id = session["doctor_id"]

    # Validate UUID format
    import uuid
    try:
        uuid.UUID(str(patient_id))
        uuid.UUID(str(doctor_id))
    except (ValueError, AttributeError):
        return {
            "success": False,
            "message": "Invalid patient or doctor identifier."
        }, 403

    try:
        # ----------------------------------------------------
        # 2. CHECK ACTIVE PATIENT ACCESS
        # ----------------------------------------------------
        access_response = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("patient_id", patient_id)
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .execute()
        )

        access_requests = access_response.data or []

        if not access_requests:
            return {
                "success": False,
                "message": "You do not have active access to this patient's records."
            }, 403

        access = access_requests[0]

        # ----------------------------------------------------
        # 3. CHECK ACCESS EXPIRATION
        # ----------------------------------------------------
        expires_at = access.get("expires_at")
        if expires_at:
            expiry_time = datetime.fromisoformat(
                expires_at.replace("Z", "+00:00")
            )
            current_time = datetime.now(timezone.utc)

            if current_time >= expiry_time:
                supabase_admin.table("access_requests").update({
                    "status": "expired"
                }).eq("id", access["id"]).execute()

                return {
                    "success": False,
                    "message": "This patient's temporary access has expired."
                }, 403

        # ----------------------------------------------------
        # 4. GET PATIENT DETAILS
        # ----------------------------------------------------
        patient_response = (
            supabase_admin
            .table("patients")
            .select("*")
            .eq("id", patient_id)
            .single()
            .execute()
        )
        patient = patient_response.data or {}
        patient_name = (
            patient.get("full_name")
            or patient.get("name")
            or "Patient"
        )

        # ----------------------------------------------------
        # 5. GET AUTHORIZED MEDICAL RECORDS
        # ----------------------------------------------------
        records_response = (
            supabase_admin
            .table("medical_records")
            .select("*")
            .eq("patient_id", patient_id)
            .order("uploaded_at", desc=True)
            .execute()
        )
        records = records_response.data or []

        # ----------------------------------------------------
        # 6. GET HEALTH TIMELINE EVENTS
        # ----------------------------------------------------
        timeline_response = (
            supabase_admin
            .table("health_timeline_events")
            .select("*")
            .eq("patient_id", patient_id)
            .order("event_date", desc=True)
            .execute()
        )
        timeline_events = timeline_response.data or []

        # ----------------------------------------------------
        # 7. PARSE FILTER PARAMETERS
        # ----------------------------------------------------
        req_data = request.get_json(silent=True) or {}
        time_period = req_data.get("time_period", "all")
        selected_params = req_data.get("parameters")

        # ----------------------------------------------------
        # 8. COMPUTE TREND ANALYSIS
        # ----------------------------------------------------
        trend_data = get_trend_analysis_data(
            timeline_events=timeline_events,
            medical_records=records,
            selected_params=selected_params,
            time_period=time_period,
            patient_name=patient_name
        )

        return {
            "success": True,
            "trend_data": trend_data
        }

    except Exception as e:
        print("=" * 70)
        print("DOCTOR TREND DATA API ERROR")
        print("=" * 70)
        print("Patient ID:", patient_id)
        print("Doctor ID :", doctor_id)
        print("Error     :", repr(e))
        print("=" * 70)

        return {
            "success": False,
            "message": "An error occurred while analyzing health trends."
        }, 500


@app.route("/doctor/shared-medical-records")
def doctor_shared_medical_records():

    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = session["doctor_id"]
    patients = []

    try:
        response = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .eq("access_type", "permanent")
            .order("approved_at", desc=True)
            .execute()
        )

        now = datetime.now(timezone.utc)

        for access in response.data or []:
            patient_id = access.get("patient_id")

            if not patient_id:
                continue

            expires_at = access.get("expires_at")

            # Permanent access should not expire, but still
            # enforce an expiry timestamp if one exists.
            if expires_at:
                try:
                    expiry = datetime.fromisoformat(
                        expires_at.replace("Z", "+00:00")
                    )

                    if expiry.tzinfo is None:
                        expiry = expiry.replace(tzinfo=timezone.utc)

                    if now >= expiry:
                        (
                            supabase_admin
                            .table("access_requests")
                            .update({"status": "expired"})
                            .eq("id", access["id"])
                            .execute()
                        )
                        continue

                except (ValueError, TypeError, AttributeError):
                    # Do not display a grant with an invalid expiry.
                    continue

            patient_response = (
                supabase_admin
                .table("patients")
                .select("*")
                .eq("id", patient_id)
                .limit(1)
                .execute()
            )

            patient_rows = patient_response.data or []

            if not patient_rows:
                continue

            patient = patient_rows[0]

            patient["patient_id"] = patient.get("id")
            patient["access_id"] = access.get("id")
            patient["access_type"] = "permanent"
            patient["access_status"] = "active"
            patient["approved_at"] = access.get("approved_at")

            approved_at = access.get("approved_at")
            patient["approved_at_display"] = None

            if approved_at:
                try:
                    approved_dt = datetime.fromisoformat(
                        approved_at.replace("Z", "+00:00")
                    )
                    patient["approved_at_display"] = (
                        approved_dt.strftime("%d %b %Y, %I:%M %p")
                    )
                except (ValueError, TypeError, AttributeError):
                    patient["approved_at_display"] = str(approved_at)

            # Compatibility with the existing patient-card template.
            patient["patient_name"] = (
                patient.get("full_name")
                or patient.get("name")
                or "Patient"
            )

            patients.append(patient)

        return render_template(
            "doctor/shared_medical_records.html",
            patients=patients,
            error=None
        )

    except Exception as e:
        print("SHARED MEDICAL RECORDS ERROR:", repr(e))

        return render_template(
            "doctor/shared_medical_records.html",
            patients=[],
            error="Unable to load shared medical records."
        )
    
if __name__ == "__main__":

    app.run(
        debug=True
    )

