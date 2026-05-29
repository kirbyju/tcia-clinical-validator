import sys
import os
import re

filepath = 'tcia-remapper.py'
with open(filepath, 'r') as f:
    content = f.read()

# 1. Update phase names and sidebar
old_phase_setup = """# Show current phase
phase_names = ["Phase 0: Summary Metadata", "Phase 1: Column Headers", "Phase 2: Permissible Values"]
st.sidebar.title("Progress")
st.sidebar.write(f"**Current Phase:** {phase_names[st.session_state.phase]}")

if st.sidebar.button("🔄 Reset App"):
    reset_app()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### Navigation")
if st.sidebar.button("📋 Phase 0: Summary Metadata"):
    st.session_state.phase = 0
    st.rerun()
if st.sidebar.button("🔗 Phase 1: Column Headers"):
    st.session_state.phase = 1
    st.rerun()
if st.sidebar.button("✅ Phase 2: Permissible Values"):
    st.session_state.phase = 2
    st.rerun()"""

new_phase_setup = """# Show current phase
phase_names = ["Summary Metadata", "CICADAS", "Tabular Data Standardization"]
st.sidebar.title("Progress")
st.sidebar.write(f"**Current Phase:** {phase_names[st.session_state.phase]}")

if st.sidebar.button("🔄 Reset App"):
    reset_app()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### Navigation")
if st.sidebar.button("📋 Summary Metadata"):
    st.session_state.phase = 0
    st.rerun()
if st.sidebar.button("📝 CICADAS"):
    st.session_state.phase = 1
    st.rerun()
if st.sidebar.button("📊 Tabular Data Standardization"):
    st.session_state.phase = 2
    st.rerun()"""

content = content.replace(old_phase_setup, new_phase_setup)

# 2. Update render_dynamic_form to handle multiselects correctly
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
            # Handle list of dicts from MDF parser
            if options and isinstance(options[0], dict):
                option_labels = [f"{o['value']}" for o in options]
            else:
                option_labels = options

            # Determine if this property should use a multiselect
            is_multiselect = prop_name in ['adult_or_childhood_study', 'why_tcia', 'disease_site', 'diagnosis']

            # Prepare default value
            if is_multiselect:
                if not isinstance(default_val, list):
                    if isinstance(default_val, str) and default_val.startswith('[') and default_val.endswith(']'):
                        try:
                            default_val = ast.literal_eval(default_val)
                        except:
                            default_val = [default_val] if default_val else []
                    elif isinstance(default_val, str) and default_val:
                        default_val = [v.strip() for v in default_val.split(',')]
                    else:
                        default_val = [default_val] if default_val else []

                # Filter default_val to only include valid options
                default_val = [v for v in default_val if v in option_labels]
                selected = st.multiselect(label, options=option_labels, default=default_val, help=help_text, disabled=disabled)
            else:
                if not is_required:
                    option_labels = [""] + option_labels

                current_val = str(default_val) if default_val else ""
                try:
                    default_idx = option_labels.index(current_val)
                except ValueError:
                    default_idx = 0
                selected = st.selectbox(label, options=option_labels, index=default_idx, help=help_text, disabled=disabled)
            form_data[prop_name] = selected"""

content = content.replace(old_render, new_render)

# 3. Update Phase 0 Proposal Import
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
                    # Clean up proposal data: replace nan with empty string, handle list-like strings
                    proposal_data = {}
                    for k, v in import_df.iloc[0].to_dict().items():
                        if pd.isna(v) or str(v).lower() == 'nan':
                            proposal_data[k] = ""
                        elif isinstance(v, str) and v.startswith('[') and v.endswith(']'):
                            try:
                                proposal_data[k] = ast.literal_eval(v)
                            except:
                                proposal_data[k] = v
                        else:
                            proposal_data[k] = v
                    st.session_state.proposal_raw_data = proposal_data

                    # Map Dataset
                    ds_data = {
                        'dataset_long_name': proposal_data.get('Title', ''),
                        'dataset_short_name': proposal_data.get('Nickname', ''),
                        'dataset_abstract': proposal_data.get('Abstract', ''),
                        'dataset_description': '', # No longer import description from proposal
                        'adult_or_childhood_study': proposal_data.get('adult_or_childhood_study', []),
                        'acknowledgements': proposal_data.get('acknowledgements') or proposal_data.get('acknowledgments') or '',
                        'funding_agency': proposal_data.get('funding_agency', ''),
                        'funding_source_program_name': proposal_data.get('funding_source_program_name', ''),
                        'grant_id': proposal_data.get('grant_id', ''),
                        'why_tcia': proposal_data.get('why_tcia', [])
                    }"""

content = content.replace(old_import, new_import)

# 4. Remove CICADAS from Phase 0 step
content = content.replace('"CICADAS": "📋 CICADAS",', '')

