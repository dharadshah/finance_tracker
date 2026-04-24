import gradio as gr


def build_app() -> gr.Blocks:
    """
    Builds and returns the Gradio application.
    Currently a placeholder — full dashboard built in Phase 4.
    Each tab will be a separate module imported here.
    """

    with gr.Blocks(
        title="Finance Tracker",
        theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate"),
    ) as app:
        gr.Markdown("## Finance Tracker")
        gr.Markdown(
            "Database initialised successfully. "
            "Ingestion and dashboard views will appear here in Phase 2 and 4."
        )

        with gr.Row():
            gr.Markdown("**Phase 1 complete** — database schema is ready.")

    return app
