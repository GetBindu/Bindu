"""Utility script to obtain Auth0 access tokens for testing."""

import argparse
import os
import sys

import pyperclip
import requests
from rich.console import Console
from rich.panel import Panel

console = Console()


def get_auth0_token(domain: str, client_id: str, client_secret: str) -> str:
    """Get Auth0 access token using client credentials flow."""
    audience = f"https://{domain}/api/v2/"
    url = f"https://{domain}/oauth/token"

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "audience": audience,
        "grant_type": "client_credentials",
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.exceptions.HTTPError as e:  # type: ignore[attr-defined]
        console.print(f"[red]HTTP Error {e.response.status_code}:[/red] {e.response.text}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:  # type: ignore[attr-defined]
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def main():
    """Obtain Auth0 access token for testing and optionally copy to clipboard."""
    parser = argparse.ArgumentParser(
        description="Obtain Auth0 access tokens for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--domain",
        default=os.getenv("AUTH0_DOMAIN"),
        help="Auth0 domain (e.g., dev-xxx.us.auth0.com). Can also use AUTH0_DOMAIN env var.",
    )
    parser.add_argument(
        "--client-id",
        default=os.getenv("AUTH0_CLIENT_ID"),
        help="Auth0 client ID. Can also use AUTH0_CLIENT_ID env var.",
    )
    parser.add_argument(
        "--client-secret",
        default=os.getenv("AUTH0_CLIENT_SECRET"),
        help="Auth0 client secret. Can also use AUTH0_CLIENT_SECRET env var.",
    )
    parser.add_argument(
        "--copy",
        default=True,
        action="store_true",
        help="Automatically copy token to clipboard (requires pyperclip)",
    )

    args = parser.parse_args()

    # Validate required arguments
    missing = []
    if not args.domain:
        missing.append("--domain or AUTH0_DOMAIN")
    if not args.client_id:
        missing.append("--client-id or AUTH0_CLIENT_ID")
    if not args.client_secret:
        missing.append("--client-secret or AUTH0_CLIENT_SECRET")

    if missing:
        console.print(f"[red]Error:[/red] Missing required arguments: {', '.join(missing)}")
        parser.print_help()
        sys.exit(1)

    # Get token
    with console.status("[bold green]Requesting Auth0 token..."):
        token = get_auth0_token(args.domain, args.client_id, args.client_secret)

    # Output token
    console.print(
        Panel(
            token,
            title="[bold green]✓ Auth0 Access Token[/bold green]",
            border_style="green",
        )
    )

    if args.copy:
        pyperclip.copy(token)
        console.print("\n[green]✓ Token copied to clipboard![/green]")


if __name__ == "__main__":
    main()
