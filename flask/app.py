"""The Flask application."""

from typing import Union

from flask import flash, Flask, redirect, render_template, request, Response, url_for

import koffee
from koffee.exceptions import InvalidVideoFileError


app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index() -> Union[Response, str]:
    """Renders the index page."""
    if request.method == "POST":
        file_path = request.form["file_path"]
        try:
            output_path = koffee.translate(file_path)
            flash(f"Successfully processed video! Output saved at: {output_path}")
            return redirect(url_for("index"))
        except InvalidVideoFileError as e:
            flash(str(e))
        except Exception as e:
            flash(f"An error occurred: {str(e)}")

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
