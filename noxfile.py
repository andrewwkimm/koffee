"""Configuration for Nox."""

import nox
from nox.sessions import Session


@nox.session()
def test_build_from_wheel(session: Session) -> None:
    """Runs tests with local installation from a built wheel."""
    session.install("pytest")
    session.install("pytest-mock")
    session.install("behave")
    session.install("pydantic")

    session.run("poetry", "build", "--format", "wheel")
    session.run(
        "pip",
        "install",
        "--force-reinstall",
        f"{session.invoked_from}/dist/koffee-0.1.0-py3-none-any.whl",
    )

    session.run("pytest", "tests", "-x")
    session.run("behave")
