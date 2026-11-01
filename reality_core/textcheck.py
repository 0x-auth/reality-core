"""Look every claim of a note back up in its source. No model: words,
numbers (which must sit in the same source sentence) and negations.

A line-for-line port of Memory Check (the browser tool), checked against
it on 96 claims in tests/textcheck_fixture.json. Validated there on two
held-out documents: AUC 0.879 at the frozen line 0.183; wrong numbers
6/6, wrong terms 5/5, flipped negations 3/3, swapped relations 0/2.
"""

from __future__ import annotations

import re
import unicodedata

LINE = 0.183

STOP = set(("a an the and or but if then than that this these those to of in on at by for with from as is are was were be been being it its it's into over under about after before "
            "he she they them his her their we our you your i me my mine us not no nor so such also very just only both each other some any all more most less few own same can could would should will shall may might must "
            "do does did done have has had having there here when where which who whom what why how up down out off again further once while because until against between through during above below "
            "per vs via one's itself himself herself themselves ourselves yourself").split())
NEG = {"not", "no", "never", "none", "neither", "nor", "without", "cannot", "can't", "doesn't", "didn't", "isn't", "wasn't", "aren't", "won't", "don't", "fails", "failed"}
MONTHS = {"january": "jan", "february": "feb", "march": "mar", "april": "apr", "june": "jun", "july": "jul", "august": "aug",
          "september": "sep", "sept": "sep", "october": "oct", "november": "nov", "december": "dec"}
W = {"num": 3, "name": 2, "sym": 2, "word": 1}
_TAIL = set("'’._%-")
_COMMA = re.compile(r"([0-9]),(?=[0-9]{3}(?![A-Za-z0-9_]))")


def _cat(c):
    return unicodedata.category(c)


def _is_ln(c):
    return _cat(c)[0] in "LN"


def _raw_tokens(text):
    out, i, n = [], 0, len(text)
    while i < n:
        if _is_ln(text[i]):
            j = i + 1
            while j < n and (_is_ln(text[j]) or text[j] in _TAIL):
                j += 1
            out.append(text[i:j])
            i = j
        else:
            i += 1
    return out


def _stem(w):
    if w and _cat(w[0])[0] == "N":
        return w
    for s in ("ing", "ed", "es", "e", "s", "ly"):
        if len(w) > 3 and w.endswith(s):
            return w[:-len(s)]
    return w


def _js_number(m):
    f = float(m)
    return str(int(f)) if f.is_integer() and abs(f) < 1e21 else repr(f)


def _norm_num(w):
    m = re.sub(r"[’']", "", w)
    m = re.sub(r",(?=[0-9]{3}(?![A-Za-z0-9_]))", "", m)
    m = re.sub(r"%$", "", m)
    m = re.sub(r"[.\-]+$", "", m)
    if re.fullmatch(r"[0-9]+(\.[0-9]+)?", m):
        m = _js_number(m)
    return m


def tokens(text):
    text = _COMMA.sub(r"\1", text)
    out = []
    for i, raw in enumerate(_raw_tokens(text)):
        w = raw.rstrip(".-’'")
        if not w:
            continue
        lower = w.lower()
        is_num = _cat(w[0])[0] == "N" and re.search(r"[0-9]", w) is not None
        if not is_num and lower in STOP:
            continue
        if is_num:
            kind = "num"
        elif _cat(w[0]) == "Lu" and i > 0:
            kind = "name"
        elif any(ord(c) > 0x7F for c in w):
            kind = "sym"
        else:
            kind = "word"
        key = "#" + _norm_num(w) if is_num else (MONTHS.get(lower) or _stem(lower))
        if not is_num and len(key) < 2 and kind != "sym":
            continue
        out.append({"key": key, "kind": kind, "raw": w, "neg": lower in NEG})
    return out


def sentences(text):
    out = []
    for piece in re.split(r"\n+", text):
        start = 0
        for m in re.finditer(r"(?<=[.!?])\s+", piece):
            nxt = piece[m.end():m.end() + 1]
            if nxt and (_cat(nxt) == "Lu" or _cat(nxt)[0] == "N" or nxt in "(“\"'"):
                out.append(piece[start:m.start()])
                start = m.end()
        out.append(piece[start:])
    return [s.strip() for s in out if len(s.strip()) > 2]


def _negated_keys(text):
    raw, out = _raw_tokens(_COMMA.sub(r"\1", text)), set()
    for i, r in enumerate(raw):
        if r.lower() not in NEG:
            continue
        for j in range(i + 1, min(len(raw), i + 5)):
            ts = [q for q in tokens(" x " + raw[j]) if q["raw"] != "x"]
            if ts and not ts[0]["neg"]:
                out.add(ts[0]["key"])
                break
    return out


def _has_neg(text):
    words, cur = [], ""
    for c in text.lower():
        if _cat(c)[0] == "L" or c == "'":
            cur += c
        elif cur:
            words.append(cur)
            cur = ""
    if cur:
        words.append(cur)
    return any(w in NEG for w in words)


def check(source: str, note: str) -> dict:
    """Every sentence of the note becomes a claim with a residual: the share
    of its weighted words and numbers that the best source sentence lacks.
    Above LINE: send the claim to a person."""
    win = sentences(source)
    win_keys = [set(t["key"] for t in tokens(w)) for w in win]
    near = []
    for j in range(len(win)):
        u = set(win_keys[j])
        for k in (j - 1, j + 1):
            if 0 <= k < len(win):
                u |= {x for x in win_keys[k] if x[0] != "#"}
        near.append(u)

    def has(j, t):
        return t["key"] in (win_keys[j] if t["kind"] == "num" else near[j])

    all_src = set(t["key"] for t in tokens(source))
    claims = []
    for c in sentences(note):
        seen, tk = set(), []
        for t in tokens(c):
            if t["neg"] or t["key"] in seen:
                continue
            seen.add(t["key"])
            tk.append(t)
        total = sum(W[t["kind"]] for t in tk) or 1
        best, bi = -1.0, 0
        for j in range(len(win)):
            got = 0.0
            for t in tk:
                got += (W[t["kind"]] if has(j, t) else 0) + (0.001 * W[t["kind"]] if t["key"] in win_keys[j] else 0)
            if got > best:
                best, bi = got, j
        missing = [t for t in tk if not (win and has(bi, t))]
        neg_claim = _has_neg(c)
        neg_src = _has_neg(win[bi]) if win else False
        neg_hit = False
        if win and not neg_claim:
            nk = _negated_keys(win[bi])
            neg_hit = any(t["key"] in nk for t in tk)
        best = 0
        for t in tk:
            best += W[t["kind"]] if (win and has(bi, t)) else 0
        resid = 1 - max(0, best) / total
        neg_diff = ((neg_claim and not neg_src) or neg_hit) and resid < 0.5
        if neg_diff:
            resid = min(1, resid + 0.35)
        claims.append({"text": c, "residual": resid, "missing": [t["raw"] for t in missing],
                       "nowhere": [t["raw"] for t in missing if t["key"] not in all_src],
                       "neg_diff": neg_diff, "source": win[bi] if win else "",
                       "matched": [t["raw"] for t in tk if win and has(bi, t)]})
    return {"claims": claims}
