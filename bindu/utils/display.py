"""Display utilities for the bindu server."""

from __future__ import annotations

import sys

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

from bindu.__version__ import __version__


def prepare_server_display(
    host: str | None = None,
    port: int | None = None,
    agent_id: str | None = None,
    agent_did: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
    tunnel_url: str | None = None,
) -> None:
    """Prepare a beautiful display for the server using rich.

    Args:
        host: Server hostname
        port: Server port
        agent_id: Agent identifier
        agent_did: Agent DID
        client_id: OAuth client ID for token retrieval
        client_secret: OAuth client secret for token retrieval
        tunnel_url: Public tunnel URL if tunneling is enabled
    """
    # Force UTF-8 output on Windows to avoid cp1252 UnicodeEncodeError when
    # rich renders emoji (e.g. in Panel titles). reconfigure() changes the
    # encoding in-place without closing stdout.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[call-non-callable]
        except Exception:
            pass
    console = Console()

    # ASCII art with gradient colors
    ascii_art = (
        r"[cyan]}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}[/cyan]"
        "\n"
        r"[cyan]{{[/cyan]            [yellow]+[/yellow]             [yellow]+[/yellow]"
        r"                  [yellow]+[/yellow]   [yellow]@[/yellow]          [cyan]{{[/cyan]"
        "\n"
        r"[cyan]}}[/cyan]   [yellow]|[/yellow]                [yellow]*[/yellow]           "
        r"[yellow]o[/yellow]     [yellow]+[/yellow]                [yellow].[/yellow]    [cyan]}}[/cyan]"
        "\n"
        r"[cyan]{{[/cyan]  [yellow]-O-[/yellow]    [yellow]o[/yellow]               [yellow].[/yellow]"
        r"               [yellow].[/yellow]          [yellow]+[/yellow]       [cyan]{{[/cyan]"
        "\n"
        r"[cyan]}}[/cyan]   [yellow]|[/yellow]                    [magenta]_,.-----.,_[/magenta]"
        r"         [yellow]o[/yellow]    [yellow]|[/yellow]          [cyan]}}[/cyan]"
        "\n"
        r"[cyan]{{[/cyan]           [yellow]+[/yellow]    [yellow]*[/yellow]    [magenta].-'.         .'-.          "
        r"-O-[/magenta]         [cyan]{{[/cyan]"
        "\n"
        r"[cyan]}}[/cyan]      [yellow]*[/yellow]            [magenta].'.-'   .---.   `'.'.[/magenta]"
        r"         [yellow]|[/yellow]     [yellow]*[/yellow]    [cyan]}}[/cyan]"
        "\n"
        r"[cyan]{{[/cyan] [yellow].[/yellow]                [magenta]/_.-'   /     \   .'-.[/magenta]\\"
        r"                   [cyan]{{[/cyan]"
        "\n"
        r"[cyan]}}[/cyan]         [yellow]'[/yellow] [yellow]-=*<[/yellow]  [magenta]|-._.-  |   @   |   '-._|"
        r"[/magenta]  [yellow]>*=-[/yellow]    [yellow].[/yellow]     [yellow]+[/yellow] [cyan]}}[/cyan]"
        "\n"
        r"[cyan]{{[/cyan] [yellow]-- )--[/yellow]           [magenta]\`-.    \     /    .-'/[/magenta]"
        r"                   [cyan]{{[/cyan]"
        "\n"
        r"[cyan]}}[/cyan]       [yellow]*[/yellow]     [yellow]+[/yellow]     [magenta]`.'.    '---'    .'.'[/magenta]"
        r"    [yellow]+[/yellow]       [yellow]o[/yellow]       [cyan]}}[/cyan]"
        "\n"
        r"[cyan]{{[/cyan]                  [yellow].[/yellow]  [magenta]'-._         _.-'[/magenta]  [yellow].[/yellow]"
        r"                   [cyan]{{[/cyan]"
        "\n"
        r"[cyan]}}[/cyan]         [yellow]|[/yellow]               [magenta]`~~~~~~~`[/magenta]"
        r"       [yellow]- --===D[/yellow]       [yellow]@[/yellow]   [cyan]}}[/cyan]"
        "\n"
        r"[cyan]{{[/cyan]   [yellow]o[/yellow]    [yellow]-O-[/yellow]      [yellow]*[/yellow]   [yellow].[/yellow]"
        r"                  [yellow]*[/yellow]        [yellow]+[/yellow]          [cyan]{{[/cyan]"
        "\n"
        r"[cyan]}}[/cyan]         [yellow]|[/yellow]                      [yellow]+[/yellow]"
        r"         [yellow].[/yellow]            [yellow]+[/yellow]    [cyan]}}[/cyan]"
        "\n"
        r"[cyan]{{[/cyan] [dim]jgs[/dim]          [yellow].[/yellow]     [yellow]@[/yellow]      [yellow]o[/yellow]"
        r"                        [yellow]*[/yellow]       [cyan]{{[/cyan]"
        "\n"
        r"[cyan]}}[/cyan]       [yellow]o[/yellow]                          [yellow]*[/yellow]"
        r"          [yellow]o[/yellow]           [yellow].[/yellow]  [cyan]}}[/cyan]"
        "\n"
        r"[cyan]{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{[/cyan]"
    )

    # Create tagline
    tagline = Text("a bindu, part of Night Sky", style="italic magenta")

    # Group ASCII art and tagline together
    title = Text("Bindu 🌻", style="bold magenta")
    panel_content = Group(Align.center(ascii_art), "", Align.center(tagline))

    # Print ASCII art panel
    console.print()
    console.print(
        Panel(panel_content, title=title, border_style="bright_cyan", padding=(1, 2))
    )
    console.print()

    # Print version
    console.print(Text(f"Version: {__version__}", style="bold white"), highlight=False)
    console.print()

    # Print server information
    if host and port:
        console.print(Text("🚀 Bindu Server 🚀", style="bold magenta"), highlight=False)
        console.print(
            Text(f"Local Server: http://{host}:{port}", style="green"), highlight=False
        )

        # Display tunnel URL prominently if available
        if tunnel_url:
            console.print(
                Text(f"🌐 Public URL: {tunnel_url}", style="bold bright_green"),
                highlight=False,
            )

        console.print()

    if agent_id:
        console.print(Text(f"Agent ID: {agent_id}", style="cyan"), highlight=False)

    if agent_did:
        console.print(Text(f"Agent DID: {agent_did}", style="cyan"), highlight=False)

    if agent_id or agent_did:
        console.print()

    # Print protocol endpoints
    if host and port:
        # Use tunnel URL if available, otherwise local URL
        base_url = tunnel_url if tunnel_url else f"http://{host}:{port}"

        console.print(Text("Protocol Endpoints:", style="bold white"), highlight=False)
        console.print(
            Text(f"  - Agent Endpoint: {base_url}/", style="white"), highlight=False
        )
        console.print(
            Text(f"  - Agent Card: {base_url}/.well-known/agent.json", style="white"),
            highlight=False,
        )
        console.print(
            Text(f"  - DID Resolution: {base_url}/did/resolve", style="white"),
            highlight=False,
        )
        console.print()

    # Print community and documentation
    console.print(
        Text("⭐️⭐️⭐️ Support Open Source ⭐️⭐️⭐️", style="bold yellow"),
        highlight=False,
    )
    console.print(
        Text("⭐️⭐️⭐️ Star on GitHub! ⭐️⭐️⭐️", style="bold yellow"), highlight=False
    )
    console.print(
        Text("https://github.com/getbindu/Bindu", style="cyan underline"),
        highlight=False,
    )
    console.print()

    console.print(Text("Join our Community 🤝", style="bold green"), highlight=False)
    console.print(
        Text("https://discord.gg/3w5zuYUuwt", style="cyan underline"), highlight=False
    )
    console.print()

    console.print(Text("Documentation 🌻", style="bold blue"), highlight=False)
    console.print(
        Text("https://docs.getbindu.com", style="cyan underline"), highlight=False
    )
    console.print()

    # Print token retrieval command if credentials are available
    if client_id and client_secret:
        console.print(
            Text("🔑 Get Access Token:", style="bold yellow"), highlight=False
        )
        curl_cmd = (
            f"curl -X POST https://hydra.getbindu.com/oauth2/token \\\n"
            f'  -H "Content-Type: application/x-www-form-urlencoded" \\\n'
            f'  -d "grant_type=client_credentials" \\\n'
            f'  -d "client_id={client_id}" \\\n'
            f'  -d "client_secret=<YOUR_CLIENT_SECRET>" \\\n'
            f'  -d "scope=openid offline agent:read agent:write"'
        )
        console.print(Text(curl_cmd, style="dim"), highlight=False)
        console.print(
            Text(
                "📁 Find your client_secret in: .bindu/oauth_credentials.json",
                style="italic cyan",
            ),
            highlight=False,
        )
        console.print()
