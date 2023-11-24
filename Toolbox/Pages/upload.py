import gradio as gr

from Toolbox.Pages.common import *

from Toolbox.Tools.Upload import upload

EXIT_APP = False


# ----------------------------------------------------------------------------------------------------------------------
# Module
# ----------------------------------------------------------------------------------------------------------------------

def module_callback(username, password, source_id, images, prefix, annotations, labelset, headless, output_dir):
    """

    """
    console = sys.stdout
    sys.stdout = Logger(LOG_PATH)

    args = argparse.Namespace(
        username=username,
        password=password,
        source_id=source_id,
        images=images,
        prefix=prefix,
        annotations=annotations,
        labelset=labelset,
        headless=headless,
        output_dir=output_dir
    )

    try:
        # Call the function
        gr.Info("Starting process...")
        upload(args)
        gr.Info("Completed process!")
    except Exception as e:
        gr.Error("Could not complete process!")
        print(f"ERROR: {e}\n{traceback.format_exc()}")

    sys.stdout = console


# ----------------------------------------------------------------------------------------------------------------------
# Interface
# ----------------------------------------------------------------------------------------------------------------------
def exit_interface():
    """

    """
    global EXIT_APP
    EXIT_APP = True

    gr.Info("Please close the browser tab.")
    gr.Info("Stopped program successfully!")
    time.sleep(3)


def create_interface():
    """

    """

    with gr.Blocks(title="Upload ⬆️", analytics_enabled=False, theme=gr.themes.Soft(), js=js) as interface:
        # Title
        gr.Markdown("# Upload ⬆️")

        with gr.Row():
            username = gr.Textbox(os.getenv('CORALNET_USERNAME'), label="Username", type='email')
            password = gr.Textbox(os.getenv('CORALNET_PASSWORD'), label="Password", type='password')

        with gr.Row():
            source_id = gr.Number(label="Source ID", precision=0)
            prefix = gr.Textbox(label="Image Name Prefix")
            headless = gr.Checkbox(label="Run Browser in Headless Mode", value=True)

        # Browse button
        images = gr.Textbox(f"{DATA_DIR}", label="Selected Image Directory")
        dir_button = gr.Button("Browse Directory")
        dir_button.click(choose_directory, outputs=images, show_progress="hidden")

        annotations = gr.Textbox(label="Selected Annotation File")
        file_button = gr.Button("Browse Files")
        file_button.click(choose_file, outputs=annotations, show_progress="hidden")

        labelset = gr.Textbox(label="Selected Labelset File")
        file_button = gr.Button("Browse Files")
        file_button.click(choose_file, outputs=labelset, show_progress="hidden")

        # Browse button
        output_dir = gr.Textbox(f"{DATA_DIR}", label="Selected Output Directory")
        dir_button = gr.Button("Browse Directory")
        dir_button.click(choose_directory, outputs=output_dir, show_progress="hidden")

        with gr.Row():
            # Run button (callback)
            run_button = gr.Button("Run")
            run = run_button.click(module_callback,
                                   [username,
                                    password,
                                    source_id,
                                    images,
                                    prefix,
                                    annotations,
                                    labelset,
                                    headless,
                                    output_dir])

            stop_button = gr.Button(value="Stop")
            stop = stop_button.click(exit_interface)

        with gr.Accordion("Console Logs"):
            # Add logs
            logs = gr.Code(label="", language="shell", interactive=False, container=True, lines=30)
            interface.load(read_logs, None, logs, every=1)

    interface.launch(prevent_thread_lock=True, server_port=get_port(), inbrowser=True, show_error=True)

    return interface


# ----------------------------------------------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------------------------------------------
interface = create_interface()

while True:
    time.sleep(0.5)
    if EXIT_APP:
        Logger(LOG_PATH).reset_logs()
        break

