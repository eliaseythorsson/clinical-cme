"""The test runner itself (tests/conftest.py, issue #73): a script run in the test process behaves
as the same script run as its own process, so the suite means the same either way. Each check
runs the script both ways and compares."""
import json
import os

import pytest

from conftest import run_script

PROBE = '''
import json, os, sys, warnings
COUNT = []                                  # module state: a new process starts with it empty

def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="probe.py")
    ap.add_argument("what")
    ap.add_argument("rest", nargs="*")
    args = ap.parse_args(argv)
    COUNT.append(1)
    if args.what == "state":
        os.environ["PROBE_SET"] = "x"
        os.chdir(os.path.dirname(os.getcwd()))
        print(json.dumps({"count": len(COUNT), "env": os.environ.get("PROBE_SET_BEFORE"), "argv": sys.argv[1:]}))
    elif args.what == "cwd":
        print(os.getcwd())
    elif args.what == "stdin":
        print(json.dumps(sys.stdin.read()))
    elif args.what == "write":
        sys.stdout.write("out\\r\\n")
        sys.stderr.write("err\\n")
    elif args.what == "warn":
        warnings.warn("old", DeprecationWarning)          # shown: raised by the script itself
        warnings.warn_explicit("hidden", DeprecationWarning, "elsewhere.py", 1, module="elsewhere")
        warnings.warn("careful", UserWarning)
    elif args.what == "crash":
        raise ValueError("boom")
    elif args.what == "exit":
        sys.exit(args.rest[0] if args.rest[0].isalpha() else int(args.rest[0]))
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''


@pytest.fixture
def probe(tmp_path):
    path = tmp_path / "probe.py"
    path.write_text(PROBE, encoding="utf-8")
    (tmp_path / "cwd").mkdir()
    return str(path)


def both(probe, *args, **kw):
    """The same call in the test process and as a process: (in-process, process)."""
    return run_script(probe, args, process=False, **kw), run_script(probe, args, process=True, **kw)


def same(a, b):
    assert (a.returncode, a.stdout, a.stderr) == (b.returncode, b.stdout, b.stderr)


def test_module_state_env_cwd_and_argv_do_not_survive_a_call(probe, tmp_path):
    here = os.getcwd()
    cwd = str(tmp_path / "cwd")
    for _ in range(2):
        a, b = both(probe, "state", "x", cwd=cwd)
        same(a, b)
        assert json.loads(a.stdout) == {"count": 1, "env": None, "argv": ["state", "x"]}
        assert "PROBE_SET" not in os.environ and os.getcwd() == here


def test_runs_in_the_folder_given_or_the_current_one(probe, tmp_path):
    a, b = both(probe, "cwd", cwd=str(tmp_path / "cwd"))
    same(a, b)
    assert a.stdout.strip() == str(tmp_path / "cwd")
    same(*both(probe, "cwd"))


def test_standard_input_is_empty_unless_given(probe):
    same(*both(probe, "stdin"))
    a, b = both(probe, "stdin", input="line one\r\nline two\n")
    same(a, b)
    assert json.loads(a.stdout) == "line one\r\nline two\n"


def test_output_is_captured_as_a_pipe_in_text_mode_gives_it(probe):
    a, b = both(probe, "write")
    same(a, b)
    assert (a.stdout, a.stderr) == ("out\n", "err\n")


def test_warnings_go_to_standard_error_as_a_fresh_interpreter_shows_them(probe):
    a, b = both(probe, "warn")
    same(a, b)
    assert "DeprecationWarning: old" in a.stderr and "UserWarning: careful" in a.stderr and "hidden" not in a.stderr


@pytest.mark.parametrize("args, status", [(("exit", "3"), 3), (("exit", "300"), 44), (("exit", "stop"), 1),
                                          (("--bad",), 2), ((), 2)])
def test_exit_status_is_what_the_process_would_return(probe, args, status):
    a, b = both(probe, *args)
    same(a, b)
    assert a.returncode == status


def test_an_uncaught_exception_is_status_1_with_the_traceback(probe):
    a, b = both(probe, "crash")
    assert a.returncode == b.returncode == 1
    for r in (a, b):
        assert r.stdout == "" and r.stderr.rstrip().endswith("ValueError: boom") and "Traceback" in r.stderr
