import os
import sys

import typer

from buyatheorem import mint as m
from buyatheorem import stock as st

app = typer.Typer(add_completion=False)


@app.command()
def mint(for_: str = typer.Option(..., "--for"), seed: str = typer.Option(..., "--seed")):
    cert = m.mint(for_, seed)
    print(cert["serial"])


@app.command()
def verify(serial: str, dir: str = typer.Option(None, "--dir")):
    if dir:
        os.environ["BAT_REGISTRY"] = dir
    sys.exit(m.verify(serial))


@app.command()
def stock(n: int = typer.Option(50, "--n"), out: str = typer.Option("stock", "--out")):
    rows = st.stock(n, out)
    print(len(rows))


@app.command()
def claim(serial: str, for_: str = typer.Option(..., "--for"), dir: str = typer.Option("stock", "--dir")):
    st.claim(serial, for_, dir)
    print(serial)


if __name__ == "__main__":
    app()
