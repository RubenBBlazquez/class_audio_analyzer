import base64
from app.services.file_management import get_html_content

def display_resume_content(subject, filename):
    if filename:
        content = get_html_content(subject, filename)
        if not content or content.startswith("Error") or content == "File not found.":
             return f"<div style='color:red'>{content}</div>"

        # Use Data URI iframe to isolate CSS and script execution
        b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        data_uri = f"data:text/html;charset=utf-8;base64,{b64}"
        return f'<iframe src="{data_uri}" style="width:100%; height:100%; min-height:600px; border:none;"></iframe>'
    return ""
