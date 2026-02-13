import streamlit as st
import pandas as pd
import os
import io
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

st.set_page_config(page_title="TCIA Dataset Proposal Form", layout="wide")

# Constants & Configuration
RESOURCES_DIR = os.path.join(os.path.dirname(__file__), 'tcia-remapping-skill', 'resources')
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
    email = st.text_input("Email Address*", help="A copy of your responses will be emailed to this address.")
    sci_poc = st.text_input("Scientific Point of Contact*", help="Name, email, and phone number for the person to contact about the proposal and data collection.")
    tech_poc = st.text_input("Technical Point of Contact*", help="Name, email, and phone number for the person involved in sending the data.")
    legal_poc = st.text_input("Legal/Contracts Administrator*", help="Name and email of an authorized signatory who will sign the TCIA Data Submission Agreement. This should not be the PI or department chair.")

    st.subheader("Dataset Publication Details")
    title = st.text_input("Suggest a descriptive title for your dataset*", help="Similar to a manuscript title.")
    nickname = st.text_input("Suggest a shorter nickname for your dataset*", help="Must be < 30 characters, letters, numbers, and dashes only.")
    authors = st.text_area("List the authors of this data set*", help="Format: (FAMILY, GIVEN). Please include OrcIDs (e.g. 0000-0000-0000-0000).")
    abstract = st.text_area("Dataset Abstract*", help="Focus on describing the dataset itself.")

    st.subheader("Data Collection Details")
    published_elsewhere = st.text_area("Has this data ever been published elsewhere?*", help="If so, why publish on TCIA? Do you intend for the original to remain accessible?")

    # Adaptive fields
    extra_data = {}
    if proposal_type == "New Collection Proposal":
        extra_data['disease_site'] = st.text_input("Primary disease site/location*")
        extra_data['diagnosis'] = st.text_input("Histologic diagnosis*")
        extra_data['image_types'] = st.multiselect(
            "Which image types are included in the data set?*",
            options=["MR", "CT", "PET", "PET-CT", "PET-MR", "Mammograms", "Ultrasound", "Xray", "Radiation Therapy", "Whole Slide Image", "CODEX", "Single-cell Image", "Photomicrograph", "Microarray", "Multiphoton", "Immunofluorescence", "Other"]
        )
        extra_data['supporting_data'] = st.multiselect(
            "Which kinds of supporting data are included in the data set?*",
            options=["Clinical", "Image Analyses", "Image Registrations", "Genomics", "Proteomics", "Software / Source Code", "No additional data", "Other"]
        )
        extra_data['file_formats'] = st.text_area("Specify the file format utilized for each type of data*")
        extra_data['num_subjects'] = st.number_input("How many subjects are in your data set?*", min_value=0)
        extra_data['num_studies'] = st.text_input("How many total radiology studies or pathology slides?*")
        extra_data['modifications'] = st.text_area("Describe any steps taken to modify data prior to submission*")
        extra_data['faces'] = st.radio("Does your data contain any images of patient faces?*", options=["Yes", "No"])
        extra_data['exceptions'] = st.text_input("Do you need to request any exceptions to TCIA's Open Access Policy?", value="No exceptions requested")
        extra_data['citations_content'] = st.text_area("Publications specifically about the contents of the dataset")

    else: # Analysis Results
        extra_data['collections_analyzed'] = st.text_input("Which TCIA collection(s) did you analyze?*")
        extra_data['derived_types'] = st.multiselect(
            "What types of derived data are included in the dataset?*",
            options=["Segmentation", "Classification", "Quantitative Feature", "Image (converted/processed/registered)", "Other"]
        )
        extra_data['num_subjects'] = st.number_input("How many patients are included in your dataset?*", min_value=0)
        extra_data['series_slides'] = st.text_input("Number of DICOM series or digitized pathology slides")
        extra_data['image_records'] = st.radio("Do you have records to indicate exactly which TCIA images analyzed?*", options=["Yes, I know exactly.", "No, I need assistance."])
        extra_data['file_formats'] = st.text_area("Specify the file format utilized for each type of data*")
        extra_data['citation_primary'] = st.text_area("Publication people should cite when utilizing this data")

    # Shared bottom fields
    extra_data['disk_space'] = st.text_input("Approximate disk space required*")
    extra_data['additional_publications'] = st.text_area("Any additional publications derived from these data?")
    extra_data['acknowledgments'] = st.text_area("Acknowledgments or funding statements*")
    extra_data['why_tcia'] = st.multiselect(
        "Why would you like to publish this dataset on TCIA?*",
        options=["To meet a funding agency's requirements", "To meet a journal's requirements", "To facilitate collaboration", "To facilitate a challenge competition", "Other"]
    )
    time_constraints = st.text_input("Are there any time constraints associated with sharing your data set?*")

    submit_button = st.form_submit_button("Generate Proposal Documents")

