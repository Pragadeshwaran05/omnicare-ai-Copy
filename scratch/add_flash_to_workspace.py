with open("templates/doctor/patient_workspace.html", "r", encoding="utf-8") as f:
    content = f.read()

target = """    <!-- =====================================================
         PATIENT HEADER
         ===================================================== -->"""

replacement = """    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            <div class="workspace-flash-messages" style="margin-bottom: 22px;">
                {% for category, message in messages %}
                    <div class="workspace-flash-message workspace-flash-{{ category }}"
                         style="padding: 13px 18px; border-radius: 10px; margin-bottom: 10px; font-weight: 500; font-size: 14px; display: flex; align-items: center; gap: 10px; {% if category == 'success' %}background: #e7f7ed; color: #187342; border: 1px solid #bbf7d0;{% elif category == 'warning' %}background: #fffbeb; color: #b45309; border: 1px solid #fde68a;{% else %}background: #fff0f0; color: #a12525; border: 1px solid #fecaca;{% endif %}">
                        <span>{% if category == 'success' %}✓{% elif category == 'warning' %}⚠️{% else %}❌{% endif %}</span>
                        <span>{{ message }}</span>
                    </div>
                {% endfor %}
            </div>
        {% endif %}
    {% endwith %}


    <!-- =====================================================
         PATIENT HEADER
         ===================================================== -->"""

assert target in content, "target not found"
content = content.replace(target, replacement, 1)

with open("templates/doctor/patient_workspace.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Added flash messages block to patient_workspace.html successfully!")
