import gradio as gr
from app.interface.styles import CSS
from app.interface.components.history import create_history_component, setup_history_events
from app.interface.components.inputs import create_input_components
from app.interface.components.results import create_results_component
from app.interface.components.resume_viewer import create_resume_viewer_component, setup_resume_viewer_events
from app.interface.components.modal import create_modal_component, setup_modal_events
from app.services.workflow import transcribe_workflow, summarize_workflow

def unified_workflow(current_tab, audio_path, text_path, subject, theme, objective, do_summarize, context_files, summarizer_type):
    # Dispatch based on active tab
    if current_tab == "audio":
        if audio_path:
            yield from transcribe_workflow(audio_path, subject, theme, objective, do_summarize, context_files, summarizer_type)
        else:
            yield "Error: No audio file provided (Check Audio Source tab).", ""

    if current_tab == "text":
        if text_path:
            yield from summarize_workflow(text_path, theme, objective, context_files, summarizer_type)
        else:
             yield "Error: No text file provided (Check Text Source tab).", ""

        return

    yield f"Error: Unknown tab state '{current_tab}'.", ""

def create_interface():
    with gr.Blocks(title="Class Audio Analyzer", css=CSS) as app:
        gr.Markdown("# Class Audio Analyzer & Summarizer")

        # History Section
        history_dropdown, refresh_history_btn = create_history_component()

        with gr.Row():
            # Left Column: Inputs
            with gr.Column():
                (active_tab, audio_input, subject_input, text_file_input,
                 theme_input, objective_input, context_files_input,
                 summarizer_selector, auto_summarize, action_btn, stop_btn) = create_input_components()

            # Right Column: Results & Resume Viewer
            with gr.Column():
                log_output, summary_output = create_results_component()
                (subject_dd, refresh_sub_btn, html_dd,
                 view_full_btn, dl_pdf_btn, pdf_out, resume_content) = create_resume_viewer_component()

        # Modal (Root level)
        (resume_modal, modal_close_btn, modal_download_btn,
         modal_resume_content, modal_pdf_output) = create_modal_component()

        # Init modal state
        app.load(lambda: gr.update(visible=False), outputs=resume_modal)

        # Event Wiring

        # History
        setup_history_events(app, history_dropdown, refresh_history_btn,
                             [subject_input, theme_input, objective_input, summary_output])

        # Workflow
        process_event = action_btn.click(
            fn=unified_workflow,
            inputs=[active_tab, audio_input, text_file_input, subject_input, theme_input, objective_input, auto_summarize,
                    context_files_input, summarizer_selector],
            outputs=[log_output, summary_output]
        )
        stop_btn.click(fn=None, inputs=None, outputs=None, cancels=[process_event])

        # Resume Viewer
        setup_resume_viewer_events(subject_dd, refresh_sub_btn, html_dd, dl_pdf_btn, pdf_out, resume_content)

        # Modal
        setup_modal_events(view_full_btn, subject_dd, html_dd, resume_modal, modal_resume_content, modal_pdf_output,
                           modal_close_btn, modal_download_btn)

    return app
