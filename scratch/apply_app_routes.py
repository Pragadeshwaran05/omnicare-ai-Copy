with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update doctor_guest_workspace to add processing_status and ai_processed to records
old_block_workspace = '''        timeline_events = timeline_response.data or []
        for event in timeline_events:
            event["medical_record_id"] = event.get("guest_medical_record_id")
            event["patient_id"] = clean_guest_id

        # 5. Detect Medical Conflicts across guest timeline events'''

new_block_workspace = '''        timeline_events = timeline_response.data or []
        for event in timeline_events:
            event["medical_record_id"] = event.get("guest_medical_record_id")
            event["patient_id"] = clean_guest_id

        # Map processing status to records
        record_status_map = {}
        for event in timeline_events:
            rec_id = event.get("guest_medical_record_id")
            if rec_id:
                if event.get("ai_processed"):
                    record_status_map[rec_id] = "processed"
                elif rec_id not in record_status_map:
                    record_status_map[rec_id] = "failed"

        for record in records:
            rec_id = record.get("id")
            status = record_status_map.get(rec_id, "pending")
            record["processing_status"] = status
            record["ai_processed"] = (status == "processed")

        # 5. Detect Medical Conflicts across guest timeline events'''

assert old_block_workspace in content, "old_block_workspace not found"
content = content.replace(old_block_workspace, new_block_workspace, 1)

# 2. Add the four routes before doctor_guest_ai_assistant
old_route_anchor = '''        flash("Unable to view the medical record.", "error")
        return redirect(url_for("doctor_guest_workspace", guest_patient_id=clean_guest_id))


@app.route(
    "/doctor/guest-workspace/<guest_patient_id>/ai-assistant",'''

