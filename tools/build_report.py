"""Build the submission .docx from Harsh's text in the official Apart template (15 Nov 2026).

Text: Harsh's own file (path given as argv[1]); used as written, apart from the heading case.
Tables: rebuilt from results/*.json (the plain-text tables lost their columns).
Run: python tools/build_report.py "<his .txt>" "<template.docx>" "<out.docx>"
(python-docx is a user-site package, so run without -I.)
"""
import copy
import json
import re
import sys
from pathlib import Path

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
TITLE = ("Announced Audits, Actual Evidence: Telling a Model Its References Will Be Checked, "
         "Versus Showing It the Check")
REPO = "https://github.com/harshnsawant-source/apart-epistemics-2026"
LLM_STATEMENT = (
    "Claude (Anthropic) assisted throughout this project and in drafting this paper. Claude Opus 5.5 wrote and "
    "tested the code, ran the data collection, produced the figures and tables, and wrote a first draft of the "
    "report, which the author then rewrote. Claude Fable 5.2 was used for design discussion, and GPT-6-Astra "
    "(OpenAI, via Codex) critiqued the design before it was frozen. The author designed the study, froze the "
    "plan and carried out the blind audit by hand. Every number in this report was checked against the "
    "analysis outputs in the repository.")

HEAD = re.compile(r"^(ABSTRACT|\d\. [A-Z ]+|\d\.\d [A-Z].*|CODE AND DATA|BIBLIOGRAPHY|APPENDIX [A-D]\..*|LLM USAGE STATEMENT|"
                  r"Limitations|Dual-use and ethical considerations|Dual-Use/Ethics|Previous Work|AI Tools)$")
ITEM = re.compile(r"^(- |\d+b?\. |Archival version|Audit version|Archived \(version|Audit \(version)")
SMALL = Pt(8.5)


def nice_heading(h):
    if h == "BIBLIOGRAPHY":
        return "References", 2
    if h == "CODE AND DATA":
        return "Code and Data", 2
    if h == "LLM USAGE STATEMENT":
        return "LLM Usage Statement", 2
    fixed = {"A": "Appendix A. Limitations and Dual-Use/Ethics",
             "B": "Appendix B. Deviations from the Frozen Plan",
             "C": "Appendix C. Previous Work and AI Tools",
             "D": "Appendix D. Stage Two on the Other Models (Exploratory)"}
    m = re.match(r"^APPENDIX ([A-D])\. ", h)
    if m:
        return fixed[m.group(1)], 2
    m = re.match(r"^(\d)\. ([A-Z ]+)$", h)
    if m:
        return f"{m.group(1)}. {m.group(2).title()}", 2
    return h, 3


def blocks(text):
    """Yield ('head', text) or ('block', [lines])."""
    cur = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if HEAD.match(line.strip()):
            if cur:
                yield "block", cur
                cur = []
            yield "head", line.strip()
        elif not line.strip():
            if cur:
                yield "block", cur
                cur = []
        else:
            cur.append(line.strip())
    if cur:
        yield "block", cur


def set_cell_borders(table):
    tbl = table._tbl
    pr = tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for edge in ("top", "bottom", "insideH"):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "4")
        e.set(qn("w:color"), "999999")
        b.append(e)
    pr.append(b)


def add_table(doc, head, rows, widths=None):
    t = doc.add_table(rows=1 + len(rows), cols=len(head))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_cell_borders(t)
    for i, row in enumerate([head] + rows):
        for j, val in enumerate(row):
            c = t.rows[i].cells[j]
            c.text = ""
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.space_before = Pt(0)
            r = p.add_run(str(val))
            r.font.size = SMALL
            r.bold = i == 0
            if widths:
                c.width = Inches(widths[j])
            p.paragraph_format.keep_with_next = i < len(rows)
        trpr = t.rows[i]._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        trpr.append(cs)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return t


def fmt(x):
    return f"{x:+.2f}"


def ci(s):
    return f"{fmt(s['mean'])} [{fmt(s['ci'][0])}, {fmt(s['ci'][1])}]"


def table1(doc, r):
    names = {"gptoss": "gpt-oss-120b", "qwen": "Qwen3.8 27B", "nemotron": "Nemotron 3 Ultra", "llama": "Llama 3.2 3B"}
    rows = []
    for a in ("gptoss", "qwen", "nemotron", "llama"):
        A = r["arms"][a]
        cm = A["cell_means"]
        rows.append([names[a], f"{cm['P10']['U']:.2f}", f"{cm['A10']['U']:.2f}", ci(A["primary_U_A10_minus_P10"]),
                     ci(A["guardrail_V_A10_minus_P10"]), f"{cm['P10']['given']:.2f} / {cm['A10']['given']:.2f}"])
    add_table(doc, ["Model", "Unmatched (Archived)", "Unmatched (Audit)", "Difference in Unmatched Titles [95% CI]",
                    "Difference in Verified Papers [95% CI]", "Titles Given (Archived/Audit)"], rows,
              [1.15, 0.8, 0.75, 1.35, 1.35, 1.0])


