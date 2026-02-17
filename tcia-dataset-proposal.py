import streamlit as st
import pandas as pd
import os
import io
import json
import zipfile
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from docx import Document
import PyPDF2
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import simpleSplit
import importlib.util
import re
import requests

st.set_page_config(page_title="TCIA Dataset Proposal Form", layout="wide")

# Constants & Configuration
RESOURCES_DIR = os.path.join(os.path.dirname(__file__), 'tcia-remapping-skill', 'resources')

# Import MDF parser and helpers
skill_dir = os.path.join(os.path.dirname(__file__), 'tcia-remapping-skill')
mdf_parser_path = os.path.join(skill_dir, 'mdf_parser.py')
spec_mdf = importlib.util.spec_from_file_location("mdf_parser", mdf_parser_path)
mdf_parser = importlib.util.module_from_spec(spec_mdf)
spec_mdf.loader.exec_module(mdf_parser)
get_mdf_resources = mdf_parser.get_mdf_resources

orcid_helper_path = os.path.join(skill_dir, 'orcid_helper.py')
spec_orcid = importlib.util.spec_from_file_location("orcid_helper", orcid_helper_path)
orcid_helper = importlib.util.module_from_spec(spec_orcid)
spec_orcid.loader.exec_module(orcid_helper)

PERMISSIBLE_VALUES_FILE = os.path.join(RESOURCES_DIR, 'permissible_values.json')

LABELS = {
    "Proposal Type": "What kind of dataset are you submitting?",
    "Scientific POC Name": "Scientific POC Name*",
    "Scientific POC Email": "Scientific POC Email*",
    "Technical POC Name": "Technical POC Name*",
    "Technical POC Email": "Technical POC Email*",
    "Legal POC Name": "Legal POC Name*",
    "Legal POC Email": "Legal POC Email*",
    "Title": "Suggest a descriptive title for your dataset*",
    "Nickname": "Suggest a shorter nickname for your dataset*",
    "Authors": "List the authors of this data set*",
    "Abstract": "Dataset Abstract*",
    "Published Elsewhere": "Has this data ever been published elsewhere?*",
    "disease_site": "Primary disease site/location*",
    "diagnosis": "Histologic diagnosis*",
    "image_types": "Which image types are included in the data set?*",
    "supporting_data": "Which kinds of supporting data are included in the data set?*",
    "file_formats": "Specify the file format utilized for each type of data*",
    "modifications": "Describe any steps taken to modify data prior to submission*",
    "faces": "Does your data contain any images of patient faces?*",
    "exceptions": "Do you need to request any exceptions to TCIA's Open Access Policy?*",
    "collections_analyzed": "Which TCIA collection(s) did you analyze?*",
    "derived_types": "What types of derived data are included in the dataset?*",
    "image_records": "Do you have records to indicate exactly which TCIA images analyzed?*",
    "disk_space": "Approximate disk space required*",
    "Time Constraints": "Are there any time constraints associated with sharing your data set?*",
    "descriptor_publication": "Is there a related dataset descriptor publication? (i.e. Nature Scientific Data article on how to use the dataset)*",
    "additional_publications": "Any additional publications derived from these data?*",
    "acknowledgments": "Acknowledgments or funding statements*",
    "why_tcia": "Why would you like to publish this dataset on TCIA?*"
}

