import streamlit as st
import pandas as pd
import sys
import os
from io import BytesIO

# Add the tcia-remapping-skill directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tcia-remapping-skill'))
from remap_helper import write_metadata_tsv, load_json

st.set_page_config(page_title="TCIA Metadata Collection", page_icon="📋", layout="wide")

# Default programs with complete metadata
DEFAULT_PROGRAMS = {
    "Community": {
        "program_name": "Community",
        "program_short_name": "Community",
        "institution_name": "",
        "program_short_description": "Community-contributed imaging collections",
        "program_full_description": "The Community program encompasses imaging collections contributed by individual researchers and institutions that are not part of larger organized programs.",
        "program_external_url": "https://www.cancerimagingarchive.net/"
    },
    "TCGA": {
        "program_name": "The Cancer Genome Atlas",
        "program_short_name": "TCGA",
        "institution_name": "National Cancer Institute",
        "program_short_description": "A landmark cancer genomics program",
        "program_full_description": "The Cancer Genome Atlas (TCGA) is a landmark cancer genomics program that molecularly characterized over 20,000 primary cancer and matched normal samples spanning 33 cancer types.",
        "program_external_url": "https://www.cancer.gov/tcga"
    },
    "CPTAC": {
        "program_name": "Clinical Proteomic Tumor Analysis Consortium",
        "program_short_name": "CPTAC",
        "institution_name": "National Cancer Institute",
        "program_short_description": "A comprehensive and coordinated effort to accelerate proteogenomic cancer research",
        "program_full_description": "The Clinical Proteomic Tumor Analysis Consortium (CPTAC) is a comprehensive and coordinated effort to accelerate the understanding of the molecular basis of cancer through the application of large-scale proteome and genome analysis (proteogenomics).",
        "program_external_url": "https://proteomics.cancer.gov/programs/cptac"
    },
    "APOLLO": {
        "program_name": "Applied Proteogenomics OrganizationaL Learning and Outcomes",
        "program_short_name": "APOLLO",
        "institution_name": "National Cancer Institute",
        "program_short_description": "Network for proteogenomic characterization of cancer",
        "program_full_description": "The Applied Proteogenomics OrganizationaL Learning and Outcomes (APOLLO) Network aims to generate proteogenomic data and develop analytical tools to advance precision oncology.",
        "program_external_url": "https://proteomics.cancer.gov/programs/apollo-network"
    },
    "Biobank": {
        "program_name": "Cancer Imaging Biobank",
        "program_short_name": "Biobank",
        "institution_name": "",
        "program_short_description": "Organized collections of cancer imaging data",
        "program_full_description": "The Cancer Imaging Biobank program organizes and maintains curated collections of cancer imaging data for research purposes.",
        "program_external_url": "https://www.cancerimagingarchive.net/"
    }
}

# Initialize session state
if 'metadata' not in st.session_state:
    st.session_state.metadata = {
        'program': None,
        'dataset': None,
        'investigators': [],
        'related_works': []
    }

if 'tsv_files_generated' not in st.session_state:
    st.session_state.tsv_files_generated = False

if 'tsv_data' not in st.session_state:
    st.session_state.tsv_data = {}

# Load schema
schema_path = os.path.join(os.path.dirname(__file__), 'tcia-remapping-skill', 'resources', 'schema.json')
schema = load_json(schema_path)

st.title("📋 TCIA Metadata Collection")
st.markdown("Collect and generate standardized TSV files for TCIA imaging submission")

# Create tabs for each metadata type
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📁 Program", "📊 Dataset", "👥 Investigators", "📚 Related Works", "⬇️ Download TSVs"])

