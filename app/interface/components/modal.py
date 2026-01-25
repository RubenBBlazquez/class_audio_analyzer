import gradio as gr
from app.interface.components.utils import display_resume_content
from app.services.pdf_generation import download_resume_as_pdf

def create_modal_component():
    with gr.Column(
            visible=False,
            elem_classes=["modal-visible"],
            elem_id="resume-modal",
    ) as resume_modal:
        with gr.Column(elem_classes="modal-content-box"):
            with gr.Row():
                modal_close_btn = gr.Button(
                    "Close Preview",
                    variant="stop",
                    size="sm",
                )
                modal_download_btn = gr.Button("Download PDF", variant="primary", size="sm")

            with gr.Group(elem_classes="modal-html-scroll"):
                modal_resume_content = gr.HTML()

            modal_pdf_output = gr.File(label="PDF Download (Modal)", visible=False)

    return resume_modal, modal_close_btn, modal_download_btn, modal_resume_content, modal_pdf_output

def open_modal(subject, filename):
    content = display_resume_content(subject, filename)
    return gr.update(visible=True), content, gr.update(visible=False)

def close_modal():
    return gr.update(visible=False)

def modal_download(subject, filename):
    if filename:
        pdf_path = download_resume_as_pdf(subject, filename)
        if pdf_path:
            return gr.File(value=pdf_path, visible=True)
    return gr.File(visible=False)

def setup_modal_events(view_btn, subject_dd, file_dd, resume_modal, modal_content, modal_pdf, close_btn, download_btn):
    view_btn.click(
        fn=open_modal,
        inputs=[subject_dd, file_dd],
        outputs=[resume_modal, modal_content, modal_pdf]
    )

    close_btn.click(
        fn=close_modal,
        outputs=[resume_modal]
    )

    download_btn.click(
        fn=modal_download,
        inputs=[subject_dd, file_dd],
        outputs=[modal_pdf]
    )
