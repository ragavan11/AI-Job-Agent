"""PDF export via reportlab — pure Python, no system-level dependencies
(unlike e.g. weasyprint, which needs Pango/Cairo), which keeps the Docker
image simple."""
from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

from app.models import Profile, Resume

_styles = getSampleStyleSheet()

_NAME = ParagraphStyle("Name", parent=_styles["Title"], fontSize=20, spaceAfter=2, textColor=colors.HexColor("#14181F"))
_CONTACT = ParagraphStyle("Contact", parent=_styles["Normal"], fontSize=9.5, textColor=colors.HexColor("#5B6472"), spaceAfter=10)
_SECTION = ParagraphStyle("Section", parent=_styles["Heading2"], fontSize=11.5, spaceBefore=12, spaceAfter=4, textColor=colors.HexColor("#1F6F78"))
_BODY = ParagraphStyle("Body", parent=_styles["Normal"], fontSize=10, leading=14)
_BULLET = ParagraphStyle("Bullet", parent=_BODY, leftIndent=14, bulletIndent=4, spaceAfter=2)
_ROLE = ParagraphStyle("Role", parent=_styles["Normal"], fontSize=10.5, spaceBefore=6, textColor=colors.HexColor("#14181F"))
_ROLE_META = ParagraphStyle("RoleMeta", parent=_styles["Normal"], fontSize=9, textColor=colors.HexColor("#5B6472"))


def resume_to_pdf(profile: Profile, resume: Resume) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=LETTER,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch, leftMargin=0.7 * inch, rightMargin=0.7 * inch,
    )
    story = []

    story.append(Paragraph(profile.full_name, _NAME))
    contact_bits = [b for b in [profile.email, profile.phone, profile.linkedin_url, profile.github_url, profile.portfolio_url] if b]
    story.append(Paragraph(" &nbsp;|&nbsp; ".join(contact_bits), _CONTACT))
    story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#D9DDE3")))

    if resume.summary:
        story.append(Paragraph("SUMMARY", _SECTION))
        story.append(Paragraph(resume.summary, _BODY))

    if resume.skills:
        story.append(Paragraph("SKILLS", _SECTION))
        story.append(Paragraph(" &nbsp;•&nbsp; ".join(resume.skills), _BODY))

    if resume.work_history:
        story.append(Paragraph("EXPERIENCE", _SECTION))
        for job in resume.work_history:
            story.append(Paragraph(f"<b>{job.get('title', '')}</b> — {job.get('company', '')}", _ROLE))
            story.append(Paragraph(f"{job.get('start', '')} – {job.get('end', 'Present')}", _ROLE_META))
            for bullet in job.get("bullets", []):
                story.append(Paragraph(f"• {bullet}", _BULLET))

    if resume.projects:
        story.append(Paragraph("PROJECTS", _SECTION))
        for proj in resume.projects:
            tech = ", ".join(proj.get("tech", []))
            story.append(Paragraph(f"<b>{proj.get('name', '')}</b>" + (f" ({tech})" if tech else ""), _ROLE))
            story.append(Paragraph(proj.get("description", ""), _BODY))

    if resume.education:
        story.append(Paragraph("EDUCATION", _SECTION))
        for edu in resume.education:
            story.append(Paragraph(f"{edu.get('degree', '')} — {edu.get('school', '')} ({edu.get('year', '')})", _BODY))

    doc.build(story)
    return buffer.getvalue()


def cover_letter_to_pdf(profile: Profile, company: str, content: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=LETTER,
        topMargin=0.8 * inch, bottomMargin=0.8 * inch, leftMargin=0.9 * inch, rightMargin=0.9 * inch,
    )
    story = [
        Paragraph(profile.full_name, _NAME),
        Paragraph(" &nbsp;|&nbsp; ".join(b for b in [profile.email, profile.phone] if b), _CONTACT),
        Spacer(1, 12),
    ]
    for para in content.split("\n\n"):
        if para.strip():
            story.append(Paragraph(para.strip().replace("\n", " "), _BODY))
            story.append(Spacer(1, 10))

    doc.build(story)
    return buffer.getvalue()
