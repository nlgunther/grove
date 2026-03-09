"""
dataframe_conversion.py
=======================
Bidirectional conversion between XML trees and pandas DataFrames.

Four public functions:
    to_dataframe(root)              XML element → DataFrame
    find_to_dataframe(tree, xpath)  XPath search → DataFrame
    from_dataframe(df)              DataFrame → XML element (round-trip)
    preview_dataframe(df)           Formatted summary string

No file I/O — callers own load/save. pandas is an optional dependency;
ImportError is raised only when these functions are called without it.
"""

import copy

try:
    import pandas as pd
    from lxml import etree
except ImportError:
    pass  # ImportError raised at call time if missing


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def to_dataframe(root, *, include_text: bool = True,
                 generate_ids: bool = False) -> "pd.DataFrame":
    """Convert an XML element tree to a flat DataFrame.

    Each row represents one element. Hierarchy is preserved via parent_id.

    Columns always present:
        id          Element's 'id' attribute (empty string if absent,
                    or auto-generated if generate_ids=True)
        parent_id   Parent's 'id' attribute, or 'root' for top-level nodes
        tag         Element tag name
        text        Stripped text content (if include_text=True)

    Additional columns: one per distinct attribute found across all elements.

    Args:
        root:           lxml Element (the tree root to convert).
        include_text:   Include text content column (default True).
                        Set False for 2x speedup on metadata-only exports.
        generate_ids:   Auto-generate sequential IDs for nodes that lack an
                        'id' attribute (default False).

    Returns:
        DataFrame. Empty DataFrame (with standard columns) if root has no
        children.

    Example:
        >>> df = to_dataframe(repo.root)
        >>> df[df['tag'] == 'task'].groupby('status').size()
    """
    _require_pandas()
    rows = []
    counter = [0]
    _collect_rows(root, parent_id="root", rows=rows, include_text=include_text,
                  generate_ids=generate_ids, counter=counter)
    if not rows:
        cols = ["id", "parent_id", "tag"]
        if include_text:
            cols.append("text")
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows)


def find_to_dataframe(tree, xpath: str, *, wrap_tag: str = "results",
                      include_text: bool = True) -> "pd.DataFrame":
    """Execute an XPath query and return matching nodes as a DataFrame.

    Results are deep-copied into a wrapper element so the original tree
    is never modified. Returns an empty DataFrame if nothing matches.

    Args:
        tree:           lxml ElementTree or Element to search.
        xpath:          XPath expression.
        wrap_tag:       Tag name for the synthetic container node.
        include_text:   Passed through to to_dataframe().

    Returns:
        DataFrame of matched nodes (and their descendants).

    Example:
        >>> df = find_to_dataframe(repo.tree, "//task[@status='active']")
        >>> df.groupby('assignee').size()
    """
    _require_pandas()
    if isinstance(tree, etree._ElementTree):
        tree = tree.getroot()
    matches = tree.xpath(xpath)
    if not matches:
        return pd.DataFrame(columns=["id", "parent_id", "tag", "text"])
    container = etree.Element(wrap_tag)
    for match in matches:
        container.append(copy.deepcopy(match))
    return to_dataframe(container, include_text=include_text)


def preview_dataframe(df: "pd.DataFrame", max_rows: int = 10) -> str:
    """Return a formatted summary string for a DataFrame.

    Args:
        df:       DataFrame to preview.
        max_rows: Maximum data rows to show in the preview table.

    Returns:
        Multi-line string suitable for printing to the console.

    Example output::

        DataFrame: 47 rows x 8 columns
        Columns: id, parent_id, tag, text, status, assignee
        Tags: task(25), project(7), milestone(15)

        Preview:
            id parent_id      tag  status
        0   p1      root  project  active
        ...
    """
    _require_pandas()

    if df.empty:
        return "Empty DataFrame"

    lines = []
    lines.append(f"DataFrame: {len(df)} rows x {len(df.columns)} columns")
    lines.append(f"Columns: {', '.join(df.columns.tolist())}")

    if "tag" in df.columns:
        counts = df["tag"].value_counts()
        tag_str = ", ".join(f"{tag}({n})" for tag, n in counts.items())
        lines.append(f"Tags: {tag_str}")

    lines.append("")
    lines.append("Preview:")
    with pd.option_context("display.max_columns", None, "display.width", None):
        lines.append(df.head(max_rows).to_string())

    return "\n".join(lines)


