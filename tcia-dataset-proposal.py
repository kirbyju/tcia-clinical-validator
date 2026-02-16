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

st.set_page_config(page_title="TCIA Dataset Proposal Form", layout="wide")

# Constants & Configuration
RESOURCES_DIR = os.path.join(os.path.dirname(__file__), 'tcia-remapping-skill', 'resources')

# Import MDF parser
skill_dir = os.path.join(os.path.dirname(__file__), 'tcia-remapping-skill')
mdf_parser_path = os.path.join(skill_dir, 'mdf_parser.py')
spec_mdf = importlib.util.spec_from_file_location("mdf_parser", mdf_parser_path)
mdf_parser = importlib.util.module_from_spec(spec_mdf)
spec_mdf.loader.exec_module(mdf_parser)
get_mdf_resources = mdf_parser.get_mdf_resources

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
    "num_subjects_new": "How many subjects are in your data set?*",
    "num_subjects_analysis": "How many patients are included in your dataset?*",
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

# Initial choice
proposal_type = st.radio(
    "What kind of dataset are you submitting?",
    options=["New Collection Proposal", "Analysis Results Proposal"],
    help="Select 'New Collection' if you are submitting primary imaging data. Select 'Analysis Results' if you are submitting derived data (e.g., segmentations) from existing TCIA collections."
)

if proposal_type == "New Collection Proposal":
    st.info("💡 **New Collection Proposal**: Used for contributing original imaging data that has not been previously hosted on TCIA.")
else:
    st.info("💡 **Analysis Results Proposal**: Used for contributing derived data like annotations, segmentations, or radiomics features based on existing TCIA datasets.")

st.markdown("---")