# TAB 1: Program
with tab1:
    st.header("Program Information")
    st.markdown("Select an existing program or add a custom one if needed.")
    
    # Program selection
    program_choice = st.selectbox(
        "Select a Program",
        options=[""] + list(DEFAULT_PROGRAMS.keys()) + ["➕ Add Custom Program"],
        key="program_select"
    )
    
    if program_choice and program_choice != "➕ Add Custom Program":
        # Use selected default program
        selected_program = DEFAULT_PROGRAMS[program_choice].copy()
        
        # Display the pre-populated information
        st.success(f"✓ Selected: **{selected_program['program_name']}**")
        
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Program Name*", value=selected_program['program_name'], disabled=True, key="prog_name_display")
            st.text_input("Program Short Name*", value=selected_program['program_short_name'], disabled=True, key="prog_short_display")
        with col2:
            st.text_input("Institution Name", value=selected_program['institution_name'], disabled=True, key="prog_inst_display")
            st.text_input("External URL", value=selected_program['program_external_url'], disabled=True, key="prog_url_display")
        
        st.text_area("Short Description", value=selected_program['program_short_description'], disabled=True, key="prog_short_desc_display", height=100)
        st.text_area("Full Description", value=selected_program['program_full_description'], disabled=True, key="prog_full_desc_display", height=150)
        
        if st.button("✓ Confirm Program Selection", key="confirm_program_btn"):
            st.session_state.metadata['program'] = selected_program
            st.success("Program information saved!")
            st.rerun()
    
    elif program_choice == "➕ Add Custom Program":
        # Custom program entry
        st.info("💡 Only add a custom program if none of the existing options fit your needs.")
        
        with st.form(key="custom_program_form"):
            col1, col2 = st.columns(2)
            with col1:
                program_name = st.text_input("Program Name*", key="custom_prog_name")
                program_short_name = st.text_input("Program Short Name*", key="custom_prog_short")
            with col2:
                institution_name = st.text_input("Institution Name", key="custom_prog_inst")
                program_url = st.text_input("External URL", key="custom_prog_url")
            
            program_short_desc = st.text_area("Short Description", key="custom_prog_short_desc", height=100)
            program_full_desc = st.text_area("Full Description", key="custom_prog_full_desc", height=150)
            
            submit_custom = st.form_submit_button("Save Custom Program")
            
            if submit_custom:
                if program_name and program_short_name:
                    custom_program = {
                        "program_name": program_name,
                        "program_short_name": program_short_name,
                        "institution_name": institution_name or "",
                        "program_short_description": program_short_desc or "",
                        "program_full_description": program_full_desc or "",
                        "program_external_url": program_url or ""
                    }
                    st.session_state.metadata['program'] = custom_program
                    st.success("✓ Custom program information saved!")
                    st.rerun()
                else:
                    st.error("Please fill in the required fields (marked with *)")
    
    # Show current saved program
    if st.session_state.metadata['program']:
        st.divider()
        st.subheader("Current Saved Program")
        st.json(st.session_state.metadata['program'])

# TAB 2: Dataset
with tab2:
    st.header("Dataset Information")
    st.markdown("Provide details about your dataset/collection.")
    
    with st.form(key="dataset_form"):
        col1, col2 = st.columns(2)
        with col1:
            dataset_long_name = st.text_input("Dataset Long Name*", key="dataset_long")
            dataset_short_name = st.text_input("Dataset Short Name*", key="dataset_short")
            num_participants = st.number_input("Number of Participants*", min_value=0, step=1, key="dataset_num")
        with col2:
            adult_or_childhood = st.selectbox("Adult or Childhood Study", ["", "Adult", "Pediatric", "Both"], key="dataset_age")
            funding_agency = st.text_input("Funding Agency", key="dataset_funding")
            de_identified = st.selectbox("Data Has Been De-identified*", ["", "Yes", "No"], key="dataset_deident")
        
        dataset_description = st.text_area("Dataset Description*", key="dataset_desc", height=100)
        dataset_abstract = st.text_area("Dataset Abstract*", key="dataset_abstract", height=100)
        
        submit_dataset = st.form_submit_button("Save Dataset Information")
        
        if submit_dataset:
            if dataset_long_name and dataset_short_name and dataset_description and dataset_abstract and num_participants > 0 and de_identified:
                dataset_info = {
                    "dataset_long_name": dataset_long_name,
                    "dataset_short_name": dataset_short_name,
                    "dataset_description": dataset_description,
                    "dataset_abstract": dataset_abstract,
                    "number_of_participants": int(num_participants),
                    "adult_or_childhood_study": adult_or_childhood if adult_or_childhood else None,
                    "funding_agency": funding_agency if funding_agency else None,
                    "data_has_been_de-identified": de_identified
                }
                st.session_state.metadata['dataset'] = dataset_info
                st.success("✓ Dataset information saved!")
                st.rerun()
            else:
                st.error("Please fill in all required fields (marked with *)")
    
    # Show current saved dataset
    if st.session_state.metadata['dataset']:
        st.divider()
        st.subheader("Current Saved Dataset")
        st.json(st.session_state.metadata['dataset'])

