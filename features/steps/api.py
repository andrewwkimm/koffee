"""Behavior test steps for koffee APIs."""

from pathlib import Path

from behave import given, then, when
from behave.runner import Context

from koffee.translate import translate


@given("a user has a basic {language} video file")
def step_given(context: Context, language: str) -> None:
    """Adds a path to a good video file to the context."""
    if language == "Korean":
        context.video_file_path = Path("examples/videos/sample_korean_video.mp4")
        context.output_name = "sample_korean_video_test"
    elif language == "Japanese":
        context.video_file_path = Path("examples/videos/sample_japanese_video.mp4")
        context.output_name = "sample_japanese_video_test"


@given("the user sets the output directory to {path}")
def step_impl(context, path) -> None:
    """Sets the output directory for the translated video file."""
    context.output_dir = Path(path)


@when("the user calls the koffee API")
def step_impl(context):
    """Invoke the koffee API."""
    context.output_file_path = translate(
        context.video_file_path,
        output_dir=context.output_dir,
        output_name=context.output_name,
    )


@then("the user receives a built video file")
def step_impl(context):
    """Assert that the output file exists."""
    assert context.output_file_path.exists()