def from_dataframe(df: "pd.DataFrame", root_tag: str = "root") -> "etree.Element":
    """Reconstruct an XML element tree from a DataFrame.

    Enables round-trip workflows: export -> transform -> import.
    Uses parent_id to rebuild hierarchy; nodes whose parent_id is not
    found are attached to the root.

    Args:
        df:         DataFrame produced by to_dataframe() or find_to_dataframe(),
                    or any DataFrame with columns [id, parent_id, tag].
        root_tag:   Tag for the synthetic root element (default: 'root').
                    Ignored when the DataFrame was produced by to_dataframe()
                    on a named root (the original tag is preserved).

    Returns:
        lxml Element tree ready for insertion or saving.

    Raises:
        ValueError: If required columns (id, parent_id, tag) are missing.

    Example:
        >>> df = to_dataframe(repo.root)
        >>> df.loc[df['status'] == 'done', 'status'] = 'archived'
        >>> new_root = from_dataframe(df)
    """
    _require_pandas()
    if df.empty:
        return etree.Element(root_tag)

    missing = [c for c in ("id", "parent_id", "tag") if c not in df.columns]
    if missing:
        raise ValueError(f"DataFrame missing required columns: {missing}")

    rows = df.to_dict("records")

    # Detect whether the first row IS the original root element.
    # to_dataframe() always emits the root itself as the first row with
    # parent_id == 'root'.  We must treat it as the root rather than
    # creating an additional wrapper.
    first = rows[0]
    first_parent = str(first.get("parent_id", ""))
    first_is_root = first_parent == "root"

    if first_is_root:
        root_elem = _make_element(first)
        first_id = str(first.get("id", ""))
        # Register under both the element's own id and the sentinel "root"
        # so that children pointing to either key resolve correctly.
        id_map = {"root": root_elem}
        if first_id and first_id != "nan":
            id_map[first_id] = root_elem
        remaining = rows[1:]
    else:
        root_elem = etree.Element(root_tag)
        id_map = {"root": root_elem}
        remaining = rows

    for row in remaining:
        elem = _make_element(row)
        elem_id = str(row.get("id", ""))
        if elem_id and elem_id != "nan":
            id_map[elem_id] = elem
        parent_id = str(row.get("parent_id", "root"))
        parent = id_map.get(parent_id, root_elem)
        parent.append(elem)

    return root_elem


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SKIP_COLS = {"id", "parent_id", "tag", "text"}


def _require_pandas():
    try:
        import pandas  # noqa: F401
    except ImportError:
        raise ImportError(
            "pandas is required for DataFrame operations. "
            "Install it with: pip install pandas"
        )


def _collect_rows(elem, parent_id: str, rows: list, include_text: bool,
                  generate_ids: bool, counter: list):
    """Recursively walk tree, appending one dict per element."""
    elem_id = elem.get("id", "")

    if not elem_id and generate_ids:
        counter[0] += 1
        elem_id = f"gen{counter[0]:04d}"

    row = {
        "id": elem_id,
        "parent_id": parent_id,
        "tag": elem.tag,
    }
    if include_text:
        row["text"] = (elem.text or "").strip()

    # All other attributes become columns
    for key, val in elem.attrib.items():
        if key != "id":
            row[key] = val

    rows.append(row)

    child_parent = elem_id if elem_id else parent_id
    for child in elem:
        _collect_rows(child, child_parent, rows, include_text,
                      generate_ids, counter)


def _make_element(row: dict) -> "etree.Element":
    """Build an lxml Element from a DataFrame row dict."""
    tag = str(row.get("tag", "node"))
    attrs = {
        k: str(v) for k, v in row.items()
        if k not in _SKIP_COLS and v is not None and str(v) != "nan"
    }
    elem_id = str(row.get("id", ""))
    if elem_id and elem_id != "nan":
        attrs["id"] = elem_id

    elem = etree.Element(tag, attrib=attrs)
    text = str(row.get("text", ""))
    if text and text != "nan":
        elem.text = text
    return elem
