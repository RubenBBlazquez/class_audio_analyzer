import gradio as gr
from app.services import database_manager


def load_history():
    choices, rows = database_manager.get_recent_transcriptions()
    return gr.Dropdown(choices=choices)

def populate_from_history(selected_record):
    if not selected_record:
        return "", "", "", ""

    details = database_manager.get_transcription_details(selected_record)

    if details:
        return details  # subject, theme, objective, summary_text

    return "", "", "", ""

def create_history_component():
    with gr.Row(variant="panel", elem_classes="history-container"):
        history_dropdown = gr.Dropdown(label="Load Past Transcription/Summary", choices=[], interactive=True, scale=10)
        refresh_btn = gr.Button("Reload DB Changes", size="sm", scale=1, elem_classes="center-btn")

    return history_dropdown, refresh_btn

def setup_history_events(app, history_dropdown, refresh_btn, outputs_list):
    # outputs_list = [subject_input, theme_input, objective_input, summary_output]
    app.load(load_history, outputs=history_dropdown)
    refresh_btn.click(load_history, outputs=history_dropdown)
    history_dropdown.change(fn=populate_from_history, inputs=[history_dropdown],
                            outputs=outputs_list)
