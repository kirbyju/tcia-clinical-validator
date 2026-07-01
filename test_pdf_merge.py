import io
import os
import PyPDF2
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

RESOURCES_DIR = 'tcia-remapping-skill/resources'
AGREEMENT_TEMPLATE = os.path.join(RESOURCES_DIR, 'agreement_template.pdf')

def test_merge():
    report_data = [
        ("Scientific POC Name*", "John Doe"),
        ("Scientific POC Email*", "john@example.com"),
        ("Dataset Abstract*", "This is a very long abstract. " * 500), # Very long to force multiple pages
        ("Manuscripts/Preprints", "- [Dataset Descriptor] https://doi.org/10.1101/...\n- [Regular manuscript] manuscript.pdf")
    ]

    # Prepare Exhibit A pages using Platypus
    exhibit_a_buffer = io.BytesIO()

    class ExhibitCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            canvas.Canvas.__init__(self, *args, **kwargs)
            self.pages = []

        def showPage(self):
            self.pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            page_count = len(self.pages)
            for count, page in enumerate(self.pages):
                self.__dict__.update(page)
                self.draw_canvas(count+1, page_count)
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)

        def draw_canvas(self, page_num, total_pages):
            width, height = letter
            display_page = page_num + 5
            total_display = total_pages + 6

            self.saveState()
            self.setFont("Helvetica", 10)
            header_text = f"TCIA Data Submission Agreement (v. 20220 914) Page {display_page} of {total_display}"
            self.drawString(50, height - 50, header_text)
            self.restoreState()

    doc_exhibit = SimpleDocTemplate(
        exhibit_a_buffer,
        pagesize=letter,
        rightMargin=50, leftMargin=50,
        topMargin=70, bottomMargin=50
    )

    styles = getSampleStyleSheet()
    style_center = ParagraphStyle(
        name='Center',
        parent=styles['Normal'],
        alignment=TA_CENTER
    )
    style_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        wordWrap='LTR'
    )

    elements = []
    elements.append(Paragraph("<br/><br/><br/><b><font size=14>EXHIBIT A</font></b>", style_center))
    elements.append(Paragraph("<b><font size=14>DESCRIPTION OF SUBMISSION DATA</font></b>", style_center))
    elements.append(Spacer(1, 20))

    table_data = []
    for label, val in report_data:
        safe_val = val.replace('\n', '<br/>')
        table_data.append([
            Paragraph(f"<b>{label}</b>", style_cell),
            Paragraph(safe_val, style_cell)
        ])

    t = Table(table_data, colWidths=[150, 350])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t)

    doc_exhibit.build(elements, canvasmaker=ExhibitCanvas)
    exhibit_a_buffer.seek(0)

    # Merge with template
    reader = PyPDF2.PdfReader(AGREEMENT_TEMPLATE)
    writer = PyPDF2.PdfWriter()

    for i in range(5):
        writer.add_page(reader.pages[i])

    new_exhibit_reader = PyPDF2.PdfReader(exhibit_a_buffer)
    for page in new_exhibit_reader.pages:
        writer.add_page(page)

    last_page = reader.pages[6]
    total_exhibit_pages = len(new_exhibit_reader.pages)
    total_final_pages = total_exhibit_pages + 6

    overlay_buffer = io.BytesIO()
    c_overlay = canvas.Canvas(overlay_buffer, pagesize=letter)
    c_overlay.setFont("Helvetica", 10)
    c_overlay.setFillColor(colors.white)
    c_overlay.rect(40, letter[1] - 60, 500, 20, fill=1, stroke=0)
    c_overlay.setFillColor(colors.black)
    header_text = f"TCIA Data Submission Agreement (v. 20220 914) Page {total_final_pages} of {total_final_pages}"
    c_overlay.drawString(50, letter[1] - 50, header_text)
    c_overlay.showPage()
    c_overlay.save()
    overlay_buffer.seek(0)

    overlay_reader = PyPDF2.PdfReader(overlay_buffer)
    last_page.merge_page(overlay_reader.pages[0])
    writer.add_page(last_page)

    with open("test_final_agreement.pdf", "wb") as f:
        writer.write(f)

    print(f"Final agreement generated with {len(writer.pages)} pages.")

if __name__ == "__main__":
    test_merge()
