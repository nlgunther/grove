"""
text_to_ics — free text in, a Google-Calendar-ready .ics file out.

Two independent halves, kept separate on purpose: extraction (fuzzy —
turning prose into structured events) and generation (deterministic —
turning structured events into a spec-compliant .ics). Generation is
shared.calendar's ICSWriter; this package only adds the extraction
step and the small adapter between the two.
"""
