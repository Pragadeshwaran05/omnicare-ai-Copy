with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update medical record card to show file_name and processing status badge
old_card_block = '''                                {% if record.get('uploaded_at') %}

                                    <p class="record-date">
                                        Uploaded:
                                        {{ record.get('uploaded_at') }}
                                    </p>

                                {% endif %}

                            </div>'''

new_card_block = '''                                {% if record.get('file_name') %}
                                    <p class="record-filename" style="font-size: 13px; color: #475467; margin-top: 4px;">
                                        <strong>Document:</strong> {{ record.get('file_name') }}
                                    </p>
                                {% endif %}

                                {% if record.get('uploaded_at') %}
                                    <p class="record-date">
                                        Uploaded: {{ record.get('uploaded_at') }}
                                    </p>
                                {% endif %}

                                <div class="record-status-row" style="margin-top: 8px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                    {% if record.get('processing_status') == 'processed' or record.get('ai_processed') %}
                                        <span class="status-badge" style="background: #ecfdf3; color: #027a48; border: 1px solid #a6f4c5; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;">
                                            ✓ AI Processed
                                        </span>
                                    {% elif record.get('processing_status') == 'failed' or record.get('ai_processed') is sameas false %}
                                        <span class="status-badge" style="background: #fef3f2; color: #b42318; border: 1px solid #fecdca; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;">
                                            ⚠ Processing Failed
                                        </span>
                                        {% if is_guest %}
                                            <a href="{{ url_for('doctor_guest_retry_record', guest_patient_id=patient.get('id'), record_id=record.get('id')) }}"
                                               class="retry-processing-btn"
                                               style="display: inline-flex; align-items: center; gap: 4px; padding: 2px 10px; border-radius: 6px; border: 1px solid #d0d5dd; background: #ffffff; color: #344054; font-size: 12px; font-weight: 600; text-decoration: none; cursor: pointer;">
                                                ⟳ Retry Analysis
                                            </a>
                                        {% endif %}
                                    {% else %}
                                        <span class="status-badge" style="background: #fffaeb; color: #b54708; border: 1px solid #fedf89; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;">
                                            ⏳ Processing Pending
                                        </span>
                                    {% endif %}
                                </div>

                            </div>'''

assert old_card_block in content, "old_card_block not found"
content = content.replace(old_card_block, new_card_block, 1)

# 2. Update trend and conflict links to use is_guest check
# Line 1740: chart.meta[0].record_id
old_trend_single = '''<a href="{{ url_for('doctor_view_medical_record', patient_id=patient.id, record_id=chart.meta[0].record_id) }}"'''
new_trend_single = '''<a href="{% if is_guest %}{{ url_for('doctor_view_guest_medical_record', guest_patient_id=patient.get('id'), record_id=chart.meta[0].record_id) }}{% else %}{{ url_for('doctor_view_medical_record', patient_id=patient.id, record_id=chart.meta[0].record_id) }}{% endif %}"'''
assert old_trend_single in content, "old_trend_single not found"
content = content.replace(old_trend_single, new_trend_single, 1)

# Line 1897: row.record_id
old_trend_table = '''<a href="{{ url_for('doctor_view_medical_record', patient_id=patient.id, record_id=row.record_id) }}"'''
new_trend_table = '''<a href="{% if is_guest %}{{ url_for('doctor_view_guest_medical_record', guest_patient_id=patient.get('id'), record_id=row.record_id) }}{% else %}{{ url_for('doctor_view_medical_record', patient_id=patient.id, record_id=row.record_id) }}{% endif %}"'''
assert old_trend_table in content, "old_trend_table not found"
content = content.replace(old_trend_table, new_trend_table, 1)

# Line 2099: conflict change_from
old_c_from = '''<a href="{{ url_for('doctor_view_medical_record', patient_id=patient.get('id'), record_id=conflict.get('change_from').get('medical_record_id')) }}"'''
new_c_from = '''<a href="{% if is_guest %}{{ url_for('doctor_view_guest_medical_record', guest_patient_id=patient.get('id'), record_id=conflict.get('change_from').get('medical_record_id')) }}{% else %}{{ url_for('doctor_view_medical_record', patient_id=patient.get('id'), record_id=conflict.get('change_from').get('medical_record_id')) }}{% endif %}"'''
assert old_c_from in content, "old_c_from not found"
content = content.replace(old_c_from, new_c_from, 1)

# Line 2180: conflict change_to
old_c_to = '''<a href="{{ url_for('doctor_view_medical_record', patient_id=patient.get('id'), record_id=conflict.get('change_to').get('medical_record_id')) }}"'''
new_c_to = '''<a href="{% if is_guest %}{{ url_for('doctor_view_guest_medical_record', guest_patient_id=patient.get('id'), record_id=conflict.get('change_to').get('medical_record_id')) }}{% else %}{{ url_for('doctor_view_medical_record', patient_id=patient.get('id'), record_id=conflict.get('change_to').get('medical_record_id')) }}{% endif %}"'''
assert old_c_to in content, "old_c_to not found"
content = content.replace(old_c_to, new_c_to, 1)

# Line 2257: lab compare source
old_lab_src = '''<a
                                    href="{{ url_for(
                                        'doctor_view_medical_record',
                                        patient_id=patient.get('id'),
                                        record_id=source.get('medical_record_id')
                                    ) }}"'''
new_lab_src = '''<a
                                    href="{% if is_guest %}{{ url_for('doctor_view_guest_medical_record', guest_patient_id=patient.get('id'), record_id=source.get('medical_record_id')) }}{% else %}{{ url_for('doctor_view_medical_record', patient_id=patient.get('id'), record_id=source.get('medical_record_id')) }}{% endif %}"'''
assert old_lab_src in content, "old_lab_src not found"
content = content.replace(old_lab_src, new_lab_src, 1)

# Line 2332: conflict source
old_c_src = '''<a href="{{ url_for('doctor_view_medical_record', patient_id=patient.get('id'), record_id=source.get('medical_record_id')) }}"'''
new_c_src = '''<a href="{% if is_guest %}{{ url_for('doctor_view_guest_medical_record', guest_patient_id=patient.get('id'), record_id=source.get('medical_record_id')) }}{% else %}{{ url_for('doctor_view_medical_record', patient_id=patient.get('id'), record_id=source.get('medical_record_id')) }}{% endif %}"'''
assert old_c_src in content, "old_c_src not found"
content = content.replace(old_c_src, new_c_src, 1)

with open('templates/doctor/patient_workspace.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully updated templates/doctor/patient_workspace.html!")
