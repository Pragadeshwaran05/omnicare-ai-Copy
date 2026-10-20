import sys

with open("templates/doctor/patient_workspace.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Back button
target1 = """    <!-- BACK -->
    <a href="{{ url_for('doctor_my_patients') }}"
       class="back-to-patients">
        ← Back to My Patients
    </a>"""

replacement1 = """    <!-- BACK -->
    {% if is_guest %}
    <a href="{{ url_for('doctor_guest_patient') }}"
       class="back-to-patients">
        ← Back to Guest Patients
    </a>
    {% else %}
    <a href="{{ url_for('doctor_my_patients') }}"
       class="back-to-patients">
        ← Back to My Patients
    </a>
    {% endif %}"""

assert target1 in content, "target1 not found"
content = content.replace(target1, replacement1, 1)

# 2. Health ID / Guest ID
target2 = """                <p>
                    Health ID:
                    <strong>
                        {{ patient.get('health_id') or 'Not available' }}
                    </strong>
                </p>"""

replacement2 = """                <p>
                    {% if is_guest %}Guest ID:{% else %}Health ID:{% endif %}
                    <strong>
                        {{ patient.get('health_id') or patient.get('guest_code') or 'Not available' }}
                    </strong>
                </p>"""

assert target2 in content, "target2 not found"
content = content.replace(target2, replacement2, 1)

# 3. Access status badge
target3 = """        <div class="workspace-access-status">

            {% if access.get('access_type') == 'temporary' %}"""

replacement3 = """        <div class="workspace-access-status">

            {% if is_guest or access.get('access_type') == 'guest' %}

                <span class="workspace-access-badge guest" style="background: #f3e8ff; color: #6b21a8; border: 1px solid #d8b4fe;">
                    🟣 Guest Patient Record
                </span>

            {% elif access.get('access_type') == 'temporary' %}"""

assert target3 in content, "target3 not found"
content = content.replace(target3, replacement3, 1)

# 4. Access information card
target4 = """        <div class="access-information-item">

            <span class="access-information-label">
                Access Granted
            </span>

            <span class="access-information-value">
                {{ access.get('approved_at') or 'Not available' }}
            </span>

        </div>


        <div class="access-information-item">

            <span class="access-information-label">
                Access Type
            </span>

            <span class="access-information-value">

                {% if access.get('access_type') == 'temporary' %}"""

replacement4 = """        <div class="access-information-item">

            <span class="access-information-label">
                {% if is_guest %}Session Created{% else %}Access Granted{% endif %}
            </span>

            <span class="access-information-value">
                {{ access.get('approved_at') or patient.get('created_at') or 'Not available' }}
            </span>

        </div>


        <div class="access-information-item">

            <span class="access-information-label">
                Access Type
            </span>

            <span class="access-information-value">

                {% if is_guest or access.get('access_type') == 'guest' %}
                    Temporary Guest Session

                {% elif access.get('access_type') == 'temporary' %}"""

assert target4 in content, "target4 not found"
content = content.replace(target4, replacement4, 1)

# 5. Section Header in Records Tab
target5 = """            <div class="workspace-section-header">

                <div>

                    <h2>
                        Authorized Medical Records
                    </h2>

                    <p>
                        Medical records currently available to you
                        under this patient's authorization.
                    </p>

                </div>

                <span class="record-count">
                    {{ records|length }}
                </span>

            </div>"""

replacement5 = """            <div class="workspace-section-header">

                <div>

                    <h2>
                        Authorized Medical Records
                    </h2>

                    <p>
                        {% if is_guest %}
                            Medical records uploaded for this guest patient session.
                        {% else %}
                            Medical records currently available to you
                            under this patient's authorization.
                        {% endif %}
                    </p>

                </div>

                <div style="display: flex; align-items: center; gap: 12px;">
                    {% if is_guest %}
                    <button type="button" class="upload-record-btn" onclick="openGuestUploadModal()" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border: none; border-radius: 8px; background: #6841c6; color: #fff; font-size: 14px; font-weight: 600; cursor: pointer;">
                        <span>＋</span> Upload Medical Record
                    </button>
                    {% endif %}
                    <span class="record-count">
                        {{ records|length }}
                    </span>
                </div>

            </div>"""

assert target5 in content, "target5 not found"
content = content.replace(target5, replacement5, 1)

# 6. View Record in Records Tab
target6 = """                            {% if record.get('file_url') %}

                                <a href="{{ record.get('file_url') }}"
                                   target="_blank"
                                   rel="noopener noreferrer"
                                   class="view-record-btn">

                                    View Record
                                    <span>→</span>

                                </a>

                            {% endif %}"""

replacement6 = """                            {% if record.get('file_url') %}

                                <a href="{{ record.get('file_url') }}"
                                   target="_blank"
                                   rel="noopener noreferrer"
                                   class="view-record-btn">

                                    View Record
                                    <span>→</span>

                                </a>

                            {% elif is_guest and record.get('id') %}

                                <a href="{{ url_for('doctor_view_guest_medical_record', guest_patient_id=patient.get('id'), record_id=record.get('id')) }}"
                                   target="_blank"
                                   rel="noopener noreferrer"
                                   class="view-record-btn">

                                    View Record
                                    <span>→</span>

                                </a>

                            {% elif record.get('id') %}

                                <a href="{{ url_for('doctor_view_medical_record', patient_id=patient.get('id'), record_id=record.get('id')) }}"
                                   target="_blank"
                                   rel="noopener noreferrer"
                                   class="view-record-btn">

                                    View Record
                                    <span>→</span>

                                </a>

                            {% endif %}"""

assert target6 in content, "target6 not found"
content = content.replace(target6, replacement6, 1)

# 7. Original Record in Timeline Tab
target7 = """<div class="event-actions">

    {% if event.get('medical_record_id') %}

        <a href="{{ url_for(
                'doctor_view_medical_record',
                patient_id=patient.get('id'),
                record_id=event.get('medical_record_id')
            ) }}"
           target="_blank"
           rel="noopener noreferrer"
           class="view-original-btn">

            📄 View Original

        </a>

    {% else %}"""

replacement7 = """<div class="event-actions">

    {% if event.get('medical_record_id') %}

        {% if is_guest %}
            <a href="{{ url_for(
                    'doctor_view_guest_medical_record',
                    guest_patient_id=patient.get('id'),
                    record_id=event.get('medical_record_id')
                ) }}"
               target="_blank"
               rel="noopener noreferrer"
               class="view-original-btn">

                📄 View Original

            </a>
        {% else %}
            <a href="{{ url_for(
                    'doctor_view_medical_record',
                    patient_id=patient.get('id'),
                    record_id=event.get('medical_record_id')
                ) }}"
               target="_blank"
               rel="noopener noreferrer"
               class="view-original-btn">

                📄 View Original

            </a>
        {% endif %}

    {% else %}"""

assert target7 in content, "target7 not found"
content = content.replace(target7, replacement7, 1)

# 8. Workspace Config
target8 = """<div
    id="workspace-config"
    data-patient-id="{{ patient.get('id', '') | e }}"
    hidden>
</div>"""

replacement8 = """<div
    id="workspace-config"
    data-patient-id="{{ patient.get('id', '') | e }}"
    data-is-guest="{{ '1' if is_guest else '0' }}"
    data-ai-url="{% if is_guest %}{{ url_for('doctor_guest_ai_assistant', guest_patient_id=patient.get('id')) }}{% else %}{{ url_for('doctor_patient_ai_assistant', patient_id=patient.get('id')) }}{% endif %}"
    data-sources-url="{% if is_guest %}{{ url_for('doctor_guest_ai_sources', guest_patient_id=patient.get('id')) }}{% else %}{{ url_for('doctor_patient_ai_sources', patient_id=patient.get('id')) }}{% endif %}"
    data-trend-url="{% if is_guest %}{{ url_for('doctor_guest_trend_data', guest_patient_id=patient.get('id')) }}{% else %}{{ url_for('doctor_patient_trend_data', patient_id=patient.get('id')) }}{% endif %}"
    data-record-url-template="{% if is_guest %}{{ url_for('doctor_view_guest_medical_record', guest_patient_id=patient.get('id'), record_id='__RECORD_ID__') }}{% else %}{{ url_for('doctor_view_medical_record', patient_id=patient.get('id'), record_id='__RECORD_ID__') }}{% endif %}"
    hidden>
</div>"""

assert target8 in content, "target8 not found"
content = content.replace(target8, replacement8, 1)

# 9. AI Assistant Fetch in JS
target9 = """        const response =
            await fetch(
                `/doctor/patient-workspace/${doctorAIPatientId}/ai-assistant`,"""

replacement9 = """        const aiEndpointUrl =
            (workspaceConfig && workspaceConfig.getAttribute("data-ai-url")) ||
            `/doctor/patient-workspace/${doctorAIPatientId}/ai-assistant`;

        const response =
            await fetch(
                aiEndpointUrl,"""

assert target9 in content, "target9 not found"
content = content.replace(target9, replacement9, 1)

# 10. AI Sources Fetch in JS
target10 = """            const sourceURL =
                `/doctor/patient-workspace/${doctorAIPatientId}/ai-sources`;"""

replacement10 = """            const sourceURL =
                (workspaceConfig && workspaceConfig.getAttribute("data-sources-url")) ||
                `/doctor/patient-workspace/${doctorAIPatientId}/ai-sources`;"""

assert target10 in content, "target10 not found"
content = content.replace(target10, replacement10, 1)

# 11. Trend Data Fetch in JS
target11 = """            const response = await fetch(`/doctor/patient-workspace/${patientId}/trend-data`, {"""

replacement11 = """            const trendEndpointUrl =
                (workspaceConfig && workspaceConfig.getAttribute("data-trend-url")) ||
                `/doctor/patient-workspace/${patientId}/trend-data`;

            const response = await fetch(trendEndpointUrl, {"""

assert target11 in content, "target11 not found"
content = content.replace(target11, replacement11, 1)

# 12. Trend Report Links in JS
target12 = """                const singleMeta = chart.meta && chart.meta[0];
                const recordLink = singleMeta && singleMeta.record_id ?
                    '<a href="/doctor/patient-record/' + patientId + '/' + singleMeta.record_id + '" target="_blank" rel="noopener noreferrer" class="trend-chart-source-link">📄 View Source Report</a>' : "";"""

replacement12 = """                const singleMeta = chart.meta && chart.meta[0];
                const recordUrlTemplate = (workspaceConfig && workspaceConfig.getAttribute("data-record-url-template")) || ('/doctor/patient-record/' + patientId + '/__RECORD_ID__');
                const resolvedRecordUrl = singleMeta && singleMeta.record_id ? recordUrlTemplate.replace('__RECORD_ID__', singleMeta.record_id) : "";
                const recordLink = resolvedRecordUrl ?
                    '<a href="' + resolvedRecordUrl + '" target="_blank" rel="noopener noreferrer" class="trend-chart-source-link">📄 View Source Report</a>' : "";"""

assert target12 in content, "target12 not found"
content = content.replace(target12, replacement12, 1)

target13 = """        rows.forEach(function (row) {
            const actionLink = row.record_id ?
                '<a href="/doctor/patient-record/' + patientId + '/' + row.record_id + '" target="_blank" rel="noopener noreferrer" class="trend-table-action-btn">📄 View Original</a>' :
                '<span style="color: #94a3b8; font-size: 11px;">Unavailable</span>';"""

replacement13 = """        const tableRecordUrlTemplate = (workspaceConfig && workspaceConfig.getAttribute("data-record-url-template")) || ('/doctor/patient-record/' + patientId + '/__RECORD_ID__');
        rows.forEach(function (row) {
            const tableRecordUrl = row.record_id ? tableRecordUrlTemplate.replace('__RECORD_ID__', row.record_id) : "";
            const actionLink = tableRecordUrl ?
                '<a href="' + tableRecordUrl + '" target="_blank" rel="noopener noreferrer" class="trend-table-action-btn">📄 View Original</a>' :
                '<span style="color: #94a3b8; font-size: 11px;">Unavailable</span>';"""

assert target13 in content, "target13 not found"
content = content.replace(target13, replacement13, 1)

# 14. Add Guest Modal and Modal Functions before closing block
modal_html = """
{% if is_guest %}
<!-- =====================================================
     GUEST RECORD UPLOAD MODAL
     ===================================================== -->
<div id="guestUploadModal" class="guest-modal-overlay" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(15,23,42,0.6); z-index:9999; justify-content:center; align-items:center; padding:20px; box-sizing:border-box;">
    <div class="guest-modal-dialog" style="background:#fff; border-radius:16px; width:100%; max-width:600px; max-height:90vh; overflow-y:auto; box-shadow:0 20px 40px rgba(0,0,0,0.2); border:1px solid #e2e8f0; padding:28px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <div style="display:flex; align-items:center; gap:12px;">
                <span style="display:grid; place-items:center; width:38px; height:38px; border-radius:10px; background:#f0eaff; color:#6841c6; font-size:20px;">📤</span>
                <h2 style="margin:0; font-size:19px; color:#1e293b;">Upload Guest Medical Record</h2>
            </div>
            <button type="button" onclick="closeGuestUploadModal()" style="background:none; border:none; font-size:24px; color:#94a3b8; cursor:pointer; line-height:1;">&times;</button>
        </div>

        <form id="modalUploadForm" action="{{ url_for('doctor_guest_upload_records', guest_patient_id=patient.get('id')) }}" method="POST" enctype="multipart/form-data">
            <div class="modal-dropzone" id="modalDropzone" onclick="document.getElementById('modal_medical_file').click()" style="border:2px dashed #c4b5fd; background:#faf8ff; border-radius:12px; padding:26px 16px; text-align:center; cursor:pointer; margin-bottom:18px;">
                <div style="font-size:32px; margin-bottom:8px;">☁️</div>
                <div style="font-weight:600; font-size:14px; margin-bottom:4px;">Click to select file or drag &amp; drop</div>
                <div style="font-size:12px; color:#64748b;">PDF, PNG, JPG, JPEG or WEBP (Max 10 MB)</div>
                <input type="file" id="modal_medical_file" name="medical_file" accept=".pdf,.png,.jpg,.jpeg,.webp" style="display:none;" required>
                <div id="modalFileText" style="margin-top:10px; font-weight:600; color:#6841c6; font-size:13px;">No file selected</div>
            </div>

            <div style="margin-bottom:16px;">
                <label for="modal_title" style="display:block; font-size:13px; font-weight:600; margin-bottom:6px; color:#334155;">Record Title *</label>
                <input type="text" id="modal_title" name="title" placeholder="e.g. Blood Test Report, Prescription" required style="width:100%; box-sizing:border-box; padding:10px 12px; border:1px solid #d1d5db; border-radius:8px; font:inherit;">
            </div>

            <div style="margin-bottom:16px;">
                <label for="modal_record_type" style="display:block; font-size:13px; font-weight:600; margin-bottom:6px; color:#334155;">Record Type *</label>
                <select id="modal_record_type" name="record_type" required style="width:100%; box-sizing:border-box; padding:10px 12px; border:1px solid #d1d5db; border-radius:8px; font:inherit; background:#fff;">
                    <option value="">Select Record Type</option>
                    <option value="Prescription">Prescription</option>
                    <option value="Lab Report">Lab Report</option>
                    <option value="Diagnostic Report">Diagnostic Report</option>
                    <option value="Scan / Imaging">Scan / Imaging</option>
                    <option value="Discharge Summary">Discharge Summary</option>
                    <option value="Medical Certificate">Medical Certificate</option>
                    <option value="Other">Other</option>
                </select>
            </div>

            <div style="margin-bottom:22px;">
                <label for="modal_description" style="display:block; font-size:13px; font-weight:600; margin-bottom:6px; color:#334155;">Clinical Notes / Description (Optional)</label>
                <textarea id="modal_description" name="description" rows="2" placeholder="Optional notes about this document..." style="width:100%; box-sizing:border-box; padding:10px 12px; border:1px solid #d1d5db; border-radius:8px; font:inherit;"></textarea>
            </div>

            <div style="display:flex; justify-content:flex-end; gap:10px;">
                <button type="button" onclick="closeGuestUploadModal()" style="padding:9px 16px; border:1px solid #cbd5e1; background:#fff; color:#475569; border-radius:8px; font-weight:600; cursor:pointer;">Cancel</button>
                <button type="submit" id="modalSubmitBtn" style="padding:9px 20px; border:none; background:#6841c6; color:#fff; border-radius:8px; font-weight:600; cursor:pointer;">Upload &amp; Analyze with AI</button>
            </div>
        </form>
    </div>
</div>

<script>
window.openGuestUploadModal = function() {
    const modal = document.getElementById("guestUploadModal");
    if (modal) modal.style.display = "flex";
};
window.closeGuestUploadModal = function() {
    const modal = document.getElementById("guestUploadModal");
    if (modal) modal.style.display = "none";
};

document.addEventListener("DOMContentLoaded", function() {
    const modalFileInput = document.getElementById("modal_medical_file");
    const modalDropzone = document.getElementById("modalDropzone");
    const modalFileText = document.getElementById("modalFileText");
    const modalForm = document.getElementById("modalUploadForm");
    const modalSubmitBtn = document.getElementById("modalSubmitBtn");

    if (modalFileInput && modalFileText) {
        modalFileInput.addEventListener("change", function() {
            if (modalFileInput.files && modalFileInput.files[0]) {
                const f = modalFileInput.files[0];
                const mb = (f.size / (1024 * 1024)).toFixed(2);
                modalFileText.textContent = `✓ Selected: ${f.name} (${mb} MB)`;
                modalFileText.style.color = "#187342";
            } else {
                modalFileText.textContent = "No file selected";
                modalFileText.style.color = "#6841c6";
            }
        });
    }

    if (modalDropzone) {
        ["dragenter", "dragover"].forEach(evt => {
            modalDropzone.addEventListener(evt, e => {
                e.preventDefault();
                e.stopPropagation();
                modalDropzone.style.background = "#f3e8ff";
            }, false);
        });
        ["dragleave", "drop"].forEach(evt => {
            modalDropzone.addEventListener(evt, e => {
                e.preventDefault();
                e.stopPropagation();
                modalDropzone.style.background = "#faf8ff";
            }, false);
        });
        modalDropzone.addEventListener("drop", e => {
            if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                modalFileInput.files = e.dataTransfer.files;
                const f = e.dataTransfer.files[0];
                const mb = (f.size / (1024 * 1024)).toFixed(2);
                modalFileText.textContent = `✓ Selected: ${f.name} (${mb} MB)`;
                modalFileText.style.color = "#187342";
            }
        });
    }

    if (modalForm) {
        modalForm.addEventListener("submit", function(e) {
            if (!modalFileInput.files || modalFileInput.files.length === 0) {
                e.preventDefault();
                alert("Please select a medical file to upload.");
                return false;
            }
            if (modalFileInput.files[0].size > 10 * 1024 * 1024) {
                e.preventDefault();
                alert("The selected file exceeds 10 MB limit.");
                return false;
            }
            if (modalSubmitBtn) {
                modalSubmitBtn.disabled = true;
                modalSubmitBtn.innerHTML = `<span>⏳</span> <span>Uploading &amp; Analyzing...</span>`;
                modalSubmitBtn.style.opacity = "0.75";
                modalSubmitBtn.style.cursor = "not-allowed";
            }
        });
    }
});
</script>
{% endif %}
"""

assert "{% endblock %}" in content, "{% endblock %} not found"
content = content.replace("{% endblock %}", modal_html + "\n{% endblock %}", 1)

with open("templates/doctor/patient_workspace.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated templates/doctor/patient_workspace.html successfully!")
