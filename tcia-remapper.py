import streamlit as st
import pandas as pd
import json
import os
import sys
from io import BytesIO
import importlib.util

# Add tcia-remapping-skill to the path and import the helper
remap_helper_path = os.path.join(os.path.dirname(__file__), 'tcia-remapping-skill', 'remap_helper.py')
spec = importlib.util.spec_from_file_location("remap_helper", remap_helper_path)
remap_helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(remap_helper)

# Import functions
load_json = remap_helper.load_json
get_closest_match = remap_helper.get_closest_match
validate_dataframe = remap_helper.validate_dataframe
split_data_by_schema = remap_helper.split_data_by_schema
write_metadata_tsv = remap_helper.write_metadata_tsv
check_metadata_conflict = remap_helper.check_metadata_conflict

st.set_page_config(page_title="TCIA Dataset Remapper", layout="wide")

# Load resources
RESOURCES_DIR = os.path.join(os.path.dirname(__file__), 'tcia-remapping-skill', 'resources')
SCHEMA_FILE = os.path.join(RESOURCES_DIR, 'schema.json')
PERMISSIBLE_VALUES_FILE = os.path.join(RESOURCES_DIR, 'permissible_values.json')

@st.cache_data
def load_resources():
    schema = load_json(SCHEMA_FILE)
    permissible_values = load_json(PERMISSIBLE_VALUES_FILE)
    return schema, permissible_values

def reset_app():
    """Reset all session state"""
    keys_to_keep = []
    keys_to_remove = [k for k in st.session_state.keys() if k not in keys_to_keep]
    for key in keys_to_remove:
        del st.session_state[key]
    st.session_state.phase = 0
    st.session_state.phase0_step = 'program'

# Initialize session state
if 'phase' not in st.session_state:
    st.session_state.phase = 0  # 0: Dataset-level metadata, 1: Structure mapping, 2: Value standardization
    st.session_state.metadata = {
        'Program': [],
        'Dataset': [],
        'Investigator': [],
        'Related_Work': []
    }
    st.session_state.phase0_step = 'program'
    st.session_state.uploaded_data = None
    st.session_state.column_mapping = {}
    st.session_state.structure_approved = False
    st.session_state.output_dir = 'output'

# Create output directory
if not os.path.exists(st.session_state.output_dir):
    os.makedirs(st.session_state.output_dir)

# Load schema and permissible values
schema, permissible_values = load_resources()

# Title and intro
st.title("🗂️ TCIA Dataset Remapper")
st.markdown("""
Welcome to the TCIA Dataset Remapper! This tool helps you transform your clinical and imaging research data 
into the standardized TCIA data model using a tiered conversational workflow.
""")

# Show current phase
phase_names = ["Phase 0: Dataset-Level Metadata", "Phase 1: Structure Mapping", "Phase 2: Value Standardization"]
st.sidebar.title("Progress")
st.sidebar.write(f"**Current Phase:** {phase_names[st.session_state.phase]}")

if st.sidebar.button("🔄 Reset Application"):
    reset_app()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### Navigation")
if st.sidebar.button("📋 Phase 0: Metadata"):
    st.session_state.phase = 0
    st.rerun()
if st.sidebar.button("🔗 Phase 1: Structure"):
    st.session_state.phase = 1
    st.rerun()
if st.sidebar.button("✅ Phase 2: Values"):
    st.session_state.phase = 2
    st.rerun()

