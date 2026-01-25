import gradio as gr
from app.services.file_management import get_subjects, get_html_files
from app.services.pdf_generation import download_resume_as_pdf
from app.interface.components.utils import display_resume_content

def update_subjects():
    return gr.Dropdown(choices=get_subjects())

def update_html_file_dropdown(subject):
    return gr.Dropdown(choices=get_html_files(subject))


def download_pdf_handler(subject, filename):
    if filename:
        pdf_path = download_resume_as_pdf(subject, filename)
        if pdf_path:
            return pdf_path
    return None

def create_resume_viewer_component():
    with gr.Tab("Resume Viewer"):
        with gr.Row():
            subject_dropdown = gr.Dropdown(label="Select Subject", choices=get_subjects(), interactive=True)
            refresh_subjects_btn = gr.Button("Refresh Folders", size="sm")

        with gr.Row():
            html_file_dropdown = gr.Dropdown(label="Select HTML File", choices=[], interactive=True, scale=3)
            view_fullscreen_btn = gr.Button("View Fullscreen", variant="secondary", scale=1, elem_classes="center-btn")

        with gr.Row(equal_height=True):
            download_pdf_btn = gr.Button("Generate & Download PDF", variant="primary", scale=1, elem_classes="pdf-gen-btn")
            pdf_output = gr.File(label="PDF Download", scale=3, elem_classes="pdf-output-file")

        resume_content = gr.HTML(elem_classes="resume-content", label="HTML Preview")

    return (subject_dropdown, refresh_subjects_btn, html_file_dropdown,
            view_fullscreen_btn, download_pdf_btn, pdf_output, resume_content)

def setup_resume_viewer_events(subject_dropdown, refresh_subjects_btn, html_file_dropdown, download_pdf_btn, pdf_output, resume_content):
    refresh_subjects_btn.click(fn=update_subjects, outputs=subject_dropdown)

    subject_dropdown.change(
        fn=update_html_file_dropdown,
        inputs=[subject_dropdown],
        outputs=[html_file_dropdown]
    )

    html_file_dropdown.change(
        fn=display_resume_content,
        inputs=[subject_dropdown, html_file_dropdown],
        outputs=[resume_content]
    )

    download_pdf_btn.click(
        fn=download_pdf_handler,
        inputs=[subject_dropdown, html_file_dropdown],
        outputs=[pdf_output]
    )
