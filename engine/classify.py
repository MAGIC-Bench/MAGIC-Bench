"""Assertion classification + grading (the other half of the differential oracle).

The generator only writes the *input* and, per output field, a *class* (and rule):
  exact      - byte/value identical to what the original produced
  normalized - equal after a normalization rule (line endings, sorting, regex-match...)
  invariant  - a value-independent predicate holds (valid_json, nonempty, regex...)
  ignored    - present but not checked (e.g. an error message's exact wording)

freeze_golden() runs against the ORIGINAL's Observation and fills in the concrete
golden (for exact/normalized) or asserts the predicate holds (for invariant).
check() grades a candidate's Observation against the frozen assertions.

A field is one of: "exit", "stdout", "stderr", "file:<relpath>".
"""
from __future__ import annotations

import base64
import json
import re


# ---- field extraction -------------------------------------------------------

def extract(obs, field):
    if field == "exit":
        return obs.exit_code
    if field == "stdout":
        return obs.stdout
    if field == "stderr":
        return obs.stderr
    if field.startswith("file:"):
        return obs.out_files.get(field[5:])
    if field.startswith("http:"):
        # service fields: "http:<N>:status" | "http:<N>:body" | "http:<N>:header:<Name>"
        parts = field.split(":", 3)
        step = (obs.extra.get("http") or [])[int(parts[1])]
        what = parts[2]
        if what == "status":
            return step["status"]
        if what == "body":
            return step["body"]
        if what == "header":
            return step.get("headers", {}).get(parts[3])
    raise KeyError(f"unknown field: {field}")


def _text(value) -> str:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", "replace")
    return str(value)


# ---- exact encoding (JSON-serialisable, byte-faithful) ----------------------

def enc_exact(value):
    if isinstance(value, bool):
        return {"bool": value}
    if isinstance(value, int):
        return {"int": value}
    if value is None:
        return {"null": True}
    b = value if isinstance(value, (bytes, bytearray)) else str(value).encode("utf-8")
    b = bytes(b)
    try:
        t = b.decode("utf-8")
        if t.encode("utf-8") == b:
            return {"utf8": t}
    except UnicodeDecodeError:
        pass
    return {"b64": base64.b64encode(b).decode("ascii")}


# ---- normalization rules (canonical form for capture + compare) -------------

def norm_apply(rule: str, value):
    t = _text(value)
    if rule == "crlf_lf":
        return t.replace("\r\n", "\n")
    if rule == "strip":
        return t.strip()
    if rule == "rstrip_eol":
        return "\n".join(line.rstrip() for line in t.replace("\r\n", "\n").split("\n")).strip("\n")
    if rule == "lines_sorted":
        return "\n".join(sorted(t.replace("\r\n", "\n").rstrip("\n").split("\n")))
    if rule == "json_canonical":
        return json.dumps(json.loads(t), sort_keys=True, separators=(",", ":"))
    if rule.startswith("regex_extract:"):
        m = re.search(rule[len("regex_extract:"):], t, re.S)
        return m.group(0) if m else None
    raise ValueError(f"unknown normalize rule: {rule}")


# ---- invariant predicates (value-independent) -------------------------------

def inv_check(rule: str, value) -> bool:
    t = _text(value)
    if rule == "nonempty":
        return len(t) > 0
    if rule == "empty":
        return len(t) == 0
    if rule == "valid_json":
        try:
            json.loads(t)
            return True
        except Exception:
            return False
    if rule.startswith("regex:"):
        return re.search(rule[len("regex:"):], t, re.S) is not None
    if rule.startswith("eq_int:"):
        try:
            return int(value) == int(rule[len("eq_int:"):])
        except Exception:
            return False
    raise ValueError(f"unknown invariant rule: {rule}")


# ---- freeze (against original) + check (against candidate) ------------------

def freeze_golden(obs, spec: list[dict]) -> list[dict]:
    """spec item: {field, class, rule?}. Returns assertions with golden values filled.
    Raises if an invariant the generator chose does not actually hold on the original."""
    out = []
    for a in spec:
        field, cls, rule = a["field"], a["class"], a.get("rule")
        val = extract(obs, field)
        rec = {"field": field, "class": cls}
        if rule:
            rec["rule"] = rule
        if cls == "exact":
            rec["value"] = enc_exact(val)
        elif cls == "normalized":
            rec["value"] = norm_apply(rule, val)
        elif cls == "invariant":
            if not inv_check(rule, val):
                raise AssertionError(f"invariant '{rule}' does NOT hold on original for {field!r} "
                                     f"-> generator chose a bad assertion")
        elif cls == "ignored":
            pass
        else:
            raise ValueError(f"unknown class: {cls}")
        out.append(rec)
    return out


def check(obs, assertions: list[dict]) -> list[dict]:
    """Grade an Observation against frozen assertions. Returns per-field results."""
    results = []
    for a in assertions:
        field, cls = a["field"], a["class"]
        try:                                         # any malformed assertion -> fail (don't crash grading)
            val = extract(obs, field)
            if cls == "exact":
                ok = enc_exact(val) == a["value"]
            elif cls == "normalized":
                ok = norm_apply(a["rule"], val) == a["value"]
            elif cls == "invariant":
                ok = inv_check(a["rule"], val)
            elif cls == "ignored":
                ok = True
            else:
                ok = False
        except Exception:
            ok = False
        results.append({"field": field, "class": cls, "ok": bool(ok)})
    return results


def agrees(obs1, obs2, spec: list[dict]) -> bool:
    """Two runs of the SAME input agree under the assertion classes -> deterministic.
    Used at golden-capture: the original is run twice (network allowed); only inputs whose
    two runs agree are frozen as tests (others are non-deterministic and dropped)."""
    for a in spec:
        field, cls, rule = a["field"], a["class"], a.get("rule")
        try:
            v1, v2 = extract(obs1, field), extract(obs2, field)
            if cls == "exact":
                if enc_exact(v1) != enc_exact(v2):
                    return False
            elif cls == "normalized":
                if norm_apply(rule, v1) != norm_apply(rule, v2):
                    return False
            elif cls == "invariant":
                if inv_check(rule, v1) != inv_check(rule, v2):
                    return False
        except Exception:
            return False
    return True
