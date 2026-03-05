# Screenshot & GIF Placeholders

Place the following files here before publishing:

- **`web-ui-demo.png`** — Screenshot of the Gradio Web UI showing the Advocatus/Inquisitor toggle
- **`duel-mode-demo.gif`** — Terminal recording of `penggen duel --mode court` (use [asciinema](https://asciinema.org/) + [agg](https://github.com/asciinema/agg) or [terminalizer](https://github.com/faressoft/terminalizer))

Recommended capture commands:

```bash
# Record terminal session
asciinema rec duel-demo.cast -c "penggen duel --mode court --topic '1+1=2' --rounds 3"

# Convert to GIF
agg duel-demo.cast duel-mode-demo.gif --theme monokai --cols 100 --rows 30
```
