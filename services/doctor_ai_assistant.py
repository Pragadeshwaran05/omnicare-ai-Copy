
# ============================================================
# OMNICARE AI - DOCTOR HEALTH ASSISTANT
# ============================================================

import os
import json
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors


# ------------------------------------------------------------
# LOAD ENVIRONMENT
# ------------------------------------------------------------

load_dotenv()


# ------------------------------------------------------------
# GEMINI CONFIGURATION
# ------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_NAME = "gemini-3.5-flash-lite"

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not configured."
    )

client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options={
        "timeout": 30000
    }
)


# ------------------------------------------------------------
# BUILD PATIENT CONTEXT
# ------------------------------------------------------------

def build_patient_context(timeline_events):

    if not timeline_events:
        return (
            "No processed clinical timeline events are "
            "available for this patient."
        )

    context_parts = []

    for index, event in enumerate(
        timeline_events,
        start=1
    ):

        event_data = {
            "event_date": event.get("event_date"),
            "event_type": event.get("event_type"),
            "provider_name": event.get("provider_name"),
            "hospital_name": event.get("hospital_name"),
            "diagnosis": event.get("diagnosis"),
            "clinical_findings": event.get("clinical_findings"),
            "investigations": event.get("investigations") or [],
            "medications": event.get("medications") or [],
            "follow_up": event.get("follow_up"),
            "clinical_summary": event.get("clinical_summary"),
        }

        context_parts.append(
            f"CLINICAL EVENT {index}:\n"
            + json.dumps(
                event_data,
                ensure_ascii=False,
                indent=2,
                default=str
            )
        )

    return "\n\n".join(context_parts)


# ------------------------------------------------------------
# ASK DOCTOR AI ASSISTANT
# ------------------------------------------------------------

def ask_doctor_ai(question, timeline_events):

    patient_context = build_patient_context(
        timeline_events
    )

    # --------------------------------------------------------
    # DEBUGGING
    # --------------------------------------------------------

    print("\n========== DOCTOR AI DEBUG ==========")
    print("Timeline event count:", len(timeline_events))

    for event in timeline_events:
        print({
            "event_date": event.get("event_date"),
            "medical_record_id": event.get("medical_record_id"),
            "diagnosis": event.get("diagnosis"),
            "investigations": event.get("investigations"),
            "medications": event.get("medications")
        })

    print("\n========== GENERATED PATIENT CONTEXT ==========")
    print(patient_context)
    print("======================================\n")

    # --------------------------------------------------------
    # SYSTEM INSTRUCTIONS
    # --------------------------------------------------------

    prompt = f"""
You are OmniCare AI, a medical-record understanding
assistant for a doctor.

Your task is to help the doctor understand the
authorized patient's documented medical history.

IMPORTANT RULES:

1. Use ONLY the patient information provided
   in the clinical timeline below.

2. Never invent diagnoses, medications,
   investigations, dates, doctors, results,
   or follow-up information.

3. If requested information is not present, clearly say:
   "This is not documented in the available patient records."

4. Do not use information from any other patient.

5. Keep answers concise and clinically useful.

6. When appropriate, mention the medical event date.

7. For medications, provide the documented name,
   dose, frequency, duration, and instructions when available.

8. For investigations, report only results documented
   in the supplied records.

9. Do not make a new medical diagnosis.

10. Do not claim a treatment is medically appropriate
    unless that conclusion is explicitly documented.

11. Clearly distinguish documented facts from
    anything that cannot be determined.

12. The doctor can verify details against the original
    medical record.

13. Treat every clinical event as a separate record.
    Never transfer results or dates between events.

14. For comparison questions, report each requested
    event date and its corresponding values separately.

15. Use only explicitly documented event dates.
    Never infer a date from another event.

PATIENT CLINICAL TIMELINE:

{patient_context}

DOCTOR'S QUESTION:

{question}

Provide a concise answer using only the supplied records.
"""


    # --------------------------------------------------------
    # GEMINI REQUEST WITH RETRIES
    # --------------------------------------------------------

    max_attempts = 3

    for attempt in range(max_attempts):

        try:
            print(
                f"Doctor AI: Gemini request "
                f"{attempt + 1}/{max_attempts}"
            )

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )

            # --------------------------------------------
            # EXTRACT RESPONSE
            # --------------------------------------------

            answer = getattr(
                response,
                "text",
                None
            )

            if answer and answer.strip():
                return answer.strip()

            print(
                "Doctor AI: Gemini returned an empty response."
            )

            return (
                "I could not generate an answer from "
                "the available patient records. "
                "Please try again."
            )

        except errors.ServerError as e:

            print(
                f"Gemini server error on attempt "
                f"{attempt + 1}/{max_attempts}: {e}"
            )

            if attempt < max_attempts - 1:
                wait_seconds = 2 * (attempt + 1)

                print(
                    f"Retrying in {wait_seconds} seconds..."
                )

                time.sleep(wait_seconds)

            else:
                print(
                    "Doctor AI: Gemini remains unavailable "
                    "after all retry attempts."
                )

                return (
                    "The AI service is temporarily busy. "
                    "Your patient records have not been changed. "
                    "Please try again shortly."
                )

        except Exception as e:

            print(
                "Doctor AI generation error:",
                repr(e)
            )

            return (
                "I couldn't process this request right now. "
                "Please try again shortly."
            )

    return (
        "The AI service is temporarily unavailable. "
        "Please try again shortly."
    )