def table2(doc, r):
    cm = r["arms"]["gptoss"]["cell_means"]
    lab = [("P10", "Archived (10 titles) (P10)"), ("A10", "Audit (10 titles) (A10)"),
           ("P<10", "Archived (fewer titles allowed) (P<10)"), ("A<10", "Audit (fewer titles allowed) (A<10)"),
           ("BASE", "Unmodified base prompt (A/A)")]
    rows = [[n, f"{cm[k]['U']:.2f}", f"{cm[k]['V']:.2f}", f"{cm[k]['given']:.2f}"] for k, n in lab]
    add_table(doc, ["Cell", "Unmatched", "Verified", "Titles Given"], rows, [2.6, 1.0, 1.0, 1.0])


def table3(doc, x):
    rows = []
    for b, n in (("neutral", "Neutral"), ("audit", "Audit Reminder"), ("receipts", "Real Check Results")):
        s = x["stage2"][b]

        def cell(k):
            sh = s[f"share_{k}_withdrawn"] * 100
            lo, hi = (v * 100 for v in s[f"share_{k}_withdrawn_ci"])
            iv = "" if b == "receipts" else f", {lo:.0f} to {hi:.0f}"
            return f"{s[k + '_withdrawn']} / {s[k]} ({sh:.0f}%{iv})"
        rows.append([n, cell("unres"), cell("ver"), f"{s['random_deletion_share'] * 100:.0f}% of each group"])
    add_table(doc, ["Branch", "Unmatched Deleted", "Verified Deleted", "Randomly Deleted (Same Number)"],
              rows, [1.4, 1.75, 1.6, 1.65])


def table4(doc, x):
    """Stage two on all four models: gpt-oss-120b (pre-registered) + the exploratory addendum (item 11)."""
    add = json.loads((RES / "stage2_addendum.json").read_text("utf-8"))["arms"]
    src = [("gpt-oss-120b", x["stage2"])] + [(n, add[a]["branches"]) for a, n in
                                            (("qwen", "Qwen3.8 27B"), ("nemotron", "Nemotron 3 Ultra"),
                                             ("llama", "Llama 3.2 3B"))]
    rows = []
    for name, br in src:
        for b, n in (("neutral", "Neutral"), ("audit", "Audit Reminder"), ("receipts", "Real Check Results")):
            s = br[b]

            def cell(k):
                sh = s[f"share_{k}_withdrawn"] * 100
                lo, hi = (v * 100 for v in s[f"share_{k}_withdrawn_ci"])
                iv = "" if round(lo) == round(hi) == round(sh) else f", {lo:.0f} to {hi:.0f}"
                return f"{s[k + '_withdrawn']} / {s[k]} ({sh:.0f}%{iv})"
            rows.append([name if b == "neutral" else "", n, cell("unres"), cell("ver"),
                         f"{s['random_deletion_share'] * 100:.0f}%"])
    add_table(doc, ["Model", "Branch", "Unmatched Deleted", "Verified Deleted", "Random (Same Number)"],
              rows, [1.25, 1.3, 1.6, 1.5, 0.9])


def para(doc, text, style="normal", size=None, bold_lead=None, italic=False, align=None, after=4):
    p = doc.add_paragraph(style=style)
    p.paragraph_format.space_after = Pt(after)
    if align is not None:
        p.alignment = align
    if bold_lead and text.startswith(bold_lead):
        r = p.add_run(bold_lead)
        r.bold = True
        if size:
            r.font.size = size
        text = text[len(bold_lead):]
    r = p.add_run(text)
    r.italic = italic
    if size:
        r.font.size = size
    return p


