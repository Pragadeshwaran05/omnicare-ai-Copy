import json
import os
import time
from typing import Any, Dict, Optional
from google import genai

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
# ============================================================
# GEMINI CONFIGURATION
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY environment variable is not configured."
    )


client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ============================================================
# MODEL
# ============================================================

MODEL_NAME = "gemini-3.5-flash-lite"
# Number of attempts for temporary Gemini failures
MAX_RETRIES = 3


# ============================================================
# MEDICAL EXTRACTION PROMPT
# ============================================================

MEDICAL_EXTRACTION_PROMPT = """
You are a medical document information extraction system.

Analyze the provided medical document and extract ONLY information
that is explicitly present in the document.

The document may be:

- Doctor consultation
- Prescription
- Laboratory report
- Diagnostic report
- Discharge summary
- Medical certificate
- Handwritten prescription
- Other medical document

IMPORTANT RULES:

1. Do NOT invent medical information.
2. Do NOT guess unclear handwriting.
3. If information is missing, return null.
4. Extract the actual medical event date when present.
5. Do NOT use the upload date as the medical event date.
6. Extract medications exactly as documented.
7. Extract investigations/tests exactly as documented.
8. Extract diagnoses only when explicitly documented.
9. Extract follow-up instructions when explicitly documented.
10. For unclear handwriting, use null rather than guessing.
11. Return valid JSON only.

Allowed event types:

- consultation
- diagnosis
- investigation
- medication
- follow_up
- hospitalization
- other

Return this exact structure:

{
    "event_date": null,
    "event_type": "other",
    "provider_name": null,
    "hospital_name": null,
    "diagnosis": null,
    "clinical_findings": null,
    "investigations": [],
    "medications": [],
    "follow_up": null,
    "clinical_summary": null
}

Medication object:

{
    "name": null,
    "dose": null,
    "frequency": null,
    "route": null,
    "duration": null,
    "instructions": null
}

Investigation object:

{
    "name": null,
    "result": null,
    "unit": null,
    "reference_range": null
}
"""


# ============================================================
# VALIDATE EXTRACTION
# ============================================================

def _validate_extraction(data: Dict[str, Any]) -> Dict[str, Any]:

    defaults = {
        "event_date": None,
        "event_type": "other",
        "provider_name": None,
        "hospital_name": None,
        "diagnosis": None,
        "clinical_findings": None,
        "investigations": [],
        "medications": [],
        "follow_up": None,
        "clinical_summary": None
    }

    for field, default in defaults.items():

        if field not in data:
            data[field] = default

    if not isinstance(data["investigations"], list):
        data["investigations"] = []

    if not isinstance(data["medications"], list):
        data["medications"] = []

    allowed_event_types = {
        "consultation",
        "diagnosis",
        "investigation",
        "medication",
        "follow_up",
        "hospitalization",
        "other"
    }

    if data["event_type"] not in allowed_event_types:
        data["event_type"] = "other"

    return data


# ============================================================
# CHECK WHETHER ERROR SHOULD BE RETRIED
# ============================================================

def _is_retryable_error(error: Exception) -> bool:

    error_text = str(error).upper()

    retryable_errors = [
        "503",
        "UNAVAILABLE",
        "429",
        "RESOURCE_EXHAUSTED",
        "500",
        "INTERNAL",
        "DEADLINE",
        "TIMEOUT"
    ]

    return any(
        error_code in error_text
        for error_code in retryable_errors
    )


# ============================================================
# MAIN PROCESSOR
# ============================================================

def process_medical_document(
    file_bytes: bytes,
    filename: str,
    content_type: Optional[str] = None
) -> Dict[str, Any]:

    if not file_bytes:
        raise ValueError("Medical document is empty.")

    if not filename:
        raise ValueError("Medical document filename is missing.")

    # --------------------------------------------------------
    # Determine MIME type
    # --------------------------------------------------------

    mime_type = content_type

    if not mime_type:

        extension = filename.rsplit(".", 1)[-1].lower()

        mime_map = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp"
        }

        mime_type = mime_map.get(
            extension,
            "application/octet-stream"
        )

    supported_types = {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/webp"
    }

    if mime_type not in supported_types:
        raise ValueError(
            f"Unsupported medical document type: {mime_type}"
        )

    print("=" * 70)
    print("AI MEDICAL DOCUMENT PROCESSING")
    print("=" * 70)
    print("Filename:", filename)
    print("Content type:", mime_type)
    print("=" * 70)

    # --------------------------------------------------------
    # Create Gemini document part directly from bytes
    # --------------------------------------------------------

    document_part = types.Part.from_bytes(
        data=file_bytes,
        mime_type=mime_type
    )

    # --------------------------------------------------------
    # Generate structured medical extraction
    # With automatic retry for temporary failures
    # --------------------------------------------------------

    response = None

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            print(
                f"Gemini processing attempt "
                f"{attempt}/{MAX_RETRIES}"
            )

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[
                    MEDICAL_EXTRACTION_PROMPT,
                    document_part
                ],
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json"
                )
            )

            print("Gemini response received.")

            break

        except Exception as error:

            print("=" * 70)
            print("GEMINI PROCESSING ERROR")
            print("=" * 70)
            print("Attempt:", attempt)
            print("Error:", repr(error))
            print("=" * 70)

            # ------------------------------------------------
            # Do not retry permanent errors
            # ------------------------------------------------

            if not _is_retryable_error(error):

                raise

            # ------------------------------------------------
            # Stop after final attempt
            # ------------------------------------------------

            if attempt >= MAX_RETRIES:

                print(
                    "Gemini failed after "
                    f"{MAX_RETRIES} attempts."
                )

                raise

            # ------------------------------------------------
            # Exponential backoff
            #
            # Attempt 1 → wait 2 seconds
            # Attempt 2 → wait 4 seconds
            # ------------------------------------------------

            wait_seconds = 2 ** attempt

            print(
                f"Temporary Gemini error detected."
            )

            print(
                f"Waiting {wait_seconds} seconds "
                f"before retry..."
            )

            time.sleep(wait_seconds)

    # --------------------------------------------------------
    # Validate response
    # --------------------------------------------------------

    if not response or not response.text:

        raise RuntimeError(
            "Gemini returned an empty response."
        )

    # --------------------------------------------------------
    # Parse JSON
    # --------------------------------------------------------

    try:

        extracted_data = json.loads(
            response.text
        )

    except json.JSONDecodeError as error:

        print("RAW GEMINI RESPONSE:")
        print(response.text)

        raise RuntimeError(
            "Gemini returned invalid JSON."
        ) from error

    # --------------------------------------------------------
    # Validate structure
    # --------------------------------------------------------

    extracted_data = _validate_extraction(
        extracted_data
    )

    print("Medical information extracted successfully.")

    print("EXTRACTED DATA:")

    print(
        json.dumps(
            extracted_data,
            indent=2,
            ensure_ascii=False
        )
    )

    print("=" * 70)

    return extracted_data