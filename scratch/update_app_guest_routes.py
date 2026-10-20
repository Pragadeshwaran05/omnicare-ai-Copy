import sys

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

start_marker = '@app.route("/doctor/access")\ndef doctor_access():'
end_marker = '@app.route("/doctor/medical-records")'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print(f"Error: markers not found! start_idx={start_idx}, end_idx={end_idx}")
    sys.exit(1)

replacement = '''def _is_guest_patient(patient_id):
    """
    Check if a given ID belongs to a guest patient rather than a registered patient.
    Guarantees strict patient isolation without executing improper cross-table queries.
    """
    if not patient_id:
        return False
    try:
        clean_id = str(uuid.UUID(str(patient_id)))
        res = (
            supabase_admin
            .table("guest_patients")
            .select("id")
            .eq("id", clean_id)
            .limit(1)
            .execute()
        )
        return bool(res.data)
    except Exception:
        return False


@app.route("/doctor/access")
def doctor_access():
    """Consolidated route redirecting to the canonical guest patient record page."""
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))
    return redirect(url_for("doctor_guest_patient"))


@app.route("/doctor/guest-patient", methods=["GET"])
def doctor_guest_patient():
    """List all guest patients created by or authorized for the authenticated doctor."""
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = str(session["doctor_id"]).strip()

    try:
        # Fetch all guest patients created by this doctor, latest first
        response = (
            supabase_admin
            .table("guest_patients")
            .select("*")
            .eq("created_by_doctor_id", doctor_id)
            .order("created_at", desc=True)
            .execute()
        )

        guests = response.data or []

        # Also include any guest patients shared with this doctor via guest_patient_access
        try:
            access_res = (
                supabase_admin
                .table("guest_patient_access")
                .select("guest_patient_id")
                .eq("doctor_id", doctor_id)
                .eq("status", "active")
                .execute()
            )
            shared_ids = [
                a["guest_patient_id"]
                for a in (access_res.data or [])
                if a.get("guest_patient_id")
            ]
            known_ids = {g["id"] for g in guests}
            missing_ids = [sid for sid in shared_ids if sid not in known_ids]
            if missing_ids:
                shared_guests_res = (
                    supabase_admin
                    .table("guest_patients")
                    .select("*")
                    .in_("id", missing_ids)
                    .order("created_at", desc=True)
                    .execute()
                )
                if shared_guests_res.data:
                    guests.extend(shared_guests_res.data)
        except Exception as shared_err:
            print("Notice: shared guest access query non-critical error:", repr(shared_err))

        print("GUEST LIST COUNT:", len(guests))

        return render_template(
            "doctor/guest_patient.html",
            guests=guests
        )

    except Exception as e:
        import traceback
        print("GUEST PATIENT LIST ERROR:", repr(e))
        traceback.print_exc()

        flash("Unable to load guest patients. Please try refreshing.", "error")
        return render_template(
            "doctor/guest_patient.html",
            guests=[]
        )


@app.route("/doctor/guest-patient/create", methods=["POST"])
def create_guest_patient():
    """Validate and create a persistent guest patient record isolated from registered patients."""
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = str(session["doctor_id"]).strip()

    full_name = request.form.get("full_name", "").strip()
    date_of_birth_raw = request.form.get("date_of_birth", "").strip()
    gender_raw = request.form.get("gender", "").strip()

    if not full_name:
        flash("Please enter the guest patient's name.", "error")
        return redirect(url_for("doctor_guest_patient"))

    if len(full_name) > 150:
        flash("Patient name is too long (maximum 150 characters).", "error")
        return redirect(url_for("doctor_guest_patient"))

    date_of_birth = None
    if date_of_birth_raw:
        try:
            parsed_dob = datetime.strptime(date_of_birth_raw, "%Y-%m-%d").date()
            if parsed_dob > datetime.now(timezone.utc).date():
                flash("Date of birth cannot be in the future.", "error")
                return redirect(url_for("doctor_guest_patient"))
            date_of_birth = date_of_birth_raw
        except ValueError:
            flash("Invalid date of birth format. Please use YYYY-MM-DD.", "error")
            return redirect(url_for("doctor_guest_patient"))

    allowed_genders = {"Male", "Female", "Other"}
    gender = gender_raw if gender_raw in allowed_genders else None

    # Duplicate submission guard: check if a record with same name was created within the last 5 seconds
    try:
        recent_check = (
            supabase_admin
            .table("guest_patients")
            .select("id, guest_code, created_at")
            .eq("created_by_doctor_id", doctor_id)
            .eq("full_name", full_name)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if recent_check.data:
            latest = recent_check.data[0]
            if latest.get("created_at"):
                created_dt = datetime.fromisoformat(latest["created_at"].replace("Z", "+00:00"))
                if (datetime.now(timezone.utc) - created_dt).total_seconds() < 5:
                    print("Duplicate guest patient creation prevented:", latest.get("id"))
                    return redirect(url_for("doctor_guest_workspace", guest_patient_id=latest["id"]))
    except Exception as dup_err:
        print("Duplicate check notice:", repr(dup_err))

    guest_id = str(uuid.uuid4())
    guest_code = "GUEST-" + secrets.token_hex(4).upper()

    try:
        # Insert guest patient into isolated guest_patients table
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
            raise RuntimeError("Guest patient record was not saved.")

        # Insert authorization into guest_patient_access table
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

        flash(f"Guest patient created successfully: {guest_code}", "success")

        return redirect(
            url_for(
                "doctor_guest_workspace",
                guest_patient_id=guest_id
            )
        )

    except Exception as e:
        import traceback
        print("CREATE GUEST PATIENT ERROR:", repr(e))
        traceback.print_exc()
        flash("Unable to create the guest patient. Please check your input and try again.", "error")
        return redirect(url_for("doctor_guest_patient"))


@app.route("/doctor/guest-workspace/<guest_patient_id>")
def doctor_guest_workspace(guest_patient_id):
    """
    Open the unified patient workspace for an authorized guest patient,
    populating records, timeline, medical conflicts, trend analysis, and AI assistant.
    """
    if "doctor_id" not in session:
        flash("Please login as a doctor.", "error")
        return redirect(url_for("doctor_login"))

    doctor_id = str(session["doctor_id"]).strip()

    try:
        clean_guest_id = str(uuid.UUID(str(guest_patient_id)))
    except (ValueError, AttributeError):
        flash("Invalid guest patient identifier.", "error")
        return redirect(url_for("doctor_guest_patient"))

    try:
        # 1. Verify doctor authorization
        access_response = (
            supabase_admin
            .table("guest_patient_access")
            .select("*")
            .eq("guest_patient_id", clean_guest_id)
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .limit(1)
            .execute()
        )

        has_access = bool(access_response.data)

        if not has_access:
            creator_check = (
                supabase_admin
                .table("guest_patients")
                .select("id")
                .eq("id", clean_guest_id)
                .eq("created_by_doctor_id", doctor_id)
                .limit(1)
                .execute()
            )
            if creator_check.data:
                has_access = True
                try:
                    supabase_admin.table("guest_patient_access").insert({
                        "guest_patient_id": clean_guest_id,
                        "doctor_id": doctor_id,
                        "status": "active"
                    }).execute()
                except Exception:
                    pass

        if not has_access:
            flash("You do not have active access to this guest patient's medical records.", "error")
            return redirect(url_for("doctor_guest_patient"))

        # 2. Get Guest Patient Record
        guest_response = (
            supabase_admin
            .table("guest_patients")
            .select("*")
            .eq("id", clean_guest_id)
            .single()
            .execute()
        )

        guest_patient = guest_response.data
        if not guest_patient:
            flash("Guest patient not found.", "error")
            return redirect(url_for("doctor_guest_patient"))

        patient = dict(guest_patient)
        patient["is_guest"] = True
        patient["health_id"] = guest_patient.get("guest_code") or "GUEST-PATIENT"
        patient["name"] = guest_patient.get("full_name") or "Guest Patient"

        # 3. Get Guest Medical Records
        records_response = (
            supabase_admin
            .table("guest_medical_records")
            .select("*")
            .eq("guest_patient_id", clean_guest_id)
            .order("created_at", desc=True)
            .execute()
        )

        records = records_response.data or []

        # Generate secure signed URLs for original documents
        for record in records:
            record["uploaded_at"] = record.get("created_at")
            file_path = record.get("file_path")
            if file_path:
                clean_path = file_path
                bucket_name = "medical-records"
                if clean_path.startswith(bucket_name + "/"):
                    clean_path = clean_path[len(bucket_name) + 1:]
                try:
                    signed_res = supabase_admin.storage.from_(bucket_name).create_signed_url(clean_path, 3600)
                    signed_url = None
                    if isinstance(signed_res, dict):
                        signed_url = signed_res.get("signedURL") or signed_res.get("signedUrl") or signed_res.get("signed_url")
                    elif hasattr(signed_res, "data") and isinstance(signed_res.data, dict):
                        signed_url = signed_res.data.get("signedUrl") or signed_res.data.get("signedURL")
                    record["file_url"] = signed_url
                except Exception as url_err:
                    print("Guest record signed URL error:", repr(url_err))
                    record["file_url"] = None

        # 4. Get Guest Health Timeline Events
        timeline_response = (
            supabase_admin
            .table("guest_health_timeline_events")
            .select("*")
            .eq("guest_patient_id", clean_guest_id)
            .order("event_date", desc=True)
            .execute()
        )

        timeline_events = timeline_response.data or []
        for event in timeline_events:
            event["medical_record_id"] = event.get("guest_medical_record_id")
            event["patient_id"] = clean_guest_id

        # 5. Detect Medical Conflicts across guest timeline events
        conflicts = detect_medical_conflicts(timeline_events)

        conflict_summary = {
            "total": len(conflicts),
            "high": sum(1 for c in conflicts if c.get("severity") == "high"),
            "medium": sum(1 for c in conflicts if c.get("severity") == "medium"),
            "low": sum(1 for c in conflicts if c.get("severity") == "low")
        }

        # 6. Compute Health Trend Analysis Data
        trend_data = get_trend_analysis_data(
            timeline_events=timeline_events,
            medical_records=records,
            patient_name=patient["name"]
        )

        # 7. Workspace Access Context
        access = {
            "access_type": "guest",
            "status": "active",
            "approved_at": guest_patient.get("created_at"),
            "expires_at": None
        }

        print("=" * 70)
        print("DOCTOR GUEST PATIENT WORKSPACE")
        print("=" * 70)
        print("Guest Patient ID:", clean_guest_id)
        print("Guest Code:", guest_patient.get("guest_code"))
        print("Doctor ID:", doctor_id)
        print("Medical Records:", len(records))
        print("Timeline Events:", len(timeline_events))
        print("Medical Conflicts:", len(conflicts))
        print("=" * 70)

        return render_template(
            "doctor/patient_workspace.html",
            patient=patient,
            records=records,
            timeline_events=timeline_events,
            conflicts=conflicts,
            conflict_summary=conflict_summary,
            access=access,
            trend_data=trend_data,
            is_guest=True
        )

    except Exception as e:
        import traceback
        print("DOCTOR GUEST WORKSPACE ERROR:", repr(e))
        traceback.print_exc()
        flash("Unable to open the guest patient workspace.", "error")
        return redirect(url_for("doctor_guest_patient"))


@app.route(
    "/doctor/guest-workspace/<guest_patient_id>/upload",
    methods=["GET", "POST"]
)
def doctor_guest_upload_records(guest_patient_id):
    """
    Handle medical document uploads for a guest patient.
    Stores the document under guests/{guest_patient_id}/..., saves record metadata,
    executes existing AI medical document extraction, and persists the extracted findings
    into the guest timeline.
    """
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = str(session["doctor_id"]).strip()

    try:
        clean_guest_id = str(uuid.UUID(str(guest_patient_id)))
    except (ValueError, AttributeError):
        flash("Invalid guest patient identifier.", "error")
        return redirect(url_for("doctor_guest_patient"))

    # Verify authorization
    access = (
        supabase_admin.table("guest_patient_access")
        .select("id")
        .eq("guest_patient_id", clean_guest_id)
        .eq("doctor_id", doctor_id)
        .eq("status", "active")
        .limit(1)
        .execute()
    )

    if not access.data:
        creator_check = (
            supabase_admin.table("guest_patients")
            .select("id")
            .eq("id", clean_guest_id)
            .eq("created_by_doctor_id", doctor_id)
            .limit(1)
            .execute()
        )
        if not creator_check.data:
            flash("Guest patient access denied.", "error")
            return redirect(url_for("doctor_guest_patient"))

    if request.method == "GET":
        guest_res = (
            supabase_admin.table("guest_patients")
            .select("*")
            .eq("id", clean_guest_id)
            .single()
            .execute()
        )
        guest_patient = guest_res.data or {}
        return render_template(
            "doctor/guest_upload_records.html",
            guest_patient=guest_patient,
            guest_patient_id=clean_guest_id
        )

    # POST handling
    record_type = request.form.get("record_type", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    uploaded_file = request.files.get("medical_file")

    if not record_type or not title:
        flash("Please enter the record type and title.", "error")
        return redirect(url_for("doctor_guest_workspace", guest_patient_id=clean_guest_id))

    if not uploaded_file or not uploaded_file.filename:
        flash("Please select a medical file.", "error")
        return redirect(url_for("doctor_guest_workspace", guest_patient_id=clean_guest_id))

    raw_filename = uploaded_file.filename
    original_filename = secure_filename(raw_filename) if "secure_filename" in globals() else raw_filename
    if not original_filename:
        original_filename = "medical_record"

    allowed_extensions = {"pdf", "png", "jpg", "jpeg", "webp"}
    if "." not in raw_filename or raw_filename.rsplit(".", 1)[-1].lower() not in allowed_extensions:
        flash("Only PDF, PNG, JPG, JPEG and WEBP files are allowed.", "error")
        return redirect(url_for("doctor_guest_workspace", guest_patient_id=clean_guest_id))

    extension = raw_filename.rsplit(".", 1)[-1].lower()
    unique_name = secrets.token_hex(16) + "." + extension
    storage_path = f"guests/{clean_guest_id}/{unique_name}"

    file_bytes = uploaded_file.read()
    if not file_bytes:
        flash("The selected file is empty.", "error")
        return redirect(url_for("doctor_guest_workspace", guest_patient_id=clean_guest_id))

    # Max 10 MB limit
    if len(file_bytes) > 10 * 1024 * 1024:
        flash("File size exceeds maximum allowed limit of 10 MB.", "error")
        return redirect(url_for("doctor_guest_workspace", guest_patient_id=clean_guest_id))

    content_type = uploaded_file.content_type or "application/octet-stream"

    try:
        # 1. Upload to Supabase Storage under guest-isolated path
        supabase_admin.storage.from_("medical-records").upload(
            storage_path,
            file_bytes,
            {"content-type": content_type}
        )

        # 2. Insert record metadata into guest_medical_records
        record_response = (
            supabase_admin.table("guest_medical_records")
            .insert({
                "guest_patient_id": clean_guest_id,
                "uploaded_by_doctor_id": doctor_id,
                "record_type": record_type,
                "title": title,
                "description": description,
                "file_name": raw_filename,
                "file_path": storage_path,
                "file_url": None
            })
            .execute()
        )

        if not record_response.data:
            try:
                supabase_admin.storage.from_("medical-records").remove([storage_path])
            except Exception:
                pass
            raise RuntimeError("Guest record metadata was not saved.")

        guest_record = record_response.data[0]
        guest_record_id = guest_record.get("id")

        # 3. Call existing medical document processing pipeline
        ai_success = False
        extracted = None
        try:
            print("=" * 70)
            print("AI EXTRACTION FOR GUEST MEDICAL DOCUMENT")
            print("=" * 70)
            extracted = process_medical_document(
                file_bytes=file_bytes,
                filename=raw_filename,
                content_type=content_type
            )
            print("GUEST DOCUMENT EXTRACTION RESULT:", repr(extracted))
            if extracted and isinstance(extracted, dict):
                ai_success = True
        except Exception as ai_err:
            print("GUEST DOCUMENT AI EXTRACTION ERROR:", repr(ai_err))
            ai_success = False

        # 4. Persist to guest_health_timeline_events
        if ai_success and extracted:
            timeline_data = {
                "guest_patient_id": clean_guest_id,
                "guest_medical_record_id": guest_record_id,
                "event_date": extracted.get("event_date"),
                "event_type": extracted.get("event_type", "other") or "other",
                "provider_name": extracted.get("provider_name"),
                "hospital_name": extracted.get("hospital_name"),
                "diagnosis": extracted.get("diagnosis"),
                "clinical_findings": extracted.get("clinical_findings"),
                "investigations": extracted.get("investigations", []) or [],
                "medications": extracted.get("medications", []) or [],
                "follow_up": extracted.get("follow_up"),
                "clinical_summary": extracted.get("clinical_summary"),
                "ai_processed": True
            }

            timeline_res = (
                supabase_admin
                .table("guest_health_timeline_events")
                .insert(timeline_data)
                .execute()
            )
            print("GUEST TIMELINE EVENT PERSISTED:", bool(timeline_res.data))
            flash("Medical record uploaded and analyzed successfully!", "success")
        else:
            # Fallback event: preserve original record, record an event with ai_processed=False
            fallback_timeline = {
                "guest_patient_id": clean_guest_id,
                "guest_medical_record_id": guest_record_id,
                "event_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "event_type": "other",
                "provider_name": None,
                "hospital_name": None,
                "diagnosis": None,
                "clinical_findings": None,
                "investigations": [],
                "medications": [],
                "follow_up": None,
                "clinical_summary": f"Uploaded document: {raw_filename} ({record_type}). AI structured extraction pending.",
                "ai_processed": False
            }
            try:
                supabase_admin.table("guest_health_timeline_events").insert(fallback_timeline).execute()
            except Exception as fb_err:
                print("Fallback timeline insert error:", repr(fb_err))

            flash("Medical record uploaded successfully, but AI extraction could not be completed at this time.", "warning")

        return redirect(
            url_for(
                "doctor_guest_workspace",
                guest_patient_id=clean_guest_id
            )
        )

    except Exception as e:
        import traceback
        print("GUEST UPLOAD ERROR:", repr(e))
        traceback.print_exc()
        flash("Unable to upload or process the guest medical record. Please try again.", "error")
        return redirect(
            url_for(
                "doctor_guest_workspace",
                guest_patient_id=clean_guest_id
            )
        )


@app.route("/doctor/guest-record/<guest_patient_id>/<record_id>")
def doctor_view_guest_medical_record(guest_patient_id, record_id):
    """Securely stream or redirect to signed URL for an authorized guest medical record."""
    if "doctor_id" not in session:
        flash("Please login as a doctor.", "error")
        return redirect(url_for("doctor_login"))

    doctor_id = str(session["doctor_id"]).strip()

    try:
        clean_guest_id = str(uuid.UUID(str(guest_patient_id)))
    except (ValueError, AttributeError):
        flash("Invalid guest patient identifier.", "error")
        return redirect(url_for("doctor_guest_patient"))

    try:
        # Check authorization
        access_check = (
            supabase_admin.table("guest_patient_access")
            .select("id")
            .eq("guest_patient_id", clean_guest_id)
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        if not access_check.data:
            creator_check = (
                supabase_admin.table("guest_patients")
                .select("id")
                .eq("id", clean_guest_id)
                .eq("created_by_doctor_id", doctor_id)
                .limit(1)
                .execute()
            )
            if not creator_check.data:
                flash("You do not have authorization to view this guest record.", "error")
                return redirect(url_for("doctor_guest_patient"))

        # Fetch guest medical record
        rec_res = (
            supabase_admin.table("guest_medical_records")
            .select("*")
            .eq("id", record_id)
            .eq("guest_patient_id", clean_guest_id)
            .limit(1)
            .execute()
        )
        if not rec_res.data:
            flash("Medical record not found.", "error")
            return redirect(url_for("doctor_guest_workspace", guest_patient_id=clean_guest_id))

        record = rec_res.data[0]
        file_path = record.get("file_path")
        if not file_path:
            flash("Original medical file path is not available.", "error")
            return redirect(url_for("doctor_guest_workspace", guest_patient_id=clean_guest_id))

        bucket_name = "medical-records"
        if file_path.startswith(bucket_name + "/"):
            file_path = file_path[len(bucket_name) + 1:]

        signed_res = supabase_admin.storage.from_(bucket_name).create_signed_url(file_path, 300)
        signed_url = None
        if isinstance(signed_res, dict):
            signed_url = signed_res.get("signedURL") or signed_res.get("signedUrl") or signed_res.get("signed_url")
        elif hasattr(signed_res, "data") and isinstance(signed_res.data, dict):
            signed_url = signed_res.data.get("signedUrl") or signed_res.data.get("signedURL")

        if not signed_url:
            flash("Could not generate a secure link to the medical record.", "error")
            return redirect(url_for("doctor_guest_workspace", guest_patient_id=clean_guest_id))

        return redirect(signed_url)

    except Exception as e:
        import traceback
        print("DOCTOR VIEW GUEST RECORD ERROR:", repr(e))
        traceback.print_exc()
        flash("Unable to view the medical record.", "error")
        return redirect(url_for("doctor_guest_workspace", guest_patient_id=clean_guest_id))


@app.route(
    "/doctor/guest-workspace/<guest_patient_id>/ai-assistant",
    methods=["POST"]
)
def doctor_guest_ai_assistant(guest_patient_id):
    """Clinical AI assistant for guest patient record workspace."""
    if "doctor_id" not in session:
        return {"success": False, "message": "Doctor login required."}, 401

    doctor_id = str(session["doctor_id"]).strip()

    try:
        clean_guest_id = str(uuid.UUID(str(guest_patient_id)))
    except (ValueError, AttributeError):
        return {"success": False, "message": "Invalid guest patient identifier."}, 400

    try:
        # Check authorization
        access_check = (
            supabase_admin.table("guest_patient_access")
            .select("id")
            .eq("guest_patient_id", clean_guest_id)
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        if not access_check.data:
            creator_check = (
                supabase_admin.table("guest_patients")
                .select("id")
                .eq("id", clean_guest_id)
                .eq("created_by_doctor_id", doctor_id)
                .limit(1)
                .execute()
            )
            if not creator_check.data:
                return {"success": False, "message": "You do not have active access to this guest patient."}, 403

        # Fetch guest timeline events
        timeline_res = (
            supabase_admin.table("guest_health_timeline_events")
            .select("*")
            .eq("guest_patient_id", clean_guest_id)
            .order("event_date", desc=True)
            .execute()
        )
        timeline_events = timeline_res.data or []
        for ev in timeline_events:
            ev["medical_record_id"] = ev.get("guest_medical_record_id")

        data = request.get_json(silent=True) or {}
        question = (data.get("question") or "").strip()
        if not question:
            return {"success": False, "message": "Please enter a question."}, 400

        answer = ask_doctor_ai(question, timeline_events)
        return {"success": True, "answer": answer}

    except Exception as e:
        import traceback
        print("GUEST DOCTOR AI ERROR:", repr(e))
        traceback.print_exc()
        return {"success": False, "message": "AI assistant encountered an error. Please try again."}, 500


@app.route(
    "/doctor/guest-workspace/<guest_patient_id>/ai-sources",
    methods=["GET"]
)
def doctor_guest_ai_sources(guest_patient_id):
    """Retrieve source records cited by the AI assistant for guest patient."""
    if "doctor_id" not in session:
        return {"success": False, "message": "Doctor login required."}, 401

    doctor_id = str(session["doctor_id"]).strip()

    try:
        clean_guest_id = str(uuid.UUID(str(guest_patient_id)))
    except (ValueError, AttributeError):
        return {"success": False, "message": "Invalid guest identifier."}, 400

    try:
        access_check = (
            supabase_admin.table("guest_patient_access")
            .select("id")
            .eq("guest_patient_id", clean_guest_id)
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        if not access_check.data:
            creator_check = (
                supabase_admin.table("guest_patients")
                .select("id")
                .eq("id", clean_guest_id)
                .eq("created_by_doctor_id", doctor_id)
                .limit(1)
                .execute()
            )
            if not creator_check.data:
                return {"success": False, "message": "You do not have active access to this guest patient."}, 403

        timeline_res = (
            supabase_admin.table("guest_health_timeline_events")
            .select("id, guest_medical_record_id, event_date, event_type, provider_name, hospital_name")
            .eq("guest_patient_id", clean_guest_id)
            .order("event_date", desc=True)
            .execute()
        )
        timeline_events = timeline_res.data or []

        sources = []
        seen = set()
        for ev in timeline_events:
            rec_id = ev.get("guest_medical_record_id")
            if not rec_id or rec_id in seen:
                continue
            seen.add(rec_id)
            view_url = url_for("doctor_view_guest_medical_record", guest_patient_id=clean_guest_id, record_id=rec_id)
            sources.append({
                "medical_record_id": rec_id,
                "event_date": ev.get("event_date"),
                "event_type": ev.get("event_type"),
                "provider_name": ev.get("provider_name"),
                "hospital_name": ev.get("hospital_name"),
                "view_url": view_url
            })
        return {"success": True, "sources": sources}

    except Exception as e:
        import traceback
        print("GUEST AI SOURCES ERROR:", repr(e))
        traceback.print_exc()
        return {"success": False, "message": "Failed to fetch source records."}, 500


@app.route(
    "/doctor/guest-workspace/<guest_patient_id>/trend-data",
    methods=["POST"]
)
def doctor_guest_trend_data(guest_patient_id):
    """Retrieve filtered health trend measurements and charts for a guest patient."""
    if "doctor_id" not in session:
        return {"success": False, "message": "Doctor login required."}, 401

    doctor_id = str(session["doctor_id"]).strip()

    try:
        clean_guest_id = str(uuid.UUID(str(guest_patient_id)))
    except (ValueError, AttributeError):
        return {"success": False, "message": "Invalid guest identifier."}, 400

    try:
        access_check = (
            supabase_admin.table("guest_patient_access")
            .select("id")
            .eq("guest_patient_id", clean_guest_id)
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        if not access_check.data:
            creator_check = (
                supabase_admin.table("guest_patients")
                .select("id")
                .eq("id", clean_guest_id)
                .eq("created_by_doctor_id", doctor_id)
                .limit(1)
                .execute()
            )
            if not creator_check.data:
                return {"success": False, "message": "You do not have active access to this guest patient."}, 403

        p_res = (
            supabase_admin.table("guest_patients")
            .select("full_name")
            .eq("id", clean_guest_id)
            .single()
            .execute()
        )
        patient_name = (p_res.data or {}).get("full_name") or "Guest Patient"

        records_res = (
            supabase_admin.table("guest_medical_records")
            .select("*")
            .eq("guest_patient_id", clean_guest_id)
            .order("created_at", desc=True)
            .execute()
        )
        records = records_res.data or []
        for r in records:
            r["uploaded_at"] = r.get("created_at")

        timeline_res = (
            supabase_admin.table("guest_health_timeline_events")
            .select("*")
            .eq("guest_patient_id", clean_guest_id)
            .order("event_date", desc=True)
            .execute()
        )
        timeline_events = timeline_res.data or []
        for ev in timeline_events:
            ev["medical_record_id"] = ev.get("guest_medical_record_id")

        data = request.get_json(silent=True) or {}
        selected_params = data.get("parameters")
        time_period = data.get("time_period", "all")

        trend_data = get_trend_analysis_data(
            timeline_events=timeline_events,
            medical_records=records,
            selected_params=selected_params,
            time_period=time_period,
            patient_name=patient_name
        )
        return {"success": True, "trend_data": trend_data}

    except Exception as e:
        import traceback
        print("GUEST TREND DATA ERROR:", repr(e))
        traceback.print_exc()
        return {"success": False, "message": "Failed to calculate trend data."}, 500


'''

new_content = content[:start_idx] + replacement + content[end_idx:]

with open("app.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print("Updated app.py successfully!")