def load_json(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def lookup_doi(doi):
    """Fetch metadata from Crossref API"""
    if not doi:
        return None
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
            return f"{authors} ({year}). {title}. {journal}. DOI: {doi}"
    except:
        pass
    return None

@st.cache_data
def load_mdf_data():
    schema, mdf_pv, relationships = get_mdf_resources(RESOURCES_DIR)
    legacy_pv = load_json(PERMISSIBLE_VALUES_FILE)

    final_pv = legacy_pv.copy()
    if mdf_pv:
        for k, v in mdf_pv.items():
            final_pv[k] = v
    return schema, final_pv, relationships

schema, permissible_values, relationships = load_mdf_data()
AGREEMENT_TEMPLATE = os.path.join(RESOURCES_DIR, 'agreement_template.pdf')
HELP_DESK_EMAIL = os.getenv("TCIA_HELP_DESK_EMAIL", "help@cancerimagingarchive.net")

# Server-side SMTP configuration
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

st.title("📋 TCIA Dataset Proposal Form")
st.markdown("""
Welcome to the TCIA Dataset Proposal Form. Please fill out the information below to submit a proposal for
publishing a new dataset or analysis results on The Cancer Imaging Archive.
""")

# Initialize session state for authors
if 'validated_authors' not in st.session_state:
    st.session_state.validated_authors = []

# Initial choice
proposal_type = st.radio(
    "What kind of dataset are you submitting?",
    options=["New Collection Proposal", "Analysis Results Proposal"],
    help="Select 'New Collection' if you are submitting primary imaging data. Select 'Analysis Results' if you are submitting derived data (e.g., segmentations) from existing TCIA collections.",
    key="prop_type"
)

if proposal_type == "New Collection Proposal":
    st.info("💡 **New Collection Proposal**: Used for contributing original imaging data that has not been previously hosted on TCIA.")
else:
    st.info("💡 **Analysis Results Proposal**: Used for contributing derived data like annotations, segmentations, or radiomics features based on existing TCIA datasets.")

st.markdown("---")

# Form Questions
st.subheader("Contact Information")
if SMTP_SERVER and SMTP_USER and SMTP_PASSWORD:
    st.info("💡 **Note**: After completing this form, a copy of this proposal will be emailed to the Scientific, Technical, and Legal points of contact listed below.")

col1, col2 = st.columns(2)
with col1:
    sci_poc_name = st.text_input(LABELS["Scientific POC Name"], help="The person to contact about the proposal and data collection.", key="sci_poc_name")
    tech_poc_name = st.text_input(LABELS["Technical POC Name"], help="The person involved in sending the data.", key="tech_poc_name")
    legal_poc_name = st.text_input(LABELS["Legal POC Name"], help="Authorized signatory who will sign the TCIA Data Submission Agreement. This should not be the PI or department chair.", key="legal_poc_name")
with col2:
    sci_poc_email = st.text_input(LABELS["Scientific POC Email"], key="sci_poc_email")
    tech_poc_email = st.text_input(LABELS["Technical POC Email"], key="tech_poc_email")
    legal_poc_email = st.text_input(LABELS["Legal POC Email"], key="legal_poc_email")

st.subheader("Dataset Publication Details")
title = st.text_input(LABELS["Title"], help="Similar to a manuscript title.", key="title")
nickname = st.text_input(LABELS["Nickname"], help="Must be < 30 characters, letters, numbers, and dashes only.", max_chars=30, key="nickname")

# Authors Section
st.write(f"**{LABELS['Authors']}**")
authors_raw = st.text_area("Paste author names or ORCIDs (one per line or separated by semicolons)",
                           help="Example: John Smith; 0000-0002-6543-3443; Jane Doe",
                           key="authors_raw_input")

if st.button("🔍 Process & Validate Authors"):
    if authors_raw:
        lines = re.split(r'[;\n]', authors_raw)
        new_authors = []
        for line in lines:
            line = line.strip()
            if not line: continue
            parsed = orcid_helper.parse_author_input(line)

            matches = []
            with st.spinner(f"Searching ORCID for {line}..."):
                if parsed['orcid']:
                    profile = orcid_helper.get_orcid_profile(parsed['orcid'])
                    if profile:
                        matches = [profile]
                else:
                    matches = orcid_helper.get_profiles_for_name(parsed['first_name'], parsed['last_name'])

            new_authors.append({
                'parsed': parsed,
                'matches': matches,
                'selected_orcid': parsed['orcid'] if parsed['orcid'] else (matches[0]['orcid_id'] if len(matches) == 1 else None),
                'manual_first': parsed['first_name'],
                'manual_last': parsed['last_name'],
                'manual_org': matches[0]['organization'] if len(matches) == 1 else '',
                'manual_email': ''
            })
        st.session_state.validated_authors = new_authors
    else:
        st.warning("Please paste some author information first.")

if st.session_state.validated_authors:
    with st.expander("✅ Resolved Authors", expanded=True):
        for i, auth in enumerate(st.session_state.validated_authors):
            st.markdown(f"**Author {i+1}:** `{auth['parsed']['original_text']}`")
            col_sel, col_det = st.columns([2, 2])

            with col_sel:
                if auth['matches']:
                    match_options = ["(Keep as Name Only)"] + [f"{m['given_names']} {m['family_name']} - {m['organization']} ({m['orcid_id']})" for m in auth['matches']]

                    default_idx = 0
                    if auth['selected_orcid']:
                        for idx, m in enumerate(auth['matches']):
                            if m['orcid_id'] == auth['selected_orcid']:
                                default_idx = idx + 1
                                break

                    sel = st.selectbox(f"ORCID Match for #{i+1}", options=match_options, index=default_idx, key=f"sel_auth_{i}")

                    if sel == "(Keep as Name Only)":
                        st.session_state.validated_authors[i]['selected_orcid'] = None
                    else:
                        match_id = re.search(r'\((0000-\d{4}-\d{4}-\d{3}[\dX])\)', sel).group(1)
                        st.session_state.validated_authors[i]['selected_orcid'] = match_id
                        # Update details if changed
                        for m in auth['matches']:
                            if m['orcid_id'] == match_id:
                                st.session_state.validated_authors[i]['manual_first'] = m['given_names']
                                st.session_state.validated_authors[i]['manual_last'] = m['family_name']
                                st.session_state.validated_authors[i]['manual_org'] = m['organization']
                else:
                    st.info("No ORCID matches found.")

            with col_det:
                st.session_state.validated_authors[i]['manual_first'] = st.text_input("First Name", value=auth['manual_first'], key=f"f_name_{i}")
                st.session_state.validated_authors[i]['manual_last'] = st.text_input("Last Name", value=auth['manual_last'], key=f"l_name_{i}")
                st.session_state.validated_authors[i]['manual_org'] = st.text_input("Organization", value=auth['manual_org'], key=f"org_{i}")
                st.session_state.validated_authors[i]['manual_email'] = st.text_input("Email (optional for proposal, required for Investigator TSV)", value=auth.get('manual_email', ''), key=f"email_{i}")
            st.markdown("---")

        if st.button("Clear Author List"):
            st.session_state.validated_authors = []
            st.rerun()

abstract = st.text_area(LABELS["Abstract"], help="Focus on describing the dataset itself.", max_chars=1000, key="abstract")

st.subheader("Data Collection Details")
published_elsewhere = st.text_input(LABELS["Published Elsewhere"], help="If so, why publish on TCIA? Do you intend for the original to remain accessible?", key="published_elsewhere")

# Adaptive fields
extra_data = {}
if proposal_type == "New Collection Proposal":
    col1, col2 = st.columns(2)
    with col1:
        site_raw = permissible_values.get('primary_site', []) if permissible_values else []
        site_options = sorted(list(set([v['value'] if isinstance(v, dict) else str(v) for v in site_raw])))
        extra_data['disease_site'] = st.selectbox(LABELS["disease_site"], options=[""] + site_options, key="disease_site")
    with col2:
        diag_raw = permissible_values.get('primary_diagnosis', []) if permissible_values else []
        diag_options = sorted(list(set([v['value'] if isinstance(v, dict) else str(v) for v in diag_raw])))
        extra_data['diagnosis'] = st.selectbox(LABELS["diagnosis"], options=[""] + diag_options, key="diagnosis")

    extra_data['image_types'] = st.multiselect(
        LABELS["image_types"],
        options=["MR", "CT", "PET", "PET-CT", "PET-MR", "Mammograms", "Ultrasound", "Xray", "Radiation Therapy", "Whole Slide Image", "CODEX", "Single-cell Image", "Photomicrograph", "Microarray", "Multiphoton", "Immunofluorescence", "Other"],
        key="image_types"
    )
    extra_data['supporting_data'] = st.multiselect(
        LABELS["supporting_data"],
        options=["Clinical", "Image Analyses", "Image Registrations", "Genomics", "Proteomics", "Software / Source Code", "No additional data", "Other"],
        key="supporting_data"
    )
    extra_data['file_formats'] = st.text_area(LABELS["file_formats"], key="file_formats")
    extra_data['modifications'] = st.text_area(LABELS["modifications"], key="modifications")
    extra_data['faces'] = st.radio(LABELS["faces"], options=["Yes", "No"], key="faces")
    extra_data['exceptions'] = st.text_input(LABELS["exceptions"], value="No exceptions requested", key="exceptions")
else: # Analysis Results
    extra_data['collections_analyzed'] = st.text_input(LABELS["collections_analyzed"], key="collections_analyzed")
    extra_data['derived_types'] = st.multiselect(
        LABELS["derived_types"],
        options=["Segmentation", "Classification", "Quantitative Feature", "Image (converted/processed/registered)", "Other"],
        key="derived_types"
    )
    extra_data['image_records'] = st.radio(LABELS["image_records"], options=["Yes, I know exactly.", "No, I need assistance."], key="image_records")
    extra_data['file_formats'] = st.text_area(LABELS["file_formats"], key="file_formats_analysis")
# Shared bottom fields
col1, col2 = st.columns(2)
with col1:
    extra_data['disk_space'] = st.text_input(LABELS["disk_space"], key="disk_space")
with col2:
    time_constraints = st.text_input(LABELS["Time Constraints"], key="time_constraints")

st.markdown(f"**{LABELS['descriptor_publication']}**")
doi_desc = st.text_input("Enter DOI for Descriptor Publication (optional lookup)", key="doi_desc_input")
if st.button("🔍 Lookup Descriptor DOI"):
    if doi_desc:
        with st.spinner("Looking up DOI..."):
            result = lookup_doi(doi_desc)
            if result:
                st.session_state.descriptor_publication = result
                st.success("Metadata found!")
            else:
                st.error("DOI not found.")

extra_data['descriptor_publication'] = st.text_area("Descriptor Publication Details*", value=st.session_state.get('descriptor_publication', ''), key="descriptor_publication", help="Auto-populated if DOI lookup is used.")

st.markdown(f"**{LABELS['additional_publications']}**")
doi_add = st.text_area("Enter DOIs for Additional Publications (one per line, optional lookup)", key="doi_add_input")
if st.button("🔍 Lookup Additional DOIs"):
    if doi_add:
        dois = [d.strip() for d in re.split(r'[,\n]', doi_add) if d.strip()]
        results = []
        with st.spinner(f"Looking up {len(dois)} DOIs..."):
            for d in dois:
                res = lookup_doi(d)
                if res:
                    results.append(res)
                else:
                    st.error(f"DOI not found: {d}")
        if results:
            current = st.session_state.get('additional_publications', '')
            new_text = "\n\n".join(results)
            st.session_state.additional_publications = (current + "\n\n" + new_text).strip()
            st.success(f"✅ Added {len(results)} publication(s)!")

extra_data['additional_publications'] = st.text_area("Additional Publication Details*", value=st.session_state.get('additional_publications', ''), key="additional_publications", help="Auto-populated if DOI lookup is used.")
extra_data['acknowledgments'] = st.text_area(LABELS["acknowledgments"], key="acknowledgments")
extra_data['why_tcia'] = st.multiselect(
    LABELS["why_tcia"],
    options=["To meet a funding agency's requirements", "To meet a journal's requirements", "To facilitate collaboration", "To facilitate a challenge competition", "Other"],
    key="why_tcia"
)

button_label = "Submit" if (SMTP_SERVER and SMTP_USER and SMTP_PASSWORD) else "Generate Proposal Documents"
submit_button = st.button(button_label, type="primary")

# Processing after submission
if submit_button:
    # 1. Validation
    missing_fields = []
    if not sci_poc_name: missing_fields.append(LABELS["Scientific POC Name"])
    if not sci_poc_email: missing_fields.append(LABELS["Scientific POC Email"])
    if not tech_poc_name: missing_fields.append(LABELS["Technical POC Name"])
    if not tech_poc_email: missing_fields.append(LABELS["Technical POC Email"])
    if not legal_poc_name: missing_fields.append(LABELS["Legal POC Name"])
    if not legal_poc_email: missing_fields.append(LABELS["Legal POC Email"])
    if not title: missing_fields.append(LABELS["Title"])
    if not nickname: missing_fields.append(LABELS["Nickname"])
    if not st.session_state.validated_authors:
        missing_fields.append(LABELS["Authors"] + " (Please validate at least one author)")
    if not abstract: missing_fields.append(LABELS["Abstract"])
    if not published_elsewhere: missing_fields.append(LABELS["Published Elsewhere"])

    for key, val in extra_data.items():
        if not val:
            label = LABELS.get(key, key.replace('_', ' ').title())
            missing_fields.append(label)

    if not time_constraints: missing_fields.append(LABELS["Time Constraints"])

    if missing_fields:
        st.error("Please fill in all required fields:")
        for field in missing_fields:
            st.write(f"- {field}")
    else:
        # Format authors for summary
        authors_display = "; ".join([
            f"{a['manual_last']}, {a['manual_first']} ({a['selected_orcid']})" if a['selected_orcid']
            else f"{a['manual_last']}, {a['manual_first']}"
            for a in st.session_state.validated_authors
        ])

        # Prepare data for files
        all_responses = {
            "Proposal Type": proposal_type,
            "Scientific POC Name": sci_poc_name,
            "Scientific POC Email": sci_poc_email,
            "Technical POC Name": tech_poc_name,
            "Technical POC Email": tech_poc_email,
            "Legal POC Name": legal_poc_name,
            "Legal POC Email": legal_poc_email,
            "Time Constraints": time_constraints,
            "Title": title,
            "Nickname": nickname,
            "Authors": authors_display,
            "Abstract": abstract,
            "Published Elsewhere": published_elsewhere
        }
        all_responses.update(extra_data)

        # Generate TSV
        tsv_buffer = io.StringIO()
        df = pd.DataFrame([all_responses])
        df.to_csv(tsv_buffer, sep='\t', index=False)

        # Generate Investigators TSV
        inv_data = []
        for a in st.session_state.validated_authors:
            inv_data.append({
                'first_name': a['manual_first'],
                'last_name': a['manual_last'],
                'person_orcid': a.get('selected_orcid', ''),
                'organization_name': a.get('manual_org', ''),
                'email': a.get('manual_email', '')
            })
        inv_df = pd.DataFrame(inv_data)
        # Ensure columns match Investigator schema (exclude ID fields)
        inv_cols = [p['Property'] for p in schema.get('Investigator', []) if not p['Property'].endswith('_id') and '.' not in p['Property']]
        for col in inv_cols:
            if col not in inv_df.columns:
                inv_df[col] = ""
        inv_df = inv_df[inv_cols]
        inv_tsv_content = inv_df.to_csv(sep='\t', index=False)

        # Generate DOCX
        doc = Document()
        doc.add_heading(f"TCIA Dataset Proposal: {title}", 0)
        for key, value in all_responses.items():
            label = LABELS.get(key, key)

            doc.add_paragraph(f"{label}:", style='Heading 2')
            doc.add_paragraph(str(value))

        docx_buffer = io.BytesIO()
        doc.save(docx_buffer)
        docx_buffer.seek(0)

        # Generate PDF
        pdf_buffer = io.BytesIO()
        try:
            # Create a new page 6 for Exhibit A
            exhibit_a_buffer = io.BytesIO()
            c = canvas.Canvas(exhibit_a_buffer, pagesize=letter)
            width, height = letter

            # Header matching the template
            c.setFont("Helvetica", 10)
            c.drawString(50, height - 50, "TCIA Data Submission Agreement (v. 20220 914) Page 6 of 7")

            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(width/2, height - 100, "EXHIBIT A")
            c.drawCentredString(width/2, height - 120, "DESCRIPTION OF SUBMISSION DATA")

            c.setFont("Helvetica", 11)
            text_object = c.beginText(50, height - 160)
            text_object.setFont("Helvetica", 11)

            wrapped_abstract = simpleSplit(abstract, "Helvetica", 11, width - 100)
            for line in wrapped_abstract:
                text_object.textLine(line)

            c.drawText(text_object)
            c.showPage()
            c.save()
            exhibit_a_buffer.seek(0)

            # Merge with template
            reader = PyPDF2.PdfReader(AGREEMENT_TEMPLATE)
            writer = PyPDF2.PdfWriter()

            # Pages 1-5
            for i in range(5):
                writer.add_page(reader.pages[i])

            # Replace Page 6
            new_exhibit_reader = PyPDF2.PdfReader(exhibit_a_buffer)
            writer.add_page(new_exhibit_reader.pages[0])

            # Page 7
            writer.add_page(reader.pages[6])

            writer.write(pdf_buffer)
            pdf_buffer.seek(0)
            pdf_success = True
        except Exception as e:
            st.error(f"Error generating PDF: {e}")
            pdf_success = False

        # Create ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            zip_file.writestr("proposal_summary.tsv", tsv_buffer.getvalue())
            zip_file.writestr("investigators.tsv", inv_tsv_content)
            zip_file.writestr("proposal_summary.docx", docx_buffer.getvalue())
            if pdf_success:
                zip_file.writestr("agreement_with_exhibit_a.pdf", pdf_buffer.getvalue())
        zip_buffer.seek(0)

        # Store in session state for later use in email and to persist buttons
        st.session_state['proposal_files'] = {
            'tsv': tsv_buffer.getvalue(),
            'docx': docx_buffer.getvalue(),
            'pdf': pdf_buffer.getvalue() if pdf_success else None,
            'zip': zip_buffer.getvalue(),
            'title': title,
            'proposal_type': proposal_type,
            'pocs': [sci_poc_email, tech_poc_email, legal_poc_email]
        }
        st.session_state['proposal_generated'] = True

        # Determine if we can send automatically
        can_send_auto = all([SMTP_SERVER, SMTP_USER, SMTP_PASSWORD])
        if can_send_auto:
            try:
                msg = MIMEMultipart()
                msg['From'] = SMTP_USER
                msg['To'] = HELP_DESK_EMAIL
                msg['Cc'] = ", ".join([sci_poc_email, tech_poc_email, legal_poc_email])
                msg['Subject'] = f"New Dataset Proposal: {title}"

                body = f"A new dataset proposal has been submitted via the Dataset Proposal Form.\n\nType: {proposal_type}\nTitle: {title}\nSubmitters: {', '.join([sci_poc_email, tech_poc_email, legal_poc_email])}"
                msg.attach(MIMEText(body, 'plain'))

                part = MIMEBase('application', 'zip')
                part.set_payload(zip_buffer.getvalue())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment; filename="proposal_package.zip"')
                msg.attach(part)

                server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                # Send to both To and Cc addresses
                recipients = [HELP_DESK_EMAIL, sci_poc_email, tech_poc_email, legal_poc_email]
                server.send_message(msg, to_addrs=recipients)
                server.quit()
                st.session_state['email_sent'] = True
            except Exception as e:
                st.error(f"Failed to send email: {e}")

if st.session_state.get('proposal_generated'):
    can_send_auto = all([SMTP_SERVER, SMTP_USER, SMTP_PASSWORD])
    files = st.session_state.get('proposal_files')

    if not can_send_auto:
        st.success("✅ Proposal documents generated successfully!")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button("Download TSV (Import to Remapper)", data=files['tsv'], file_name="proposal.tsv", mime="text/tab-separated-values")
        with col2:
            st.download_button("Download DOCX Summary", data=files['docx'], file_name="proposal.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        with col3:
            if files['pdf']:
                st.download_button("Download PDF Agreement", data=files['pdf'], file_name="agreement_updated.pdf", mime="application/pdf")

        st.info("💡 **Please download these documents and keep a copy for your records.**")
        st.info(f"💡 **Manual Submission**: Please email the generated files as attachments to **{HELP_DESK_EMAIL}**.")
    else:
        if st.session_state.get('email_sent'):
            st.success(f"📨 Proposal sent to {HELP_DESK_EMAIL} and CC'd to POCs!")
        else:
            st.info("Proposal generated but failed to send email. Please check your SMTP settings or contact support.")

# Footer
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
TCIA Dataset Proposal Form | {HELP_DESK_EMAIL}
</div>
""", unsafe_allow_html=True)
