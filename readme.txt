HARBORFLOW PORT INTELLIGENCE CONSOLE - TEAM README

Run instructions
----------------
Command:
From the repository root, run `python main.py`.
Python version tested: 3.13

Team members and concrete contributions
---------------------------------------
Name: Rafael Siverbo
Contribution:
Coded and implemented tasks 0 and 1
Tested tasks 2 - 6
Coded and implemented tasks 7 - 9


Name: Mykhailo Asmar
Contribution:
Coded and implemented tasks 2 - 6
Tested tasks 7 - 9
Tested final product

Name:
Contribution:

Name (if applicable):
Contribution:

Architecture
------------
`main.py` displays the console menu and dispatches selected services. It
contains only the small Task 1 inventory wrapper; service-specific prompts
and output are handled by the task modules.

`tasks_2_6.py` and `tasks_7_9.py` implement the menu services. They collect
user input, call data-access functions and business rules, and present
results or actionable errors.

`data_access.py` defines dataset/export paths, parses and validates JSON and
CSV records, and reads or writes generated files. `operations.py` contains
data-oriented business rules and formatting helpers; it does not prompt,
print, or access files. `text_tools.py` contains regular-expression text
sanitization and incident-word normalization. This separation lets services
orchestrate work while keeping file I/O and business logic reusable.

File and error-handling design
------------------------------
Dataset and export paths are `pathlib.Path` values relative to the current
working directory. Start the program from the repository root so paths such
as `dataset/vessels` and `exports` resolve correctly. Source data consists
of JSON records in `dataset/vessels`, `dataset/manifests`,
`dataset/shipments`, and `dataset/incidents`, plus `dataset/port_calls.csv`
and `dataset/weather.csv`.

JSON record loaders validate required fields and types, skip malformed
records individually, and return their filenames and reasons for reporting
where appropriate. A missing JSON source directory yields an empty record
set. CSV loaders check required headers; malformed weather numeric rows are
reported and skipped, while missing or unreadable required CSV files stop
the relevant service with an explanatory message. Invalid dates are handled
by each service: user-entered dates are prompted again, and invalid
port-call dates are reported and skipped. Missing linked records or weather
forecasts are reported without stopping unrelated results.

Customer profile exports and the incident search index are written to a
temporary sibling file and then replaced, avoiding partially written final
files. Incident searches reuse `dataset/incident-index.json`, rebuilding it
if it is missing, malformed, or older than a source incident file.
Sanitized reports are written beneath `exports/sanitized`.

Known limitations
-----------------
Paths depend on launching from the repository root; the program does not
resolve them relative to the source files. Incident-index freshness uses
file modification times, so deletions or edits that preserve/restore older
timestamps may not invalidate the cache. Sanitization only recognizes the
container, seal, and email patterns defined in `text_tools.py`; it is not a
general-purpose privacy or redaction system. Sanitized report files are
written directly rather than atomically.
