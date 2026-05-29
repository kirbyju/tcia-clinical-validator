import streamlit as st
import pandas as pd
import json
import re
import os
import sys
import requests
import zipfile
import ast
import datetime
from io import BytesIO
from docx import Document
import importlib.util

# Add tcia-remapping-skill to the path and import the helper
skill_dir = os.path.join(os.path.dirname(__file__), 'tcia-remapping-skill')
remap_helper_path = os.path.join(skill_dir, 'remap_helper.py')
spec = importlib.util.spec_from_file_location("remap_helper", remap_helper_path)
remap_helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(remap_helper)

# Import MDF parser
mdf_parser_path = os.path.join(skill_dir, 'mdf_parser.py')
spec_mdf = importlib.util.spec_from_file_location("mdf_parser", mdf_parser_path)
mdf_parser = importlib.util.module_from_spec(spec_mdf)
spec_mdf.loader.exec_module(mdf_parser)

orcid_helper_path = os.path.join(skill_dir, 'orcid_helper.py')
spec_orcid = importlib.util.spec_from_file_location("orcid_helper", orcid_helper_path)
orcid_helper = importlib.util.module_from_spec(spec_orcid)
spec_orcid.loader.exec_module(orcid_helper)

# Import functions
load_json = remap_helper.load_json
get_closest_match = remap_helper.get_closest_match
validate_dataframe = remap_helper.validate_dataframe
split_data_by_schema = remap_helper.split_data_by_schema
write_metadata_tsv = remap_helper.write_metadata_tsv
check_metadata_conflict = remap_helper.check_metadata_conflict
check_missing_links = remap_helper.check_missing_links
get_mdf_resources = mdf_parser.get_mdf_resources

st.set_page_config(page_title="NCI Imaging Submission Validator", layout="wide")

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

def lookup_doi(doi_input):
    """Fetch metadata from Crossref, arXiv, or DataCite APIs"""
    if not doi_input:
        return None

    # Strip common prefixes to extract raw DOI
    doi = doi_input.strip()
    prefixes = ["https://doi.org/", "http://doi.org/", "doi.org/", "doi:"]
    for p in prefixes:
        if doi.lower().startswith(p):
            doi = doi[len(p):]

    # Check for arXiv DOI
    if "arxiv" in doi.lower():
        # Example DOI: 10.48550/arXiv.2404.15009
        # Extract arXiv ID (e.g., 2404.15009)
        arxiv_match = re.search(r'arXiv\.(\d{4}\.\d{4,5})', doi, re.I)
        if arxiv_match:
            arxiv_id = arxiv_match.group(1)
            try:
                url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(response.text)
                    entry = root.find('{http://www.w3.org/2005/Atom}entry')
                    if entry is not None:
                        title_elem = entry.find('{http://www.w3.org/2005/Atom}title')
                        title = title_elem.text.strip().replace('\n', ' ') if title_elem is not None and title_elem.text else "No Title"

                        authors_list = entry.findall('{http://www.w3.org/2005/Atom}author')
                        author_names = []
                        for a in authors_list:
                            name_elem = a.find('{http://www.w3.org/2005/Atom}name')
                            if name_elem is not None and name_elem.text:
                                author_names.append(name_elem.text.strip())

                        authors = ", ".join(author_names)
                        if len(author_names) > 3:
                            authors = f"{author_names[0]} et al."

                        published_elem = entry.find('{http://www.w3.org/2005/Atom}published')
                        year = str(published_elem.text[:4]) if published_elem is not None and published_elem.text else ""

                        return {
                            'title': title,
                            'authors': authors,
                            'year': year,
                            'journal': 'arXiv'
                        }
            except Exception as e:
                pass

    # Try Crossref
    try:
        url = f"https://api.crossref.org/works/{doi}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()['message']
            title = data.get('title', [''])[0]
            authors_list = data.get('author', [])
            authors = ", ".join([f"{a.get('family', '')} {a.get('given', '')}".strip() for a in authors_list])
            if len(authors_list) > 3:
                authors = f"{authors_list[0].get('family', '')} et al."
            year = ""
            issued = data.get('issued', {}).get('date-parts', [[None]])[0][0]
            if issued:
                year = str(issued)
            journal = data.get('container-title', [''])[0]
            return {
                'title': title,
                'authors': authors,
                'year': year,
                'journal': journal
            }
    except:
        pass

    # Try DataCite
    try:
        url = f"https://api.datacite.org/dois/{doi}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()['data']['attributes']
            title = data.get('titles', [{'title': ''}])[0].get('title', '')
            creators = data.get('creators', [])
            authors = ", ".join([c.get('name', '') for c in creators])
            if len(creators) > 3:
                authors = f"{creators[0].get('name', '')} et al."
            year = str(data.get('publicationYear', ''))
            publisher = data.get('publisher', '')
            return {
                'title': title,
                'authors': authors,
                'year': year,
                'journal': publisher
            }
    except:
        pass

    return None

def lookup_orcid(orcid_id):
    """Fetch metadata from ORCID API using orcid_helper"""
    profile = orcid_helper.get_orcid_profile(orcid_id)
    if profile:
        return {
            'first_name': profile.get('given_names', ''),
            'last_name': profile.get('family_name', ''),
            'organization': profile.get('organization', '')
        }
    return None

@st.cache_data
def load_resources():
    # Try loading from MDF first
    schema, mdf_pv, relationships = get_mdf_resources(RESOURCES_DIR)
    
    # Load legacy permissible values
    legacy_pv = load_json(PERMISSIBLE_VALUES_FILE)
    
    if schema:
        # Merge permissible values: MDF Enums take precedence, but legacy covers missing ones
        final_pv = legacy_pv.copy()
        if mdf_pv:
            for k, v in mdf_pv.items():
                final_pv[k] = v
        return schema, final_pv, relationships
        
    # Fallback to legacy JSON files
    st.warning("⚠️ Using legacy schema files. MDF model files not found or invalid.")
    schema = load_json(SCHEMA_FILE)
    return schema, legacy_pv, {}

