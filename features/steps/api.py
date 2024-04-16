"""Behavior test steps for koffee APIs."""

from behave import given
from behave.runner import Context


@given("a user has a basic {language} video file")
def step_given(context: Context, language: str) -> None:
    """Adds a path to a good video file to the context."""
    pass