# Form Questions
with st.form("proposal_form"):
    st.subheader("Contact Information")
    if SMTP_SERVER and SMTP_USER and SMTP_PASSWORD:
        st.info("💡 **Note**: After completing this form, a copy of this proposal will be emailed to the Scientific, Technical, and Legal points of contact listed below.")

    col1, col2 = st.columns(2)
    with col1:
        sci_poc_name = st.text_input(LABELS["Scientific POC Name"], help="The person to contact about the proposal and data collection.")
        tech_poc_name = st.text_input(LABELS["Technical POC Name"], help="The person involved in sending the data.")
        legal_poc_name = st.text_input(LABELS["Legal POC Name"], help="Authorized signatory who will sign the TCIA Data Submission Agreement. This should not be the PI or department chair.")
    with col2:
        sci_poc_email = st.text_input(LABELS["Scientific POC Email"])
        tech_poc_email = st.text_input(LABELS["Technical POC Email"])
        legal_poc_email = st.text_input(LABELS["Legal POC Email"])

    st.subheader("Dataset Publication Details")
    title = st.text_input(LABELS["Title"], help="Similar to a manuscript title.")
    nickname = st.text_input(LABELS["Nickname"], help="Must be < 30 characters, letters, numbers, and dashes only.", max_chars=30)
    authors = st.text_area(LABELS["Authors"], help="Format: (FAMILY, GIVEN). Please include OrcIDs (e.g. 0000-0000-0000-0000).")
    abstract = st.text_area(LABELS["Abstract"], help="Focus on describing the dataset itself.", max_chars=1000)

    st.subheader("Data Collection Details")
    published_elsewhere = st.text_input(LABELS["Published Elsewhere"], help="If so, why publish on TCIA? Do you intend for the original to remain accessible?")

    # Adaptive fields
    extra_data = {}
    if proposal_type == "New Collection Proposal":
        col1, col2 = st.columns(2)
        with col1:
            site_raw = permissible_values.get('primary_site', []) if permissible_values else []
            site_options = sorted(list(set([v['value'] if isinstance(v, dict) else str(v) for v in site_raw])))
            extra_data['disease_site'] = st.selectbox(LABELS["disease_site"], options=[""] + site_options)
        with col2:
            diag_raw = permissible_values.get('primary_diagnosis', []) if permissible_values else []
            diag_options = sorted(list(set([v['value'] if isinstance(v, dict) else str(v) for v in diag_raw])))
            extra_data['diagnosis'] = st.selectbox(LABELS["diagnosis"], options=[""] + diag_options)

        extra_data['image_types'] = st.multiselect(
            LABELS["image_types"],
            options=["MR", "CT", "PET", "PET-CT", "PET-MR", "Mammograms", "Ultrasound", "Xray", "Radiation Therapy", "Whole Slide Image", "CODEX", "Single-cell Image", "Photomicrograph", "Microarray", "Multiphoton", "Immunofluorescence", "Other"]
        )
        extra_data['supporting_data'] = st.multiselect(
            LABELS["supporting_data"],
            options=["Clinical", "Image Analyses", "Image Registrations", "Genomics", "Proteomics", "Software / Source Code", "No additional data", "Other"]
        )
        extra_data['file_formats'] = st.text_area(LABELS["file_formats"])
        extra_data['num_subjects'] = st.number_input(LABELS["num_subjects_new"], min_value=0)
        extra_data['modifications'] = st.text_area(LABELS["modifications"])
        extra_data['faces'] = st.radio(LABELS["faces"], options=["Yes", "No"])
        extra_data['exceptions'] = st.text_input(LABELS["exceptions"], value="No exceptions requested")
    else: # Analysis Results
        extra_data['collections_analyzed'] = st.text_input(LABELS["collections_analyzed"])
        extra_data['derived_types'] = st.multiselect(
            LABELS["derived_types"],
            options=["Segmentation", "Classification", "Quantitative Feature", "Image (converted/processed/registered)", "Other"]
        )
        extra_data['num_subjects'] = st.number_input(LABELS["num_subjects_analysis"], min_value=0)
        extra_data['image_records'] = st.radio(LABELS["image_records"], options=["Yes, I know exactly.", "No, I need assistance."])
        extra_data['file_formats'] = st.text_area(LABELS["file_formats"])
    # Shared bottom fields
    col1, col2 = st.columns(2)
    with col1:
        extra_data['disk_space'] = st.text_input(LABELS["disk_space"])
    with col2:
        time_constraints = st.text_input(LABELS["Time Constraints"])

    extra_data['descriptor_publication'] = st.text_area(LABELS["descriptor_publication"])
    extra_data['additional_publications'] = st.text_area(LABELS["additional_publications"])
    extra_data['acknowledgments'] = st.text_area(LABELS["acknowledgments"])
    extra_data['why_tcia'] = st.multiselect(
        LABELS["why_tcia"],
        options=["To meet a funding agency's requirements", "To meet a journal's requirements", "To facilitate collaboration", "To facilitate a challenge competition", "Other"]
    )

    button_label = "Submit" if (SMTP_SERVER and SMTP_USER and SMTP_PASSWORD) else "Generate Proposal Documents"
    submit_button = st.form_submit_button(button_label)

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
    if not authors: missing_fields.append(LABELS["Authors"])
    if not abstract: missing_fields.append(LABELS["Abstract"])
    if not published_elsewhere: missing_fields.append(LABELS["Published Elsewhere"])

    for key, val in extra_data.items():
        if not val:
            # Special case for num_subjects
            if key == "num_subjects":
                label = LABELS["num_subjects_new"] if proposal_type == "New Collection Proposal" else LABELS["num_subjects_analysis"]
            else:
                label = LABELS.get(key, key.replace('_', ' ').title())
            missing_fields.append(label)

    if not time_constraints: missing_fields.append(LABELS["Time Constraints"])

    if missing_fields:
        st.error("Please fill in all required fields:")
        for field in missing_fields:
            st.write(f"- {field}")
    else:
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
            "Authors": authors,
            "Abstract": abstract,
            "Published Elsewhere": published_elsewhere
        }
        all_responses.update(extra_data)

        # Generate TSV
        tsv_buffer = io.StringIO()
        df = pd.DataFrame([all_responses])
        df.to_csv(tsv_buffer, sep='\t', index=False)

        # Generate DOCX
        doc = Document()
        doc.add_heading(f"TCIA Dataset Proposal: {title}", 0)
        for key, value in all_responses.items():
            label = LABELS.get(key, key)
            if key == "num_subjects":
                label = LABELS["num_subjects_new"] if proposal_type == "New Collection Proposal" else LABELS["num_subjects_analysis"]

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