def render_dynamic_form(entity_name, schema, permissible_values, current_data=None, excluded_fields=None, custom_labels=None, disabled=False, priority_fields=None):
    """
    Renders a dynamic form for an entity based on the schema.
    """
    if excluded_fields is None:
        excluded_fields = []
    if custom_labels is None:
        custom_labels = {}
    if current_data is None:
        current_data = {}
    if priority_fields is None:
        priority_fields = []

    entity_props = schema.get(entity_name, [])
    form_data = {}

    # Filter out excluded fields and ID fields
    props_to_show = [
        p for p in entity_props 
        if p['Property'] not in excluded_fields 
        and p['Property'] not in [f"{entity_name.lower()}_id", "id"]
        and '.' not in p['Property']
    ]

    # Reorder based on priority
    def get_priority(p):
        name = p['Property']
        if name in priority_fields:
            return priority_fields.index(name)
        return len(priority_fields) + 1

    props_to_show.sort(key=get_priority)

    for prop in props_to_show:
        prop_name = prop['Property']
        label = custom_labels.get(prop_name, prop_name.replace('_', ' ').title())
        is_required = prop.get('Required/optional') == 'R'
        if is_required:
            label += "*"
        
        help_text = prop.get('Description', '')
        default_val = current_data.get(prop_name, "")

        if prop_name in permissible_values:
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
            form_data[prop_name] = selected
        elif "description" in prop_name or "abstract" in prop_name or "acknowledgements" in prop_name:
            form_data[prop_name] = st.text_area(label, value=str(default_val), help=help_text, disabled=disabled)
        elif "number" in prop_name or "count" in prop_name or "size" in prop_name:
            try:
                dv = int(default_val) if default_val else 0
            except:
                dv = 0
            form_data[prop_name] = st.number_input(label, value=dv, help=help_text, disabled=disabled)
        else:
            form_data[prop_name] = st.text_input(label, value=str(default_val), help=help_text, disabled=disabled)

    return form_data

