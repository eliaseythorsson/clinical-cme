"""The command table and the work-folder file table of references/state_schema.md are printed
by the engine and compared here, as the key-header table of rule 9 is (issue #76): the command
list is written once, in cme.py, and cannot drift from the parser."""
import os

from conftest import SKILL, run_script
from examples import cme

SCHEMA = os.path.join(SKILL, "references", "state_schema.md")


def between(opening, closing):
    with open(SCHEMA, encoding="utf-8") as fh:
        text = fh.read()
    assert text.count(opening) == 1 and text.count(closing) == 1
    return text.split(opening)[1].split(closing)[0].strip()


def test_the_command_table_in_the_schema_is_the_one_cme_py_generates():
    assert between(cme.COMMAND_TABLE_OPEN, cme.COMMAND_TABLE_CLOSE) == cme.command_table(), \
        "run `python3 skills/clinical-cme/scripts/cme.py command-table` and paste its output into state_schema.md §6"


def test_the_file_table_in_the_schema_is_the_one_cme_py_generates():
    assert between(cme.FILE_TABLE_OPEN, cme.FILE_TABLE_CLOSE) == cme.file_table(), \
        "run `python3 skills/clinical-cme/scripts/cme.py file-table` and paste its output into state_schema.md §6.1"


def test_the_commands_print_the_tables_between_their_markers():
    for name, opening, table, closing in (
            ("command-table", cme.COMMAND_TABLE_OPEN, cme.command_table(), cme.COMMAND_TABLE_CLOSE),
            ("file-table", cme.FILE_TABLE_OPEN, cme.file_table(), cme.FILE_TABLE_CLOSE)):
        r = run_script(cme.__file__, [name])
        assert r.returncode == 0 and r.stdout.strip() == "%s\n%s\n%s" % (opening, table, closing)


def test_every_command_of_the_parser_is_in_the_table_and_no_other():
    import argparse
    sub = next(a for a in cme.build_parser()._actions if isinstance(a, argparse._SubParsersAction))
    parsers = set(sub.choices) - {"reindex"}        # the old name of rebuild-page, named in its row
    assert set(cme.command_names()) == parsers


def test_every_fixed_file_name_of_the_work_folder_is_in_the_file_table():
    table = cme.file_table()
    for name in (cme.WORK_FILE, cme.PLAN_FILE, cme.ANSWERS_FILE, cme.FEEDBACK_QUESTIONS_FILE, cme.STAGE2_FILE,
                 cme.FEEDBACK_FILE, cme.ROUND_FILE, cme.RECORD_FILE, cme.PART_A_FILE, cme.REFLECTION_FILE,
                 cme.PART_B_FILE, cme.NEXT_DIR, cme.PUBLISH_DIR, cme.PUBLISH_FILE, cme.VERIFY_FILE, cme.TIMES_FILE,
                 cme.CLOSE_FROM_FILE, cme.EARLIER_DIR) + cme.SEALED_FILES:
        assert "`%s" % name in table, name
