"""Behavior test steps for koffee APIs."""

from pathlib import Path

from behave import given, then, when
from behave.runner import Context

from koffee.exceptions import InvalidVideoFileError
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
def step_impl(context: Context, path) -> None:
    """Sets the output directory for the translated video file."""
    context.output_dir = Path(path)


@when("the user calls the koffee API")
def step_impl(context: Context):
    """Invoke the koffee API."""
    output_dir = getattr(context, "output_dir", None)
    output_name = getattr(context, "output_name", None)

    try:
        context.output_file_path = translate(
            context.video_file_path,
            output_dir=output_dir,
            output_name=output_name,
        )
    except InvalidVideoFileError as error:
        context.error = error


@then("the user receives a built video file")
def step_impl(context: Context):
    """Assert that the output file exists."""
    assert context.output_file_path.exists()


@given("the user corrupts the file somehow")
def step_impl(context: Context):
    """Corrupts a video file."""
    context.video_file_path = Path("invalid_video_file.mp4")


@then("the user receives the error message {error_message}")
def step_impl(context: Context, error_message: str):
    """Confirms the correct error message is raised."""
    assert isinstance(context.error, InvalidVideoFileError)
    assert str(context.error) == error_message
