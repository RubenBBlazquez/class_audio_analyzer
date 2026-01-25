import os
from weasyprint import HTML
from app.services.file_management import get_html_content, get_transcriptions_dir

def html_to_pdf(html_content, output_filename, base_url=None):
    """Converts HTML content to PDF using WeasyPrint for full style support."""
    try:
        output_path = os.path.join("/tmp", output_filename)
        # Convert HTML to PDF with base_url to resolve relative links (images, css)
        HTML(string=html_content, base_url=base_url).write_pdf(output_path)
        return output_path
    except Exception as e:
        print(f"PDF Generation Error: {e}")
        return None

def download_resume_as_pdf(subject, filename):
    """Generates a PDF from the selected HTML resume and returns the file path."""
    html_content = get_html_content(subject, filename)
    if not html_content or html_content.startswith("Error") or html_content == "File not found.":
        return None

    # Determine base directory for resolving relative paths in HTML
    transcriptions_dir = get_transcriptions_dir()
    base_url = os.path.join(transcriptions_dir, subject)

    # Flatten filename to avoid directory creation issues in /tmp
    flat_name = os.path.basename(filename)
    pdf_filename = flat_name.replace(".html", ".pdf")
    return html_to_pdf(html_content, pdf_filename, base_url=base_url)