# TAB 3: Investigators
with tab3:
    st.header("Investigator Information")
    st.markdown("Add one or more investigators for this dataset.")
    
    # Form for adding investigators
    st.subheader("Add New Investigator")
    with st.form(key="investigator_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name*", key="inv_first")
            last_name = st.text_input("Last Name*", key="inv_last")
            email = st.text_input("Email*", key="inv_email")
        with col2:
            middle_name = st.text_input("Middle Name", key="inv_middle")
            organization = st.text_input("Organization Name*", key="inv_org")
            orcid = st.text_input("ORCID", key="inv_orcid")
        
        role = st.text_input("Role", key="inv_role")
        
        add_investigator = st.form_submit_button("➕ Add Investigator")
        
        if add_investigator:
            if first_name and last_name and email and organization:
                investigator = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "middle_name": middle_name if middle_name else None,
                    "email": email,
                    "organization_name": organization,
                    "person_orcid": orcid if orcid else None,
                    "role": role if role else None
                }
                st.session_state.metadata['investigators'].append(investigator)
                st.success(f"✓ Added investigator: {first_name} {last_name}")
                st.rerun()
            else:
                st.error("Please fill in all required fields (marked with *)")
    
    # Display added investigators
    if st.session_state.metadata['investigators']:
        st.divider()
        st.subheader(f"Added Investigators ({len(st.session_state.metadata['investigators'])})")
        
        for idx, inv in enumerate(st.session_state.metadata['investigators']):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.write(f"**{idx + 1}. {inv['first_name']} {inv.get('middle_name', '')} {inv['last_name']}**")
                st.caption(f"📧 {inv['email']} | 🏢 {inv['organization_name']}")
            with col2:
                if st.button("🗑️ Remove", key=f"remove_inv_{idx}"):
                    st.session_state.metadata['investigators'].pop(idx)
                    st.rerun()