# 5. Update Investigator display
old_inv_display = """                with col1:
                    st.write(f"{idx+1}. {inv.get('first_name', '')} {inv.get('last_name', '')} ({inv.get('email', '')}) - {inv.get('organization_name', '')}")"""

new_inv_display = """                with col1:
                    email = inv.get('email', '')
                    orcid = inv.get('person_orcid', '')
                    contact_info = email if email else orcid
                    display_contact = f" ({contact_info})" if contact_info else ""
                    st.write(f"{idx+1}. {inv.get('first_name', '')} {inv.get('last_name', '')}{display_contact} - {inv.get('organization_name', '')}")"""

content = content.replace(old_inv_display, new_inv_display)

# 6. Update Summary Metadata Recap
old_recap_val = """                                display_val = ", ".join(map(str, value)) if isinstance(value, list) else value"""
new_recap_val = """                                if isinstance(value, list):
                                    display_val = ", ".join(map(str, value))
                                elif pd.isna(value) or str(value).lower() == 'nan':
                                    display_val = ""
                                else:
                                    display_val = value"""

content = content.replace(old_recap_val, new_recap_val)

# 7. Restructure Phases 1 and 2
phase_0_end = """        if st.button("➡️ Proceed to Phase 1", use_container_width=True, type="primary"):
            st.session_state.phase = 1
            st.rerun()

# ============================================================================
# PHASE 1: COLUMN HEADERS
# ============================================================================
elif st.session_state.phase == 1:
    st.header("Phase 1: Column Headers")
    st.markdown(\"\"\"
    Upload your source data files and map your columns to the target entities.
    \"\"\")

    # File upload
    uploaded_file = st.file_uploader(
        "Upload your source data file (CSV, TSV, or Excel)",
        type=['csv', 'tsv', 'xlsx', 'xls']
    )"""

new_restructure = """        if st.button("➡️ Proceed to CICADAS", use_container_width=True, type="primary"):
            st.session_state.phase = 1
            st.rerun()

# ============================================================================
# PHASE 1: CICADAS
# ============================================================================
elif st.session_state.phase == 1:
    st.header("CICADAS Dataset Description")
    st.markdown(\"\"\"
    Follow the [CICADAS checklist](https://cancerimagingarchive.net/cicadas) to ensure your dataset
    is comprehensive and optimally discoverable.
    \"\"\")

    with st.form("cicadas_form"):
        st.write("### Abstract")
        c_abstract = st.text_area(
            "Abstract (Max 1,000 Characters)*",
            value=st.session_state.cicadas.get('abstract', ''),
            help="Brief overview of the dataset: subjects, imaging types, potential applications.",
            max_chars=1000,
            label_visibility="collapsed"
        )

        st.write("### Introduction")
        c_intro = st.text_area(
            "Introduction",
            value=st.session_state.cicadas.get('introduction', ''),
            help="Purpose and uniqueness of the dataset.",
            label_visibility="collapsed"
        )

        st.write("### Methods")
        c_m_subjects = st.text_area(
            "Subject Inclusion and Exclusion Criteria",
            value=st.session_state.cicadas.get('methods_subjects', ''),
            help="Demographics, clinical characteristics, and potential study bias."
        )
        c_m_acquisition = st.text_area(
            "Data Acquisition",
            value=st.session_state.cicadas.get('methods_acquisition', ''),
            help="Scanner details, sequence parameters, radiotracers, etc."
        )
        c_m_analysis = st.text_area(
            "Data Analysis",
            value=st.session_state.cicadas.get('methods_analysis', ''),
            help="Conversions, preprocessing, annotation protocols, quality control."
        )

        st.write("### Usage Notes")
        c_usage = st.text_area(
            "Usage Notes",
            value=st.session_state.cicadas.get('usage_notes', ''),
            help="Data organization, naming conventions, recommended software."
        )

        st.write("### External Resources")
        c_ext = st.text_area(
            "External Resources (Optional)",
            value=st.session_state.cicadas.get('external_resources', ''),
            help="Links to code, related datasets, or other tools."
        )

        submitted = st.form_submit_button("Save & Next")
        if submitted:
            st.session_state.cicadas = {
                'abstract': c_abstract,
                'introduction': c_intro,
                'methods_subjects': c_m_subjects,
                'methods_acquisition': c_m_acquisition,
                'methods_analysis': c_m_analysis,
                'usage_notes': c_usage,
                'external_resources': c_ext
            }

            desc_parts = []
            if c_intro: desc_parts.append(f"## Introduction\n{c_intro}")
            methods_content = ""
            if c_m_subjects: methods_content += f"### Subject Inclusion and Exclusion Criteria\n{c_m_subjects}\n\n"
            if c_m_acquisition: methods_content += f"### Data Acquisition\n{c_m_acquisition}\n\n"
            if c_m_analysis: methods_content += f"### Data Analysis\n{c_m_analysis}\n\n"
            if methods_content: desc_parts.append(f"## Methods\n{methods_content}")
            if c_usage: desc_parts.append(f"## Usage Notes\n{c_usage}")
            if c_ext: desc_parts.append(f"## External Resources\n{c_ext}")
            full_description = "\n\n".join(desc_parts)

            if st.session_state.metadata['Dataset']:
                ds_meta = st.session_state.metadata['Dataset'][0]
                ds_meta['dataset_abstract'] = c_abstract
                ds_meta['dataset_description'] = full_description
                ds_meta['introduction'] = c_intro
                ds_meta['methods_subjects'] = c_m_subjects
                ds_meta['methods_acquisition'] = c_m_acquisition
                ds_meta['methods_analysis'] = c_m_analysis
                ds_meta['usage_notes'] = c_usage
                ds_meta['external_resources'] = c_ext
            else:
                st.warning("⚠️ Please fill out the basic Dataset information first.")

            st.toast("✅ CICADAS information saved!")
            st.session_state.phase = 2
            st.rerun()

# ============================================================================
# PHASE 2: TABULAR DATA STANDARDIZATION
# ============================================================================
elif st.session_state.phase == 2:
    st.header("Tabular Data Standardization")
    st.markdown(\"\"\"
    Upload your source data files, map your columns, and standardize values.
    \"\"\")

    # File upload
    uploaded_file = st.file_uploader(
        "Upload your source data file (CSV, TSV, or Excel)",
        type=['csv', 'tsv', 'xlsx', 'xls']
    )"""

