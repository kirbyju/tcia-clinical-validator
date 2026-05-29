import sys
import os
import re

filepath = 'tcia-remapper.py'
with open(filepath, 'r') as f:
    content = f.read()

# 1. Phase Names and Sidebar
content = content.replace(
    'phase_names = ["Phase 0: Summary Metadata", "Phase 1: Column Headers", "Phase 2: Permissible Values"]',
    'phase_names = ["Summary Metadata", "CICADAS", "Tabular Data Standardization"]'
)
content = content.replace('st.sidebar.button("📋 Phase 0: Summary Metadata")', 'st.sidebar.button("📋 Summary Metadata")')
content = content.replace('st.sidebar.button("🔗 Phase 1: Column Headers")', 'st.sidebar.button("📝 CICADAS")')
content = content.replace('st.sidebar.button("✅ Phase 2: Permissible Values")', 'st.sidebar.button("📊 Tabular Data Standardization")')

# 2. Phase 0 UI
content = content.replace('st.header("Phase 0: Summary Metadata")', 'st.header("Summary Metadata")')
content = content.replace('st.subheader("Welcome to Phase 0")', 'st.subheader("Welcome to Summary Metadata")')
content = content.replace('"CICADAS": "📋 CICADAS",', '')

# 3. Proposal Import
old_import = """                if not import_df.empty:
                    proposal_data = import_df.iloc[0].to_dict()
                    st.session_state.proposal_raw_data = proposal_data

                    # Map Dataset
                    study_val = proposal_data.get('adult_or_childhood_study', '')
                    if isinstance(study_val, str) and study_val.startswith('[') and study_val.endswith(']'):
                        try:
                            study_val = ast.literal_eval(study_val)
                        except:
                            pass

                    # Handle funding sources
                    f_agency = proposal_data.get('funding_agency', '')
                    f_prog = proposal_data.get('funding_source_program_name', '')
                    f_grant = proposal_data.get('grant_id', '')

                    ds_data = {
                        'dataset_long_name': proposal_data.get('Title', ''),
                        'dataset_short_name': proposal_data.get('Nickname', ''),
                        'dataset_abstract': proposal_data.get('Abstract', ''),
                        'dataset_description': '', # No longer import description from proposal
                        'adult_or_childhood_study': study_val,
                        'acknowledgements': proposal_data.get('acknowledgements') or proposal_data.get('acknowledgments') or '',
                        'funding_agency': f_agency,
                        'funding_source_program_name': f_prog,
                        'grant_id': f_grant
                    }"""

new_import = """                if not import_df.empty:
                    proposal_data = {}
                    for k, v in import_df.iloc[0].to_dict().items():
                        if pd.isna(v) or str(v).lower() == 'nan':
                            proposal_data[k] = ""
                        elif isinstance(v, str) and v.startswith('[') and v.endswith(']'):
                            try: proposal_data[k] = ast.literal_eval(v)
                            except: proposal_data[k] = v
                        else:
                            proposal_data[k] = v
                    st.session_state.proposal_raw_data = proposal_data
                    ds_data = {
                        'dataset_long_name': proposal_data.get('Title', ''),
                        'dataset_short_name': proposal_data.get('Nickname', ''),
                        'dataset_abstract': proposal_data.get('Abstract', ''),
                        'dataset_description': '',
                        'adult_or_childhood_study': proposal_data.get('adult_or_childhood_study', []),
                        'acknowledgements': proposal_data.get('acknowledgements') or proposal_data.get('acknowledgments') or '',
                        'funding_agency': proposal_data.get('funding_agency', ''),
                        'funding_source_program_name': proposal_data.get('funding_source_program_name', ''),
                        'grant_id': proposal_data.get('grant_id', ''),
                        'why_tcia': proposal_data.get('why_tcia', [])
                    }"""
content = content.replace(old_import, new_import)

