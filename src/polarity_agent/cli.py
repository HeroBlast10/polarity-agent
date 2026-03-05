"""CLI powered by Typer + Rich.

Subcommands
-----------
chat      Interactive chat with a persona.
list      Show available persona packs.
duel      Pit two personas against each other.
serve     Launch the Gradio web UI.
install   Install community persona packs.
"""

import asyncio
import random
import time
from enum import Enum

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from polarity_agent import __version__

# ── Module objects ───────────────────────────────────────────────────────

console = Console()

app = typer.Typer(
    name="penggen",
    help="Polarity Agent -- extreme emotional polarity, on demand.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

install_app = typer.Typer(name="install", help="Install components.", no_args_is_help=True)
app.add_typer(install_app)


# ── Enums & constants ───────────────────────────────────────────────────


class DuelMode(str, Enum):
    TROLL_FIGHT = "troll-fight"
    PRAISE_BATTLE = "praise-battle"
    COURT = "court"


_THINKING = {
    "inquisitor": [
        "scanning for logical fallacies...",
        "loading sarcasm module...",
        "calibrating condescension levels...",
        "searching for weaknesses...",
        "adjusting imaginary spectacles...",
    ],
    "advocatus": [
        "charging flattery cannon...",
        "synthesizing praise molecules...",
        "constructing ego scaffolding...",
        "mining compliment database...",
        "warming up the yes-engine...",
    ],
}


# ── Helpers ──────────────────────────────────────────────────────────────


def _typewriter(text: str, style: str, speed: float = 0.015) -> None:
    """Character-by-character Rich typewriter effect."""
    for i in range(0, len(text), 3):
        console.print(text[i : i + 3], style=style, end="", highlight=False)
        time.sleep(speed)
    console.print()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"penggen [bold cyan]{__version__}[/]")
        raise typer.Exit()


# ── Commands ─────────────────────────────────────────────────────────────