content = content.replace(phase_0_end, new_restructure)

# 8. Fix the rest of Tabular Data Standardization
# This is tricky because I deleted a lot. Let's just find the end of the previous phase 2 and replace it.

# Actually, let's use a simpler way. I will just overwrite the whole file with a corrected version.
# But I don't have the whole file.

# Let's try to find the "Confirm Mapping" button part.
old_confirm = """            if st.button("✅ Confirm Mapping", type="primary"):
                # Save mapping
                st.session_state.column_mapping = {target: source for target, source in mapping_data}
                st.session_state.structure_approved = True
                st.success("✅ Column mapping confirmed!")
                st.info("Proceeding to Phase 2: Value Standardization...")

                # Check for conflicts with Phase 0 metadata
                conflicts = check_metadata_conflict(st.session_state.metadata, df, st.session_state.column_mapping)
                if conflicts:
                    st.warning("⚠️ Detected conflicts between uploaded data and Phase 0 metadata:")
                    for conflict in conflicts:
                        st.write(f"- {conflict['entity']}.{conflict['property']}: Initial='{conflict['initial_value']}' vs New='{conflict['new_value']}'")
                    st.write("Please review and update either your Phase 0 metadata or your uploaded data.")

            # Show proceed button if mapping is approved
            if st.session_state.structure_approved:
                st.markdown("---")
                if st.button("➡️ Proceed to Phase 2", type="primary", use_container_width=True):
                    st.session_state.phase = 2
                    st.rerun()

        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
    else:
        st.info("👆 Please upload a file to begin structure mapping.")

# ============================================================================
# PHASE 2: PERMISSIBLE VALUES
# ============================================================================
elif st.session_state.phase == 2:
    st.header("Phase 2: Permissible Values")
    st.markdown(\"\"\"
    Now let's standardize your data values to match permissible values using ontology-enhanced matching.
    \"\"\")

    if st.session_state.uploaded_data is None:
        st.warning("No data uploaded. Please go back to Phase 1.")
    elif not st.session_state.structure_approved:
        st.warning("Structure mapping not confirmed. Please complete Phase 1 first.")
    else:
        df = st.session_state.uploaded_data"""

new_confirm = """            if st.button("✅ Confirm Mapping", type="primary"):
                # Save mapping
                st.session_state.column_mapping = {target: source for target, source in mapping_data}
                st.session_state.structure_approved = True
                st.success("✅ Column mapping confirmed!")

                # Check for conflicts with Summary Metadata
                conflicts = check_metadata_conflict(st.session_state.metadata, df, st.session_state.column_mapping)
                if conflicts:
                    st.warning("⚠️ Detected conflicts between uploaded data and metadata:")
                    for conflict in conflicts:
                        st.write(f"- {conflict['entity']}.{conflict['property']}: Initial='{conflict['initial_value']}' vs New='{conflict['new_value']}'")
                    st.write("Please review and update either your metadata or your uploaded data.")

        if st.session_state.structure_approved:
            st.markdown("---")
            st.subheader("Value Standardization")
            df = st.session_state.uploaded_data"""

# Using a simpler match since I might have already changed parts of it.
content = re.sub(r'if st\.button\("✅ Confirm Mapping", type="primary"\):.*?df = st\.session_state\.uploaded_data', new_confirm, content, flags=re.DOTALL)

with open(filepath, 'w') as f:
    f.write(content)
