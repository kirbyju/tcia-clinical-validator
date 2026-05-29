import sys

filepath = 'tcia-remapper.py'
with open(filepath, 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if '# PHASE 1: COLUMN HEADERS' in line:
        new_lines.append('# PHASE 1: CICADAS\n')
        new_lines.append('# ============================================================================\n')
        new_lines.append('elif st.session_state.phase == 1:\n')
        new_lines.append('    st.header("CICADAS Dataset Description")\n')
        new_lines.append('    with st.form("cicadas_form"):\n')
        new_lines.append('        c_abstract = st.text_area("Abstract (Max 1,000 Characters)*", value=st.session_state.cicadas.get("abstract", ""), max_chars=1000)\n')
        new_lines.append('        c_intro = st.text_area("Introduction", value=st.session_state.cicadas.get("introduction", ""))\n')
        new_lines.append('        c_m_subjects = st.text_area("Subject Inclusion and Exclusion Criteria", value=st.session_state.cicadas.get("methods_subjects", ""))\n')
        new_lines.append('        c_m_acquisition = st.text_area("Data Acquisition", value=st.session_state.cicadas.get("methods_acquisition", ""))\n')
        new_lines.append('        c_m_analysis = st.text_area("Data Analysis", value=st.session_state.cicadas.get("methods_analysis", ""))\n')
        new_lines.append('        c_usage = st.text_area("Usage Notes", value=st.session_state.cicadas.get("usage_notes", ""))\n')
        new_lines.append('        c_ext = st.text_area("External Resources (Optional)", value=st.session_state.cicadas.get("external_resources", ""))\n')
        new_lines.append('        if st.form_submit_button("Save & Next"):\n')
        new_lines.append('            st.session_state.cicadas = {"abstract": c_abstract, "introduction": c_intro, "methods_subjects": c_m_subjects, "methods_acquisition": c_m_acquisition, "methods_analysis": c_m_analysis, "usage_notes": c_usage, "external_resources": c_ext}\n')
        new_lines.append('            desc = []\n')
        new_lines.append('            if c_intro: desc.append(f"## Introduction\\n{c_intro}")\n')
        new_lines.append('            m = ""\n')
        new_lines.append('            if c_m_subjects: m += f"### Subject Inclusion and Exclusion Criteria\\n{c_m_subjects}\\n\\n"\n')
        new_lines.append('            if c_m_acquisition: m += f"### Data Acquisition\\n{c_m_acquisition}\\n\\n"\n')
        new_lines.append('            if c_m_analysis: m += f"### Data Analysis\\n{c_m_analysis}\\n\\n"\n')
        new_lines.append('            if m: desc.append(f"## Methods\\n{m}")\n')
        new_lines.append('            if c_usage: desc.append(f"## Usage Notes\\n{c_usage}")\n')
        new_lines.append('            if c_ext: desc.append(f"## External Resources\\n{c_ext}")\n')
        new_lines.append('            if st.session_state.metadata["Dataset"]:\n')
        new_lines.append('                ds = st.session_state.metadata["Dataset"][0]\n')
        new_lines.append('                ds.update({"dataset_abstract": c_abstract, "dataset_description": "\\n\\n".join(desc), "introduction": c_intro, "methods_subjects": c_m_subjects, "methods_acquisition": c_m_acquisition, "methods_analysis": c_m_analysis, "usage_notes": c_usage, "external_resources": c_ext})\n')
        new_lines.append('            st.toast("✅ CICADAS saved!"); st.session_state.phase = 2; st.rerun()\n')
        skip = True
        continue

    if skip and '# PHASE 2: PERMISSIBLE VALUES' in line:
        skip = False
        new_lines.append('# PHASE 2: TABULAR DATA STANDARDIZATION\n')
        new_lines.append('# ============================================================================\n')
        new_lines.append('elif st.session_state.phase == 2:\n')
        new_lines.append('    st.header("Tabular Data Standardization")\n')
        continue

    if not skip:
        new_lines.append(line)

with open(filepath, \'w\') as f:
    for line in new_lines:
        f.write(line.replace(\'\\n\', \'\n\'))
