CSS = """
.gradio-container .prose { margin-bottom: 10px; }
.timestamps { margin-top: 2em !important; }
.gradio-audio { height: auto !important; padding: 10px !important; }
.gradio-audio input[type="range"] { margin-top: 15px !important; margin-bottom: 15px !important; position: relative !important; z-index: 10 !important; }
.gradio-audio .time { margin-top: 25px !important; padding-top: 10px !important; display: flex !important; justify-content: space-between !important; width: 100% !important; position: relative !important; }
.gradio-audio .controls { margin-top: 15px !important; padding-bottom: 10px !important; }
.logs-container { margin-bottom: 20px !important; }
.center-btn { margin-top: 25px !important; height: 50px !important; }
.strategy-selector-container { 
    height: 100% !important; 
    display: flex !important; 
    flex-direction: column !important;
}
.strategy-selector-container .block { 
    height: 100% !important; 
    flex-grow: 1 !important;
}
.modal-visible, #resume-modal {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    z-index: 10000 !important;
    margin: 0 !important;
    padding: 0 !important;
    /* Remove background-color here as the inner box covers it */
    display: flex;
    align-items: center;
    justify-content: center;
}

#resume-modal .html-container > .prose, #resume-modal .html-container {
    height: 100vh !important;
}

/* Force hide when Gradio tries to hide it */
#resume-modal.hide, 
#resume-modal.hidden, 
#resume-modal[style*="display: none"],
.modal-visible[style*="display: none"] {
    display: none !important;
}

.modal-content-box {
    width: 100vw !important;
    height: 100vh !important;
    max-width: none !important;
    background-color: var(--background-fill-primary) !important;
    border-radius: 0 !important;
    padding: 20px !important;
    box-sizing: border-box !important;
    overflow: hidden !important;
    display: flex !important;
    flex-direction: column !important;
    box-shadow: none !important;
}
.modal-html-scroll {
    flex-grow: 1;
    overflow-y: hidden; /* Let iframe scroll */
    margin-top: 10px;
    border: none !important;
    background-color: transparent !important;
    padding: 0;
    display: flex !important;
    flex-direction: column !important;
}
.modal-html-scroll > div, .modal-html-scroll .prose {
    height: 100vh !important;
    flex-grow: 1 !important;
}
.pdf-gen-btn {
    height: 60px !important; 
    white-space: normal !important; 
    word-wrap: break-word !important; 
    display: flex !important; 
    align-items: center !important; 
    justify-content: center !important;
}
.pdf-output-file {
    height: 60px !important;
    min-height: 60px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    position: relative !important;
}
.pdf-output-file label, .pdf-output-file .block-label {
    position: absolute !important;
    left: 10px !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    margin: 0 !important;
    z-index: 10 !important;
}
"""