# Processing after submission
if submit_button:
    # 1. Validation (simplified)
    if not email or not title or not abstract:
        st.error("Please fill in all required fields marked with *")
    else:
        # Prepare data for files
        all_responses = {
            "Proposal Type": proposal_type,
            "Email": email,
            "Scientific POC": sci_poc,
            "Technical POC": tech_poc,
            "Legal POC": legal_poc,
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
            doc.add_paragraph(f"{key}:", style='Heading 2')
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

        # Store in session state for later use in email
        st.session_state['proposal_files'] = {
            'tsv': tsv_buffer.getvalue(),
            'docx': docx_buffer.getvalue(),
            'pdf': pdf_buffer.getvalue() if pdf_success else None,
            'zip': zip_buffer.getvalue(),
            'title': title
        }

        st.success("✅ Proposal documents generated successfully!")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button("Download TSV (Import to Remapper)", data=tsv_buffer.getvalue(), file_name="proposal.tsv", mime="text/tab-separated-values")
        with col2:
            st.download_button("Download DOCX Summary", data=docx_buffer.getvalue(), file_name="proposal.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        with col3:
            if pdf_success:
                st.download_button("Download PDF Agreement", data=pdf_buffer.getvalue(), file_name="agreement_updated.pdf", mime="application/pdf")

        st.markdown("---")
        st.subheader("Email Proposal")

        # Determine if we can send automatically
        can_send_auto = all([SMTP_SERVER, SMTP_USER, SMTP_PASSWORD])

        if not can_send_auto:
            st.info(f"💡 **Manual Submission**: Please download the generated files above and email them as attachments to **{HELP_DESK_EMAIL}**. Alternatively, provide SMTP credentials in the environment to send automatically.")
        else:
            if st.button("📧 Send Proposal to TCIA Help Desk"):
                files = st.session_state.get('proposal_files')
                if files:
                    try:
                        msg = MIMEMultipart()
                        msg['From'] = SMTP_USER
                        msg['To'] = HELP_DESK_EMAIL
                        msg['Subject'] = f"New Dataset Proposal: {files['title']}"

                        body = f"A new dataset proposal has been submitted via the Dataset Proposal Form.\n\nType: {proposal_type}\nTitle: {files['title']}\nSubmitter: {email}"
                        msg.attach(MIMEText(body, 'plain'))

                        part = MIMEBase('application', 'zip')
                        part.set_payload(files['zip'])
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', 'attachment; filename="proposal_package.zip"')
                        msg.attach(part)

                        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
                        server.starttls()
                        server.login(SMTP_USER, SMTP_PASSWORD)
                        server.send_message(msg)
                        server.quit()
                        st.success(f"📨 Proposal sent to {HELP_DESK_EMAIL}!")
                    except Exception as e:
                        st.error(f"Failed to send email: {e}")
                else:
                    st.warning("Please generate proposal documents first.")

# Footer
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
TCIA Dataset Proposal Form | {HELP_DESK_EMAIL}
</div>
""", unsafe_allow_html=True)