# TAB 4: Related Works
with tab4:
    st.header("Related Works")
    st.markdown("Add publications or related works associated with this dataset.")
    
    # Form for adding related works
    st.subheader("Add New Related Work")
    with st.form(key="related_work_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            doi = st.text_input("DOI*", key="rw_doi", placeholder="10.1234/example.doi")
            publication_title = st.text_input("Publication Title*", key="rw_title")
            authorship = st.text_input("Authorship*", key="rw_authors", placeholder="Smith J, et al.")
        with col2:
            publication_type = st.selectbox("Publication Type*", 
                ["", "Journal Article", "Conference Paper", "Preprint", "Book Chapter", "Technical Report", "Other"],
                key="rw_type")
            year = st.number_input("Year of Publication", min_value=1900, max_value=2100, step=1, value=2024, key="rw_year")
            journal_citation = st.text_input("Journal Citation", key="rw_journal")
        
        add_related_work = st.form_submit_button("➕ Add Related Work")
        
        if add_related_work:
            if doi and publication_title and authorship and publication_type:
                related_work = {
                    "DOI": doi,
                    "publication_title": publication_title,
                    "authorship": authorship,
                    "publication_type": publication_type,
                    "year_of_publication": int(year) if year else None,
                    "journal_citation": journal_citation if journal_citation else None
                }
                st.session_state.metadata['related_works'].append(related_work)
                st.success(f"✓ Added related work: {publication_title}")
                st.rerun()
            else:
                st.error("Please fill in all required fields (marked with *)")
    
    # Display added related works
    if st.session_state.metadata['related_works']:
        st.divider()
        st.subheader(f"Added Related Works ({len(st.session_state.metadata['related_works'])})")
        
        for idx, work in enumerate(st.session_state.metadata['related_works']):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.write(f"**{idx + 1}. {work['publication_title']}**")
                st.caption(f"📄 {work['authorship']} | 🔗 DOI: {work['DOI']}")
            with col2:
                if st.button("🗑️ Remove", key=f"remove_rw_{idx}"):
                    st.session_state.metadata['related_works'].pop(idx)
                    st.rerun()

# TAB 5: Download TSVs
with tab5:
    st.header("Generate and Download TSV Files")
    st.markdown("Generate TSV files from your collected metadata.")
    
    # Check what data is available
    has_program = st.session_state.metadata['program'] is not None
    has_dataset = st.session_state.metadata['dataset'] is not None
    has_investigators = len(st.session_state.metadata['investigators']) > 0
    has_related_works = len(st.session_state.metadata['related_works']) > 0
    
    # Summary
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if has_program:
            st.success("✓ Program")
        else:
            st.warning("⚠ Program")
    with col2:
        if has_dataset:
            st.success("✓ Dataset")
        else:
            st.warning("⚠ Dataset")
    with col3:
        if has_investigators:
            st.success(f"✓ {len(st.session_state.metadata['investigators'])} Investigators")
        else:
            st.info("ℹ No Investigators")
    with col4:
        if has_related_works:
            st.success(f"✓ {len(st.session_state.metadata['related_works'])} Related Works")
        else:
            st.info("ℹ No Related Works")
    
    st.divider()
    
    # Generate button
    if st.button("🔄 Generate TSV Files", type="primary", use_container_width=True):
        if not has_program or not has_dataset:
            st.error("⚠️ Program and Dataset information are required to generate TSV files.")
        else:
            # Generate TSV data for each entity
            st.session_state.tsv_data = {}
            
            # Program TSV
            program_df = pd.DataFrame([st.session_state.metadata['program']])
            st.session_state.tsv_data['program'] = program_df.to_csv(sep='\t', index=False)
            
            # Dataset TSV
            dataset_df = pd.DataFrame([st.session_state.metadata['dataset']])
            st.session_state.tsv_data['dataset'] = dataset_df.to_csv(sep='\t', index=False)
            
            # Investigator TSV (if any)
            if has_investigators:
                investigator_df = pd.DataFrame(st.session_state.metadata['investigators'])
                st.session_state.tsv_data['investigator'] = investigator_df.to_csv(sep='\t', index=False)
            
            # Related Work TSV (if any)
            if has_related_works:
                related_work_df = pd.DataFrame(st.session_state.metadata['related_works'])
                st.session_state.tsv_data['related_work'] = related_work_df.to_csv(sep='\t', index=False)
            
            st.session_state.tsv_files_generated = True
            st.success("✅ TSV files generated successfully!")
            st.rerun()
    
    # Display download buttons (they persist because they're in session state)
    if st.session_state.tsv_files_generated and st.session_state.tsv_data:
        st.divider()
        st.subheader("📥 Download TSV Files")
        st.markdown("Click each button to download the corresponding TSV file. **The buttons will remain visible after clicking.**")
        
        # Create columns for download buttons
        cols = st.columns(4)
        
        # Program download
        if 'program' in st.session_state.tsv_data:
            with cols[0]:
                st.download_button(
                    label="📁 Program TSV",
                    data=st.session_state.tsv_data['program'],
                    file_name="program.tsv",
                    mime="text/tab-separated-values",
                    key="download_program",
                    use_container_width=True
                )
        
        # Dataset download
        if 'dataset' in st.session_state.tsv_data:
            with cols[1]:
                st.download_button(
                    label="📊 Dataset TSV",
                    data=st.session_state.tsv_data['dataset'],
                    file_name="dataset.tsv",
                    mime="text/tab-separated-values",
                    key="download_dataset",
                    use_container_width=True
                )
        
        # Investigator download
        if 'investigator' in st.session_state.tsv_data:
            with cols[2]:
                st.download_button(
                    label="👥 Investigator TSV",
                    data=st.session_state.tsv_data['investigator'],
                    file_name="investigator.tsv",
                    mime="text/tab-separated-values",
                    key="download_investigator",
                    use_container_width=True
                )
        
        # Related Work download
        if 'related_work' in st.session_state.tsv_data:
            with cols[3]:
                st.download_button(
                    label="📚 Related Work TSV",
                    data=st.session_state.tsv_data['related_work'],
                    file_name="related_work.tsv",
                    mime="text/tab-separated-values",
                    key="download_related_work",
                    use_container_width=True
                )
        
        # Preview section
        st.divider()
        st.subheader("👁️ Preview Generated TSV Files")
        
        preview_choice = st.selectbox(
            "Select a file to preview",
            options=list(st.session_state.tsv_data.keys()),
            format_func=lambda x: x.replace('_', ' ').title()
        )
        
        if preview_choice:
            df = pd.read_csv(BytesIO(st.session_state.tsv_data[preview_choice].encode()), sep='\t')
            st.dataframe(df, use_container_width=True)
    
    # Reset button
    st.divider()
    if st.button("🔄 Start Over", type="secondary"):
        st.session_state.metadata = {
            'program': None,
            'dataset': None,
            'investigators': [],
            'related_works': []
        }
        st.session_state.tsv_files_generated = False
        st.session_state.tsv_data = {}
        st.success("Session reset. You can start entering new metadata.")
        st.rerun()

# Sidebar with help
with st.sidebar:
    st.header("ℹ️ Help")
    st.markdown("""
    ### How to Use
    1. **Program**: Select a default program or add a custom one
    2. **Dataset**: Enter your dataset information
    3. **Investigators**: Add researchers (forms clear after adding)
    4. **Related Works**: Add publications (forms clear after adding)
    5. **Download TSVs**: Generate and download all TSV files
    
    ### Tips
    - Fields marked with * are required
    - Download buttons persist after clicking
    - Forms automatically clear after adding items
    - You can remove added items before generating TSVs
    """)
    
    st.divider()
    
    # Show metadata summary
    st.subheader("📊 Current Status")
    st.write(f"Program: {'✓' if st.session_state.metadata['program'] else '✗'}")
    st.write(f"Dataset: {'✓' if st.session_state.metadata['dataset'] else '✗'}")
    st.write(f"Investigators: {len(st.session_state.metadata['investigators'])}")
    st.write(f"Related Works: {len(st.session_state.metadata['related_works'])}")
