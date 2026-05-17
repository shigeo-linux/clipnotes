def save_as_pdf(text, output_path, source_filename=''):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.enums import TA_LEFT
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib import colors
    except ImportError:
        raise RuntimeError("reportlab not installed.\nRun: pip3 install reportlab")

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=1.2*inch, rightMargin=1.2*inch,
        topMargin=1.1*inch, bottomMargin=1.1*inch,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'STitle', parent=styles['Heading1'],
        fontSize=16, spaceAfter=10, textColor=colors.HexColor('#2a2218'),
    )
    source_style = ParagraphStyle(
        'SSource', parent=styles['Normal'],
        fontSize=9, spaceAfter=16, textColor=colors.HexColor('#7a7060'),
    )
    body_style = ParagraphStyle(
        'SBody', parent=styles['Normal'],
        fontSize=11, leading=17, spaceAfter=6,
        textColor=colors.HexColor('#1a1a1a'),
    )
    bullet_style = ParagraphStyle(
        'SBullet', parent=body_style,
        leftIndent=16, bulletIndent=0, spaceAfter=5,
    )

    def esc(t):
        return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    story = []

    if source_filename:
        story.append(Paragraph(esc(f'Summary of: {source_filename}'), source_style))

    lines = text.split('\n')
    for line in lines:
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 6))
            continue

        # Bold title line (starts with **)
        if stripped.startswith('**') and stripped.endswith('**'):
            content = stripped.strip('*').strip()
            story.append(Paragraph(f'<b>{esc(content)}</b>', title_style))
        # Source/channel metadata lines
        elif stripped.startswith('Source:') or stripped.startswith('Channel:'):
            story.append(Paragraph(esc(stripped), source_style))
        # Bullet point
        elif stripped.startswith('•') or stripped.startswith('-'):
            content = stripped.lstrip('•- ').strip()
            story.append(Paragraph(f'• {esc(content)}', bullet_style))
        else:
            story.append(Paragraph(esc(stripped), body_style))

    doc.build(story)
