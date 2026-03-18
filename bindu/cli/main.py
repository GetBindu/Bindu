import typer

from bindu.cli import onboard, db, train, canary

app = typer.Typer(help="Bindu CLI")

app.add_typer(onboard.app, name="onboard")
app.add_typer(db.app, name="db")
app.add_typer(train.app, name="train")
app.add_typer(canary.app, name="canary")

def main():
    app()