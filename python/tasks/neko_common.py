"""Shared helpers for BioModelAgent NeKo tasks.

This module is NOT a scout task file: it defines no ``@task`` functions and is
never registered in ``workflow.rb``. It only holds file-format handling for our
own SIF artifacts (parsing the tab rows written by ``Exports.export_sif``) and
thin wrappers around the ``neko`` API. All network logic lives in the installed
``neko`` package; nothing here reimplements it.

Top-level imports are stdlib only. Every neko/pandas import is lazy inside a
function body, because scout-rig re-runs each task file as a subprocess and
task registration must stay cheap.

Artifact conventions:

- Files are written into ``$SCOUT_JOB_FILES_DIR`` when the variable is set
  (scout task execution); otherwise a ``tempfile.mkdtemp`` fallback keeps the
  function directly invokable for tests and probes.
- TSV outputs follow the scout convention: the first line is a ``#``-prefixed
  tab-separated header, followed by plain tab-separated rows. No ``#:``
  directives are emitted.
- SIF files are the native neko export format: an optional
  ``# Reference PMID: ...`` comment line immediately before each
  ``source<TAB>effect<TAB>target`` row.
"""

import io
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

#: Resource universes accepted wherever a ``database`` input appears.
SUPPORTED_DATABASES = ("omnipath", "signor")

#: Effect tokens that can appear in the SIF ``effect`` column, as produced by
#: ``Exports.export_sif`` from the neko ``Effect`` column.
SIF_EFFECT_TOKENS = (
    "stimulation",
    "inhibition",
    "form_complex",
    "bimodal",
    "undefined",
)


def validate_database(database: str) -> str:
    """Validate a ``database`` input and return it.

    Args:
        database: Resource universe name; ``"omnipath"`` or ``"signor"``.

    Returns:
        The validated database name.

    Raises:
        ValueError: If ``database`` is not one of the supported names.
    """
    if database not in SUPPORTED_DATABASES:
        raise ValueError(
            "database must be one of "
            f"{', '.join(SUPPORTED_DATABASES)}; got {database!r}"
        )
    return database


def files_dir() -> str:
    """Return the directory task artifacts should be written to.

    Uses ``$SCOUT_JOB_FILES_DIR`` when set (scout task execution) and otherwise
    creates a fresh temporary directory so direct python invocations still get
    a usable path.

    Returns:
        Absolute path of the artifact directory as a ``str``.
    """
    env_dir = os.environ.get("SCOUT_JOB_FILES_DIR")
    if env_dir:
        return str(Path(env_dir).resolve())
    return tempfile.mkdtemp(prefix="neko_task_")


def artifact_path(filename: str) -> str:
    """Resolve ``filename`` inside the artifact directory.

    Args:
        filename: Bare file name (no directory components expected).

    Returns:
        Absolute path of the artifact file as a ``str``.
    """
    return str(Path(files_dir()) / filename)


def load_network(sif_path, database: str = "omnipath"):
    """Load a ``Network`` from a SIF file.

    Args:
        sif_path: Path to a SIF file previously produced by a
            network-returning NeKo task (or any file in the same format).
        database: Resource universe used to resolve node identifiers and
            candidate connections; ``"omnipath"`` or ``"signor"``.

    Returns:
        The loaded ``neko.core.network.Network``.

    Raises:
        FileNotFoundError: If ``sif_path`` does not exist.
        ValueError: If ``database`` is unsupported or neko fails to load the
            file.
    """
    validate_database(database)
    path = Path(str(sif_path))
    if not path.is_file():
        raise FileNotFoundError(f"SIF file not found: {path}")

    from neko.core.network import Network

    try:
        return Network(sif_file=str(path), resources=database)
    except Exception as exc:  # noqa: BLE001 - re-raised with context
        raise ValueError(
            f"Failed to load SIF network from {path} with resources={database!r}: {exc}"
        ) from exc


def write_sif(network, filename: str = "neko_network.sif") -> str:
    """Export ``network`` as a SIF artifact and return its absolute path.

    Args:
        network: A ``neko.core.network.Network`` instance.
        filename: Artifact file name; network-returning tasks all use the
            default ``neko_network.sif``.

    Returns:
        Absolute path of the written SIF file as a ``str``.
    """
    from neko._outputs.exports import Exports

    target = artifact_path(filename)
    try:
        Exports(network).export_sif(target)
    except Exception as exc:  # noqa: BLE001 - re-raised with context
        raise ValueError(f"Failed to export SIF to {target}: {exc}") from exc
    return str(Path(target).resolve())


def read_sif_rows(sif_path):
    """Parse a SIF file into ``(source, effect, target, references)`` rows.

    Handles the neko export format: a ``# Reference PMID: ...`` comment line
    immediately preceding a row is captured as that row's references; other
    ``#`` comment lines are skipped. Rows are tab-separated with three fields.

    Args:
        sif_path: Path to the SIF file.

    Returns:
        A ``list`` of ``(source, effect, target, references)`` tuples;
        ``references`` is ``""`` when the row had no paired reference line.

    Raises:
        FileNotFoundError: If ``sif_path`` does not exist.
        ValueError: If a non-comment row does not have exactly three
            tab-separated fields.
    """
    path = Path(str(sif_path))
    if not path.is_file():
        raise FileNotFoundError(f"SIF file not found: {path}")

    rows = []
    pending_reference = ""
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n").rstrip("\r")
            if line.startswith("# Reference PMID:"):
                pending_reference = line[len("# Reference PMID:"):].strip()
                continue
            if line.startswith("#"):
                continue
            if not line.strip():
                continue
            fields = line.split("\t")
            if len(fields) != 3:
                raise ValueError(
                    f"Malformed SIF row (expected 3 tab-separated fields) in "
                    f"{path}: {line!r}"
                )
            source, effect, target = (field.strip() for field in fields)
            rows.append((source, effect, target, pending_reference))
            pending_reference = ""
    return rows


def write_tsv(path, header_fields, rows) -> str:
    """Write a scout-convention TSV artifact.

    The first line is ``#``-prefixed tab-separated header fields, followed by
    plain tab-separated data rows. No ``#:`` directives are emitted.

    Args:
        path: Destination file path.
        header_fields: Iterable of column names for the header line.
        rows: Iterable of row tuples/lists, each with one value per column.

    Returns:
        Absolute path of the written file as a ``str``.
    """
    target = Path(str(path))
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write("#" + "\t".join(str(field) for field in header_fields) + "\n")
        for row in rows:
            handle.write("\t".join("" if value is None else str(value) for value in row) + "\n")
    return str(target.resolve())


def write_md(path, title: str, lines) -> str:
    """Write a markdown report artifact.

    Args:
        path: Destination file path.
        title: Report title rendered as the first ``# `` heading.
        lines: Iterable of markdown body lines written verbatim after the
            title.

    Returns:
        Absolute path of the written file as a ``str``.
    """
    target = Path(str(path))
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(f"# {title}\n\n")
        for line in lines:
            handle.write(f"{line}\n")
    return str(target.resolve())


def log(*args) -> None:
    """Log a message to stderr (never stdout; stdout carries task results)."""
    print(*args, file=sys.stderr, flush=True)


def capture_stdout(function, *args, **kwargs):
    """Run ``function`` capturing its ``print`` output.

    Args:
        function: Callable to run.
        *args: Positional arguments forwarded to ``function``.
        **kwargs: Keyword arguments forwarded to ``function``.

    Returns:
        The captured stdout text.
    """
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        function(*args, **kwargs)
    return buffer.getvalue()