new_routes_code = '''        flash("Unable to view the medical record.", "error")
        return redirect(url_for("doctor_guest_workspace", guest_patient_id=clean_guest_id))


@app.route("/doctor/guest-record/<guest_patient_id>/status/<int:record_id>")
def doctor_guest_record_status(guest_patient_id, record_id):
    """
    Check processing status of a specific guest medical record.
    Returns JSON containing status ('processed', 'failed', 'pending') and extraction metadata.
    """
    if "doctor_id" not in session:
        return {"success": False, "message": "Doctor login required."}, 401

    doctor_id = str(session["doctor_id"]).strip()

    try:
        clean_guest_id = str(uuid.UUID(str(guest_patient_id)))
    except (ValueError, AttributeError):
        return {"success": False, "message": "Invalid guest patient identifier."}, 400

    try:
        # Authorization check
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
                return {"success": False, "message": "Access denied."}, 403

        # Verify record exists
        rec_res = (
            supabase_admin.table("guest_medical_records")
            .select("id, file_name, created_at, record_type")
            .eq("id", record_id)
            .eq("guest_patient_id", clean_guest_id)
            .limit(1)
            .execute()
        )
        if not rec_res.data:
            return {"success": False, "message": "Record not found."}, 404

        record = rec_res.data[0]

        # Check corresponding timeline event
        ev_res = (
            supabase_admin.table("guest_health_timeline_events")
            .select("id, ai_processed, event_date, diagnosis")
            .eq("guest_medical_record_id", record_id)
            .eq("guest_patient_id", clean_guest_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if ev_res.data:
            ev = ev_res.data[0]
            is_processed = bool(ev.get("ai_processed"))
            status = "processed" if is_processed else "failed"
            return {
                "success": True,
                "record_id": record_id,
                "status": status,
                "ai_processed": is_processed,
                "event_id": ev.get("id"),
                "event_date": ev.get("event_date"),
                "diagnosis": ev.get("diagnosis"),
                "file_name": record.get("file_name"),
                "record_type": record.get("record_type")
            }
        else:
            return {
                "success": True,
                "record_id": record_id,
                "status": "pending",
                "ai_processed": False,
                "file_name": record.get("file_name"),
                "record_type": record.get("record_type")
            }

    except Exception as e:
        import traceback
        print("GUEST RECORD STATUS ERROR:", repr(e))
        traceback.print_exc()
        return {"success": False, "message": "Failed to check record status."}, 500


@app.route(
    "/doctor/guest-record/<guest_patient_id>/retry/<int:record_id>",
    methods=["GET", "POST"]
)
def doctor_guest_retry_record(guest_patient_id, record_id):
    """
    Retry AI document extraction for a guest medical record.
    Downloads the original document from Supabase storage, runs process_medical_document,
    and updates/replaces the timeline event for this record to prevent duplicate entries.
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
        # Authorization check
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
                flash("Access denied.", "error")
                return redirect(url_for("doctor_guest_patient"))

        # Fetch record
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
            flash("Original file path not found for this record.", "error")
            return redirect(url_for("doctor_guest_workspace", guest_patient_id=clean_guest_id))

        clean_path = file_path
        bucket_name = "medical-records"
        if clean_path.startswith(bucket_name + "/"):
            clean_path = clean_path[len(bucket_name) + 1:]

        # Download original file from Supabase Storage
        file_bytes = supabase_admin.storage.from_(bucket_name).download(clean_path)
        if not file_bytes:
            flash("Unable to download original file from storage.", "error")
            return redirect(url_for("doctor_guest_workspace", guest_patient_id=clean_guest_id))

        raw_filename = record.get("file_name") or "document.pdf"
        extension = raw_filename.rsplit(".", 1)[-1].lower() if "." in raw_filename else "pdf"
        mime_map = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp"
        }
        content_type = mime_map.get(extension, "application/pdf")

        # Re-run medical document extraction
        extracted = None
        try:
            print("=" * 70)
            print("RETRYING AI EXTRACTION FOR GUEST RECORD:", record_id)
            print("=" * 70)
            extracted = process_medical_document(
                file_bytes=file_bytes,
                filename=raw_filename,
                content_type=content_type
            )
        except Exception as retry_err:
            print("RETRY EXTRACTION FAILED:", repr(retry_err))

        if extracted and isinstance(extracted, dict):
            # Check for existing timeline events for this specific record to prevent duplicate entries
            existing_events = (
                supabase_admin.table("guest_health_timeline_events")
                .select("id")
                .eq("guest_medical_record_id", record_id)
                .eq("guest_patient_id", clean_guest_id)
                .execute()
            )

            timeline_payload = {
                "guest_patient_id": clean_guest_id,
                "guest_medical_record_id": record_id,
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

            if existing_events.data:
                first_id = existing_events.data[0]["id"]
                supabase_admin.table("guest_health_timeline_events").update(timeline_payload).eq("id", first_id).execute()
                # Remove any accidental duplicates that existed previously for this exact record
                if len(existing_events.data) > 1:
                    excess_ids = [e["id"] for e in existing_events.data[1:]]
                    for eid in excess_ids:
                        supabase_admin.table("guest_health_timeline_events").delete().eq("id", eid).execute()
            else:
                supabase_admin.table("guest_health_timeline_events").insert(timeline_payload).execute()

            flash("Medical record reprocessed and analyzed successfully!", "success")
        else:
            flash("AI extraction could not be completed at this time. Original record is preserved.", "warning")

        return redirect(url_for("doctor_guest_workspace", guest_patient_id=clean_guest_id))

    except Exception as e:
        import traceback
        print("GUEST RETRY RECORD ERROR:", repr(e))
        traceback.print_exc()
        flash("Failed to reprocess medical record.", "error")
        return redirect(url_for("doctor_guest_workspace", guest_patient_id=clean_guest_id))


@app.route("/doctor/guest-workspace/<guest_patient_id>/timeline")
def doctor_guest_timeline(guest_patient_id):
    """
    Retrieve or view guest health timeline.
    Returns JSON if requested via AJAX, or redirects to the workspace timeline tab.
    """
    if "doctor_id" not in session:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.accept_json:
            return {"success": False, "message": "Doctor login required."}, 401
        return redirect(url_for("doctor_login"))

    doctor_id = str(session["doctor_id"]).strip()

    try:
        clean_guest_id = str(uuid.UUID(str(guest_patient_id)))
    except (ValueError, AttributeError):
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.accept_json:
            return {"success": False, "message": "Invalid guest patient identifier."}, 400
        return redirect(url_for("doctor_guest_patient"))

    try:
        # Authorization check
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
                if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.accept_json:
                    return {"success": False, "message": "Access denied."}, 403
                flash("Access denied.", "error")
                return redirect(url_for("doctor_guest_patient"))

        # Fetch timeline events
        timeline_res = (
            supabase_admin.table("guest_health_timeline_events")
            .select("*")
            .eq("guest_patient_id", clean_guest_id)
            .order("event_date", desc=True)
            .execute()
        )
        events = timeline_res.data or []
        for ev in events:
            ev["medical_record_id"] = ev.get("guest_medical_record_id")

        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.accept_json:
            return {"success": True, "timeline_events": events, "count": len(events)}

        return redirect(url_for("doctor_guest_workspace", guest_patient_id=clean_guest_id, _anchor="health-timeline-tab"))

    except Exception as e:
        import traceback
        print("GUEST TIMELINE ERROR:", repr(e))
        traceback.print_exc()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.accept_json:
            return {"success": False, "message": "Failed to fetch timeline events."}, 500
        flash("Failed to load timeline.", "error")
        return redirect(url_for("doctor_guest_workspace", guest_patient_id=clean_guest_id))


@app.route("/doctor/guest-workspace/<guest_patient_id>/conflicts")
def doctor_guest_conflicts(guest_patient_id):
    """
    Retrieve or view guest medical conflict alerts.
    Returns JSON if requested via AJAX, or redirects to the workspace conflicts tab.
    """
    if "doctor_id" not in session:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.accept_json:
            return {"success": False, "message": "Doctor login required."}, 401
        return redirect(url_for("doctor_login"))

    doctor_id = str(session["doctor_id"]).strip()

    try:
        clean_guest_id = str(uuid.UUID(str(guest_patient_id)))
    except (ValueError, AttributeError):
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.accept_json:
            return {"success": False, "message": "Invalid guest patient identifier."}, 400
        return redirect(url_for("doctor_guest_patient"))

    try:
        # Authorization check
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
                if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.accept_json:
                    return {"success": False, "message": "Access denied."}, 403
                flash("Access denied.", "error")
                return redirect(url_for("doctor_guest_patient"))

        # Fetch timeline events
        timeline_res = (
            supabase_admin.table("guest_health_timeline_events")
            .select("*")
            .eq("guest_patient_id", clean_guest_id)
            .order("event_date", desc=True)
            .execute()
        )
        events = timeline_res.data or []
        for ev in events:
            ev["medical_record_id"] = ev.get("guest_medical_record_id")

        conflicts = detect_medical_conflicts(events)
        summary = {
            "total": len(conflicts),
            "high": sum(1 for c in conflicts if c.get("severity") == "high"),
            "medium": sum(1 for c in conflicts if c.get("severity") == "medium"),
            "low": sum(1 for c in conflicts if c.get("severity") == "low")
        }

        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.accept_json:
            return {"success": True, "conflicts": conflicts, "summary": summary}

        return redirect(url_for("doctor_guest_workspace", guest_patient_id=clean_guest_id, _anchor="medical-conflicts-tab"))

    except Exception as e:
        import traceback
        print("GUEST CONFLICTS ERROR:", repr(e))
        traceback.print_exc()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.accept_json:
            return {"success": False, "message": "Failed to detect medical conflicts."}, 500
        flash("Failed to load medical conflict alerts.", "error")
        return redirect(url_for("doctor_guest_workspace", guest_patient_id=clean_guest_id))


@app.route(
    "/doctor/guest-workspace/<guest_patient_id>/ai-assistant",'''

assert old_route_anchor in content, "old_route_anchor not found"
content = content.replace(old_route_anchor, new_routes_code, 1)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully updated app.py with routes and record status!")