# 4. Render Dynamic Form Multiselect
old_render = """        if prop_name in permissible_values:
            options = permissible_values[prop_name]
            # Handle list of dicts from MDF parser
            if options and isinstance(options[0], dict):
                option_labels = [f"{o['value']}" for o in options]
                if not is_required:
                    option_labels = [""] + option_labels

                if prop_name == 'adult_or_childhood_study':
                    # Ensure default_val is a list for multiselect
                    if not isinstance(default_val, list):
                        if isinstance(default_val, str) and default_val.startswith('[') and default_val.endswith(']'):
                            try:
                                default_val = ast.literal_eval(default_val)
                            except:
                                default_val = [default_val] if default_val else []
                        else:
                            default_val = [default_val] if default_val else []

                    selected = st.multiselect(label, options=option_labels, default=default_val, help=help_text, disabled=disabled)
                else:
                    # Find index of default value
                    current_val = str(default_val) if default_val else ""
                    try:
                        default_idx = option_labels.index(current_val)
                    except ValueError:
                        default_idx = 0

                    selected = st.selectbox(label, options=option_labels, index=default_idx, help=help_text, disabled=disabled)
                form_data[prop_name] = selected
            else:
                if prop_name == 'adult_or_childhood_study':
                    if not isinstance(default_val, list):
                        default_val = [default_val] if default_val else []
                    selected = st.multiselect(label, options=options, default=default_val, help=help_text, disabled=disabled)
                else:
                    if not is_required:
                        options = [""] + options
                    try:
                        default_idx = options.index(default_val)
                    except ValueError:
                        default_idx = 0
                    selected = st.selectbox(label, options=options, index=default_idx, help=help_text, disabled=disabled)
                form_data[prop_name] = selected"""

new_render = """        if prop_name in permissible_values:
            options = permissible_values[prop_name]
            if options and isinstance(options[0], dict):
                option_labels = [f"{o['value']}" for o in options]
            else:
                option_labels = options
            is_multiselect = prop_name in ['adult_or_childhood_study', 'why_tcia', 'disease_site', 'diagnosis']
            if is_multiselect:
                if not isinstance(default_val, list):
                    if isinstance(default_val, str) and default_val.startswith('[') and default_val.endswith(']'):
                        try: default_val = ast.literal_eval(default_val)
                        except: default_val = []
                    elif isinstance(default_val, str) and default_val:
                        default_val = [v.strip() for v in default_val.split(',')]
                    else: default_val = [default_val] if default_val else []
                default_val = [v for v in default_val if v in option_labels]
                selected = st.multiselect(label, options=option_labels, default=default_val, help=help_text, disabled=disabled)
            else:
                if not is_required: option_labels = [""] + option_labels
                current_val = str(default_val) if default_val else ""
                try: default_idx = option_labels.index(current_val)
                except ValueError: default_idx = 0
                selected = st.selectbox(label, options=option_labels, index=default_idx, help=help_text, disabled=disabled)
            form_data[prop_name] = selected"""
content = content.replace(old_render, new_render)

# 5. Investigator Display
old_inv = """                with col1:
                    st.write(f"{idx+1}. {inv.get('first_name', '')} {inv.get('last_name', '')} ({inv.get('email', '')}) - {inv.get('organization_name', '')}")"""
new_inv = """                with col1:
                    email = inv.get('email', ''); orcid = inv.get('person_orcid', '')
                    contact_info = email if email else orcid
                    display_contact = f" ({contact_info})" if contact_info else ""
                    st.write(f"{idx+1}. {inv.get('first_name', '')} {inv.get('last_name', '')}{display_contact} - {inv.get('organization_name', '')}")"""
content = content.replace(old_inv, new_inv)

# 6. Metadata Recap
old_recap = """                                display_val = ", ".join(map(str, value)) if isinstance(value, list) else value"""
new_recap = """                                if isinstance(value, list): display_val = ", ".join(map(str, value))
                                elif pd.isna(value) or str(value).lower() == 'nan': display_val = ""
                                else: display_val = value"""
content = content.replace(old_recap, new_recap)

# 7. Navigation Buttons
content = content.replace('if st.button("➡️ Proceed to Phase 1", use_container_width=True, type="primary"):', 'if st.button("➡️ Proceed to CICADAS", use_container_width=True, type="primary"):')
content = content.replace('st.session_state.phase0_step = \'CICADAS\'', 'st.session_state.phase0_step = \'Investigator\'')