def main():
    src, tpl, out = sys.argv[1], sys.argv[2], sys.argv[3]
    text = Path(src).read_text("utf-8")
    title = TITLE
    if text.startswith("TITLE:"):
        first, text = text.split(chr(10), 1)
        title = first[len("TITLE:"):].strip()
    r = json.loads((RES / "results.json").read_text("utf-8"))
    x = json.loads((RES / "report_extras.json").read_text("utf-8"))
    doc = docx.Document(tpl)
    doc.styles["normal"].font.size = Pt(10.5)
    body = doc.element.body
    kids = list(body.iterchildren())
    head_tbl = doc.tables[0]

    # Title (keep the run that carries the template's footnote).
    tp = [p for p in head_tbl.rows[0].cells[0].paragraphs if p.style.name == "Title"][0]
    tp.runs[0].text = title
    for run in tp.runs[1:]:
        if "footnoteReference" not in run._r.xml:
            run.text = ""

    # Authors: replace the nested author table with three centred lines.
    cell = head_tbl.rows[1].cells[0]
    nested = [el for el in cell._tc.iterchildren() if el.tag == qn("w:tbl")]
    auth_tbl, abs_tbl = nested[0], nested[1]
    anchor = auth_tbl
    for line, bold, ital in (("Harsh Sawant", True, False), ("Independent Researcher", False, False),
                             ("With Apart Research", False, True)):
        np_ = OxmlElement("w:p")
        anchor.addnext(np_)
        anchor = np_
        p = docx.text.paragraph.Paragraph(np_, cell)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(line)
        run.bold, run.italic = bold, ital
    auth_tbl.getparent().remove(auth_tbl)

    # Abstract.
    abstract = " ".join(text.split("ABSTRACT", 1)[1].split("1. INTRODUCTION", 1)[0].split())
    acell = docx.table.Table(abs_tbl, cell).rows[0].cells[0]
    ps = acell.paragraphs
    for p in ps[1:]:
        p._p.getparent().remove(p._p)
    p0 = ps[0]
    for run in p0.runs[1:]:
        run._r.getparent().remove(run._r)
    p0.runs[0].text = abstract
    p0.runs[0].italic = False

    # Remove the template's guidance (everything after the header table, except sectPr).
    for el in kids[2:]:
        if el.tag != qn("w:sectPr"):
            body.remove(el)

    body_text = text.split("1. INTRODUCTION", 1)[1]
    body_text = "1. INTRODUCTION\n" + body_text
    seen_heads = []
    for kind, val in blocks(body_text):
        if kind == "head":
            h, lvl = nice_heading(val)
            seen_heads.append(h)
            doc.add_paragraph(h, style=f"Heading {lvl}")
            continue
        lines = val
        first = lines[0]
        joined = " ".join(lines)
        if first.startswith("Model Unmatched"):
            table1(doc, r)
        elif first.startswith("Cell Unmatched"):
            table2(doc, r)
        elif first.startswith("Branch Unmatched"):
            table3(doc, x)
        elif first.startswith("Model Branch"):
            table4(doc, x)
        elif first.startswith("[Insert Figure"):
            n = first[len("[Insert Figure "):][0]
            img, w = (("fig1_main_contrast.png", 4.6) if n == "1" else ("fig2_stage2.png", 4.3))
            doc.add_picture(str(RES / img), width=Inches(w))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.paragraphs[-1].paragraph_format.keep_with_next = True
            cap = " ".join(lines[1:])
            assert cap.startswith(f"Figure {n}."), cap[:40]
            para(doc, cap, size=Pt(9), bold_lead=f"Figure {n}.", after=8)
        elif re.match(r"^(Table|Figure) \d\.", first):
            lead = re.match(r"^((Table|Figure) \d\.)", first).group(1)
            cp = para(doc, joined, size=Pt(9), bold_lead=lead, after=4)
            cp.paragraph_format.keep_with_next = lead.startswith("Table")
        elif first.startswith(("Frozen verdict", "Inconclusive for all")):
            for ln in lines:
                para(doc, ln, size=SMALL, after=0)
            doc.add_paragraph().paragraph_format.space_after = Pt(0)
        elif first.startswith("[Repository link"):
            joined = joined.replace("[Repository link, if made public.]", f"Code repository: {REPO}.")
            para(doc, joined)
        elif any(ITEM.match(ln) for ln in lines):
            items, cur = [], []
            for ln in lines:
                if ITEM.match(ln) and cur:
                    items.append(" ".join(cur))
                    cur = []
                cur.append(ln)
            items.append(" ".join(cur))
            for it in items:
                p = para(doc, it, after=3)
                p.paragraph_format.left_indent = Inches(0.25)
                if it.startswith("- "):
                    p.runs[0].text = "• " + it[2:]
        else:
            lead = None
            for cand in ("Fake references.", "References that were invented.", "Evaluation awareness.", "Pre-existing work.",
                         "Work that was already in place beforehand.", "AI tools."):
                if first.startswith(cand):
                    lead = cand
            size = Pt(9.5) if seen_heads and seen_heads[-1] == "References" else None
            para(doc, joined, bold_lead=lead, size=size)

    if "LLM Usage Statement" not in seen_heads:
        doc.add_paragraph("LLM Usage Statement", style="Heading 2")
        para(doc, LLM_STATEMENT)
    doc.save(out)
    print("headings:", seen_heads)


if __name__ == "__main__":
    main()