def reset_app():
    """Reset all session state"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]

# Initialize session state
if 'phase' not in st.session_state:
    st.session_state.phase = 0  # 0: Dataset-level metadata, 1: Structure mapping, 2: Value standardization
    st.session_state.metadata = {
        'Program': [],
        'Dataset': [],
        'Investigator': [],
        'Related_Work': []
    }
    st.session_state.phase0_step = 'Start'
    st.session_state.uploaded_data = None
    st.session_state.column_mapping = {}
    st.session_state.structure_approved = False
    st.session_state.output_dir = 'output'
    st.session_state.proposal_raw_data = {}
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
    st.session_state.raw_authors = ""

if 'pending_dois' not in st.session_state:
    st.session_state.pending_dois = []

# Create output directory
if not os.path.exists(st.session_state.output_dir):
    os.makedirs(st.session_state.output_dir)

# Load schema and permissible values
schema, permissible_values, relationships = load_resources()

# Title and intro
st.title("🗂️ NCI Imaging Submission Validator")
st.markdown("""
Welcome to the NCI Imaging Submission Validator. This tool helps you transform and validate your dataset to align with [NCI's Imaging Submission Model](https://github.com/CBIIT/nci-imaging-submission-model).
""")

# Show current phase
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
    st.rerun()

# ============================================================================
# PHASE 0: SUMMARY METADATA COLLECTION
# ============================================================================
if st.session_state.phase == 0:
    st.header("Summary Metadata")
    st.markdown("""
    Before remapping your source files, let's collect high-level metadata for your submission.
    We'll go through this one entity at a time: **Start → Program → Dataset → Investigator → Related Work**
    """)
    
    phase0_options = {
        "Start": "🚀 Start",
        "Program": "📁 Program",
        "Dataset": "📊 Dataset",

        "Investigator": "👤 Investigator",
        "Related_Work": "📚 Related Work",
        "Review": "📝 Review & Generate"
    }
    
    # Initialize phase0_step if not in right format
    if st.session_state.phase0_step not in phase0_options:
        st.session_state.phase0_step = "Program"

    # Use a radio button to simulate tabs for programmatic control
    current_step = st.radio(
        "Navigation",
        options=list(phase0_options.keys()),
        format_func=lambda x: phase0_options[x],
        index=list(phase0_options.keys()).index(st.session_state.phase0_step),
        horizontal=True,
        label_visibility="collapsed"
    )
    
    # Update state if changed via radio
    if current_step != st.session_state.phase0_step:
        st.session_state.phase0_step = current_step
        st.rerun()

    st.markdown("---")

    # TAB 0: Start
    if st.session_state.phase0_step == "Start":
        st.subheader("Welcome to Summary Metadata")
        st.markdown("""
        Before we begin, would you like to import your Dataset Proposal Form?
        Importing a proposal will automatically fill in many of the fields for you, saving you time.
        """)

        import_file = st.file_uploader("📥 Import Proposal Package (TSV or ZIP)", type=['tsv', 'zip'])

        if import_file:
            try:
                import_df = pd.DataFrame()
                investigators_from_file = []

                if import_file.name.endswith('.zip'):
                    with zipfile.ZipFile(import_file) as z:
                        # Load proposal summary (look for file with 'proposal_summary' in name)
                        summary_file = next((name for name in z.namelist() if 'proposal_summary' in name and name.endswith('.tsv')), None)
                        if summary_file:
                            with z.open(summary_file) as f:
                                import_df = pd.read_csv(f, sep='\t')

                        # Load investigators if present
                        inv_file = next((name for name in z.namelist() if 'investigators' in name and name.endswith('.tsv')), None)
                        if inv_file:
                            with z.open(inv_file) as f:
                                inv_df = pd.read_csv(f, sep='\t')
                                investigators_from_file = inv_df.to_dict('records')
                else:
                    import_df = pd.read_csv(import_file, sep='\t')

                if not import_df.empty:
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
                    }
                    st.session_state.metadata['Dataset'] = [ds_data]

                    # Update CICADAS fields
                    st.session_state.cicadas['abstract'] = proposal_data.get('Abstract', '')
                    st.session_state.cicadas['introduction'] = ''

                    # Map Software/Source Code to CICADAS external resources
                    software_info = ""
                    if proposal_data.get('software_code') == "Yes":
                        details = proposal_data.get('software_details', '')
                        software_info = f"Related software/source code: {details}"

                    if software_info:
                        st.session_state.cicadas['external_resources'] = software_info

                    # Map Program (Default to Community)
                    st.session_state.metadata['Program'] = [DEFAULT_PROGRAMS['Community']]

                    # Store raw authors for parsing in the Investigator step
                    st.session_state.raw_authors = str(proposal_data.get('Authors', ''))

                    # Map Investigators if present in ZIP
                    if investigators_from_file:
                        st.session_state.metadata['Investigator'] = investigators_from_file

                    # Map Related Work
                    rel_works = []

                    # Legacy support
                    for k in ['citation_primary', 'citations_content', 'additional_publications', 'descriptor_publication']:
                        val = proposal_data.get(k)
                        if val and str(val).strip():
                            rel_works.append({
                                'title': str(val).strip(),
                                'publication_type': 'Journal Article',
                                'relationship_type': 'Describes' if k == 'descriptor_publication' else 'IsDerivedFrom',
                                'authorship': '',
                                'DOI': ''
                            })

                    # New Manuscripts field support
                    manuscripts_raw = proposal_data.get('Manuscripts')
                    if manuscripts_raw:
                        try:
                            ms_list = json.loads(manuscripts_raw)
                            for ms in ms_list:
                                val = ms.get('value', '')
                                cat = ms.get('category', '')

                                # Extract DOI if possible
                                doi = ""
                                if 'doi.org/' in val:
                                    doi_match = re.search(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', val, re.I)
                                    if doi_match:
                                        doi = doi_match.group()

                                rel_works.append({
                                    'title': val,
                                    'publication_type': 'Preprint', # Default for proposal stage
                                    'relationship_type': 'Describes' if cat == 'Dataset Descriptor' else 'IsDerivedFrom',
                                    'authorship': '',
                                    'DOI': doi
                                })
                        except:
                            pass

                    if rel_works:
                        st.session_state.metadata['Related_Work'] = rel_works

                    st.success("✅ Proposal imported successfully!")
                    st.info("The metadata has been pre-populated. Click 'Proceed' below to verify the information in each section.")
            except Exception as e:
                st.error(f"Import failed: {e}")

        st.markdown("---")
        if st.button("Proceed to Metadata Collection →", use_container_width=True, type="primary"):
            st.session_state.phase0_step = 'Program'
            st.rerun()

    # TAB 1: Program
    elif st.session_state.phase0_step == "Program":
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
                # Always render dynamic form but if not custom, the fields are disabled
                new_program_data = render_dynamic_form(
                    "Program", 
                    schema, 
                    permissible_values, 
                    current_data=prog_data,
                    disabled=not is_custom
                )

                submitted = st.form_submit_button("Save & Next")
                if submitted:
                    st.session_state.metadata['Program'] = [new_program_data]
                    st.toast("✅ Program information saved!")
                    st.session_state.phase0_step = 'Dataset'
                    st.rerun()
    
    # TAB 2: Dataset
    elif st.session_state.phase0_step == "Dataset":
        st.subheader("Dataset Information")
        
        current_ds_data = st.session_state.metadata['Dataset'][0] if st.session_state.metadata['Dataset'] else {}
        
        with st.form("dataset_form"):
            dataset_data = render_dynamic_form(
                "Dataset",
                schema,
                permissible_values,
                current_data=current_ds_data,
                excluded_fields=['dataset_description', 'dataset_abstract'],
                priority_fields=['dataset_long_name', 'dataset_short_name']
            )
            
            submitted = st.form_submit_button("Save & Next")
            if submitted:
                # Keep existing description and abstract if they exist
                dataset_data['dataset_description'] = current_ds_data.get('dataset_description', '')
                dataset_data['dataset_abstract'] = current_ds_data.get('dataset_abstract', '')

                st.session_state.metadata['Dataset'] = [dataset_data]
                st.toast("✅ Basic Dataset information saved!")
                st.session_state.phase0_step = 'Investigator'
                st.rerun()

    # TAB 3: CICADAS
    elif st.session_state.phase0_step == "CICADAS":
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

                st.toast("✅ CICADAS information saved!")
                st.session_state.phase0_step = 'Investigator'
                st.rerun()

    # TAB 4: Investigator
    elif st.session_state.phase0_step == "Investigator":
        st.subheader("Investigator Information")
        st.markdown("Add one or more investigators for this dataset.")
        
        # --- Batch Import ---
        with st.expander("📥 Batch Import / Edit Investigators", expanded=st.session_state.get('raw_authors') != ""):
            st.info("Paste a list of investigators or edit the imported list. Choose a parsing strategy to preview and add them.")

            raw_authors_input = st.text_area(
                "Raw Author List",
                value=st.session_state.get('raw_authors', ''),
                help="Enter one author per line or separated by semicolons. Format: (Family, Given) - ORCID or Given Family",
                height=150
            )

            strategy = st.selectbox(
                "Parsing Strategy",
                options=[
                    "Auto-detect",
                    "Family, Given - ORCID (e.g. Smith, John - 0000-0002-1234-5678)",
                    "Family, Given (e.g. Smith, John)",
                    "Given Family (e.g. John Smith)"
                ],
                index=0
            )

            # Parsing logic
            parsed_results = []
            if raw_authors_input:
                raw_lines = re.split(r'[;\n]', raw_authors_input)
                for i, line in enumerate(raw_lines, 1):
                    line = line.strip()
                    if not line: continue

                    # Always look for ORCID first
                    orcid_match = re.search(r'(\d{4}-\d{4}-\d{4}-\d{3}[\dX])', line)
                    orcid = orcid_match.group(1) if orcid_match else ""

                    # Remove ORCID from line for name parsing
                    name_part = re.sub(r'\(?\d{4}-\d{4}-\d{4}-\d{3}[\dX]\)?', '', line).strip()
                    name_part = name_part.rstrip(' -').strip() # Remove trailing hyphen or space
                    if name_part.startswith('(') and name_part.endswith(')'):
                        name_part = name_part[1:-1].strip()

                    first_name = ""
                    last_name = ""

                    actual_strategy = strategy
                    if strategy == "Auto-detect":
                        if ',' in name_part:
                            actual_strategy = "Family, Given"
                        else:
                            actual_strategy = "Given Family"

                    if actual_strategy.startswith("Family, Given"):
                        parts = name_part.split(',')
                        last_name = parts[0].strip() if len(parts) > 0 else ""
                        first_name = parts[1].strip() if len(parts) > 1 else ""
                    else: # Given Family
                        parts = name_part.split()
                        if len(parts) >= 2:
                            first_name = parts[0].strip()
                            last_name = " ".join(parts[1:]).strip()
                        elif len(parts) == 1:
                            first_name = parts[0].strip()

                    # ORCID Lookup if name is missing
                    organization = ""
                    if orcid and not first_name and not last_name:
                        with st.spinner(f"Looking up ORCID {orcid}..."):
                            orcid_meta = lookup_orcid(orcid)
                            if orcid_meta:
                                first_name = orcid_meta.get('first_name', '')
                                last_name = orcid_meta.get('last_name', '')
                                organization = orcid_meta.get('organization', '')

                    parsed_results.append({
                        'author_order': i + len(st.session_state.metadata['Investigator']),
                        'first_name': first_name,
                        'last_name': last_name,
                        'person_orcid': orcid,
                        'email': '',
                        'organization_name': organization
                    })

            if parsed_results:
                st.write("**Preview & Edit Parsed Results:**")
                # Ensure author_order is correctly typed and sequence is preserved
                preview_df = pd.DataFrame(parsed_results)
                edited_df = st.data_editor(preview_df, num_rows="dynamic", use_container_width=True, key="investigator_editor")

                if st.button("➕ Add All Parsed Investigators", type="primary"):
                    st.session_state.metadata['Investigator'].extend(edited_df.to_dict('records'))
                    st.session_state.raw_authors = "" # Clear after adding
                    st.success("✅ Added investigators!")
                    st.rerun()

        # Display existing investigators
        if st.session_state.metadata['Investigator']:
            st.write("**Current Investigators:**")
            for idx, inv in enumerate(st.session_state.metadata['Investigator']):
                col1, col2 = st.columns([6, 1])
                with col1:
                    email = inv.get('email', ''); orcid = inv.get('person_orcid', '')
                    contact_info = email if email else orcid
                    display_contact = f" ({contact_info})" if contact_info else ""
                    st.write(f"{idx+1}. {inv.get('first_name', '')} {inv.get('last_name', '')}{display_contact} - {inv.get('organization_name', '')}")
                with col2:
                    if st.button("🗑️", key=f"del_inv_{idx}"):
                        st.session_state.metadata['Investigator'].pop(idx)
                        st.rerun()

            if st.button("➡️ All Investigators Added - Proceed to Related Work", use_container_width=True):
                st.session_state.phase0_step = 'Related_Work'
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
            inv_prepopulate = {
                'author_order': len(st.session_state.metadata['Investigator']) + 1,
                'first_name': st.session_state.get('inv_first', ''),
                'last_name': st.session_state.get('inv_last', ''),
                'organization_name': st.session_state.get('inv_org', ''),
                'person_orcid': orcid_input
            }
            
            investigator_data = render_dynamic_form(
                "Investigator",
                schema,
                permissible_values,
                current_data=inv_prepopulate
            )
            
            submitted = st.form_submit_button("Save & Next")
            if submitted:
                if investigator_data.get('first_name') and investigator_data.get('last_name'):
                    st.session_state.metadata['Investigator'].append(investigator_data)

                    # Clear session state
                    for key in ['inv_orcid', 'inv_first', 'inv_last', 'inv_org']:
                        if key in st.session_state:
                            st.session_state[key] = ""

                    st.toast(f"✅ Added investigator: {investigator_data['first_name']} {investigator_data['last_name']}")
                    st.session_state.phase0_step = 'Related_Work'
                    st.rerun()
                else:
                    st.error("Please fill in all required fields (First Name, Last Name).")
    
    # TAB 5: Related Work
    elif st.session_state.phase0_step == "Related_Work":
        st.subheader("Related Work / Publications")
        st.markdown("Add publications, DOIs, or related work for this dataset.")
        
        # Display existing related works
        if st.session_state.metadata['Related_Work']:
            st.write("**Current Related Works:**")
            for idx, work in enumerate(st.session_state.metadata['Related_Work']):
                col1, col2 = st.columns([6, 1])
                with col1:
                    st.write(f"{idx+1}. {work.get('title', '')} - DOI: {work.get('DOI', '')}")
                with col2:
                    if st.button("🗑️", key=f"del_work_{idx}"):
                        st.session_state.metadata['Related_Work'].pop(idx)
                        st.rerun()
        
        st.markdown("---")
        st.write("**Add New Related Work:**")
        
        doi_input_area = st.text_area("DOIs (Enter one or more, separated by commas or newlines)*", value=st.session_state.get('rw_doi', ''), help="Example: 10.1148/radiol.2021203534, 10.1038/s41597-020-00622-z")
        if st.button("🔍 Lookup DOIs"):
            if doi_input_area:
                dois = [d.strip() for d in re.split(r'[,\n]', doi_input_area) if d.strip()]
                new_pending = []
                for d in dois:
                    with st.spinner(f"Looking up {d}..."):
                        doi_metadata = lookup_doi(d)
                        if doi_metadata:
                            # Check if already added or already pending
                            exists = any(work.get('DOI') == d for work in st.session_state.metadata['Related_Work'])
                            pending_exists = any(p.get('DOI') == d for p in st.session_state.pending_dois)
                            if not exists and not pending_exists:
                                work_data = {
                                    'DOI': d,
                                    'title': doi_metadata['title'],
                                    'authorship': doi_metadata['authors'],
                                    'year_of_publication': doi_metadata.get('year', ''),
                                    'journal_citation': doi_metadata.get('journal', '')
                                }
                                new_pending.append(work_data)
                        else:
                            st.error(f"DOI not found: {d}")

                if new_pending:
                    st.session_state.pending_dois.extend(new_pending)
                    st.session_state.rw_doi = "" # Clear input
                    st.rerun()
            else:
                st.warning("Please enter at least one DOI.")

        if st.session_state.pending_dois:
            st.write("### 🆕 New Related Work(s) Found")
            st.info("Please specify the Publication Type and Relationship Type for each item below.")

            dois_to_remove = []

            def get_options(prop_name):
                opts = permissible_values.get(prop_name, [])
                if opts and isinstance(opts[0], dict):
                    return [f"{o['value']}" for o in opts]
                return opts

            for i, pending in enumerate(st.session_state.pending_dois):
                with st.container(border=True):
                    st.markdown(f"**DOI:** `{pending['DOI']}`")
                    st.markdown(f"**Title:** {pending['title']}")

                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        p_type_opts = get_options('publication_type')
                        p_type = st.selectbox("Publication Type", options=[""] + p_type_opts, key=f"p_type_{i}")
                    with col2:
                        r_type_opts = get_options('relationship_type')
                        r_type = st.selectbox("Relationship Type", options=[""] + r_type_opts, key=f"r_type_{i}")
                    with col3:
                        st.write(" ") # alignment
                        st.write(" ")
                        if st.button("➕ Add", key=f"add_p_{i}"):
                            if p_type and r_type:
                                pending['publication_type'] = p_type
                                pending['relationship_type'] = r_type
                                st.session_state.metadata['Related_Work'].append(pending)
                                # Remove from pending list immediately before rerun
                                st.session_state.pending_dois.pop(i)
                                st.rerun()
                            else:
                                st.error("Required.")

        st.markdown("---")
        st.write("**Add Related Work Manually:**")
        with st.form("related_work_form"):
            rw_prepopulate = {
                'DOI': '',
                'title': st.session_state.get('rw_title', ''),
                'authorship': st.session_state.get('rw_authors', '')
            }
            
            work_data = render_dynamic_form(
                "Related_Work",
                schema,
                permissible_values,
                current_data=rw_prepopulate
            )
            
            submitted = st.form_submit_button("Add")
            if submitted:
                # DOI and Publication Type are required by the model
                if work_data.get('DOI') and work_data.get('publication_type'):
                    st.session_state.metadata['Related_Work'].append(work_data)

                    # Clear session state for next entry
                    for key in ['rw_doi', 'rw_title', 'rw_authors']:
                        if key in st.session_state:
                            st.session_state[key] = ""

                    st.toast(f"✅ Added related work: {work_data['DOI']}")
                    st.rerun()
                else:
                    st.error("Please fill in all required fields (DOI, Publication Type).")

        if st.button("➡️ All Related Works Added - Proceed to Review", use_container_width=True):
            st.session_state.phase0_step = 'Review'
            st.rerun()
    
    # TAB 6: Review & Generate
    elif st.session_state.phase0_step == "Review":
        st.subheader("Review & Generate TSV Files")
        st.markdown("Review all your metadata and generate the TSV files.")

        # --- Analysis Result Validation ---
        is_analysis_result = st.session_state.get('proposal_raw_data', {}).get('Proposal Type') == "Analysis Results Proposal"
        related_datasets = []
        if is_analysis_result:
            related_datasets = [w for w in st.session_state.metadata.get('Related_Work', []) if w.get('publication_type') == 'Dataset']
            if not related_datasets:
                st.error("⚠️ **Action Required**: For Analysis Results, you must provide at least one Related Dataset. Please go to the **Related Work** tab and add a Related Dataset before proceeding.")
                # We don't stop here, but we'll disable the final ZIP generation

        # --- DOCX Generation Helper ---
        def generate_summary_docx():
            doc = Document()

            nickname = ""
            if st.session_state.metadata['Dataset']:
                nickname = st.session_state.metadata['Dataset'][0].get('dataset_short_name', '')
                long_name = st.session_state.metadata['Dataset'][0].get('dataset_long_name', '')

            doc.add_heading('NCI Imaging Submission Summary', 0)

            # [H1] Basic information:
            doc.add_heading('Basic information', level=1)
            table = doc.add_table(rows=0, cols=2)
            table.style = 'Table Grid'

            def add_row(t, label, value):
                row = t.add_row().cells
                row[0].text = label
                row[0].paragraphs[0].runs[0].bold = True
                row[1].text = str(value) if value is not None else ""

            # POC names, phones, emails
            prop_data = st.session_state.get('proposal_raw_data', {})
            poc_info = []
            for role in ["Scientific", "Technical", "Legal"]:
                name = prop_data.get(f"{role} POC Name", "")
                email = prop_data.get(f"{role} POC Email", "")
                phone = str(prop_data.get(f"{role} POC Phone", ""))
                if name:
                    line = f"{role}: {name} ({email})"
                    if phone and phone.lower() != "nan" and phone.strip():
                        line += f" {phone}"
                    poc_info.append(line.strip())

            add_row(table, "POC Information", "\n".join(poc_info))
            add_row(table, "Submission schedule and deadlines", prop_data.get('Time Constraints', ''))
            add_row(table, "Expected patient count", prop_data.get('number_of_subjects', ''))
            add_row(table, "Expected disk size", prop_data.get('disk_space', ''))

            # Expected types of data
            types = []
            file_formats = prop_data.get('file_formats', '')

            # Map formats to types for better display
            format_map = {}
            if file_formats:
                for part in str(file_formats).split(';'):
                    if ' - ' in part:
                        t, f = part.split(' - ', 1)
                        format_map[t.strip()] = f.strip()

            def get_formatted_type(label, key):
                val = prop_data.get(key)
                if not val: return None

                items = []
                if isinstance(val, list):
                    items = val
                elif isinstance(val, str):
                    if val.startswith('[') and val.endswith(']'):
                        try:
                            items = ast.literal_eval(val)
                        except:
                            items = [val]
                    else:
                        items = [v.strip() for v in val.split(',')]

                formatted_items = []
                for item in items:
                    if item in format_map:
                        formatted_items.append(f"{item} ({format_map[item]})")
                    else:
                        formatted_items.append(item)
                return f"{label}: {', '.join(formatted_items)}"

            img_type = get_formatted_type("Images", "image_types")
            if img_type: types.append(img_type)

            supp_type = get_formatted_type("Supporting", "supporting_data")
            if supp_type: types.append(supp_type)

            der_type = get_formatted_type("Derived", "derived_types")
            if der_type: types.append(der_type)

            add_row(table, "Expected types of data", "\n".join(types))
            add_row(table, "Approximate date range of study execution", "")

            # [H1] DataCite Information:
            doc.add_heading('DataCite Information', level=1)
            table_dc = doc.add_table(rows=0, cols=2)
            table_dc.style = 'Table Grid'

            # Authors (Last Name, First Name (ORCiD ID if provided) for each author in the correct order)
            invs = sorted(st.session_state.metadata.get('Investigator', []), key=lambda x: int(x.get('author_order', 999)) if str(x.get('author_order', '')).isdigit() else 999)
            author_strings = []
            for inv in invs:
                auth_str = f"{inv.get('last_name', '')}, {inv.get('first_name', '')}"
                if inv.get('person_orcid'):
                    auth_str += f" ({inv.get('person_orcid')})"
                author_strings.append(auth_str)
            add_row(table_dc, "Authors", "\n".join(author_strings))
            add_row(table_dc, "Rights", "") # Placeholder for license from file.tsv logic

            # [H1] Wordpress Page:
            doc.add_heading('Wordpress Page', level=1)
            doc.add_heading('Add New Collection', level=2)
            table_wp1 = doc.add_table(rows=0, cols=2)
            table_wp1.style = 'Table Grid'
            add_row(table_wp1, "New Collection Title", nickname)

            doc.add_heading('Dataset Information', level=2)
            table_wp2 = doc.add_table(rows=0, cols=2)
            table_wp2.style = 'Table Grid'
            add_row(table_wp2, "DOI", "Do not include https://doi.org From Datacite.  10.7937/")
            add_row(table_wp2, "Status", "Set to Ongoing or Complete")
            add_row(table_wp2, "Title", st.session_state.metadata['Dataset'][0].get('dataset_long_name', '') if st.session_state.metadata['Dataset'] else "")
            add_row(table_wp2, "Short Title", nickname)
            add_row(table_wp2, "Featured Image", "Sample Image/Figure: Used as the \"Featured Image\" in Wordpress")
            add_row(table_wp2, "Summary", "Insert link to google doc (draft where we iterate with the submitter), then populate with the final description when it's ready.")

            ds_meta = st.session_state.metadata['Dataset'][0] if st.session_state.metadata['Dataset'] else {}
            add_row(table_wp2, "Acknowledgements", ds_meta.get('acknowledgements', ''))

            funding_parts = []
            if ds_meta.get('funding_agency'): funding_parts.append(f"Agency: {ds_meta['funding_agency']}")
            if ds_meta.get('funding_source_program_name'): funding_parts.append(f"Program: {ds_meta['funding_source_program_name']}")
            if ds_meta.get('grant_id'): funding_parts.append(f"Grant: {ds_meta['grant_id']}")

            add_row(table_wp2, "Funding", " | ".join(funding_parts))

            prog_meta = st.session_state.metadata['Program'][0] if st.session_state.metadata['Program'] else {}
            add_row(table_wp2, "Program", prog_meta.get('program_short_name', ''))

            doc.add_heading('Details', level=2)
            table_wp3 = doc.add_table(rows=0, cols=2)
            table_wp3.style = 'Table Grid'
            add_row(table_wp3, "Cancer Types", prop_data.get('diagnosis', ''))
            add_row(table_wp3, "Cancer Locations", prop_data.get('disease_site', ''))
            add_row(table_wp3, "Species", "Human (change if not)")
            add_row(table_wp3, "Subjects", prop_data.get('number_of_subjects', ''))

            doc.add_heading('Data Access', level=2)
            table_wp4 = doc.add_table(rows=0, cols=2)
            table_wp4.style = 'Table Grid'
            add_row(table_wp4, "Downloads", "Refer to \"data type\" (link: https://www.cancerimagingarchive.net/wp-admin/edit.php?post_type=tcia_data_type) and \"file format\" (link: https://www.cancerimagingarchive.net/wp-admin/edit.php?post_type=tcia_file_type) labels")
            add_row(table_wp4, "Make New Version", "SAVE YOUR CHANGES to this post before clicking this button or you will lose any changes by clicking the Update button (upper-right).  Clones the current version to the Previous Versions tables, and updates Version Number and Date Updated.")
            add_row(table_wp4, "Version Number", "The version number updates programmatically with the Make New Version button.")
            add_row(table_wp4, "Date Updated", "Updates programmatically with the Make New Version button, but can be changed manually.")
            add_row(table_wp4, "Version Change Log", "Before changing the version log, make a new version using Make New Version button, above.")

            doc.add_heading('Data Access Supplemental', level=2)
            table_wp5 = doc.add_table(rows=0, cols=2)
            table_wp5.style = 'Table Grid'
            add_row(table_wp5, "Additional Resources", st.session_state.cicadas.get('external_resources', ''))

            # Supporting Data from proposal
            supp_data_val = prop_data.get('supporting_data', '')
            if isinstance(supp_data_val, list):
                supp_data_str = ", ".join(supp_data_val)
            else:
                supp_data_str = str(supp_data_val)
            add_row(table_wp5, "Supporting Data", supp_data_str)

            # Related Datasets (Move 'Dataset' type related works here)
            all_rel_works = st.session_state.metadata.get('Related_Work', [])
            rel_datasets = [w for w in all_rel_works if w.get('publication_type') == 'Dataset']
            rd_text = "\n".join([f"{d.get('title')} (DOI: {d.get('DOI')})" for d in rel_datasets])
            add_row(table_wp5, "Related Datasets", rd_text)

            doc.add_heading('Citations and Data Usage Policy', level=2)
            table_wp6 = doc.add_table(rows=0, cols=2)
            table_wp6.style = 'Table Grid'

            # Citations (All other related works)
            other_rel_works = [w for w in all_rel_works if w.get('publication_type') != 'Dataset']
            citation_text = ""
            if other_rel_works:
                for w in other_rel_works:
                    citation_text += f"{w.get('authorship', 'Unknown Authors')} ({w.get('year_of_publication', 'n.d.')}). {w.get('title', 'No Title')}. {w.get('journal_citation', '')} DOI: {w.get('DOI', 'No DOI')}\n\n"
            else:
                citation_text = "Source: Default Crosscite output using DOI\n\nThis is a pop out that you add:\n1. Dataset citation\n2. Data descriptor if available\n3. Any required acknowledgement"

            add_row(table_wp6, "Citations", citation_text.strip())

            # [H1] Issue Tracking
            doc.add_heading('Issue Tracking', level=1)
            table_it = doc.add_table(rows=0, cols=2)
            table_it.style = 'Table Grid'
            add_row(table_it, "Kickoff email date", "")

            docx_buf = BytesIO()
            doc.save(docx_buf)
            docx_buf.seek(0)
            return docx_buf

        # --- ZIP Generation Helper ---
        def generate_full_zip(generated_files):
            zip_buf = BytesIO()
            today = datetime.date.today().isoformat()
            nickname = st.session_state.metadata['Dataset'][0].get('dataset_short_name', 'dataset') if st.session_state.metadata['Dataset'] else 'dataset'
            zip_filename = f"{nickname}_NCI_Submission_Package_{today}.zip"

            with zipfile.ZipFile(zip_buf, 'w') as zf:
                # Add TSVs
                for entity, path in generated_files.items():
                    if os.path.exists(path) and os.path.getsize(path) > 0:
                        zf.write(path, os.path.basename(path))

                # Add DOCX
                docx_data = generate_summary_docx()
                zf.writestr(f"{nickname}_submission_summary_{today}.docx", docx_data.getvalue())

            zip_buf.seek(0)
            return zip_buf, zip_filename

        # --- Automatic Generation ---
        generated_files_map = {}

        # Prepare metadata with relationships accounted for
        metadata_to_write = {}
        for entity_name, data_list in st.session_state.metadata.items():
            if not data_list:
                continue

            # Create a copy to avoid modifying session state directly for writing
            processed_data = [item.copy() for item in data_list]

            # Sort investigators by author_order
            if entity_name == "Investigator":
                processed_data.sort(key=lambda x: int(x.get('author_order', 999)) if str(x.get('author_order', '')).isdigit() else 999)

            # Check for relationships to other Phase 0 entities
            for rel_name, rel_info in relationships.items():
                for end in rel_info.get('Ends', []):
                    if end['Src'] == entity_name and end['Dst'] in st.session_state.metadata:
                        dst_meta = st.session_state.metadata[end['Dst']]
                        if dst_meta:
                            dst_lower = end['Dst'].lower()
                            # Use short_name or first ID found as proxy for linkage
                            link_val = dst_meta[0].get(f"{dst_lower}_short_name") or dst_meta[0].get(f"{dst_lower}_id")
                            if link_val:
                                linkage_prop = next((p['Property'] for p in schema.get(entity_name, []) if p['Property'].lower().startswith(f"{dst_lower}.")), None)
                                if linkage_prop:
                                    for item in processed_data:
                                        if not item.get(linkage_prop):
                                            item[linkage_prop] = link_val

            metadata_to_write[entity_name] = processed_data

        nickname_prefix = ""
        if st.session_state.metadata.get('Dataset') and st.session_state.metadata['Dataset'][0].get('dataset_short_name'):
            nickname_prefix = st.session_state.metadata['Dataset'][0]['dataset_short_name']

        for entity_name, data in metadata_to_write.items():
            filepath = write_metadata_tsv(entity_name, data, schema, st.session_state.output_dir, filename_prefix=nickname_prefix)
            if filepath:
                generated_files_map[entity_name] = filepath
        st.session_state.generated_tsv_files = list(generated_files_map.values())
        # ----------------------------

        # --- Final Download Button ---
        st.write("### 📦 Final Submission Package")
        if is_analysis_result and not related_datasets:
            st.warning("Final ZIP generation is disabled until a Related Dataset is added.")
            st.button("📥 Download NCI Submission Package (ZIP)", disabled=True)
        else:
            zip_data, zip_filename = generate_full_zip(generated_files_map)
            st.download_button(
                label="📥 Download NCI Submission Package (ZIP)",
                data=zip_data,
                file_name=zip_filename,
                mime="application/zip",
                type="primary",
                use_container_width=True
            )
        st.markdown("---")

        # Display recap
        st.write("### 📋 Metadata Summary")
        
        review_entities = [
            ("Program", "Program"),
            ("Dataset", "Dataset"),
            ("Investigator", "Investigators"),
            ("Related_Work", "Related Works")
        ]
        
        for entity_key, label in review_entities:
            with st.expander(label, expanded=True):
                filepath = generated_files_map.get(entity_key)
                filename = os.path.basename(filepath) if filepath else f"{entity_key.lower()}.tsv"
                data_exists = len(st.session_state.metadata.get(entity_key, [])) > 0
                
                if data_exists and filepath and os.path.exists(filepath):
                    with open(filepath, 'r') as f:
                        st.download_button(
                            label=f"Download {filename}",
                            data=f.read(),
                            file_name=filename,
                            mime="text/tab-separated-values",
                            key=f"dl_btn_{entity_key}"
                        )
                else:
                    st.button(f"Download {filename}", key=f"dl_btn_disabled_{entity_key}", disabled=True)

                st.markdown("---")

                entity_data = st.session_state.metadata.get(entity_key)
                if entity_data:
                    if entity_key in ["Investigator", "Related_Work"]:
                        for idx, item in enumerate(entity_data):
                            st.write(f"**{entity_key} {idx+1}:**")
                            for key, value in item.items():
                                if isinstance(value, list): display_val = ", ".join(map(str, value))
                                elif pd.isna(value) or str(value).lower() == 'nan': display_val = ""
                                else: display_val = value
                                st.write(f"  - {key}: {display_val}")
                    else: # Program, Dataset
                        for key, value in entity_data[0].items():
                            display_val = ", ".join(map(str, value)) if isinstance(value, list) else value
                            st.write(f"**{key}:** {display_val}")
                else:
                    st.warning(f"No {entity_key.lower()} information provided.")

        st.markdown("---")
        
        if st.button("➡️ Proceed to CICADAS", use_container_width=True, type="primary"):
            st.session_state.phase = 1
            st.rerun()

# ============================================================================
# PHASE 1: CICADAS
# ============================================================================
elif st.session_state.phase == 1:
    st.header("CICADAS Dataset Description")
    st.markdown("""
    Follow the [CICADAS checklist](https://cancerimagingarchive.net/cicadas) to ensure your dataset
    is comprehensive and optimally discoverable.
    """)
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
            if c_intro: desc.append(f"## Introduction
{c_intro}")
            methods_content = ""
            if c_m_subjects: methods_content += f"### Subject Inclusion and Exclusion Criteria
{c_m_subjects}

"
            if c_m_acquisition: methods_content += f"### Data Acquisition
{c_m_acquisition}

"
            if c_m_analysis: methods_content += f"### Data Analysis
{c_m_analysis}

"
            if methods_content: desc.append(f"## Methods
{methods_content}")
            if c_usage: desc.append(f"## Usage Notes
{c_usage}")
            if c_ext: desc.append(f"## External Resources
{c_ext}")
            if st.session_state.metadata['Dataset']:
                ds = st.session_state.metadata['Dataset'][0]
                ds.update({'dataset_abstract': c_abstract, 'dataset_description': "

".join(desc), 'introduction': c_intro, 'methods_subjects': c_m_subjects, 'methods_acquisition': c_m_acquisition, 'methods_analysis': c_m_analysis, 'usage_notes': c_usage, 'external_resources': c_ext})
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
            elif uploaded_file.name.endswith('.tsv'): df = pd.read_csv(uploaded_file, sep='	')
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
                        edf.to_csv(output, sep='	', index=False)
                        st.download_button(f"Download {e}.tsv", open(output).read(), f"{e.lower()}.tsv")
                if st.button("🔄 Reset"): reset_app(); st.rerun()
        except Exception as e: st.error(f"Error: {e}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
NCI Imaging Submission Validator | Following <a href="https://github.com/CBIIT/nci-imaging-submission-model" style="color: gray;">NCI's Imaging Submission Model</a><br>
Leveraging NCIt, UBERON, and SNOMED ontologies for standardization
</div>
""", unsafe_allow_html=True)