# ============================================================================
# PHASE 0: DATASET-LEVEL METADATA COLLECTION
# ============================================================================
if st.session_state.phase == 0:
    st.header("Phase 0: Dataset-Level Metadata Collection")
    st.markdown("""
    Before remapping your source files, let's collect high-level metadata for your submission.
    We'll go through this one entity at a time: **Program → Dataset → Investigator → Related Work**
    """)
    
    tabs = st.tabs(["📁 Program", "📊 Dataset", "👤 Investigator", "📚 Related Work", "📝 Review & Generate"])
    
    # TAB 1: Program
    with tabs[0]:
        st.subheader("Program Information")
        st.info("""
        **Steering:** Most users should use "Community" as their program unless they are part of a major 
        NCI/NIH program (e.g., TCGA, CPTAC, APOLLO, Biobank).
        """)
        
        with st.form("program_form"):
            program_name = st.text_input(
                "Program Name (Required)*",
                value=st.session_state.metadata['Program'][0]['program_name'] if st.session_state.metadata['Program'] else "Community",
                help="Full name of the program"
            )
            program_short_name = st.text_input(
                "Program Short Name (Required)*",
                value=st.session_state.metadata['Program'][0]['program_short_name'] if st.session_state.metadata['Program'] else "Community",
                help="Abbreviated name or acronym"
            )
            institution_name = st.text_input(
                "Institution Name (Optional)",
                value=st.session_state.metadata['Program'][0].get('institution_name', '') if st.session_state.metadata['Program'] else "",
            )
            program_short_description = st.text_area(
                "Program Short Description (Optional)",
                value=st.session_state.metadata['Program'][0].get('program_short_description', '') if st.session_state.metadata['Program'] else "",
            )
            program_full_description = st.text_area(
                "Program Full Description (Optional)",
                value=st.session_state.metadata['Program'][0].get('program_full_description', '') if st.session_state.metadata['Program'] else "",
            )
            program_external_url = st.text_input(
                "Program External URL (Optional)",
                value=st.session_state.metadata['Program'][0].get('program_external_url', '') if st.session_state.metadata['Program'] else "",
            )
            
            submitted = st.form_submit_button("Save Program Information")
            if submitted:
                program_data = {
                    'program_name': program_name,
                    'program_short_name': program_short_name,
                }
                if institution_name:
                    program_data['institution_name'] = institution_name
                if program_short_description:
                    program_data['program_short_description'] = program_short_description
                if program_full_description:
                    program_data['program_full_description'] = program_full_description
                if program_external_url:
                    program_data['program_external_url'] = program_external_url
                    
                st.session_state.metadata['Program'] = [program_data]
                st.success("✅ Program information saved!")
    
    # TAB 2: Dataset
    with tabs[1]:
        st.subheader("Dataset Information")
        
        with st.form("dataset_form"):
            dataset_long_name = st.text_input(
                "Dataset Long Name (Required)*",
                value=st.session_state.metadata['Dataset'][0]['dataset_long_name'] if st.session_state.metadata['Dataset'] else "",
                help="Descriptive title for the collection/dataset"
            )
            dataset_short_name = st.text_input(
                "Dataset Short Name (Required)*",
                value=st.session_state.metadata['Dataset'][0]['dataset_short_name'] if st.session_state.metadata['Dataset'] else "",
                help="Abbreviated title"
            )
            dataset_description = st.text_area(
                "Dataset Description (Required)*",
                value=st.session_state.metadata['Dataset'][0].get('dataset_description', '') if st.session_state.metadata['Dataset'] else "",
                help="Description of the collection/dataset/study"
            )
            dataset_abstract = st.text_area(
                "Dataset Abstract (Required)*",
                value=st.session_state.metadata['Dataset'][0].get('dataset_abstract', '') if st.session_state.metadata['Dataset'] else "",
                help="Short description for public pages"
            )
            # Calculate default value for number of participants
            default_participant_count = 1
            if st.session_state.metadata['Dataset'] and 'number_of_participants' in st.session_state.metadata['Dataset'][0]:
                default_participant_count = st.session_state.metadata['Dataset'][0]['number_of_participants']
            
            number_of_participants = st.number_input(
                "Number of Participants (Required)*",
                min_value=1,
                value=default_participant_count,
                help="Total number of study participants"
            )
            
            # Calculate default index for de-identification dropdown
            deidentified_index = 0  # Default to "Yes"
            if st.session_state.metadata['Dataset']:
                if st.session_state.metadata['Dataset'][0].get('data_has_been_de-identified') == "No":
                    deidentified_index = 1
            
            data_deidentified = st.selectbox(
                "Data Has Been De-identified (Required)*",
                options=["Yes", "No"],
                index=deidentified_index
            )
            adult_or_childhood = st.selectbox(
                "Adult or Childhood Study (Optional)",
                options=["", "Adult", "Pediatric", "Both"],
                index=0
            )
            
            submitted = st.form_submit_button("Save Dataset Information")
            if submitted:
                dataset_data = {
                    'dataset_long_name': dataset_long_name,
                    'dataset_short_name': dataset_short_name,
                    'dataset_description': dataset_description,
                    'dataset_abstract': dataset_abstract,
                    'number_of_participants': number_of_participants,
                    'data_has_been_de-identified': data_deidentified,
                }
                if adult_or_childhood:
                    dataset_data['adult_or_childhood_study'] = adult_or_childhood
                    
                st.session_state.metadata['Dataset'] = [dataset_data]
                st.success("✅ Dataset information saved!")
    
    # TAB 3: Investigator
    with tabs[2]:
        st.subheader("Investigator Information")
        st.markdown("Add one or more investigators for this dataset.")
        
        # Display existing investigators
        if st.session_state.metadata['Investigator']:
            st.write("**Current Investigators:**")
            for idx, inv in enumerate(st.session_state.metadata['Investigator']):
                col1, col2 = st.columns([6, 1])
                with col1:
                    st.write(f"{idx+1}. {inv.get('first_name', '')} {inv.get('last_name', '')} ({inv.get('email', '')}) - {inv.get('organization_name', '')}")
                with col2:
                    if st.button("🗑️", key=f"del_inv_{idx}"):
                        st.session_state.metadata['Investigator'].pop(idx)
                        st.rerun()
        
        st.markdown("---")
        st.write("**Add New Investigator:**")
        
        with st.form("investigator_form"):
            first_name = st.text_input("First Name (Required)*")
            last_name = st.text_input("Last Name (Required)*")
            email = st.text_input("Email (Required)*")
            organization_name = st.text_input("Organization Name (Required)*")
            
            submitted = st.form_submit_button("Add Investigator")
            if submitted:
                if first_name and last_name and email and organization_name:
                    investigator_data = {
                        'first_name': first_name,
                        'last_name': last_name,
                        'email': email,
                        'organization_name': organization_name,
                    }
                    st.session_state.metadata['Investigator'].append(investigator_data)
                    st.success(f"✅ Added investigator: {first_name} {last_name}")
                    st.rerun()
                else:
                    st.error("Please fill in all required fields.")
    
    # TAB 4: Related Work
    with tabs[3]:
        st.subheader("Related Work / Publications")
        st.markdown("Add publications, DOIs, or related work for this dataset.")
        
        # Display existing related works
        if st.session_state.metadata['Related_Work']:
            st.write("**Current Related Works:**")
            for idx, work in enumerate(st.session_state.metadata['Related_Work']):
                col1, col2 = st.columns([6, 1])
                with col1:
                    st.write(f"{idx+1}. {work.get('publication_title', '')} - DOI: {work.get('DOI', '')}")
                with col2:
                    if st.button("🗑️", key=f"del_work_{idx}"):
                        st.session_state.metadata['Related_Work'].pop(idx)
                        st.rerun()
        
        st.markdown("---")
        st.write("**Add New Related Work:**")
        
        with st.form("related_work_form"):
            doi = st.text_input("DOI (Required)*")
            publication_title = st.text_input("Publication Title (Required)*")
            authorship = st.text_input("Authorship (Required)*", help="Author names")
            publication_type = st.selectbox(
                "Publication Type (Required)*",
                options=["Journal Article", "Conference Paper", "Technical Report", "Preprint", "Other"]
            )
            
            submitted = st.form_submit_button("Add Related Work")
            if submitted:
                if doi and publication_title and authorship:
                    work_data = {
                        'DOI': doi,
                        'publication_title': publication_title,
                        'authorship': authorship,
                        'publication_type': publication_type,
                    }
                    st.session_state.metadata['Related_Work'].append(work_data)
                    st.success(f"✅ Added related work: {publication_title}")
                    st.rerun()
                else:
                    st.error("Please fill in all required fields.")
    
    # TAB 5: Review & Generate
    with tabs[4]:
        st.subheader("Review & Generate TSV Files")
        st.markdown("Review all your metadata and generate the TSV files.")
        
        # Display recap
        st.write("### 📋 Metadata Summary")
        
        with st.expander("Program", expanded=True):
            if st.session_state.metadata['Program']:
                for key, value in st.session_state.metadata['Program'][0].items():
                    st.write(f"**{key}:** {value}")
            else:
                st.warning("No program information provided.")
        
        with st.expander("Dataset", expanded=True):
            if st.session_state.metadata['Dataset']:
                for key, value in st.session_state.metadata['Dataset'][0].items():
                    st.write(f"**{key}:** {value}")
            else:
                st.warning("No dataset information provided.")
        
        with st.expander("Investigators", expanded=True):
            if st.session_state.metadata['Investigator']:
                for idx, inv in enumerate(st.session_state.metadata['Investigator']):
                    st.write(f"**Investigator {idx+1}:**")
                    for key, value in inv.items():
                        st.write(f"  - {key}: {value}")
            else:
                st.warning("No investigators provided.")
        
        with st.expander("Related Works", expanded=True):
            if st.session_state.metadata['Related_Work']:
                for idx, work in enumerate(st.session_state.metadata['Related_Work']):
                    st.write(f"**Related Work {idx+1}:**")
                    for key, value in work.items():
                        st.write(f"  - {key}: {value}")
            else:
                st.warning("No related works provided.")
        
        st.markdown("---")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("✨ Generate TSV Files", type="primary", use_container_width=True):
                # Generate TSV files
                generated_files = []
                
                for entity_name, data in st.session_state.metadata.items():
                    if data:
                        filepath = write_metadata_tsv(entity_name, data, schema, st.session_state.output_dir)
                        if filepath:
                            generated_files.append(filepath)
                
                if generated_files:
                    st.success(f"✅ Generated {len(generated_files)} TSV file(s)!")
                    st.write("**Generated Files:**")
                    for filepath in generated_files:
                        st.write(f"- {filepath}")
                        # Offer download
                        with open(filepath, 'r') as f:
                            st.download_button(
                                label=f"Download {os.path.basename(filepath)}",
                                data=f.read(),
                                file_name=os.path.basename(filepath),
                                mime="text/tab-separated-values"
                            )
                else:
                    st.error("No files generated. Please ensure you've provided metadata.")
        
        with col2:
            if st.button("➡️ Proceed to Phase 1", use_container_width=True):
                st.session_state.phase = 1
                st.rerun()

