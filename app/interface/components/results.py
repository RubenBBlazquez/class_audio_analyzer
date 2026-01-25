import gradio as gr

def create_results_component():
    with gr.Tab("Status & Results"):
        log_output = gr.Textbox(label="Process Log", lines=10, elem_classes="logs-container")
        summary_output = gr.Textbox(label="Summary Result", lines=15, elem_classes="logs-container")
    return log_output, summary_output