@app.callback()
def _root(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Polarity Agent -- because balanced opinions are overrated."""


@app.command()
def chat(
    pack: str = typer.Option("advocatus", "--pack", "-p", help="Persona pack name."),
    provider: str = typer.Option("ollama", "--provider", help="LLM provider."),
    model: str = typer.Option("llama3", "--model", "-m", help="Model name."),
    base_url: str | None = typer.Option(None, "--base-url", help="Provider base URL."),
    api_key: str | None = typer.Option(None, "--api-key", help="API key."),
    trace: bool = typer.Option(False, "--trace", help="Enable JSONL trace logging."),
) -> None:
    """Start an interactive chat session with a persona."""
    trace_dir = _resolve_trace_dir(trace)
    try:
        asyncio.run(_run_chat(pack, provider, model, base_url, api_key, trace_dir))
    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye![/]")


@app.command(name="list")
def list_packs() -> None:
    """List all available persona packs."""
    from polarity_agent.packs import PackLoader

    packs = PackLoader().discover()
    if not packs:
        console.print("[dim]No persona packs found.[/]")
        return

    table = Table(title="Available Persona Packs", border_style="cyan")
    table.add_column("Stance", justify="center", width=8)
    table.add_column("Name", style="bold")
    table.add_column("Description")
    table.add_column("Ver", justify="right", style="dim")

    for _name, p in sorted(packs.items()):
        badge = "[bold green]+[/]" if p.stance.value == "support" else "[bold red]-[/]"
        table.add_row(badge, p.display_name, p.description, p.version)

    console.print()
    console.print(table)
    console.print()


@app.command()
def duel(
    mode: DuelMode = typer.Option(
        DuelMode.COURT, "--mode", "-m", help="troll-fight | praise-battle | court"
    ),
    topic: str = typer.Option(
        ..., "--topic", "-t", prompt="Enter a topic or statement", help="Starting topic."
    ),
    provider: str = typer.Option("ollama", "--provider", help="LLM provider."),
    model: str = typer.Option("llama3", "--model", help="Model name."),
    rounds: int = typer.Option(3, "--rounds", "-r", help="Number of rounds."),
    base_url: str | None = typer.Option(None, "--base-url", help="Provider base URL."),
    api_key: str | None = typer.Option(None, "--api-key", help="API key."),
    trace: bool = typer.Option(False, "--trace", help="Enable JSONL trace logging."),
) -> None:
    """Start a duel between personas in the Cyber Arena."""
    trace_dir = _resolve_trace_dir(trace)
    try:
        asyncio.run(_run_duel(mode, topic, provider, model, rounds, base_url, api_key, trace_dir))
    except KeyboardInterrupt:
        console.print("\n[dim]Duel terminated.[/]")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", help="Bind host."),
    port: int = typer.Option(7860, "--port", help="Bind port."),
) -> None:
    """Launch the Gradio web UI."""
    try:
        from polarity_agent.web import create_demo
    except ImportError:
        console.print("[red]Web dependencies not installed.[/]")
        console.print("Run: [bold]pip install polarity-agent\\[web][/]")
        raise typer.Exit(1) from None

    console.print(
        Panel(
            f"Launching Polarity Agent Web UI\nhttp://{host}:{port}",
            title="Web Server",
            border_style="cyan",
        )
    )
    demo = create_demo()
    demo.launch(server_name=host, server_port=port)


@install_app.command("pack")
def install_pack_cmd(
    source: str = typer.Argument(..., help="Git URL or pip package name."),
) -> None:
    """Install a persona pack from a URL or package."""
    from polarity_agent.packs._installer import install_pack

    install_pack(source)


# ── Async runners ────────────────────────────────────────────────────────


def _resolve_trace_dir(enabled: bool) -> "str | None":
    """Return the trace directory path if tracing is enabled, else *None*."""
    if not enabled:
        return None
    from polarity_agent.tracing import default_trace_dir

    path = default_trace_dir()
    console.print(f"[dim]Trace logs -> {path}[/]")
    return str(path)


async def _run_chat(
    pack_name: str,
    provider_name: str,
    model: str,
    base_url: "str | None",
    api_key: "str | None",
    trace_dir: "str | None" = None,
) -> None:
    from polarity_agent.agent import PolarityAgent
    from polarity_agent.packs import PackLoader
    from polarity_agent.providers import ProviderConfig, create_provider

    loader = PackLoader()
    pack = loader.load(pack_name)
    config = ProviderConfig(model=model, base_url=base_url, api_key=api_key)

    color = "green" if pack.stance.value == "support" else "red"
    console.print(
        Panel(
            f"[bold]{pack.display_name}[/] is ready.\n"
            f"Stance: [{color}]{pack.stance.value}[/{color}]  |  "
            f"Provider: {provider_name}/{model}\n"
            f"Type [bold]quit[/] to exit.",
            title="Polarity Agent",
            border_style=color,
        )
    )

    async with create_provider(provider_name, config) as provider:
        agent = PolarityAgent(provider=provider, pack=pack, trace_dir=trace_dir)
        while True:
            try:
                user_input = console.input("[bold cyan]You >[/] ").strip()
            except EOFError:
                break
            if not user_input or user_input.lower() in ("quit", "exit", "q"):
                break
            console.print(f"[dim italic]>>> {pack.display_name} is thinking...[/]")
            response = await agent.respond(user_input)
            console.print(f"\n[bold {color}]\\[{pack.display_name}][/]")
            _typewriter(response, color)
            console.print()
    console.print("[dim]Goodbye![/]")


async def _run_duel(
    mode: DuelMode,
    topic: str,
    provider_name: str,
    model: str,
    rounds: int,
    base_url: "str | None",
    api_key: "str | None",
    trace_dir: "str | None" = None,
) -> None:
    from polarity_agent.packs import PackLoader
    from polarity_agent.providers import ProviderConfig, create_provider

    banners = {
        DuelMode.TROLL_FIGHT: ("TROLL FIGHT // 诸神黄昏", "red"),
        DuelMode.PRAISE_BATTLE: ("PRAISE BATTLE // 彩虹屁内卷", "green"),
        DuelMode.COURT: ("THE COURT // 代理人法庭", "cyan"),
    }
    title, color = banners[mode]
    console.print(
        Panel(
            f"[bold]{title}[/]\n\nTopic: [italic]{topic}[/]\n"
            f"Rounds: {rounds}  |  Provider: {provider_name}/{model}",
            title="CYBER ARENA",
            border_style=color,
            width=70,
        )
    )
    time.sleep(1)

    loader = PackLoader(include_user_dir=False)
    config = ProviderConfig(model=model, base_url=base_url, api_key=api_key)

    async with create_provider(provider_name, config) as provider:
        if mode == DuelMode.TROLL_FIGHT:
            await _duel_troll_fight(provider, loader, topic, rounds, trace_dir)
        elif mode == DuelMode.PRAISE_BATTLE:
            await _duel_praise_battle(provider, loader, topic, rounds, trace_dir)
        else:
            await _duel_court(provider, loader, topic, rounds, trace_dir)

    console.print(Panel("[bold]DUEL COMPLETE[/]", border_style="dim", width=70))


async def _duel_troll_fight(
    provider, loader, topic: str, rounds: int, trace_dir: "str | None" = None
) -> None:  # type: ignore[type-arg]
    from polarity_agent.agent import PolarityAgent

    pack = loader.load("inquisitor")
    agent_a = PolarityAgent(provider=provider, pack=pack, trace_dir=trace_dir)
    agent_b = PolarityAgent(provider=provider, pack=pack, trace_dir=trace_dir)

    current = topic
    for i in range(rounds):
        console.rule(f"[bold red]Round {i + 1}[/]")

        console.print(f"\n[dim italic]>>> \\[杠精 A] {random.choice(_THINKING['inquisitor'])}[/]")
        resp_a = await agent_a.respond(current)
        console.print("[bold red]\\[杠精 A]:[/]")
        _typewriter(resp_a, "red")
        time.sleep(1.5)

        console.print(f"\n[dim italic]>>> \\[杠精 B] {random.choice(_THINKING['inquisitor'])}[/]")
        resp_b = await agent_b.respond(resp_a)
        console.print("[bold red]\\[杠精 B]:[/]")
        _typewriter(resp_b, "red")
        time.sleep(1.5)

        current = resp_b


async def _duel_praise_battle(
    provider, loader, topic: str, rounds: int, trace_dir: "str | None" = None
) -> None:  # type: ignore[type-arg]
    from polarity_agent.agent import PolarityAgent

    pack = loader.load("advocatus")
    agent_a = PolarityAgent(provider=provider, pack=pack, trace_dir=trace_dir)
    agent_b = PolarityAgent(provider=provider, pack=pack, trace_dir=trace_dir)

    current = topic
    for i in range(rounds):
        console.rule(f"[bold green]Round {i + 1}[/]")

        console.print(f"\n[dim italic]>>> \\[捧哏 A] {random.choice(_THINKING['advocatus'])}[/]")
        resp_a = await agent_a.respond(current)
        console.print("[bold green]\\[捧哏 A]:[/]")
        _typewriter(resp_a, "green")
        time.sleep(1.5)

        console.print(f"\n[dim italic]>>> \\[捧哏 B] {random.choice(_THINKING['advocatus'])}[/]")
        resp_b = await agent_b.respond(resp_a)
        console.print("[bold green]\\[捧哏 B]:[/]")
        _typewriter(resp_b, "green")
        time.sleep(1.5)

        current = resp_b


async def _duel_court(
    provider, loader, target: str, rounds: int, trace_dir: "str | None" = None
) -> None:  # type: ignore[type-arg]
    from polarity_agent.agent import PolarityAgent

    agent_adv = PolarityAgent(
        provider=provider, pack=loader.load("advocatus"), trace_dir=trace_dir
    )
    agent_inq = PolarityAgent(
        provider=provider, pack=loader.load("inquisitor"), trace_dir=trace_dir
    )

    for i in range(rounds):
        console.rule(f"[bold cyan]Round {i + 1}[/]")
        prompt = target if i == 0 else f"请继续就以下论点进行第 {i + 1} 轮陈述:\n{target}"

        console.print(
            f"\n[dim italic]>>> \\[捧哏 Advocatus] {random.choice(_THINKING['advocatus'])}[/]"
        )
        resp_adv = await agent_adv.respond(prompt)
        console.print("[bold green]\\[捧哏 Advocatus]:[/]")
        _typewriter(resp_adv, "green")
        time.sleep(2)

        console.print(
            f"\n[dim italic]>>> \\[杠精 Inquisitor] {random.choice(_THINKING['inquisitor'])}[/]"
        )
        resp_inq = await agent_inq.respond(prompt)
        console.print("[bold red]\\[杠精 Inquisitor]:[/]")
        _typewriter(resp_inq, "red")
        time.sleep(2)


# ── Entry point ──────────────────────────────────────────────────────────


def main() -> None:
    app()


if __name__ == "__main__":
    main()
