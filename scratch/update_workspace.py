import re

template_path = "templates/doctor/patient_workspace.html"

with open(template_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Identify misplaced conflict section inside health-timeline-tab
misplaced_pattern = re.compile(
    r'\n<!-- ={40,}\s*MEDICAL CONFLICT ALERTS\s*={40,}\s*-->\s*'
    r'<!-- ={40,}\s*MEDICAL CONFLICT ALERTS\s*={40,}\s*-->\s*'
    r'<div class="medical-conflicts-section">.*?'
    r'</div>\s*(?=\s*<!-- ={40,}\s*AI CLINICAL OVERVIEW)',
    re.DOTALL
)

match = misplaced_pattern.search(content)
if not match:
    print("ERROR: Misplaced conflict section pattern not found!")
    exit(1)

print("Found misplaced conflict section, length:", len(match.group(0)))

# Remove it from health-timeline-tab
new_content = misplaced_pattern.sub("\n", content, count=1)

# 2. Define the new #medical-conflicts-tab panel
conflict_panel_html = '''
    <!-- =====================================================
         MEDICAL CONFLICT ALERTS TAB
         ===================================================== -->

    <div id="medical-conflicts-tab"
         class="workspace-tab-content">

        <div class="medical-conflicts-section">

            <!-- HEADER -->
            <div class="medical-conflicts-header">

                <div>
                    <h3>⚠️ Medical Conflict Alerts</h3>

                    <p>
                        {% if conflicts %}
                            Possible medication changes or inconsistencies detected across the patient's authorized records.
                        {% else %}
                            OmniCare AI found no obvious inconsistencies across the available records.
                        {% endif %}
                    </p>
                </div>

                <div class="conflict-count-badge">
                    {{ conflicts|length }}
                </div>

            </div>

            <!-- CLINICAL VERIFICATION NOTICE -->
            <div class="conflict-verification-note section-notice">
                <span>ℹ️</span>
                <p>
                    <strong>Clinical Verification Notice:</strong> OmniCare AI detected alerts are automated aids to highlight possible inconsistencies. All potential conflicts and changes must be checked and confirmed against original medical records before any clinical decisions are made.
                </p>
            </div>

            {% if conflicts %}

                <div class="medical-conflicts-list">

                    {% for conflict in conflicts %}

                        <div class="medical-conflict-card severity-{{ conflict.get('severity', 'medium') }}">

                            <!-- CONFLICT HEADER -->
                            <div class="conflict-card-header">

                                <div class="conflict-icon">
                                    ⚠️
                                </div>

                                <div class="conflict-title-area">

                                    <h4>
                                        {{ conflict.get('title') or 'Possible Medical Conflict' }}
                                    </h4>

                                    <span class="conflict-severity">
                                        {{ conflict.get('severity', 'medium')|upper }}
                                    </span>

                                </div>

                            </div>

                            <!-- DESCRIPTION -->
                            <div class="conflict-description">
                                <p>
                                    {{ conflict.get('description') or 'A possible inconsistency was detected across medical records.' }}
                                </p>
                            </div>

                            <!-- MEDICATION -->
                            {% if conflict.get('medication_name') %}
                                <div class="conflict-medication">
                                    <span class="conflict-label">
                                        💊 Medication
                                    </span>
                                    <strong>
                                        {{ conflict.get('medication_name') }}
                                    </strong>
                                </div>
                            {% endif %}

                            <!-- MEDICATION CHANGE COMPARISON -->
                            {% if conflict.get('conflict_type') == 'medication_change' %}

                                <div class="conflict-sources">

                                    <div class="conflict-label">
                                        📄 Medication History Comparison
                                    </div>

                                    <div class="medication-change-comparison">

                                        <!-- PREVIOUS RECORD -->
                                        <div class="medication-change-card previous">

                                            <div class="medication-change-label">
                                                Previous Record
                                            </div>

                                            <div class="medication-change-date">
                                                {% if conflict.get('change_from', {}).get('event_date') %}
                                                    📅 {{ conflict.get('change_from').get('event_date') }}
                                                {% else %}
                                                    Date unavailable
                                                {% endif %}
                                            </div>

                                            <div class="medication-change-details">

                                                {% if conflict.get('change_from', {}).get('dose') %}
                                                    <div>
                                                        <span>Dose</span>
                                                        <strong>{{ conflict.get('change_from').get('dose') }}</strong>
                                                    </div>
                                                {% endif %}

                                                {% if conflict.get('change_from', {}).get('frequency') %}
                                                    <div>
                                                        <span>Frequency</span>
                                                        <strong>{{ conflict.get('change_from').get('frequency') }}</strong>
                                                    </div>
                                                {% endif %}

                                                {% if conflict.get('change_from', {}).get('duration') %}
                                                    <div>
                                                        <span>Duration</span>
                                                        <strong>{{ conflict.get('change_from').get('duration') }}</strong>
                                                    </div>
                                                {% endif %}

                                                {% if conflict.get('change_from', {}).get('instructions') %}
                                                    <div>
                                                        <span>Instructions</span>
                                                        <strong>{{ conflict.get('change_from').get('instructions') }}</strong>
                                                    </div>
                                                {% endif %}

                                                {% if conflict.get('change_from', {}).get('provider_name') %}
                                                    <div>
                                                        <span>Doctor</span>
                                                        <strong>{{ conflict.get('change_from').get('provider_name') }}</strong>
                                                    </div>
                                                {% endif %}

                                                {% if conflict.get('change_from', {}).get('hospital_name') %}
                                                    <div>
                                                        <span>Hospital</span>
                                                        <strong>{{ conflict.get('change_from').get('hospital_name') }}</strong>
                                                    </div>
                                                {% endif %}

                                            </div>

                                            {% if conflict.get('change_from', {}).get('medical_record_id') and patient.get('id') %}
                                                <a href="{{ url_for('doctor_view_medical_record', patient_id=patient.get('id'), record_id=conflict.get('change_from').get('medical_record_id')) }}"
                                                   target="_blank"
                                                   rel="noopener noreferrer"
                                                   class="conflict-view-original-btn">
                                                    📄 View Original
                                                </a>
                                            {% else %}
                                                <span class="conflict-original-unavailable">
                                                    Original unavailable
                                                </span>
                                            {% endif %}

                                        </div>

                                        <!-- ARROW -->
                                        <div class="medication-change-arrow">
                                            →
                                        </div>

                                        <!-- NEWER RECORD -->
                                        <div class="medication-change-card newer">

                                            <div class="medication-change-label">
                                                Newer Record
                                            </div>

                                            <div class="medication-change-date">
                                                {% if conflict.get('change_to', {}).get('event_date') %}
                                                    📅 {{ conflict.get('change_to').get('event_date') }}
                                                {% else %}
                                                    Date unavailable
                                                {% endif %}
                                            </div>

                                            <div class="medication-change-details">

                                                {% if conflict.get('change_to', {}).get('dose') %}
                                                    <div>
                                                        <span>Dose</span>
                                                        <strong>{{ conflict.get('change_to').get('dose') }}</strong>
                                                    </div>
                                                {% endif %}

                                                {% if conflict.get('change_to', {}).get('frequency') %}
                                                    <div>
                                                        <span>Frequency</span>
                                                        <strong>{{ conflict.get('change_to').get('frequency') }}</strong>
                                                    </div>
                                                {% endif %}

                                                {% if conflict.get('change_to', {}).get('duration') %}
                                                    <div>
                                                        <span>Duration</span>
                                                        <strong>{{ conflict.get('change_to').get('duration') }}</strong>
                                                    </div>
                                                {% endif %}

                                                {% if conflict.get('change_to', {}).get('instructions') %}
                                                    <div>
                                                        <span>Instructions</span>
                                                        <strong>{{ conflict.get('change_to').get('instructions') }}</strong>
                                                    </div>
                                                {% endif %}

                                                {% if conflict.get('change_to', {}).get('provider_name') %}
                                                    <div>
                                                        <span>Doctor</span>
                                                        <strong>{{ conflict.get('change_to').get('provider_name') }}</strong>
                                                    </div>
                                                {% endif %}

                                                {% if conflict.get('change_to', {}).get('hospital_name') %}
                                                    <div>
                                                        <span>Hospital</span>
                                                        <strong>{{ conflict.get('change_to').get('hospital_name') }}</strong>
                                                    </div>
                                                {% endif %}

                                            </div>

                                            {% if conflict.get('change_to', {}).get('medical_record_id') and patient.get('id') %}
                                                <a href="{{ url_for('doctor_view_medical_record', patient_id=patient.get('id'), record_id=conflict.get('change_to').get('medical_record_id')) }}"
                                                   target="_blank"
                                                   rel="noopener noreferrer"
                                                   class="conflict-view-original-btn">
                                                    📄 View Original
                                                </a>
                                            {% else %}
                                                <span class="conflict-original-unavailable">
                                                    Original unavailable
                                                </span>
                                            {% endif %}

                                        </div>

                                    </div>

                                </div>

                            {% else %}

                                <!-- OTHER CONFLICT TYPES -->
                                {% if conflict.get('records') %}

                                    <div class="conflict-sources">

                                        <div class="conflict-label">
                                            📄 Documented Information
                                        </div>

                                        <div class="conflict-records">

                                            {% for source in conflict.get('records') %}

                                                <div class="conflict-record">

                                                    <div class="conflict-record-date">
                                                        {% if source.get('event_date') %}
                                                            📅 {{ source.get('event_date') }}
                                                        {% else %}
                                                            Date unavailable
                                                        {% endif %}
                                                    </div>

                                                    <div class="conflict-record-details">

                                                        {% if source.get('dose') %}
                                                            <strong>Dose: {{ source.get('dose') }}</strong>
                                                        {% endif %}

                                                        {% if source.get('frequency') %}
                                                            <span>Frequency: {{ source.get('frequency') }}</span>
                                                        {% endif %}

                                                        {% if source.get('duration') %}
                                                            <span>Duration: {{ source.get('duration') }}</span>
                                                        {% endif %}

                                                        {% if source.get('instructions') %}
                                                            <span>Instructions: {{ source.get('instructions') }}</span>
                                                        {% endif %}

                                                        {% if source.get('provider_name') %}
                                                            <span>Doctor: {{ source.get('provider_name') }}</span>
                                                        {% endif %}

                                                        {% if source.get('hospital_name') %}
                                                            <span>Hospital: {{ source.get('hospital_name') }}</span>
                                                        {% endif %}

                                                    </div>

                                                    {% if source.get('medical_record_id') and patient.get('id') %}
                                                        <a href="{{ url_for('doctor_view_medical_record', patient_id=patient.get('id'), record_id=source.get('medical_record_id')) }}"
                                                           target="_blank"
                                                           rel="noopener noreferrer"
                                                           class="conflict-view-original-btn">
                                                            📄 View Original
                                                        </a>
                                                    {% else %}
                                                        <span class="conflict-original-unavailable">
                                                            Original unavailable
                                                        </span>
                                                    {% endif %}

                                                </div>

                                            {% endfor %}

                                        </div>

                                    </div>

                                {% endif %}

                            {% endif %}

                            <!-- CARD VERIFICATION NOTE -->
                            <div class="conflict-verification-note">
                                <span>ℹ️</span>
                                <p>
                                    OmniCare AI has detected a possible medication change or inconsistency. Verify the original medical records before making a clinical decision.
                                </p>
                            </div>

                        </div>

                    {% endfor %}

                </div>

            {% else %}

                <!-- EMPTY STATE -->
                <div class="no-medical-conflicts">

                    <div class="no-conflict-icon">
                        ✅
                    </div>

                    <div>
                        <h4>
                            No Conflicts Detected
                        </h4>
                        <p>
                            No obvious inconsistencies were identified in the available medical records.
                            Please note that an absence of detected alerts does not guarantee that a patient is medically safe. Always cross-check clinical details with original documentation before making care decisions.
                        </p>
                    </div>

                </div>

            {% endif %}

        </div>

    </div>
'''

# 3. Insert the panel before AI ASSISTANT TAB
ai_tab_marker = re.compile(
    r'(\n\s*<!-- ={40,}\s*AI ASSISTANT TAB\s*={40,}\s*-->)',
    re.MULTILINE
)

if not ai_tab_marker.search(new_content):
    print("ERROR: AI ASSISTANT TAB marker not found!")
    exit(1)

# We want to insert conflict_panel_html before the FIRST AI ASSISTANT TAB comment
new_content = ai_tab_marker.sub(conflict_panel_html + r'\1', new_content, count=1)

# 4. Replace Workspace Tabs JS
old_js_pattern = re.compile(
    r'/\* ={40,}\s*WORKSPACE TABS\s*={40,}\s*\*/.*?'
    r'navItems\.forEach\(function \(item\) \{.*?'
    r'\}\);\s*(?=\s*/\* ={40,}\s*TIMELINE FILTERS)',
    re.DOTALL
)

if not old_js_pattern.search(new_content):
    print("ERROR: Old JS pattern not found!")
    exit(1)

new_js = '''/* =====================================================
       WORKSPACE TABS
       ===================================================== */

    const navItems =
        document.querySelectorAll(
            ".workspace-nav-item"
        );

    const tabContents =
        document.querySelectorAll(
            ".workspace-tab-content"
        );

    function switchWorkspaceTab(targetId) {
        if (!targetId) {
            console.warn("[OmniCare AI] Tab switch requested with empty target ID.");
            return false;
        }

        const targetPanel =
            document.getElementById(
                targetId
            );

        if (!targetPanel) {
            console.warn(
                "[OmniCare AI] Target tab panel not found for ID:",
                targetId
            );
            return false;
        }

        let foundNav = false;

        navItems.forEach(function (nav) {
            if (nav.getAttribute("data-tab") === targetId) {
                nav.classList.add("active");
                foundNav = true;
            } else {
                nav.classList.remove("active");
            }
        });

        tabContents.forEach(function (tab) {
            tab.classList.remove("active");
        });

        targetPanel.classList.add("active");

        if (!foundNav) {
            console.warn(
                "[OmniCare AI] No navigation button matches data-tab:",
                targetId
            );
        }

        return true;
    }

    navItems.forEach(function (item) {
        item.addEventListener("click", function () {
            const targetId =
                item.getAttribute("data-tab");
            switchWorkspaceTab(targetId);
        });
    });

    // Initialize the active tab on page load
    const activeNav =
        document.querySelector(".workspace-nav-item.active") ||
        navItems[0];

    if (activeNav) {
        const initialTabId =
            activeNav.getAttribute("data-tab");
        switchWorkspaceTab(initialTabId);
    }
'''

new_content = old_js_pattern.sub(new_js, new_content, count=1)

with open(template_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("SUCCESS: Updated templates/doctor/patient_workspace.html successfully!")
