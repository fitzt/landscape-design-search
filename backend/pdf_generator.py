from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from pathlib import Path
import os
from datetime import datetime
from backend.config import BASE_DIR, THUMBNAILS_DIR, DEFAULT_PHOTO_FOLDER

OUTPUT_DIR = BASE_DIR / "generated_reports"
OUTPUT_DIR.mkdir(exist_ok=True)

LOGO_PATH = BASE_DIR / "backend/static/logo.jpg"

class PDFGenerator:
    def __init__(self):
        self.width, self.height = letter

    def generate_report(self, lead_data, selected_images):
        """
        lead_data: dict with name, timeline, budget, etc.
        selected_images: list of dicts with file_path, etc.
        """
        filename = f"Project_Vision_{lead_data['name'].replace(' ', '_')}_{int(datetime.now().timestamp())}.pdf"
        output_path = OUTPUT_DIR / filename
        
        doc = SimpleDocTemplate(str(output_path), pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # 1. Header with Logo
        if os.path.exists(LOGO_PATH):
            # Aspect ratio check if needed, but for now just fix width
            img = Image(str(LOGO_PATH), width=150, height=150)
            img.hAlign = 'LEFT'
            story.append(img)
        else:
            story.append(Paragraph("Lynch Landscape & Tree Service", styles['Title']))
            
        story.append(Spacer(1, 12))
        
        # 2. Title
        title_style = ParagraphStyle('MainTitle', parent=styles['Heading1'], fontSize=24, spaceAfter=20, textColor=colors.darkblue)
        story.append(Paragraph("Your Project Vision", title_style))
        story.append(Spacer(1, 12))

        # 3. Client Details
        story.append(Paragraph("<b>Client Profile</b>", styles['Heading2']))
        details = [
            ["Name:", lead_data.get('name')],
            ["Email:", lead_data.get('email')],
            ["Phone:", lead_data.get('phone', 'N/A')],
            ["Address:", lead_data.get('address', 'N/A')],
            ["Timeline:", lead_data.get('timeline', 'N/A')],
            ["Budget Goal:", lead_data.get('budget', 'N/A')],
        ]
        
        # Styling the table
        tbl = Table(details, colWidths=[100, 300])
        tbl.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        tbl.hAlign = 'LEFT'
        story.append(tbl)
        story.append(Spacer(1, 24))

        # 4. Interaction / Consultation Pitch
        pitch = """
        Thank you for sharing your vision with us. Based on your selections, we have a clear idea 
        of the style and scope you are looking for. 
        <br/><br/>
        One of our expert landscape architects will be reviewing this document and will reach out 
        shortly to discuss how we can bring this vision to life at your property.
        """
        story.append(Paragraph(pitch, styles['BodyText']))
        story.append(Spacer(1, 20))

        # 4.5 Vision Context Map
        if lead_data.get('vision_report'):
            story.append(Paragraph("<b>Vision Analysis (AI Context Map)</b>", styles['Heading2']))
            story.append(Spacer(1, 6))
            
            vr = lead_data['vision_report']
            # Create a nice layout for the 3 traits
            # Maybe a small table or bullet points
            
            # Formatted string
            analysis_text = f"""
            <b>Dominant Style:</b> {vr.get('Style', 'N/A')}<br/>
            <b>Key Material:</b> {vr.get('Material', 'N/A')}<br/>
            <b>Atmosphere:</b> {vr.get('Atmosphere', 'N/A')}
            """
            
            # Boxed style? Or just text.
            story.append(Paragraph(analysis_text, styles['BodyText']))
            story.append(Spacer(1, 20))

        # 5. Selected Images
        story.append(Paragraph("<b>Inspiration Board</b>", styles['Heading2']))
        story.append(Spacer(1, 10))

        # Grid of images (2 per row)
        img_data = []
        row = []
        
        for img_meta in selected_images:
            # Try to use thumbnail logic or full path
            # We need absolute path on disk
            # In DB we store file_path (full path)
            # But let's verify it exists
            
            p = img_meta.get('file_path')
            # If we don't have file_path, maybe we have ID and can look it up?
            # Assuming passed list has 'file_path'
            
            if p and os.path.exists(p):
                # Resize for PDF - maintain aspect a bit?
                # reportlab Image can take width/height
                # 3 inches ~ 216 pts
                im = Image(p, width=220, height=140) 
                # Keep ratio? Image(path, width, height) squezzes. 
                # Better to use preserveAspectRatio=True? Reportlab 4 might do it differently
                # For simplicity, fixed box
                row.append(im)
            
            if len(row) == 2:
                img_data.append(row)
                row = []
        
        if row:
            img_data.append(row)
            
        if img_data:
            img_tbl = Table(img_data, colWidths=[240, 240])
            img_tbl.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (-1,-1), 5),
                ('RIGHTPADDING', (0,0), (-1,-1), 5),
                ('TOPPADDING', (0,0), (-1,-1), 5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 15),
            ]))
            story.append(img_tbl)
        else:
             story.append(Paragraph("(No valid images selected)", styles['BodyText']))

        # 6. Footer
        story.append(Spacer(1, 40))
        footer_text = """
        <b>Lynch Landscape & Tree Service</b><br/>
        80 Union Ave., Sudbury, MA<br/>
        (978) 443-2626 | www.lynchlandscape.com
        """
        story.append(Paragraph(footer_text, styles['Normal']))

        doc.build(story)
        return str(output_path)