# ============================================================================
# PHASE 1: STRUCTURE MAPPING & ORGANIZATION
# ============================================================================
elif st.session_state.phase == 1:
    st.header("Phase 1: Structure Mapping & Organization")
    st.markdown("""
    Upload your source data files and map your columns to the TCIA target entities.
    """)
    
    # File upload
    uploaded_file = st.file_uploader(
        "Upload your source data file (CSV, TSV, or Excel)",
        type=['csv', 'tsv', 'xlsx', 'xls']
    )
    
    if uploaded_file is not None:
        # Read the file
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith('.tsv'):
                df = pd.read_csv(uploaded_file, sep='\t')
            else:
                df = pd.read_excel(uploaded_file)
            
            st.session_state.uploaded_data = df
            st.success(f"✅ Uploaded file with {len(df)} rows and {len(df.columns)} columns")
            
            # Show preview
            with st.expander("Preview Data", expanded=True):
                st.dataframe(df.head(10))
            
            st.markdown("---")
            st.subheader("Column Mapping")
            st.markdown("Map your source columns to the TCIA target properties.")
            
            # Get all target properties from schema
            all_properties = {}
            for entity_name, properties in schema.items():
                for prop in properties:
                    prop_name = prop['Property']
                    if not prop_name.endswith('_id') and prop_name != 'program.program_id':
                        all_properties[f"{entity_name}.{prop_name}"] = prop
            
            # Create mapping interface
            st.write("**Map Source Columns to Target Properties:**")
            
            mapping_data = []
            for col in df.columns:
                cols = st.columns([3, 4, 2])
                with cols[0]:
                    st.write(f"**{col}**")
                    # Show sample values
                    sample_vals = df[col].dropna().unique()[:3]
                    st.caption(f"Sample: {', '.join(map(str, sample_vals))}")
                
                with cols[1]:
                    # Get current mapping if exists
                    current_mapping = None
                    for target, source in st.session_state.column_mapping.items():
                        if source == col:
                            current_mapping = target
                            break
                    
                    # Property selector
                    property_options = ["(Skip this column)"] + list(all_properties.keys())
                    default_index = 0
                    if current_mapping and current_mapping in property_options:
                        default_index = property_options.index(current_mapping)
                    
                    selected = st.selectbox(
                        "Target Property",
                        options=property_options,
                        index=default_index,
                        key=f"map_{col}",
                        label_visibility="collapsed"
                    )
                    
                    if selected != "(Skip this column)":
                        mapping_data.append((selected, col))
                
                with cols[2]:
                    if selected != "(Skip this column)" and selected in all_properties:
                        prop_info = all_properties[selected]
                        if prop_info.get('Required/optional') == 'R':
                            st.write("✅ Required")
                        else:
                            st.write("⚪ Optional")
            
            st.markdown("---")
            
            if st.button("✅ Confirm Mapping", type="primary"):
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
# PHASE 2: VALUE STANDARDIZATION
# ============================================================================
elif st.session_state.phase == 2:
    st.header("Phase 2: Value Standardization")
    st.markdown("""
    Now let's standardize your data values to match TCIA permissible values using ontology-enhanced matching.
    """)
    
    if st.session_state.uploaded_data is None:
        st.warning("No data uploaded. Please go back to Phase 1.")
    elif not st.session_state.structure_approved:
        st.warning("Structure mapping not confirmed. Please complete Phase 1 first.")
    else:
        df = st.session_state.uploaded_data
        
        # Split data by schema
        split_data = split_data_by_schema(df, st.session_state.column_mapping, schema)
        
        st.write(f"**Identified {len(split_data)} target entities from your data.**")
        
        for entity_name, entity_df in split_data.items():
            with st.expander(f"📊 {entity_name} ({len(entity_df)} rows)", expanded=True):
                st.dataframe(entity_df.head(10))
                
                # Validate values
                report, corrections = validate_dataframe(entity_df, entity_name, schema, permissible_values)
                
                if report:
                    st.write("**Validation Issues Found:**")
                    for item in report[:10]:  # Show first 10
                        st.write(f"- {item}")
                    
                    if len(report) > 10:
                        st.info(f"... and {len(report) - 10} more issues")
                    
                    if corrections:
                        st.write("**Suggested Corrections:**")
                        for col, col_corrections in corrections.items():
                            st.write(f"Column: **{col}**")
                            for old_val, new_val in list(col_corrections.items())[:5]:
                                st.write(f"  - '{old_val}' → '{new_val}'")
                        
                        if st.button(f"Apply Corrections to {entity_name}", key=f"apply_{entity_name}"):
                            # Apply corrections
                            for col, col_corrections in corrections.items():
                                entity_df[col] = entity_df[col].replace(col_corrections)
                            st.success(f"✅ Applied corrections to {entity_name}")
                            
                            # Save the corrected dataframe
                            output_file = os.path.join(st.session_state.output_dir, f"{entity_name.lower()}.tsv")
                            entity_df.to_csv(output_file, sep='\t', index=False)
                            st.success(f"✅ Saved to {output_file}")
                            
                            # Offer download
                            with open(output_file, 'r') as f:
                                st.download_button(
                                    label=f"Download {entity_name}.tsv",
                                    data=f.read(),
                                    file_name=f"{entity_name.lower()}.tsv",
                                    mime="text/tab-separated-values",
                                    key=f"download_{entity_name}"
                                )
                else:
                    st.success("✅ All values are valid!")
                    
                    # Save the dataframe
                    output_file = os.path.join(st.session_state.output_dir, f"{entity_name.lower()}.tsv")
                    entity_df.to_csv(output_file, sep='\t', index=False)
                    st.success(f"✅ Saved to {output_file}")
                    
                    # Offer download
                    with open(output_file, 'r') as f:
                        st.download_button(
                            label=f"Download {entity_name}.tsv",
                            data=f.read(),
                            file_name=f"{entity_name.lower()}.tsv",
                            mime="text/tab-separated-values",
                            key=f"download_{entity_name}"
                        )
        
        st.markdown("---")
        st.success("🎉 Remapping complete! All TSV files have been generated.")
        
        if st.button("🔄 Start New Remapping"):
            reset_app()
            st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
TCIA Dataset Remapper | Following TCIA Imaging Submission Data Model<br>
Leveraging NCIt, UBERON, and SNOMED ontologies for standardization
</div>
""", unsafe_allow_html=True)
