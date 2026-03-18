import typer

from bindu.cli import onboard

app = typer.Typer(help="Bindu CLI")

app.add_typer(onboard.app, name="onboard")

def main():
    app()