# Find whole Phase 1 and Phase 2 sections and replace
phase_1_2_pattern = re.compile(r'# PHASE 1: COLUMN HEADERS.*?# Footer', re.DOTALL)
new_phase_1_2 = """# PHASE 1: CICADAS
# ============================================================================
elif st.session_state.phase == 1:
    st.header("CICADAS Dataset Description")
    st.markdown(\"\"\"
    Follow the [CICADAS checklist](https://cancerimagingarchive.net/cicadas) to ensure your dataset
    is comprehensive and optimally discoverable.
    \"\"\")
    with st.form("cicadas_form"):
        st.write("### Abstract")
        c_abstract = st.text_area("Abstract (Max 1,000 Characters)*", value=st.session_state.cicadas.get('abstract', ''), max_chars=1000, label_visibility="collapsed")
        st.write("### Introduction")
        c_intro = st.text_area("Introduction", value=st.session_state.cicadas.get('introduction', ''), label_visibility="collapsed")
        st.write("### Methods")
        c_m_subjects = st.text_area("Subject Inclusion and Exclusion Criteria", value=st.session_state.cicadas.get('methods_subjects', ''))
        c_m_acquisition = st.text_area("Data Acquisition", value=st.session_state.cicadas.get('methods_acquisition', ''))
        c_m_analysis = st.text_area("Data Analysis", value=st.session_state.cicadas.get('methods_analysis', ''))
        st.write("### Usage Notes")
        c_usage = st.text_area("Usage Notes", value=st.session_state.cicadas.get('usage_notes', ''))
        st.write("### External Resources")
        c_ext = st.text_area("External Resources (Optional)", value=st.session_state.cicadas.get('external_resources', ''))
        if st.form_submit_button("Save & Next"):
            st.session_state.cicadas = {'abstract': c_abstract, 'introduction': c_intro, 'methods_subjects': c_m_subjects, 'methods_acquisition': c_m_acquisition, 'methods_analysis': c_m_analysis, 'usage_notes': c_usage, 'external_resources': c_ext}
            desc = []
            if c_intro: desc.append(f"## Introduction\n{c_intro}")
            methods_content = ""
            if c_m_subjects: methods_content += f"### Subject Inclusion and Exclusion Criteria\n{c_m_subjects}\n\n"
            if c_m_acquisition: methods_content += f"### Data Acquisition\n{c_m_acquisition}\n\n"
            if c_m_analysis: methods_content += f"### Data Analysis\n{c_m_analysis}\n\n"
            if methods_content: desc.append(f"## Methods\n{methods_content}")
            if c_usage: desc.append(f"## Usage Notes\n{c_usage}")
            if c_ext: desc.append(f"## External Resources\n{c_ext}")
            if st.session_state.metadata['Dataset']:
                ds = st.session_state.metadata['Dataset'][0]
                ds.update({'dataset_abstract': c_abstract, 'dataset_description': "\n\n".join(desc), 'introduction': c_intro, 'methods_subjects': c_m_subjects, 'methods_acquisition': c_m_acquisition, 'methods_analysis': c_m_analysis, 'usage_notes': c_usage, 'external_resources': c_ext})
            st.toast("✅ CICADAS information saved!")
            st.session_state.phase = 2; st.rerun()

# ============================================================================
# PHASE 2: TABULAR DATA STANDARDIZATION
# ============================================================================
elif st.session_state.phase == 2:
    st.header("Tabular Data Standardization")
    uploaded_file = st.file_uploader("Upload your source data file (CSV, TSV, or Excel)", type=['csv', 'tsv', 'xlsx', 'xls'])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith('.tsv'): df = pd.read_csv(uploaded_file, sep='\\t')
            else:
                excel = pd.ExcelFile(uploaded_file)
                df = pd.read_excel(uploaded_file, sheet_name=st.selectbox("Select sheet:", excel.sheet_names) if len(excel.sheet_names) > 1 else excel.sheet_names[0])
            if df is not None:
                df = df.dropna(how='all').dropna(axis=1, how='all')
                if len(df) > 1 and df.iloc[0].count() == 1 and df.iloc[1].count() > 1:
                    header = df.iloc[1]; df = df[2:]; df.columns = header
                df.columns = [str(c).strip() for c in df.columns]
                df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
                st.session_state.uploaded_data = df
                st.success(f"✅ Loaded data"); st.dataframe(df.head(10))
            st.subheader("Column Mapping")
            all_props = {}
            for e, props in schema.items():
                if e in st.session_state.metadata: continue
                for p in props:
                    if "." not in p['Property']: all_props[f"{e}.{p['Property']}"] = p
            mapping_data = []
            for col in df.columns:
                c1, c2, c3 = st.columns([3, 4, 2])
                with c1: st.write(f"**{col}**")
                with c2:
                    curr = next((t for t, s in st.session_state.column_mapping.items() if s == col), "(Skip this column)")
                    sel = st.selectbox("Target", options=["(Skip this column)"] + list(all_props.keys()), index=(["(Skip this column)"] + list(all_props.keys())).index(curr) if curr in (["(Skip this column)"] + list(all_props.keys())) else 0, key=f"m_{col}", label_visibility="collapsed")
                    if sel != "(Skip this column)": mapping_data.append((sel, col))
                with c3:
                    if sel != "(Skip this column)": st.write("✅ Required" if all_props[sel].get('Required/optional') == 'R' else "⚪ Optional")
            if st.button("✅ Confirm Mapping", type="primary"):
                st.session_state.column_mapping = {t: s for t, s in mapping_data}
                st.session_state.structure_approved = True
                conflicts = check_metadata_conflict(st.session_state.metadata, df, st.session_state.column_mapping)
                if conflicts:
                    for c in conflicts: st.warning(f"Conflict: {c['entity']}.{c['property']}")
            if st.session_state.structure_approved:
                st.subheader("Value Standardization")
                df = st.session_state.uploaded_data
                p_ids = {t.split(".")[0].lower(): s for t, s in st.session_state.column_mapping.items() if "." in t and (t.split(".")[1].lower() == f"{t.split('.')[0].lower()}_id" or t.split(".")[1].lower() == "id")}
                for e, props in schema.items():
                    for p in props:
                        if "." in p['Property']:
                            target = p['Property'].split(".")[0].lower()
                            if target in p_ids:
                                full = f"{e}.{p['Property']}"
                                if full not in st.session_state.column_mapping: st.session_state.column_mapping[full] = p_ids[target]
                split_data = split_data_by_schema(df, st.session_state.column_mapping, schema)
                for e, edf in split_data.items():
                    for r, ri in relationships.items():
                        for end in ri.get('Ends', []):
                            if end['Src'] == e and end['Dst'] in st.session_state.metadata:
                                meta = st.session_state.metadata[end['Dst']]
                                if meta:
                                    val = meta[0].get(f"{end['Dst'].lower()}_short_name") or meta[0].get(f"{end['Dst'].lower()}_id")
                                    prop = next((p['Property'] for p in schema.get(e, []) if p['Property'].lower().startswith(f"{end['Dst'].lower()}.")), None)
                                    if prop and prop not in edf.columns: edf[prop] = val
                for e, edf in split_data.items():
                    with st.expander(f"📊 {e}"):
                        rep, corr = validate_dataframe(edf, e, schema, permissible_values)
                        if rep:
                            for item in rep[:5]: st.write(f"- {item}")
                            if corr and st.button(f"Apply to {e}"):
                                for col, cdict in corr.items(): edf[col] = edf[col].replace(cdict)
                                st.success("Applied")
                        output = os.path.join(st.session_state.output_dir, f"{e.lower()}.tsv")
                        edf.to_csv(output, sep='\\t', index=False)
                        st.download_button(f"Download {e}.tsv", open(output).read(), f"{e.lower()}.tsv")
                if st.button("🔄 Reset"): reset_app(); st.rerun()
        except Exception as e: st.error(f"Error: {e}")

# Footer"""
content = phase_1_2_pattern.sub(new_phase_1_2, content)

with open(filepath, 'w') as f:
    f.write(content)
