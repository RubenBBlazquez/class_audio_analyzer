import gradio as gr

def create_input_components():
    # State to track active tab - actually this should be created outside or passed in,
    # but we can create it here and return it.
    active_tab = gr.Textbox(value="audio", visible=False, label="Active Tab State")

    with gr.Column():
        with gr.Tab("Audio Source") as audio_tab:
            audio_input = gr.Audio(type="filepath", label="Audio File")
            subject_input = gr.Textbox(label="Subject (Folder Name)", placeholder="e.g. Physics")

        with gr.Tab("Text Source (Summarize Only)") as text_tab:
            text_file_input = gr.File(label="Upload Transcription Text File", file_types=[".txt"])

        with gr.Group():
            gr.Markdown("### Summarization Context")
            theme_input = gr.Textbox(label="Theme/Class Name", placeholder="e.g. Aerodinámica básica II")
            objective_input = gr.Textbox(label="Objective/Context", placeholder="e.g. Entender viscosidad...")
            mandatory_rules_input = gr.Textbox(label="Mandatory Rules", placeholder="e.g. The teacher has an accent, ignore 'uhm'...", lines=2)

            # Wrapper for context files and strategy selector
            with gr.Row():
                context_files_input = gr.File(label="Context Files (Optional)", file_count="multiple", scale=3)
                with gr.Column(elem_classes="strategy-selector-container", scale=1):
                    summarizer_selector = gr.Dropdown(
                        choices=["OpenAI Assistant", "Gemini Pro"],
                        value="OpenAI Assistant",
                        label="Summarizer Strategy",
                        interactive=True
                    )

            with gr.Row():
                auto_summarize = gr.Checkbox(label="Summarize immediately after transcription?", value=True)

        with gr.Row():
            action_btn = gr.Button("Start Process", variant="primary")
            stop_btn = gr.Button("Stop", variant="stop")

    # Wire internal tab logic
    audio_tab.select(fn=lambda: "audio", outputs=active_tab)
    text_tab.select(fn=lambda: "text", outputs=active_tab)

    return (active_tab, audio_input, subject_input, text_file_input,
            theme_input, objective_input, mandatory_rules_input, context_files_input,
            summarizer_selector, auto_summarize, action_btn, stop_btn)
