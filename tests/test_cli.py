from typer.testing import CliRunner

from podpaper import __version__
from podpaper.cli import app


def test_version_command() -> None:
    result = CliRunner().invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == __version__
