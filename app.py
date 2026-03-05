"""Standalone launcher for the Polarity Agent Gradio UI.

Run directly::

    python app.py

Or via the CLI::

    penggen serve --port 7860
"""

from polarity_agent.web import create_demo

if __name__ == "__main__":
    demo = create_demo()
    demo.launch(server_name="0.0.0.0", server_port=7860)
