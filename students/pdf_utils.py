def _escape_pdf_text(value):
    text = str(value)
    return text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def build_simple_pdf(lines, title=None):
    all_lines = []
    if title:
        all_lines.append(title)
        all_lines.append('')
    all_lines.extend(lines)

    if not all_lines:
        all_lines = ['']

    page_height = 842
    top_margin = 800
    line_height = 14
    lines_per_page = 48

    objects = [None]

    def add_object(payload):
        objects.append(payload)
        return len(objects) - 1

    font_id = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")
    pages_id = add_object(b"")
    page_ids = []

    for start in range(0, len(all_lines), lines_per_page):
        page_lines = all_lines[start:start + lines_per_page]
        stream_lines = ["BT", "/F1 11 Tf"]
        y = top_margin
        for line in page_lines:
            stream_lines.append(f"1 0 0 1 40 {y} Tm")
            stream_lines.append(f"({_escape_pdf_text(line)}) Tj")
            y -= line_height

        if y < 80:
            y = 80

        stream_lines.append("ET")
        stream = "\n".join(stream_lines).encode('latin-1', 'replace')
        content_id = add_object(
            f"<< /Length {len(stream)} >>\nstream\n".encode('latin-1')
            + stream
            + b"\nendstream"
        )
        page_id = add_object(
            (
                f"<< /Type /Page /Parent {pages_id} 0 R "
                f"/MediaBox [0 0 595 {page_height}] "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            ).encode('latin-1')
        )
        page_ids.append(page_id)

    kids = ' '.join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_id] = f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>".encode('latin-1')
    catalog_id = add_object(f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode('latin-1'))

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * len(objects)

    for object_id in range(1, len(objects)):
        offsets[object_id] = len(pdf)
        pdf.extend(f"{object_id} 0 obj\n".encode('latin-1'))
        pdf.extend(objects[object_id])
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects)}\n".encode('latin-1'))
    pdf.extend(b"0000000000 65535 f \n")
    for object_id in range(1, len(objects)):
        pdf.extend(f"{offsets[object_id]:010d} 00000 n \n".encode('latin-1'))

    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects)} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        ).encode('latin-1')
    )
    return bytes(pdf)
