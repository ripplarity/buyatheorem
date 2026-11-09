import sys

import typer

from buyatheorem import mint as m

app = typer.Typer(add_completion=False)


@app.command()
def mint(
    for_: str = typer.Option(..., "--for"), seed: str = typer.Option(..., "--seed")
):
    cert = m.mint(for_, seed)
    print(cert["serial"])


@app.command()
def verify(serial: str):
    sys.exit(m.verify(serial))


if __name__ == "__main__":
    app()
