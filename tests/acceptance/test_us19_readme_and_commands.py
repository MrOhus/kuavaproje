"""US-19 README and one-command start and test — acceptance tests.

Expected behaviour comes from docs/design/DESIGN_f351eee.md (US-19, OQ-41,
and the Round 2 metric definitions in DESIGN_0bfd04e.md OQ-30) and
docs/architecture/ARCHITECTURE_899eaea.md (D-22: skipped GUI tests print
their reason, pytest -rs in the default options).
"""

import pathlib
import re
import subprocess
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[2]
README = ROOT / "README.md"


def readme():
    return README.read_text(encoding="utf-8")


def run_pytest(tmp_path, body):
    """Run the project's pytest configuration on one throw-away test file."""
    test_file = tmp_path / "test_throwaway.py"
    test_file.write_text(body, encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-c", str(ROOT / "pyproject.toml"),
         "--rootdir", str(ROOT), "-p", "no:cacheprovider", str(test_file)],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )


# --- Scenario: The README covers setup, start, tests and the metrics ----------


def test_readme_states_the_python_version_and_the_three_commands():
    text = readme()
    assert "Python 3.12 or newer" in text
    assert 'python -m pip install -e ".[dev]"' in text
    assert "python -m kuava_sim" in text
    assert "python -m pytest" in text


def test_readme_defines_the_four_metrics_as_round_2_does():
    text = readme()
    section = text[text.index("## Metric definitions"):]
    for name in ("Rise time", "Overshoot", "Settling time", "Steady-state error"):
        assert f"**{name}**" in section, name
    assert "10 % to 90 %" in section  # rise time
    assert "within 2 %" in section  # settling time
    assert "last sample" in section  # the final value, as step_info uses it
    assert "setpoint − final altitude" in section  # steady-state error, signed
    assert "not reached" in section
    assert "step_info" in section


def test_readme_names_what_the_app_shows_and_its_controls():
    text = readme()
    for phrase in ("Kp", "Ki", "Kd", "setpoint", "Wind gust", "Pause", "Reset", "fps"):
        assert phrase in text, phrase


def test_setup_command_installs_the_test_tools():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dev = " ".join(config["project"]["optional-dependencies"]["dev"])
    assert "pytest" in dev and "control" in dev
    assert config["project"]["dependencies"] == []  # nothing extra at runtime (D-1, D-16)


# --- Scenario: One command runs every test ------------------------------------


def test_one_command_collects_the_tests_of_every_story():
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True, timeout=300,
    )
    assert proc.returncode == 0, proc.stdout[-2000:]
    files = set(re.findall(r"(test_us\d+_\w+\.py)::", proc.stdout))
    stories = {int(re.match(r"test_us(\d+)_", f).group(1)) for f in files}
    assert stories == set(range(1, 20))  # US-1 ... US-19, GUI and python-control included


def test_skipped_tests_print_their_reason(tmp_path):
    proc = run_pytest(
        tmp_path,
        "import pytest\n\ndef test_window():\n"
        "    pytest.skip('no display available: no $DISPLAY')\n",
    )
    assert proc.returncode == 0
    assert "SKIPPED" in proc.stdout
    assert "no display available: no $DISPLAY" in proc.stdout


# --- Scenario: The test command reports a failing test ------------------------


def test_a_broken_test_is_reported_with_a_non_zero_exit_code(tmp_path):
    proc = run_pytest(tmp_path, "def test_broken():\n    assert 1 + 1 == 3\n")
    assert proc.returncode != 0
    assert "1 failed" in proc.stdout
