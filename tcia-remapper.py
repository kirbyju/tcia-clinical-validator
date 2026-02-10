import streamlit as st
import pandas as pd
import json
import os
import sys
import requests
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

def lookup_doi(doi):
    """Fetch metadata from Crossref API"""
    if not doi:
        return None
    try:
        url = f"https://api.crossref.org/works/{doi}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()['message']

            # Extract title
            title = data.get('title', [''])[0]

            # Extract authors
            authors_list = data.get('author', [])
            authors = ", ".join([f"{a.get('family', '')} {a.get('given', '')}".strip() for a in authors_list])
            if len(authors_list) > 3:
                authors = f"{authors_list[0].get('family', '')} et al."

            # Extract year
            year = ""
            issued = data.get('issued', {}).get('date-parts', [[None]])[0][0]
            if issued:
                year = str(issued)

            # Extract journal
            journal = data.get('container-title', [''])[0]

            return {
                'title': title,
                'authors': authors,
                'year': year,
                'journal': journal
            }
    except Exception as e:
        st.error(f"Error looking up DOI: {e}")
    return None

def lookup_orcid(orcid_id):
    """Fetch metadata from ORCID API"""
    if not orcid_id:
        return None
    try:
        headers = {"Accept": "application/json"}
        # Get personal details
        url_p = f"https://pub.orcid.org/v3.0/{orcid_id}/personal-details"
        res_p = requests.get(url_p, headers=headers, timeout=10)

        # Get employments
        url_e = f"https://pub.orcid.org/v3.0/{orcid_id}/employments"
        res_e = requests.get(url_e, headers=headers, timeout=10)

        metadata = {}

        if res_p.status_code == 200:
            data_p = res_p.json()
            name = data_p.get('name', {})
            metadata['first_name'] = name.get('given-names', {}).get('value', '')
            metadata['last_name'] = name.get('family-name', {}).get('value', '')

        if res_e.status_code == 200:
            data_e = res_e.json()
            affiliations = data_e.get('affiliation-group', [])
            if affiliations:
                # Get the first (likely most recent) employment
                org = affiliations[0].get('summaries', [{}])[0].get('employment-summary', {}).get('organization', {})
                metadata['organization'] = org.get('name', '')

        return metadata if metadata else None
    except Exception as e:
        st.error(f"Error looking up ORCID: {e}")
    return None

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
    st.session_state.cicadas = {
        'abstract': '',
        'introduction': '',
        'methods_subjects': '',
        'methods_acquisition': '',
        'methods_analysis': '',
        'usage_notes': '',
        'external_resources': ''
    }
    st.session_state.generated_tsv_files = []
    # UI helper keys
    st.session_state.rw_doi = ""
    st.session_state.rw_title = ""
    st.session_state.rw_authors = ""
    st.session_state.inv_orcid = ""
    st.session_state.inv_first = ""
    st.session_state.inv_last = ""
    st.session_state.inv_org = ""

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
    
    tabs = st.tabs(["📁 Program", "📊 Dataset", "📋 CICADAS", "👤 Investigator", "📚 Related Work", "📝 Review & Generate"])
    
    # TAB 1: Program
    with tabs[0]:
        st.subheader("Program Information")
        st.info("""
        **Steering:** Most users should use "Community" as their program unless they are part of a major 
        NCI/NIH program (e.g., TCGA, CPTAC, APOLLO, Biobank).
        """)
        
        # Program selection
        program_options = ["(Select a Program)"] + list(DEFAULT_PROGRAMS.keys()) + ["➕ Create New Program"]

        # Determine current index
        current_idx = 0
        if st.session_state.metadata['Program']:
            prog_name = st.session_state.metadata['Program'][0].get('program_short_name')
            if prog_name in DEFAULT_PROGRAMS:
                current_idx = list(DEFAULT_PROGRAMS.keys()).index(prog_name) + 1
            else:
                current_idx = len(program_options) - 1

        program_choice = st.selectbox(
            "Select Program",
            options=program_options,
            index=current_idx,
            help="Choose a pre-defined program or create a custom one."
        )

        if program_choice != "(Select a Program)":
            is_custom = program_choice == "➕ Create New Program"
            
            if not is_custom:
                prog_data = DEFAULT_PROGRAMS[program_choice]
            else:
                prog_data = st.session_state.metadata['Program'][0] if st.session_state.metadata['Program'] else {}

            with st.form("program_form"):
                program_name = st.text_input(
                    "Program Name (Required)*",
                    value=prog_data.get('program_name', ''),
                    disabled=not is_custom,
                    help="Full name of the program"
                )
                program_short_name = st.text_input(
                    "Program Short Name (Required)*",
                    value=prog_data.get('program_short_name', ''),
                    disabled=not is_custom,
                    help="Abbreviated name or acronym"
                )
                institution_name = st.text_input(
                    "Institution Name (Optional)",
                    value=prog_data.get('institution_name', ''),
                    disabled=not is_custom
                )
                program_short_description = st.text_area(
                    "Program Short Description (Optional)",
                    value=prog_data.get('program_short_description', ''),
                    disabled=not is_custom
                )
                program_full_description = st.text_area(
                    "Program Full Description (Optional)",
                    value=prog_data.get('program_full_description', ''),
                    disabled=not is_custom
                )
                program_external_url = st.text_input(
                    "Program External URL (Optional)",
                    value=prog_data.get('program_external_url', ''),
                    disabled=not is_custom
                )

                submitted = st.form_submit_button("Save Program Information")
                if submitted:
                    new_program_data = {
                        'program_name': program_name,
                        'program_short_name': program_short_name,
                    }
                    if institution_name:
                        new_program_data['institution_name'] = institution_name
                    if program_short_description:
                        new_program_data['program_short_description'] = program_short_description
                    if program_full_description:
                        new_program_data['program_full_description'] = program_full_description
                    if program_external_url:
                        new_program_data['program_external_url'] = program_external_url

                    st.session_state.metadata['Program'] = [new_program_data]
                    st.success("✅ Program information saved!")
                    st.rerun()
    
    # TAB 2: Dataset
    with tabs[1]:
        st.subheader("Dataset Information")
        
        with st.form("dataset_form"):
            dataset_long_name = st.text_input(
                "Dataset Long Name (Required)*",
                value=st.session_state.metadata['Dataset'][0]['dataset_long_name'] if st.session_state.metadata['Dataset'] else "",
                help="Descriptive title for the collection/dataset (Recommended < 110 chars)"
            )
            dataset_short_name = st.text_input(
                "Dataset Short Name (Required)*",
                value=st.session_state.metadata['Dataset'][0]['dataset_short_name'] if st.session_state.metadata['Dataset'] else "",
                help="Abbreviated title (< 30 chars, alphanumeric/dashes only)"
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
                # Keep existing description and abstract if they exist
                existing_desc = st.session_state.metadata['Dataset'][0].get('dataset_description', '') if st.session_state.metadata['Dataset'] else ''
                existing_abstract = st.session_state.metadata['Dataset'][0].get('dataset_abstract', '') if st.session_state.metadata['Dataset'] else ''

                dataset_data = {
                    'dataset_long_name': dataset_long_name,
                    'dataset_short_name': dataset_short_name,
                    'dataset_description': existing_desc,
                    'dataset_abstract': existing_abstract,
                    'number_of_participants': number_of_participants,
                    'data_has_been_de-identified': data_deidentified,
                }
                if adult_or_childhood:
                    dataset_data['adult_or_childhood_study'] = adult_or_childhood
                    
                st.session_state.metadata['Dataset'] = [dataset_data]
                st.success("✅ Basic Dataset information saved! Now complete the CICADAS tab.")

    # TAB 3: CICADAS
    with tabs[2]:
        st.subheader("CICADAS Dataset Description")
        st.markdown("""
        Follow the [CICADAS checklist](https://cancerimagingarchive.net/cicadas) to ensure your dataset
        is comprehensive and optimally discoverable.
        """)

        with st.form("cicadas_form"):
            st.write("### Abstract")
            c_abstract = st.text_area(
                "Abstract (Max 1,000 Characters)*",
                value=st.session_state.cicadas.get('abstract', ''),
                help="Brief overview of the dataset: subjects, imaging types, potential applications.",
                max_chars=1000
            )

            st.write("### Introduction")
            c_intro = st.text_area(
                "Introduction",
                value=st.session_state.cicadas.get('introduction', ''),
                help="Purpose and uniqueness of the dataset."
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

            submitted = st.form_submit_button("Save CICADAS Description")
            if submitted:
                # Update CICADAS state
                st.session_state.cicadas = {
                    'abstract': c_abstract,
                    'introduction': c_intro,
                    'methods_subjects': c_m_subjects,
                    'methods_acquisition': c_m_acquisition,
                    'methods_analysis': c_m_analysis,
                    'usage_notes': c_usage,
                    'external_resources': c_ext
                }

                # Construct dataset_description
                desc_parts = []
                if c_intro:
                    desc_parts.append(f"## Introduction\n{c_intro}")

                methods_content = ""
                if c_m_subjects:
                    methods_content += f"### Subject Inclusion and Exclusion Criteria\n{c_m_subjects}\n\n"
                if c_m_acquisition:
                    methods_content += f"### Data Acquisition\n{c_m_acquisition}\n\n"
                if c_m_analysis:
                    methods_content += f"### Data Analysis\n{c_m_analysis}\n\n"

                if methods_content:
                    desc_parts.append(f"## Methods\n{methods_content}")

                if c_usage:
                    desc_parts.append(f"## Usage Notes\n{c_usage}")

                if c_ext:
                    desc_parts.append(f"## External Resources\n{c_ext}")

                full_description = "\n\n".join(desc_parts)

                # Update metadata if Dataset exists
                if st.session_state.metadata['Dataset']:
                    st.session_state.metadata['Dataset'][0]['dataset_abstract'] = c_abstract
                    st.session_state.metadata['Dataset'][0]['dataset_description'] = full_description
                else:
                    st.warning("⚠️ Please fill out the basic Dataset information first.")

                st.success("✅ CICADAS information saved and concatenated into Dataset Description!")

    # TAB 4: Investigator
    with tabs[3]:
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
        
        col_orcid, col_lookup_orc = st.columns([3, 1])
        with col_orcid:
            orcid_input = st.text_input("ORCID (Optional)", value=st.session_state.get('inv_orcid', ''), help="e.g., 0000-0002-1825-0097")
        with col_lookup_orc:
            st.write(" ") # alignment
            st.write(" ")
            if st.button("🔍 Lookup ORCID"):
                orcid_metadata = lookup_orcid(orcid_input)
                if orcid_metadata:
                    st.session_state.inv_orcid = orcid_input
                    st.session_state.inv_first = orcid_metadata.get('first_name', '')
                    st.session_state.inv_last = orcid_metadata.get('last_name', '')
                    st.session_state.inv_org = orcid_metadata.get('organization', '')
                    st.success("Metadata found!")
                    st.rerun()
                else:
                    st.error("ORCID not found or no public profile.")

        with st.form("investigator_form"):
            first_name = st.text_input("First Name (Required)*", value=st.session_state.get('inv_first', ''))
            last_name = st.text_input("Last Name (Required)*", value=st.session_state.get('inv_last', ''))
            email = st.text_input("Email (Required)*")
            organization_name = st.text_input("Organization Name (Required)*", value=st.session_state.get('inv_org', ''))
            
            submitted = st.form_submit_button("Add Investigator")
            if submitted:
                if first_name and last_name and email and organization_name:
                    investigator_data = {
                        'first_name': first_name,
                        'last_name': last_name,
                        'email': email,
                        'organization_name': organization_name,
                    }
                    if orcid_input:
                        investigator_data['person_orcid'] = orcid_input

                    st.session_state.metadata['Investigator'].append(investigator_data)

                    # Clear session state
                    for key in ['inv_orcid', 'inv_first', 'inv_last', 'inv_org']:
                        if key in st.session_state:
                            st.session_state[key] = ""

                    st.success(f"✅ Added investigator: {first_name} {last_name}")
                    st.rerun()
                else:
                    st.error("Please fill in all required fields.")
    
    # TAB 5: Related Work
    with tabs[4]:
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
        
        # Define permissible relationship types
        rel_types = [
            "IsNewVersionOf",
            "IsPreviousVersionOf",
            "IsReferencedBy",
            "References",
            "IsDerivedFrom",
            "IsSourceOf",
            "Obsoletes",
            "IsObsoletedBy"
        ]

        col_doi, col_lookup = st.columns([3, 1])
        with col_doi:
            doi_input = st.text_input("DOI (Required)*", value=st.session_state.get('rw_doi', ''))
        with col_lookup:
            st.write(" ") # alignment
            st.write(" ")
            if st.button("🔍 Lookup DOI"):
                doi_metadata = lookup_doi(doi_input)
                if doi_metadata:
                    st.session_state.rw_doi = doi_input
                    st.session_state.rw_title = doi_metadata['title']
                    st.session_state.rw_authors = doi_metadata['authors']
                    # We could also use year and journal if we had fields for them
                    st.success("Metadata found!")
                    st.rerun()
                else:
                    st.error("DOI not found.")

        with st.form("related_work_form"):
            # We don't use clear_on_submit because we want to control clearing via session state
            doi = st.text_input("DOI (Required)*", value=st.session_state.get('rw_doi', doi_input))
            publication_title = st.text_input("Publication Title (Optional)", value=st.session_state.get('rw_title', ''))
            authorship = st.text_input("Authorship (Optional)", value=st.session_state.get('rw_authors', ''), help="Author names")
            publication_type = st.selectbox(
                "Publication Type (Required)*",
                options=["Journal Article", "Conference Paper", "Technical Report", "Preprint", "Other"]
            )
            relationship_type = st.selectbox(
                "Relationship Type (Required)*",
                options=[""] + rel_types
            )
            
            submitted = st.form_submit_button("Add Related Work")
            if submitted:
                if doi and publication_type and relationship_type:
                    work_data = {
                        'DOI': doi,
                        'publication_type': publication_type,
                        'relationship_type': relationship_type,
                    }
                    if publication_title:
                        work_data['publication_title'] = publication_title
                    if authorship:
                        work_data['authorship'] = authorship

                    st.session_state.metadata['Related_Work'].append(work_data)

                    # Clear session state for next entry
                    for key in ['rw_doi', 'rw_title', 'rw_authors']:
                        if key in st.session_state:
                            st.session_state[key] = ""

                    st.success(f"✅ Added related work: {doi}")
                    st.rerun()
                else:
                    st.error("Please fill in all required fields (DOI, Publication Type, Relationship Type).")
    
    # TAB 6: Review & Generate
    with tabs[5]:
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
                new_generated_files = []
                
                for entity_name, data in st.session_state.metadata.items():
                    if data:
                        filepath = write_metadata_tsv(entity_name, data, schema, st.session_state.output_dir)
                        if filepath:
                            new_generated_files.append(filepath)
                
                if new_generated_files:
                    st.session_state.generated_tsv_files = new_generated_files
                    st.success(f"✅ Generated {len(new_generated_files)} TSV file(s)!")
                else:
                    st.error("No files generated. Please ensure you've provided metadata.")

            # Display download buttons if files have been generated
            if st.session_state.generated_tsv_files:
                st.write("**Generated Files:**")
                for filepath in st.session_state.generated_tsv_files:
                    if os.path.exists(filepath):
                        with open(filepath, 'r') as f:
                            st.download_button(
                                label=f"Download {os.path.basename(filepath)}",
                                data=f.read(),
                                file_name=os.path.basename(filepath),
                                mime="text/tab-separated-values",
                                key=f"download_{os.path.basename(filepath)}"
                            )
        
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
