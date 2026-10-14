"""PatchCourt Master Reference Sheet — PDF generator.
Run: pip install reportlab && python gen_pdf.py
Output: PatchCourt_Master_Reference.pdf
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

W, H = A4
MARGIN = 1.8 * cm

# ── Colour palette ──────────────────────────────────────────────────────────
C_PRIMARY   = colors.HexColor("#1C3C3C")   # dark teal
C_ACCENT    = colors.HexColor("#009688")   # teal
C_RED       = colors.HexColor("#C62828")
C_ORANGE    = colors.HexColor("#E65100")
C_YELLOW    = colors.HexColor("#F9A825")
C_GREEN     = colors.HexColor("#2E7D32")
C_BLUE      = colors.HexColor("#1565C0")
C_PURPLE    = colors.HexColor("#6A1B9A")
C_LIGHT     = colors.HexColor("#F5F5F5")
C_BORDER    = colors.HexColor("#BDBDBD")
C_CODE_BG   = colors.HexColor("#263238")
C_CODE_FG   = colors.HexColor("#ECEFF1")
C_MUTED     = colors.HexColor("#757575")
C_WHITE     = colors.white
C_BLACK     = colors.black

ss = getSampleStyleSheet()

def sty(name, **kw):
    base = ss["Normal"]
    return ParagraphStyle(name, parent=base, **kw)

# ── Styles ───────────────────────────────────────────────────────────────────
S_COVER_TITLE = sty("CoverTitle",
    fontSize=32, leading=40, textColor=C_WHITE,
    fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=8)

S_COVER_SUB = sty("CoverSub",
    fontSize=14, leading=20, textColor=colors.HexColor("#B2DFDB"),
    fontName="Helvetica", alignment=TA_CENTER, spaceAfter=6)

S_COVER_META = sty("CoverMeta",
    fontSize=10, leading=14, textColor=colors.HexColor("#80CBC4"),
    fontName="Helvetica", alignment=TA_CENTER)

S_H1 = sty("H1",
    fontSize=18, leading=24, textColor=C_PRIMARY,
    fontName="Helvetica-Bold", spaceBefore=18, spaceAfter=6,
    borderPad=4)

S_H2 = sty("H2",
    fontSize=13, leading=18, textColor=C_ACCENT,
    fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=4)

S_H3 = sty("H3",
    fontSize=11, leading=15, textColor=C_PRIMARY,
    fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=3)

S_BODY = sty("Body",
    fontSize=9.5, leading=14, textColor=C_BLACK,
    fontName="Helvetica", spaceAfter=4, alignment=TA_JUSTIFY)

S_BULLET = sty("Bullet",
    fontSize=9.5, leading=13, textColor=C_BLACK,
    fontName="Helvetica", leftIndent=14, spaceAfter=2,
    bulletIndent=4)

S_CODE = sty("Code",
    fontSize=8, leading=11, textColor=C_CODE_FG,
    fontName="Courier", backColor=C_CODE_BG,
    leftIndent=8, rightIndent=8, spaceBefore=4, spaceAfter=4,
    borderPad=6)

S_NOTE = sty("Note",
    fontSize=8.5, leading=12, textColor=colors.HexColor("#4A148C"),
    fontName="Helvetica-Oblique", leftIndent=10, spaceAfter=3)

S_WARN = sty("Warn",
    fontSize=8.5, leading=12, textColor=C_RED,
    fontName="Helvetica-Bold", leftIndent=10, spaceAfter=3)

S_TH = sty("TH",
    fontSize=8.5, leading=11, textColor=C_WHITE,
    fontName="Helvetica-Bold", alignment=TA_CENTER)

S_TD = sty("TD",
    fontSize=8.5, leading=11, textColor=C_BLACK,
    fontName="Helvetica", alignment=TA_LEFT)

S_TD_C = sty("TDC",
    fontSize=8.5, leading=11, textColor=C_BLACK,
    fontName="Helvetica", alignment=TA_CENTER)

S_TD_CODE = sty("TDCode",
    fontSize=7.5, leading=10, textColor=colors.HexColor("#1A237E"),
    fontName="Courier", alignment=TA_LEFT)

def HR():
    return HRFlowable(width="100%", thickness=1,
                      color=C_BORDER, spaceAfter=6, spaceBefore=2)

def SP(h=6):
    return Spacer(1, h)

def h1(t): return Paragraph(t, S_H1)
def h2(t): return Paragraph(t, S_H2)
def h3(t): return Paragraph(t, S_H3)
def body(t): return Paragraph(t, S_BODY)
def note(t): return Paragraph(f"ℹ  {t}", S_NOTE)
def warn(t): return Paragraph(f"⚠  {t}", S_WARN)
def bullet(t): return Paragraph(f"• {t}", S_BULLET)
def code(t): return Paragraph(t.replace("\n","<br/>").replace(" ","&nbsp;"), S_CODE)

def tbl(data, col_widths, header_rows=1, row_colors=None):
    t = Table(data, colWidths=col_widths, repeatRows=header_rows)
    style = [
        ("BACKGROUND", (0,0), (-1, header_rows-1), C_PRIMARY),
        ("TEXTCOLOR",  (0,0), (-1, header_rows-1), C_WHITE),
        ("FONTNAME",   (0,0), (-1, header_rows-1), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS", (0, header_rows), (-1,-1),
         [C_WHITE, C_LIGHT]),
        ("GRID",       (0,0), (-1,-1), 0.4, C_BORDER),
        ("VALIGN",     (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING",(0,0), (-1,-1), 5),
        ("RIGHTPADDING",(0,0),(-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
    ]
    if row_colors:
        for row_idx, color in row_colors:
            style.append(("BACKGROUND", (0, row_idx), (-1, row_idx), color))
    t.setStyle(TableStyle(style))
    return t

def section_box(title, color=C_ACCENT):
    data = [[Paragraph(title, sty("BT", fontSize=11, leading=14,
             textColor=C_WHITE, fontName="Helvetica-Bold"))]]
    t = Table(data, colWidths=[W - 2*MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), color),
        ("LEFTPADDING",(0,0),(-1,-1), 10),
        ("TOPPADDING", (0,0),(-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return t


# ============================================================================
# CONTENT BUILDERS
# ============================================================================

def cover_page():
    elems = []
    # Full-bleed cover block via a table
    cover_data = [[
        Paragraph("PATCHCOURT", sty("CT", fontSize=38, leading=44,
            textColor=C_WHITE, fontName="Helvetica-Bold", alignment=TA_CENTER)),
    ]]
    ct = Table(cover_data, colWidths=[W - 2*MARGIN])
    ct.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), C_PRIMARY),
        ("TOPPADDING",(0,0),(-1,-1), 30),
        ("BOTTOMPADDING",(0,0),(-1,-1), 10),
    ]))
    elems.append(ct)
    elems.append(SP(4))

    sub_data = [[
        Paragraph("Multi-Agent Evidence-Tiered AI Code Review System",
            sty("CS", fontSize=14, leading=18, textColor=C_WHITE,
                fontName="Helvetica", alignment=TA_CENTER)),
    ]]
    st = Table(sub_data, colWidths=[W - 2*MARGIN])
    st.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), C_ACCENT),
        ("TOPPADDING",(0,0),(-1,-1), 10),
        ("BOTTOMPADDING",(0,0),(-1,-1), 10),
    ]))
    elems.append(st)
    elems.append(SP(20))

    elems.append(Paragraph("MASTER REFERENCE SHEET", sty("MR",
        fontSize=11, leading=14, textColor=C_MUTED,
        fontName="Helvetica-Bold", alignment=TA_CENTER)))
    elems.append(SP(6))

    meta = [
        ["Stack", "Python 3.12 · FastAPI · LangGraph · Next.js 15"],
        ["LLM Support", "Mock · OpenAI · Gemini · Claude · Ollama"],
        ["Tools", "Semgrep · Bandit · Gitleaks · Radon · SonarQube"],
        ["Infra", "Docker Compose · PostgreSQL · Redis · Qdrant"],
        ["Verdict", "MERGE | NEEDS_REVIEW | BLOCK"],
        ["Hard Rule", "BLOCK never rests on T5 (LLM-only) evidence alone"],
    ]
    mt = Table(
        [[Paragraph(r[0], sty("mk", fontSize=9, fontName="Helvetica-Bold",
                               textColor=C_PRIMARY)),
          Paragraph(r[1], sty("mv", fontSize=9, fontName="Helvetica",
                               textColor=C_BLACK))]
         for r in meta],
        colWidths=[4*cm, W - 2*MARGIN - 4*cm]
    )
    mt.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[C_LIGHT, C_WHITE]),
        ("GRID",(0,0),(-1,-1),0.4,C_BORDER),
        ("LEFTPADDING",(0,0),(-1,-1),8),
        ("TOPPADDING",(0,0),(-1,-1),5),
        ("BOTTOMPADDING",(0,0),(-1,-1),5),
    ]))
    elems.append(mt)
    elems.append(SP(20))
    elems.append(Paragraph(
        "Covers: Architecture · Pipeline · Evidence Tiers · Agents · Debate · Judge · "
        "Adjudication · QA-Checker · Taint Inference · SonarQube Baseline · "
        "Dashboard · API · Docker · Deployment · Troubleshooting · Research Basis",
        sty("toc", fontSize=8.5, leading=13, textColor=C_MUTED,
            fontName="Helvetica-Oblique", alignment=TA_CENTER)))
    elems.append(PageBreak())
    return elems


def sec1_overview():
    e = []
    e.append(h1("1. PROJECT OVERVIEW"))
    e.append(HR())
    e.append(body(
        "PatchCourt is a fully containerised, multi-agent AI system that reviews GitHub "
        "Pull Requests using <b>evidence-tiered reasoning</b>. Three specialist LLM agents "
        "(Security, Quality, Pragmatist) analyse a PR in parallel. Every claim is anchored "
        "to a trust tier (T1–T5) derived from static-analysis tools, repository policies, "
        "git precedent, or LLM reasoning. Disagreements trigger a bounded, retrieval-gated "
        "debate. A deterministic judge produces a final score and one of three verdicts."
    ))
    e.append(SP(6))

    e.append(h2("1.1 Core Design Principles"))
    principles = [
        ("Evidence-first", "Every claim must cite a tier. LLM reasoning alone (T5) can never force a BLOCK."),
        ("Deterministic judge", "Scoring is pure arithmetic — no LLM in the verdict path."),
        ("Sandboxed tools", "PR code runs inside an isolated Docker container (--network none)."),
        ("Offline-capable", "Full pipeline runs with zero credentials using mock LLM + synthetic scanner."),
        ("Pluggable LLM", "Switch provider at runtime via API — no container restart needed."),
        ("Audit trail", "Every review is persisted to PostgreSQL with full claim/evidence detail."),
    ]
    pt = Table(
        [[Paragraph(p[0], sty("pk", fontSize=9, fontName="Helvetica-Bold", textColor=C_ACCENT)),
          Paragraph(p[1], sty("pv", fontSize=9, fontName="Helvetica", textColor=C_BLACK))]
         for p in principles],
        colWidths=[3.5*cm, W - 2*MARGIN - 3.5*cm]
    )
    pt.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[C_LIGHT, C_WHITE]),
        ("GRID",(0,0),(-1,-1),0.4,C_BORDER),
        ("LEFTPADDING",(0,0),(-1,-1),7),
        ("TOPPADDING",(0,0),(-1,-1),4),
        ("BOTTOMPADDING",(0,0),(-1,-1),4),
    ]))
    e.append(pt)
    e.append(SP(8))

    e.append(h2("1.2 Verdict System"))
    vdata = [
        [Paragraph("Verdict", S_TH), Paragraph("Score Threshold", S_TH),
         Paragraph("Meaning", S_TH), Paragraph("Colour", S_TH)],
        [Paragraph("MERGE", sty("v1", fontSize=9, fontName="Helvetica-Bold",
                                 textColor=C_GREEN, alignment=TA_CENTER)),
         Paragraph("< 4.0", S_TD_C),
         Paragraph("No blocking issues found", S_TD),
         Paragraph("Green", sty("vc", fontSize=9, textColor=C_GREEN, alignment=TA_CENTER))],
        [Paragraph("NEEDS_REVIEW", sty("v2", fontSize=9, fontName="Helvetica-Bold",
                                        textColor=C_YELLOW, alignment=TA_CENTER)),
         Paragraph("4.0 – 9.99", S_TD_C),
         Paragraph("Issues present; human review required", S_TD),
         Paragraph("Amber", sty("vc2", fontSize=9, textColor=C_YELLOW, alignment=TA_CENTER))],
        [Paragraph("BLOCK", sty("v3", fontSize=9, fontName="Helvetica-Bold",
                                 textColor=C_RED, alignment=TA_CENTER)),
         Paragraph("≥ 10.0", S_TD_C),
         Paragraph("Critical issues; merge must be blocked", S_TD),
         Paragraph("Red", sty("vc3", fontSize=9, textColor=C_RED, alignment=TA_CENTER))],
    ]
    e.append(tbl(vdata, [3*cm, 3*cm, 8*cm, 2.5*cm]))
    e.append(note("BLOCK is downgraded to NEEDS_REVIEW if the score crosses the threshold "
                  "only via T5-only claims. This is enforced in judge/scoring.py and unit-tested."))
    e.append(PageBreak())
    return e


def sec2_architecture():
    e = []
    e.append(h1("2. ARCHITECTURE"))
    e.append(HR())

    e.append(h2("2.1 Five-Layer Stack"))
    layers = [
        ("L1 · Presentation", "CLI (python -m patchcourt) · FastAPI REST · Next.js 15 Dashboard"),
        ("L2 · Async & Persistence", "Celery workers · Redis broker · PostgreSQL audit trail"),
        ("L3 · Intelligence", "Security / Quality / Pragmatist agents · Conflict detector · Debate · Judge"),
        ("L4 · Evidence", "Evidence engine · Docker sandbox · Semgrep/Bandit/Gitleaks/Radon · Qdrant RAG"),
        ("L5 · Data & External", "GitHub REST API · LLM provider · .env config"),
    ]
    lt = Table(
        [[Paragraph(l[0], sty("lk", fontSize=9, fontName="Helvetica-Bold", textColor=C_WHITE)),
          Paragraph(l[1], sty("lv", fontSize=9, fontName="Helvetica", textColor=C_WHITE))]
         for l in layers],
        colWidths=[4.5*cm, W - 2*MARGIN - 4.5*cm]
    )
    lt.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[C_PRIMARY, colors.HexColor("#2E4F4F")]),
        ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#4A7070")),
        ("LEFTPADDING",(0,0),(-1,-1),8),
        ("TOPPADDING",(0,0),(-1,-1),5),
        ("BOTTOMPADDING",(0,0),(-1,-1),5),
    ]))
    e.append(lt)
    e.append(SP(10))

    e.append(h2("2.2 LangGraph Pipeline (graph.py)"))
    e.append(body(
        "The review pipeline is wired as a LangGraph StateGraph. Each node is an async "
        "function that reads from and writes to a shared GraphState TypedDict. "
        "Nodes run sequentially except the three agent nodes which run in parallel "
        "after adjudication."
    ))
    e.append(SP(4))

    pipeline = [
        [Paragraph("Node", S_TH), Paragraph("Input State Keys", S_TH),
         Paragraph("Output State Keys", S_TH), Paragraph("Notes", S_TH)],
        [Paragraph("ingest", S_TD_CODE), Paragraph("pr (empty)", S_TD),
         Paragraph("pr (populated)", S_TD),
         Paragraph("Skipped in demo/offline mode if pr already has file_contents", S_TD)],
        [Paragraph("rag", S_TD_CODE), Paragraph("pr", S_TD),
         Paragraph("rag_results", S_TD),
         Paragraph("Clears Qdrant, indexes PR files, queries top-8 chunks", S_TD)],
        [Paragraph("evidence", S_TD_CODE), Paragraph("pr, rag_results", S_TD),
         Paragraph("tool_claims, raw_findings", S_TD),
         Paragraph("Runs sandbox or local tools; normalizes findings to Claims", S_TD)],
        [Paragraph("adjudicate", S_TD_CODE), Paragraph("pr, raw_findings", S_TD),
         Paragraph("correlations, finding_assessments", S_TD),
         Paragraph("FindingValidator + taint inference (IRIS-inspired)", S_TD)],
        [Paragraph("security", S_TD_CODE), Paragraph("pr, rag_results, tool_claims", S_TD),
         Paragraph("security_claims", S_TD),
         Paragraph("SecurityAgent LLM call", S_TD)],
        [Paragraph("quality", S_TD_CODE), Paragraph("pr, rag_results, tool_claims", S_TD),
         Paragraph("quality_claims", S_TD),
         Paragraph("QualityAgent LLM call", S_TD)],
        [Paragraph("pragmatist", S_TD_CODE), Paragraph("pr, rag_results, tool_claims", S_TD),
         Paragraph("pragmatist_claims", S_TD),
         Paragraph("PragmatistAgent LLM call", S_TD)],
        [Paragraph("merge_all", S_TD_CODE), Paragraph("*_claims", S_TD),
         Paragraph("all_claims", S_TD),
         Paragraph("Merges tool + LLM claims; runs corroborate_claims()", S_TD)],
        [Paragraph("detect", S_TD_CODE), Paragraph("all_claims", S_TD),
         Paragraph("conflicts", S_TD),
         Paragraph("detect_conflicts() — routes to debate or judge", S_TD)],
        [Paragraph("debate", S_TD_CODE), Paragraph("conflicts, pr, finding_assessments", S_TD),
         Paragraph("debated_claims, finding_assessments", S_TD),
         Paragraph("≤2 rounds; QA-Checker runs after; mutates qa_verdict/qa_note", S_TD)],
        [Paragraph("judge", S_TD_CODE), Paragraph("all_claims, debated_claims, finding_assessments", S_TD),
         Paragraph("report (ReviewReport)", S_TD),
         Paragraph("Deterministic scoring; safe_verdict() enforces T5 rule", S_TD)],
    ]
    e.append(tbl(pipeline, [2.8*cm, 3.5*cm, 3.5*cm, 6.7*cm]))
    e.append(SP(8))

    e.append(h2("2.3 Module Layout"))
    modules = [
        ("patchcourt/agents/", "schemas.py (all Pydantic models) · base.py · security.py · quality.py · pragmatist.py"),
        ("patchcourt/ingest/", "github.py — fetch PR metadata, diff, raw file contents, base file contents"),
        ("patchcourt/rag/", "store.py — Qdrant chunking, indexing, query (real embeddings or hash fallback)"),
        ("patchcourt/evidence.py", "EvidenceEngine, normalize_findings(), corroborate_claims()"),
        ("patchcourt/tools/", "base.py · registry.py · semgrep/bandit/gitleaks/radon/synthetic adapters"),
        ("patchcourt/sandbox/", "runner.py — docker run --rm --network none per-scan container"),
        ("patchcourt/adjudication/", "validator.py · contextual.py · correlate.py · rules.py"),
        ("patchcourt/debate/", "conflict.py · debate.py — bounded retrieval-gated debate"),
        ("patchcourt/judge/", "scoring.py — claim_score(), safe_verdict(), build_report()"),
        ("patchcourt/baseline/", "sonarqube_baseline.py — fetch issues, on-demand scan, compare_findings()"),
        ("patchcourt/db/", "models.py · session.py · audit.py — SQLAlchemy PostgreSQL audit"),
        ("patchcourt/worker/", "tasks.py — Celery review_pr task"),
        ("patchcourt/api/", "app.py — all FastAPI endpoints · webhook.py"),
        ("patchcourt/qa_checker.py", "QA-Checker agent — validates debate conclusions (CodeAgent-inspired)"),
        ("patchcourt/taint.py", "IRIS-inspired taint inference — LLM-confirmed source/sink flows"),
        ("patchcourt/llm.py", "Provider dispatch: mock / openai / claude / gemini / ollama"),
        ("patchcourt/config.py", "Settings (pydantic) + TIER_WEIGHTS dict"),
        ("patchcourt/graph.py", "LangGraph StateGraph wiring — build_graph(), run_review()"),
        ("dashboard/src/", "Next.js 15 app — app/ · components/ · lib/"),
    ]
    mt = Table(
        [[Paragraph(m[0], sty("mk2", fontSize=8, fontName="Courier",
                               textColor=colors.HexColor("#1A237E"))),
          Paragraph(m[1], sty("mv2", fontSize=8.5, fontName="Helvetica",
                               textColor=C_BLACK))]
         for m in modules],
        colWidths=[5*cm, W - 2*MARGIN - 5*cm]
    )
    mt.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[C_LIGHT, C_WHITE]),
        ("GRID",(0,0),(-1,-1),0.4,C_BORDER),
        ("LEFTPADDING",(0,0),(-1,-1),6),
        ("TOPPADDING",(0,0),(-1,-1),3),
        ("BOTTOMPADDING",(0,0),(-1,-1),3),
    ]))
    e.append(mt)
    e.append(PageBreak())
    return e


def sec3_evidence():
    e = []
    e.append(h1("3. EVIDENCE TIERS & SCORING"))
    e.append(HR())

    e.append(h2("3.1 Evidence Tier Weights (config.py)"))
    tdata = [
        [Paragraph("Tier", S_TH), Paragraph("Weight", S_TH),
         Paragraph("Source", S_TH), Paragraph("Can Block Alone?", S_TH)],
        [Paragraph("T1", sty("t1", fontSize=9, fontName="Helvetica-Bold",
                              textColor=C_RED, alignment=TA_CENTER)),
         Paragraph("1.0", S_TD_C),
         Paragraph("Direct static-analysis tool flag with file:line", S_TD),
         Paragraph("YES", sty("y", fontSize=9, fontName="Helvetica-Bold",
                               textColor=C_GREEN, alignment=TA_CENTER))],
        [Paragraph("T2", sty("t2", fontSize=9, fontName="Helvetica-Bold",
                              textColor=C_ORANGE, alignment=TA_CENTER)),
         Paragraph("0.8", S_TD_C),
         Paragraph("Two independent tools agree on the same file:line (corroborated)", S_TD),
         Paragraph("YES", sty("y2", fontSize=9, fontName="Helvetica-Bold",
                               textColor=C_GREEN, alignment=TA_CENTER))],
        [Paragraph("T3", sty("t3", fontSize=9, fontName="Helvetica-Bold",
                              textColor=C_YELLOW, alignment=TA_CENTER)),
         Paragraph("0.5", S_TD_C),
         Paragraph("Retrieved from repository policy / coding standards (RAG)", S_TD),
         Paragraph("NO", sty("n3", fontSize=9, fontName="Helvetica-Bold",
                              textColor=C_MUTED, alignment=TA_CENTER))],
        [Paragraph("T4", sty("t4", fontSize=9, fontName="Helvetica-Bold",
                              textColor=C_BLUE, alignment=TA_CENTER)),
         Paragraph("0.4", S_TD_C),
         Paragraph("Git precedent — pattern from history / similar PRs (RAG)", S_TD),
         Paragraph("NO", sty("n4", fontSize=9, fontName="Helvetica-Bold",
                              textColor=C_MUTED, alignment=TA_CENTER))],
        [Paragraph("T5", sty("t5", fontSize=9, fontName="Helvetica-Bold",
                              textColor=C_MUTED, alignment=TA_CENTER)),
         Paragraph("0.1", S_TD_C),
         Paragraph("LLM reasoning only — no tool or policy backing", S_TD),
         Paragraph("NEVER", sty("n5", fontSize=9, fontName="Helvetica-Bold",
                                 textColor=C_RED, alignment=TA_CENTER))],
    ]
    e.append(tbl(tdata, [1.5*cm, 2*cm, 9*cm, 3*cm]))
    e.append(SP(8))

    e.append(h2("3.2 Scoring Formula (judge/scoring.py)"))
    e.append(body(
        "Each claim is scored independently then summed per file, then across all files:"
    ))
    e.append(SP(3))
    score_data = [[Paragraph(
        "score = severity × tier_weight × corroboration_factor × confidence × fault_multiplier",
        sty("sf", fontSize=10, fontName="Courier", textColor=C_CODE_FG,
            backColor=C_CODE_BG, alignment=TA_CENTER)
    )]]
    st = Table(score_data, colWidths=[W - 2*MARGIN])
    st.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), C_CODE_BG),
        ("TOPPADDING",(0,0),(-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("LEFTPADDING",(0,0),(-1,-1), 10),
    ]))
    e.append(st)
    e.append(SP(6))

    params = [
        [Paragraph("Parameter", S_TH), Paragraph("Range", S_TH), Paragraph("Description", S_TH)],
        [Paragraph("severity", S_TD_CODE), Paragraph("1–5", S_TD_C),
         Paragraph("1=info, 2=low, 3=medium, 4=high, 5=critical", S_TD)],
        [Paragraph("tier_weight", S_TD_CODE), Paragraph("0.1–1.0", S_TD_C),
         Paragraph("From TIER_WEIGHTS dict (T1=1.0 … T5=0.1)", S_TD)],
        [Paragraph("corroboration_factor", S_TD_CODE), Paragraph("1.0–1.75", S_TD_C),
         Paragraph("1.0 + 0.25 × (agents agreeing on same file). Max 1.75 with 3 agents.", S_TD)],
        [Paragraph("confidence", S_TD_CODE), Paragraph("0.0–1.0", S_TD_C),
         Paragraph("Agent-reported confidence in the claim", S_TD)],
        [Paragraph("fault_multiplier", S_TD_CODE), Paragraph("0.85–1.15", S_TD_C),
         Paragraph("±15% nudge for T1/T2 tool claims only. High-fault rules (SQL, shell, secrets) → 1.15; cosmetic → 0.85", S_TD)],
    ]
    e.append(tbl(params, [3.5*cm, 2*cm, W - 2*MARGIN - 5.5*cm]))
    e.append(SP(6))

    e.append(h2("3.3 Hard BLOCK Constraint"))
    e.append(body(
        "safe_verdict() in scoring.py computes two scores: overall_score (all claims) and "
        "non_t5_score (claims with at least one T1–T4 evidence item). "
        "If overall_score ≥ 10.0 but non_t5_score < 10.0, the verdict is downgraded from "
        "BLOCK to NEEDS_REVIEW. This is unit-tested in tests/test_judge.py."
    ))
    e.append(SP(6))

    e.append(h2("3.4 Adjudication Statuses (validator.py)"))
    adj = [
        [Paragraph("Status", S_TH), Paragraph("Meaning", S_TH), Paragraph("Typical Cause", S_TH)],
        [Paragraph("SUPPORTED", sty("s1", fontSize=9, fontName="Helvetica-Bold",
                                     textColor=C_GREEN)),
         Paragraph("Unsafe pattern independently reproduced on the flagged line", S_TD),
         Paragraph("danger pattern matched AND no safe pattern present", S_TD)],
        [Paragraph("CONTRADICTED", sty("s2", fontSize=9, fontName="Helvetica-Bold",
                                        textColor=C_RED)),
         Paragraph("Code already uses a safe pattern, or scanner match not reproducible", S_TD),
         Paragraph("safe pattern found on line, or rule not reproducible", S_TD)],
        [Paragraph("UNCERTAIN", sty("s3", fontSize=9, fontName="Helvetica-Bold",
                                     textColor=C_YELLOW)),
         Paragraph("Evidence insufficient; escalate for human review", S_TD),
         Paragraph("Rule uncatalogued, or corroborated but not reproduced", S_TD)],
        [Paragraph("OUT_OF_SCOPE", sty("s4", fontSize=9, fontName="Helvetica-Bold",
                                        textColor=C_MUTED)),
         Paragraph("Finding is outside the reviewed change", S_TD),
         Paragraph("File not in PR's changed_files set", S_TD)],
    ]
    e.append(tbl(adj, [3*cm, 7*cm, 6.5*cm]))
    e.append(SP(8))

    e.append(h2("3.5 Three Specialist Agents"))
    agents = [
        [Paragraph("Agent", S_TH), Paragraph("Focus", S_TH), Paragraph("Typical Claims", S_TH)],
        [Paragraph("SecurityAgent", sty("ag1", fontSize=9, fontName="Helvetica-Bold",
                                         textColor=C_RED)),
         Paragraph("Vulnerabilities, secrets, injection, unsafe deserialization", S_TD),
         Paragraph("SQL injection, hardcoded credentials, pickle.load(), shell=True", S_TD)],
        [Paragraph("QualityAgent", sty("ag2", fontSize=9, fontName="Helvetica-Bold",
                                        textColor=C_BLUE)),
         Paragraph("Code correctness, maintainability, complexity, dead code", S_TD),
         Paragraph("Unused variables, missing args, high cyclomatic complexity", S_TD)],
        [Paragraph("PragmatistAgent", sty("ag3", fontSize=9, fontName="Helvetica-Bold",
                                           textColor=C_GREEN)),
         Paragraph("Practical risk, deployment impact, real-world exploitability", S_TD),
         Paragraph("Risk-weighted severity, context-aware blocking recommendations", S_TD)],
    ]
    e.append(tbl(agents, [3.5*cm, 6*cm, 7*cm]))
    e.append(PageBreak())
    return e


def sec4_research():
    e = []
    e.append(h1("4. RESEARCH-BACKED FEATURES"))
    e.append(HR())
    e.append(body(
        "Five features were implemented from analysis of 8 research papers. "
        "Each is traceable to a specific paper and implemented in a specific module."
    ))
    e.append(SP(6))

    papers = [
        [Paragraph("Feature", S_TH), Paragraph("Paper Inspiration", S_TH),
         Paragraph("Module", S_TH), Paragraph("What It Does", S_TH)],
        [Paragraph("QA-Checker Agent", sty("f1", fontSize=9, fontName="Helvetica-Bold",
                                            textColor=C_ACCENT)),
         Paragraph("CodeAgent — autonomous communicative agents for code review", S_TD),
         Paragraph("patchcourt/qa_checker.py", S_TD_CODE),
         Paragraph("Validates debate conclusions: checks T5-only BLOCK, vague summaries, "
                   "empty arguments, evidence-tier inconsistencies. Mutates qa_verdict/qa_note.", S_TD)],
        [Paragraph("FP/FN Root Cause Tagging", sty("f2", fontSize=9, fontName="Helvetica-Bold",
                                                     textColor=C_ACCENT)),
         Paragraph("Empirical Study of False Negatives and Positives of Static Code Analyzers", S_TD),
         Paragraph("adjudication/validator.py", S_TD_CODE),
         Paragraph("7-category taxonomy (Flawed Rule Spec, Missing Cases, Unhandled Language "
                   "Features, etc.) tagged on every CONTRADICTED/UNCERTAIN assessment.", S_TD)],
        [Paragraph("Fault-Risk Weighting", sty("f3", fontSize=9, fontName="Helvetica-Bold",
                                                textColor=C_ACCENT)),
         Paragraph("Some SonarQube Issues have a Significant but Small Effect on Faults", S_TD),
         Paragraph("judge/scoring.py", S_TD_CODE),
         Paragraph("±15% nudge (_fault_multiplier) on T1/T2 tool claims only. "
                   "High-fault rules (SQL, shell, secrets) → 1.15×; cosmetic → 0.85×.", S_TD)],
        [Paragraph("LLM Taint Inference", sty("f4", fontSize=9, fontName="Helvetica-Bold",
                                               textColor=C_ACCENT)),
         Paragraph("IRIS — LLM-assisted taint specification inference", S_TD),
         Paragraph("patchcourt/taint.py", S_TD_CODE),
         Paragraph("4 taint specs (SQL/CMD/PATH/XSS). Pattern-based source/sink extraction "
                   "+ LLM confirmation. Returns FindingAssessment with tool='taint-inference'.", S_TD)],
        [Paragraph("PR Diff-Only Scan", sty("f5", fontSize=9, fontName="Helvetica-Bold",
                                             textColor=C_ACCENT)),
         Paragraph("Bugdar — bug detection focused on changed code", S_TD),
         Paragraph("api/app.py POST /api/baseline/diff", S_TD_CODE),
         Paragraph("Scans only changed files/lines. Filters issues to in_pr=True. "
                   "Faster than full scan for large repos.", S_TD)],
    ]
    e.append(tbl(papers, [3*cm, 4*cm, 3.5*cm, 6*cm]))
    e.append(SP(8))

    e.append(h2("4.1 QA-Checker Detail (qa_checker.py)"))
    checks = [
        ("_check_t5_block", "INCONSISTENT if debate concludes BLOCK but all evidence is T5. Patches verdict_summary."),
        ("_check_evidence_tier_consistency", "INCONSISTENT if severity ≥ 4 claim has only T5 evidence."),
        ("_check_rationale_vagueness", "NEEDS_REWORK if verdict_summary is empty or < 12 words of vague language."),
        ("_check_supporting_opposing_balance", "NEEDS_REWORK if either prosecution or defense argument is empty."),
        ("qa_check_assessment()", "Validates FindingAssessment: SUPPORTED needs T1/T2; CONTRADICTED needs rationale; block action only on SUPPORTED."),
    ]
    ct = Table(
        [[Paragraph(c[0], sty("ck", fontSize=8.5, fontName="Courier",
                               textColor=colors.HexColor("#1A237E"))),
          Paragraph(c[1], sty("cv", fontSize=8.5, fontName="Helvetica",
                               textColor=C_BLACK))]
         for c in checks],
        colWidths=[5*cm, W - 2*MARGIN - 5*cm]
    )
    ct.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[C_LIGHT, C_WHITE]),
        ("GRID",(0,0),(-1,-1),0.4,C_BORDER),
        ("LEFTPADDING",(0,0),(-1,-1),6),
        ("TOPPADDING",(0,0),(-1,-1),3),
        ("BOTTOMPADDING",(0,0),(-1,-1),3),
    ]))
    e.append(ct)
    e.append(SP(8))

    e.append(h2("4.2 Taint Inference Detail (taint.py)"))
    tspecs = [
        [Paragraph("Spec ID", S_TH), Paragraph("CWE", S_TH),
         Paragraph("Source Patterns", S_TH), Paragraph("Sink Patterns", S_TH)],
        [Paragraph("TAINT-SQL", S_TD_CODE), Paragraph("CWE-89", S_TD_C),
         Paragraph("request.args/form/json, input(), sys.argv, os.environ", S_TD),
         Paragraph("execute/query/cursor(... +, f-string SELECT, string + SELECT", S_TD)],
        [Paragraph("TAINT-CMD", S_TD_CODE), Paragraph("CWE-78", S_TD_C),
         Paragraph("request.*, input(), sys.argv", S_TD),
         Paragraph("subprocess.call/run/Popen, os.system/popen, eval()", S_TD)],
        [Paragraph("TAINT-PATH", S_TD_CODE), Paragraph("CWE-22", S_TD_C),
         Paragraph("request.*, input()", S_TD),
         Paragraph("open(), os.path.join/exists, pathlib.Path", S_TD)],
        [Paragraph("TAINT-XSS", S_TD_CODE), Paragraph("CWE-79", S_TD_C),
         Paragraph("request.*", S_TD),
         Paragraph("render_template_string, Markup(), innerHTML=, document.write()", S_TD)],
    ]
    e.append(tbl(tspecs, [2.5*cm, 2*cm, 5.5*cm, 6.5*cm]))
    e.append(note(
        "Flows are only flagged if source and sink are within 50 lines (same-function heuristic). "
        "LLM confirmation is skipped in mock mode; pattern-based detection is used instead. "
        "Confidence threshold: 0.4 minimum to emit a FindingAssessment."
    ))
    e.append(PageBreak())
    return e


def sec5_deployment():
    e = []
    e.append(h1("5. DEPLOYMENT"))
    e.append(HR())

    e.append(h2("5.1 Container Inventory"))
    containers = [
        [Paragraph("Container", S_TH), Paragraph("Image", S_TH),
         Paragraph("Port", S_TH), Paragraph("Role", S_TH)],
        [Paragraph("patchcourt-api-1", S_TD_CODE),
         Paragraph("patchcourt-api:latest\n(python:3.12-slim)", S_TD),
         Paragraph("8000", S_TD_C),
         Paragraph("FastAPI backend, LangGraph pipeline, sandbox orchestration", S_TD)],
        [Paragraph("patchcourt-dashboard-1", S_TD_CODE),
         Paragraph("patchcourt-dashboard:latest\n(node:22-alpine)", S_TD),
         Paragraph("3001→3000", S_TD_C),
         Paragraph("Next.js 15 frontend dashboard", S_TD)],
        [Paragraph("patchcourt-postgres-1", S_TD_CODE),
         Paragraph("postgres:16-alpine", S_TD),
         Paragraph("5432 (internal)", S_TD_C),
         Paragraph("Audit log persistence (SQLAlchemy)", S_TD)],
        [Paragraph("patchcourt-redis-1", S_TD_CODE),
         Paragraph("redis:7-alpine", S_TD),
         Paragraph("6379 (internal)", S_TD_C),
         Paragraph("Celery task broker", S_TD)],
        [Paragraph("patchcourt-qdrant-1", S_TD_CODE),
         Paragraph("qdrant/qdrant:latest", S_TD),
         Paragraph("16333→6333", S_TD_C),
         Paragraph("RAG vector store for policy/precedent retrieval", S_TD)],
        [Paragraph("patchcourt-worker-1", S_TD_CODE),
         Paragraph("patchcourt-api:latest", S_TD),
         Paragraph("— (profile: worker)", S_TD_C),
         Paragraph("Celery async worker for webhook-triggered reviews", S_TD)],
        [Paragraph("patchcourt-sonar-\nsonarqube-1", S_TD_CODE),
         Paragraph("sonarqube:community\n(docker-compose.sonar.yml)", S_TD),
         Paragraph("9000", S_TD_C),
         Paragraph("Static analysis baseline; embedded H2 DB", S_TD)],
        [Paragraph("patchcourt-sandbox\n(build-only)", S_TD_CODE),
         Paragraph("patchcourt-sandbox:latest\n(python:3.12-slim)", S_TD),
         Paragraph("— (profile: tools)", S_TD_C),
         Paragraph("Semgrep + Bandit + Gitleaks + Radon. Spawned per-scan via docker run --rm", S_TD)],
    ]
    e.append(tbl(containers, [3.5*cm, 3.5*cm, 2.5*cm, 7*cm]))
    e.append(SP(8))

    e.append(h2("5.2 Docker Deployment Commands"))
    cmds = [
        ("Build all images", "docker compose build\ndocker compose build sandbox\ndocker compose -f docker-compose.sonar.yml build"),
        ("Start core stack", "docker compose up -d"),
        ("Start with dashboard + worker", "docker compose --profile dashboard --profile worker up -d"),
        ("Start SonarQube", "docker compose -f docker-compose.sonar.yml up -d"),
        ("Connect API to SonarQube network\n(required after every restart)", "docker network connect patchcourt-sonar_default patchcourt-api-1"),
        ("Check health", "curl http://localhost:8000/health\ncurl http://localhost:8000/api/sonar/health"),
        ("Run demo review", "curl -X POST http://localhost:8000/api/review/demo"),
        ("View API logs", "docker logs patchcourt-api-1 --tail 50"),
        ("Rebuild single service", "docker compose build api\ndocker compose up -d api"),
    ]
    for label, cmd in cmds:
        row_data = [[
            Paragraph(label, sty("cl", fontSize=8.5, fontName="Helvetica-Bold",
                                  textColor=C_PRIMARY)),
            Paragraph(cmd.replace("\n","<br/>").replace(" ","&nbsp;"),
                      sty("cc", fontSize=8, fontName="Courier",
                          textColor=C_CODE_FG, backColor=C_CODE_BG)),
        ]]
        rt = Table(row_data, colWidths=[4.5*cm, W - 2*MARGIN - 4.5*cm])
        rt.setStyle(TableStyle([
            ("GRID",(0,0),(-1,-1),0.4,C_BORDER),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("LEFTPADDING",(0,0),(-1,-1),6),
            ("TOPPADDING",(0,0),(-1,-1),4),
            ("BOTTOMPADDING",(0,0),(-1,-1),4),
            ("BACKGROUND",(0,0),(0,-1),C_LIGHT),
            ("BACKGROUND",(1,0),(1,-1),C_CODE_BG),
        ]))
        e.append(rt)
    e.append(SP(8))

    e.append(h2("5.3 Network Architecture"))
    e.append(body(
        "Two Docker bridge networks are used. The API container must be manually joined "
        "to the SonarQube network after each restart because the two stacks are managed "
        "by separate compose files."
    ))
    nets = [
        [Paragraph("Network", S_TH), Paragraph("Members", S_TH), Paragraph("Purpose", S_TH)],
        [Paragraph("patchcourt_default", S_TD_CODE),
         Paragraph("api, dashboard, postgres, redis, qdrant, worker", S_TD),
         Paragraph("Internal service communication", S_TD)],
        [Paragraph("patchcourt-sonar_default", S_TD_CODE),
         Paragraph("sonarqube, api (manually joined)", S_TD),
         Paragraph("SonarQube baseline access from API container", S_TD)],
    ]
    e.append(tbl(nets, [4.5*cm, 6*cm, 6*cm]))
    e.append(SP(4))
    e.append(note(
        "The sonar-scanner-cli sibling container cannot reach SonarQube via 'localhost'. "
        "_scanner_host_url() rewrites the URL to host.docker.internal so the scanner "
        "container reaches the host-mapped port 9000."
    ))
    e.append(SP(6))

    e.append(h2("5.4 Storage Volumes"))
    vols = [
        [Paragraph("Volume / Path", S_TH), Paragraph("Type", S_TH),
         Paragraph("Contents", S_TH), Paragraph("Size", S_TH)],
        [Paragraph("pgdata", S_TD_CODE), Paragraph("Named volume", S_TD),
         Paragraph("PostgreSQL audit log", S_TD), Paragraph("~50 MB", S_TD_C)],
        [Paragraph("redisdata", S_TD_CODE), Paragraph("Named volume", S_TD),
         Paragraph("Celery task queue, transient job state", S_TD), Paragraph("~10 MB", S_TD_C)],
        [Paragraph("qdrantdata", S_TD_CODE), Paragraph("Named volume", S_TD),
         Paragraph("RAG vector embeddings of policy documents", S_TD), Paragraph("~20 MB", S_TD_C)],
        [Paragraph("sonardata/logs/extensions", S_TD_CODE), Paragraph("Named volumes", S_TD),
         Paragraph("SonarQube embedded H2 DB, scan results, plugins", S_TD), Paragraph("500 MB–1 GB", S_TD_C)],
        [Paragraph("./reports → /app/reports", S_TD_CODE), Paragraph("Host bind-mount", S_TD),
         Paragraph("JSON + Markdown baseline reports, benchmark results", S_TD), Paragraph("~1 MB/scan", S_TD_C)],
        [Paragraph("./.sandbox → container path", S_TD_CODE), Paragraph("Host bind-mount", S_TD),
         Paragraph("Temp scan workdirs for sonar-scanner-cli. Deleted after scan.", S_TD), Paragraph("Transient", S_TD_C)],
    ]
    e.append(tbl(vols, [4.5*cm, 2.5*cm, 6.5*cm, 2.5*cm]))
    e.append(PageBreak())
    return e


def sec5_deployment():
    e = []
    e.append(h1("5. DEPLOYMENT"))
    e.append(HR())

    e.append(h2("5.1 Container Inventory"))
    containers = [
        [Paragraph("Container", S_TH), Paragraph("Image", S_TH),
         Paragraph("Port", S_TH), Paragraph("Role", S_TH)],
        [Paragraph("patchcourt-api-1", S_TD_CODE), Paragraph("patchcourt-api:latest (python:3.12-slim)", S_TD),
         Paragraph("8000", S_TD_C), Paragraph("FastAPI backend, LangGraph pipeline, sandbox orchestration", S_TD)],
        [Paragraph("patchcourt-dashboard-1", S_TD_CODE), Paragraph("patchcourt-dashboard:latest (node:22-alpine)", S_TD),
         Paragraph("3001→3000", S_TD_C), Paragraph("Next.js 15 frontend dashboard", S_TD)],
        [Paragraph("patchcourt-postgres-1", S_TD_CODE), Paragraph("postgres:16-alpine", S_TD),
         Paragraph("5432 (internal)", S_TD_C), Paragraph("Audit log persistence (SQLAlchemy)", S_TD)],
        [Paragraph("patchcourt-redis-1", S_TD_CODE), Paragraph("redis:7-alpine", S_TD),
         Paragraph("6379 (internal)", S_TD_C), Paragraph("Celery task broker", S_TD)],
        [Paragraph("patchcourt-qdrant-1", S_TD_CODE), Paragraph("qdrant/qdrant:latest", S_TD),
         Paragraph("16333→6333", S_TD_C), Paragraph("RAG vector store for policy/precedent retrieval", S_TD)],
        [Paragraph("patchcourt-worker-1", S_TD_CODE), Paragraph("patchcourt-api:latest", S_TD),
         Paragraph("— (profile: worker)", S_TD_C), Paragraph("Celery async worker for webhook-triggered reviews", S_TD)],
        [Paragraph("patchcourt-sonar-sonarqube-1", S_TD_CODE), Paragraph("sonarqube:community", S_TD),
         Paragraph("9000", S_TD_C), Paragraph("Static analysis baseline; embedded H2 DB", S_TD)],
        [Paragraph("patchcourt-sandbox (build-only)", S_TD_CODE), Paragraph("patchcourt-sandbox:latest", S_TD),
         Paragraph("— (profile: tools)", S_TD_C), Paragraph("Semgrep+Bandit+Gitleaks+Radon. Spawned per-scan via docker run --rm", S_TD)],
    ]
    e.append(tbl(containers, [3.8*cm, 3.8*cm, 2.4*cm, 6.5*cm]))
    e.append(SP(8))

    e.append(h2("5.2 Docker Deployment Commands"))
    cmds = [
        ("Build all images", "docker compose build && docker compose build sandbox"),
        ("Start core stack", "docker compose up -d"),
        ("Start with dashboard + worker", "docker compose --profile dashboard --profile worker up -d"),
        ("Start SonarQube", "docker compose -f docker-compose.sonar.yml up -d"),
        ("Connect API to SonarQube network (after every restart)",
         "docker network connect patchcourt-sonar_default patchcourt-api-1"),
        ("Check health", "curl http://localhost:8000/health"),
        ("Run demo review", "curl -X POST http://localhost:8000/api/review/demo"),
        ("Rebuild single service", "docker compose build api && docker compose up -d api"),
        ("View API logs", "docker logs patchcourt-api-1 --tail 50"),
    ]
    cmd_data = [[Paragraph("Action", S_TH), Paragraph("Command", S_TH)]]
    for label, cmd in cmds:
        cmd_data.append([
            Paragraph(label, sty("cl", fontSize=8.5, fontName="Helvetica-Bold", textColor=C_PRIMARY)),
            Paragraph(cmd.replace(" ", "&nbsp;"), sty("cc", fontSize=8, fontName="Courier",
                      textColor=C_CODE_FG, backColor=C_CODE_BG)),
        ])
    e.append(tbl(cmd_data, [5*cm, W - 2*MARGIN - 5*cm]))
    e.append(SP(8))

    e.append(h2("5.3 Network Architecture"))
    nets = [
        [Paragraph("Network", S_TH), Paragraph("Members", S_TH), Paragraph("Purpose", S_TH)],
        [Paragraph("patchcourt_default", S_TD_CODE),
         Paragraph("api, dashboard, postgres, redis, qdrant, worker", S_TD),
         Paragraph("Internal service communication", S_TD)],
        [Paragraph("patchcourt-sonar_default", S_TD_CODE),
         Paragraph("sonarqube, api (manually joined)", S_TD),
         Paragraph("SonarQube baseline access from API container", S_TD)],
    ]
    e.append(tbl(nets, [4.5*cm, 6*cm, 6*cm]))
    e.append(note(
        "The sonar-scanner-cli sibling container cannot reach SonarQube via localhost. "
        "_scanner_host_url() rewrites the URL to host.docker.internal so the scanner "
        "container reaches the host-mapped port 9000."
    ))
    e.append(SP(6))

    e.append(h2("5.4 Storage Volumes"))
    vols = [
        [Paragraph("Volume / Path", S_TH), Paragraph("Type", S_TH),
         Paragraph("Contents", S_TH), Paragraph("Size", S_TH)],
        [Paragraph("pgdata", S_TD_CODE), Paragraph("Named volume", S_TD),
         Paragraph("PostgreSQL audit log", S_TD), Paragraph("~50 MB", S_TD_C)],
        [Paragraph("redisdata", S_TD_CODE), Paragraph("Named volume", S_TD),
         Paragraph("Celery task queue, transient job state", S_TD), Paragraph("~10 MB", S_TD_C)],
        [Paragraph("qdrantdata", S_TD_CODE), Paragraph("Named volume", S_TD),
         Paragraph("RAG vector embeddings of policy documents", S_TD), Paragraph("~20 MB", S_TD_C)],
        [Paragraph("sonardata/logs/extensions", S_TD_CODE), Paragraph("Named volumes", S_TD),
         Paragraph("SonarQube embedded H2 DB, scan results, plugins", S_TD), Paragraph("500MB-1GB", S_TD_C)],
        [Paragraph("./reports → /app/reports", S_TD_CODE), Paragraph("Host bind-mount", S_TD),
         Paragraph("JSON + Markdown baseline reports, benchmark results", S_TD), Paragraph("~1 MB/scan", S_TD_C)],
        [Paragraph("./.sandbox → container path", S_TD_CODE), Paragraph("Host bind-mount", S_TD),
         Paragraph("Temp scan workdirs for sonar-scanner-cli. Deleted after scan.", S_TD), Paragraph("Transient", S_TD_C)],
    ]
    e.append(tbl(vols, [4.5*cm, 2.5*cm, 6.5*cm, 2.5*cm]))
    e.append(PageBreak())
    return e


def sec6_api():
    e = []
    e.append(h1("6. API REFERENCE"))
    e.append(HR())
    e.append(body("All endpoints are served by FastAPI on port 8000. CORS is open (*). "
                  "Errors return {\"detail\": {\"category\": \"...\", \"message\": \"...\"}} with HTTP 4xx/502."))
    e.append(SP(6))

    endpoints = [
        [Paragraph("Method + Path", S_TH), Paragraph("Body / Params", S_TH),
         Paragraph("Returns", S_TH), Paragraph("Notes", S_TH)],
        [Paragraph("POST /api/review", S_TD_CODE),
         Paragraph("{pr_url}", S_TD_CODE),
         Paragraph("ReviewReport (full)", S_TD),
         Paragraph("Full pipeline: ingest→rag→evidence→agents→debate→judge. Saves audit to PG.", S_TD)],
        [Paragraph("POST /api/review/demo", S_TD_CODE),
         Paragraph("(none)", S_TD_CODE),
         Paragraph("ReviewReport (demo)", S_TD),
         Paragraph("Offline demo with synthetic PR. Forces mock LLM. Restores provider after.", S_TD)],
        [Paragraph("GET /api/baseline/latest", S_TD_CODE),
         Paragraph("(none)", S_TD_CODE),
         Paragraph("BaselineReport JSON", S_TD),
         Paragraph("Returns newest ./reports/baseline-*.json by mtime. No live SonarQube needed.", S_TD)],
        [Paragraph("POST /api/baseline", S_TD_CODE),
         Paragraph("{pr_url}", S_TD_CODE),
         Paragraph("BaselineReport + patchcourt comparison", S_TD),
         Paragraph("Fetches PR, runs on-demand SonarQube scan, runs full PatchCourt review, reconciles.", S_TD)],
        [Paragraph("POST /api/baseline/diff", S_TD_CODE),
         Paragraph("{pr_url}", S_TD_CODE),
         Paragraph("BaselineReport (diff-only)", S_TD),
         Paragraph("Scans only changed files/lines. Faster. Includes taint inference.", S_TD)],
        [Paragraph("GET /api/comparison/demo", S_TD_CODE),
         Paragraph("(none)", S_TD_CODE),
         Paragraph("Demo comparison payload", S_TD),
         Paragraph("Returns pre-built demo comparison data for the comparison tab.", S_TD)],
        [Paragraph("POST /api/benchmark/run", S_TD_CODE),
         Paragraph("(none)", S_TD_CODE),
         Paragraph("Benchmark result", S_TD),
         Paragraph("Runs labeled finding-adjudication benchmark and saves result.", S_TD)],
        [Paragraph("GET /api/benchmark/latest", S_TD_CODE),
         Paragraph("(none)", S_TD_CODE),
         Paragraph("Latest benchmark JSON", S_TD),
         Paragraph("Returns newest saved benchmark result from ./reports/benchmark-latest.json.", S_TD)],
        [Paragraph("GET /api/sonar/health", S_TD_CODE),
         Paragraph("(none)", S_TD_CODE),
         Paragraph("{available, status}", S_TD),
         Paragraph("Checks if SonarQube is reachable at SONAR_URL.", S_TD)],
        [Paragraph("GET /api/sonar/quality-gate", S_TD_CODE),
         Paragraph("?component=", S_TD_CODE),
         Paragraph("Quality gate status", S_TD),
         Paragraph("Uses configured project by default; pass component= for on-demand PR project.", S_TD)],
        [Paragraph("GET /api/sonar/measures", S_TD_CODE),
         Paragraph("?component=", S_TD_CODE),
         Paragraph("Component metrics", S_TD),
         Paragraph("Coverage, duplications, code smells, bugs, vulnerabilities.", S_TD)],
        [Paragraph("GET /api/sonar/issues", S_TD_CODE),
         Paragraph("?page=&page_size=&component=", S_TD_CODE),
         Paragraph("Paginated issues", S_TD),
         Paragraph("Paginated issue search. Pass component= for PR-specific project.", S_TD)],
        [Paragraph("GET /api/settings/llm", S_TD_CODE),
         Paragraph("(none)", S_TD_CODE),
         Paragraph("LLMSettingsResponse", S_TD),
         Paragraph("Current effective LLM settings (runtime overrides env).", S_TD)],
        [Paragraph("POST /api/settings/llm", S_TD_CODE),
         Paragraph("{provider, model, api_key, base_url, use_mock_llm}", S_TD_CODE),
         Paragraph("LLMSettingsResponse", S_TD),
         Paragraph("Update LLM settings at runtime. Re-initializes LLM client. No restart needed.", S_TD)],
        [Paragraph("POST /api/settings/llm/test", S_TD_CODE),
         Paragraph("(none)", S_TD_CODE),
         Paragraph("{ok, detail}", S_TD),
         Paragraph("Tests current LLM provider connection with a minimal generate call.", S_TD)],
        [Paragraph("POST /api/webhook/github", S_TD_CODE),
         Paragraph("GitHub webhook payload", S_TD_CODE),
         Paragraph("202 Accepted", S_TD),
         Paragraph("Enqueues review_pr Celery task. Returns 503 if REDIS_URL unset.", S_TD)],
        [Paragraph("GET /health", S_TD_CODE),
         Paragraph("(none)", S_TD_CODE),
         Paragraph("{status: ok}", S_TD),
         Paragraph("Liveness probe.", S_TD)],
    ]
    e.append(tbl(endpoints, [3.8*cm, 3.2*cm, 3*cm, 6.5*cm]))
    e.append(SP(8))

    e.append(h2("6.1 Error Category Reference"))
    errs = [
        [Paragraph("Category", S_TH), Paragraph("HTTP", S_TH), Paragraph("Cause", S_TH)],
        [Paragraph("llm_quota_exhausted", S_TD_CODE), Paragraph("502", S_TD_C),
         Paragraph("Gemini/OpenAI 429 — daily/rate limit hit. Switch to mock or new key.", S_TD)],
        [Paragraph("llm_invalid_key", S_TD_CODE), Paragraph("502", S_TD_C),
         Paragraph("401 from LLM provider. Check key in Settings.", S_TD)],
        [Paragraph("llm_service_busy", S_TD_CODE), Paragraph("502", S_TD_C),
         Paragraph("503 from LLM provider. Retry in a moment.", S_TD)],
        [Paragraph("pr_not_found", S_TD_CODE), Paragraph("400", S_TD_C),
         Paragraph("GitHub 404 — PR URL invalid or repo private without token.", S_TD)],
        [Paragraph("github_unreachable", S_TD_CODE), Paragraph("502", S_TD_C),
         Paragraph("DNS/connection failure to api.github.com.", S_TD)],
        [Paragraph("sonar_offline", S_TD_CODE), Paragraph("502", S_TD_C),
         Paragraph("Cannot reach SonarQube. Check container and network connect.", S_TD)],
        [Paragraph("timeout", S_TD_CODE), Paragraph("502", S_TD_C),
         Paragraph("Request timed out (30s for GitHub, 600s for scanner).", S_TD)],
    ]
    e.append(tbl(errs, [4*cm, 1.5*cm, W - 2*MARGIN - 5.5*cm]))
    e.append(PageBreak())
    return e


def sec7_config():
    e = []
    e.append(h1("7. CONFIGURATION (.env)"))
    e.append(HR())
    e.append(body("Copy .env.example to .env. All variables are optional — the system runs "
                  "fully offline with no keys set (mock LLM + synthetic scanner)."))
    e.append(SP(6))

    cfg = [
        [Paragraph("Variable", S_TH), Paragraph("Default", S_TH),
         Paragraph("Purpose", S_TH)],
        [Paragraph("GITHUB_TOKEN", S_TD_CODE), Paragraph("(anonymous)", S_TD),
         Paragraph("GitHub API token. Without it: 60 req/hr rate limit, no private repos.", S_TD)],
        [Paragraph("LLM_PROVIDER", S_TD_CODE), Paragraph("mock", S_TD),
         Paragraph("mock | openai | claude | gemini | ollama", S_TD)],
        [Paragraph("LLM_API_KEY", S_TD_CODE), Paragraph("—", S_TD),
         Paragraph("API key for openai / claude / gemini providers.", S_TD)],
        [Paragraph("LLM_BASE_URL", S_TD_CODE), Paragraph("https://api.openai.com/v1", S_TD),
         Paragraph("Override endpoint for openai-compatible servers (vLLM, LM Studio, Ollama).", S_TD)],
        [Paragraph("LLM_MODEL", S_TD_CODE), Paragraph("gpt-4o", S_TD),
         Paragraph("Model name passed to the provider.", S_TD)],
        [Paragraph("USE_MOCK_LLM", S_TD_CODE), Paragraph("auto", S_TD),
         Paragraph("Force deterministic mock regardless of provider setting.", S_TD)],
        [Paragraph("PATCHCOURT_TOOLS", S_TD_CODE), Paragraph("semgrep,bandit,gitleaks,radon", S_TD),
         Paragraph("Comma-separated list of enabled static-analysis adapters.", S_TD)],
        [Paragraph("USE_SYNTHETIC_TOOLS", S_TD_CODE), Paragraph("false", S_TD),
         Paragraph("Add offline synthetic scanner (always produces demo findings).", S_TD)],
        [Paragraph("SANDBOX_ENABLED", S_TD_CODE), Paragraph("false", S_TD),
         Paragraph("Run tools inside Docker sandbox container (--network none).", S_TD)],
        [Paragraph("SANDBOX_IMAGE", S_TD_CODE), Paragraph("patchcourt-sandbox:latest", S_TD),
         Paragraph("Docker image for the sandbox runner.", S_TD)],
        [Paragraph("SANDBOX_WORKDIR", S_TD_CODE), Paragraph("(system tmp)", S_TD),
         Paragraph("Host path for per-scan workdirs. Must be visible to Docker daemon.", S_TD)],
        [Paragraph("QDRANT_URL", S_TD_CODE), Paragraph("(in-memory)", S_TD),
         Paragraph("Qdrant server URL. Empty = in-memory store (no persistence).", S_TD)],
        [Paragraph("QDRANT_COLLECTION", S_TD_CODE), Paragraph("patchcourt_chunks", S_TD),
         Paragraph("Qdrant collection name for RAG chunks.", S_TD)],
        [Paragraph("REDIS_URL", S_TD_CODE), Paragraph("(no async)", S_TD),
         Paragraph("Celery broker URL. Empty = webhook returns 503.", S_TD)],
        [Paragraph("DATABASE_URL", S_TD_CODE), Paragraph("(no audit)", S_TD),
         Paragraph("SQLAlchemy URL for audit trail. Empty = no persistence.", S_TD)],
        [Paragraph("SONAR_URL", S_TD_CODE), Paragraph("http://localhost:9000", S_TD),
         Paragraph("SonarQube server URL. Inside Docker: http://patchcourt-sonar-sonarqube-1:9000", S_TD)],
        [Paragraph("SONAR_TOKEN", S_TD_CODE), Paragraph("—", S_TD),
         Paragraph("SonarQube user token. Required for baseline scan and issue fetch.", S_TD)],
        [Paragraph("SONAR_COMPONENT", S_TD_CODE), Paragraph("patchcourt", S_TD),
         Paragraph("Default SonarQube project key for the live dashboard panels.", S_TD)],
    ]
    e.append(tbl(cfg, [4*cm, 3.5*cm, W - 2*MARGIN - 7.5*cm]))
    e.append(SP(8))

    e.append(h2("7.1 LLM Provider Quick Reference"))
    llms = [
        [Paragraph("Provider", S_TH), Paragraph("LLM_PROVIDER", S_TH),
         Paragraph("Needs", S_TH), Paragraph("Default Model", S_TH)],
        [Paragraph("Mock (offline)", S_TD), Paragraph("mock", S_TD_CODE),
         Paragraph("Nothing", S_TD), Paragraph("— (deterministic stub)", S_TD)],
        [Paragraph("OpenAI", S_TD), Paragraph("openai", S_TD_CODE),
         Paragraph("LLM_API_KEY", S_TD), Paragraph("gpt-4o", S_TD_CODE)],
        [Paragraph("Anthropic Claude", S_TD), Paragraph("claude", S_TD_CODE),
         Paragraph("LLM_API_KEY", S_TD), Paragraph("claude-3-5-sonnet-latest", S_TD_CODE)],
        [Paragraph("Google Gemini (free tier)", S_TD), Paragraph("gemini", S_TD_CODE),
         Paragraph("LLM_API_KEY (AI Studio)", S_TD), Paragraph("gemini-flash-latest", S_TD_CODE)],
        [Paragraph("Local Ollama", S_TD), Paragraph("ollama", S_TD_CODE),
         Paragraph("Running Ollama server", S_TD), Paragraph("llama3.1", S_TD_CODE)],
    ]
    e.append(tbl(llms, [3.5*cm, 3*cm, 4*cm, 6*cm]))
    e.append(note("LLM settings can be changed at runtime via POST /api/settings/llm — "
                  "no container restart needed. The dashboard Settings panel uses this endpoint."))
    e.append(PageBreak())
    return e


def sec8_sonarqube():
    e = []
    e.append(h1("8. SONARQUBE BASELINE"))
    e.append(HR())
    e.append(body(
        "The SonarQube baseline compares unresolved static-analysis issues against "
        "the files a GitHub PR actually changes. It runs an on-demand scan of the PR's "
        "changed files into a per-PR SonarQube project, then reconciles the results "
        "with PatchCourt's adjudication."
    ))
    e.append(SP(6))

    e.append(h2("8.1 On-Demand Scan Flow"))
    steps = [
        ("1. fetch_pr()", "Fetches PR metadata, diff, raw file contents, and base file contents from GitHub REST API."),
        ("2. project_key_for_pr()", "Generates a unique SonarQube project key: pr-{owner}-{repo}-{num} (lowercased, sanitized)."),
        ("3. run_ondemand_scan()", "Writes changed files to a temp workdir, runs sonarsource/sonar-scanner-cli:11 as a sibling container, waits for CE processing via _wait_for_ce()."),
        ("4. build_report()", "Fetches issues from SonarQube API, cross-references with PR changed files, marks each issue in_pr=True/False."),
        ("5. run_review()", "Runs full PatchCourt review on the same PR (agents + judge)."),
        ("6. compare_findings()", "Aligns SonarQube issues to FindingAssessments by file:line (fallback: file+rule). Groups into confirmed/contradicted/uncertain/unmatched."),
        ("7. write_report()", "Saves baseline-{owner}-{repo}-{num}-{ts}.json and .md to ./reports/."),
    ]
    for step, desc in steps:
        row = [[
            Paragraph(step, sty("sk", fontSize=8.5, fontName="Courier",
                                 textColor=C_ACCENT, backColor=C_LIGHT)),
            Paragraph(desc, sty("sv", fontSize=8.5, fontName="Helvetica", textColor=C_BLACK)),
        ]]
        rt = Table(row, colWidths=[3.5*cm, W - 2*MARGIN - 3.5*cm])
        rt.setStyle(TableStyle([
            ("GRID",(0,0),(-1,-1),0.4,C_BORDER),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("LEFTPADDING",(0,0),(-1,-1),6),
            ("TOPPADDING",(0,0),(-1,-1),4),
            ("BOTTOMPADDING",(0,0),(-1,-1),4),
            ("BACKGROUND",(0,0),(0,-1),C_LIGHT),
        ]))
        e.append(rt)
    e.append(SP(8))

    e.append(h2("8.2 Comparison Groups"))
    groups = [
        [Paragraph("Group", S_TH), Paragraph("Border Colour", S_TH), Paragraph("Meaning", S_TH)],
        [Paragraph("Confirmed / kept", sty("g1", fontSize=9, fontName="Helvetica-Bold", textColor=C_GREEN)),
         Paragraph("Green", sty("gc1", fontSize=9, textColor=C_GREEN, alignment=TA_CENTER)),
         Paragraph("SonarQube issue backed by a corroborated/tool PatchCourt claim on same file:line.", S_TD)],
        [Paragraph("Down-tiered / unbacked", sty("g2", fontSize=9, fontName="Helvetica-Bold", textColor=C_ORANGE)),
         Paragraph("Orange", sty("gc2", fontSize=9, textColor=C_ORANGE, alignment=TA_CENTER)),
         Paragraph("SonarQube issue with no PatchCourt support — likely false positive.", S_TD)],
        [Paragraph("Sonar-missed", sty("g3", fontSize=9, fontName="Helvetica-Bold", textColor=C_BLUE)),
         Paragraph("Primary (teal)", sty("gc3", fontSize=9, textColor=C_ACCENT, alignment=TA_CENTER)),
         Paragraph("Strong PatchCourt tool claim that SonarQube never reported.", S_TD)],
        [Paragraph("Contradicted", sty("g4", fontSize=9, fontName="Helvetica-Bold", textColor=C_RED)),
         Paragraph("Red", sty("gc4", fontSize=9, textColor=C_RED, alignment=TA_CENTER)),
         Paragraph("PatchCourt adjudication contradicts the SonarQube finding.", S_TD)],
        [Paragraph("Uncertain", sty("g5", fontSize=9, fontName="Helvetica-Bold", textColor=C_YELLOW)),
         Paragraph("Yellow", sty("gc5", fontSize=9, textColor=C_YELLOW, alignment=TA_CENTER)),
         Paragraph("Insufficient evidence; requires human review.", S_TD)],
        [Paragraph("Unmatched", sty("g6", fontSize=9, fontName="Helvetica-Bold", textColor=C_MUTED)),
         Paragraph("Zinc", sty("gc6", fontSize=9, textColor=C_MUTED, alignment=TA_CENTER)),
         Paragraph("No PatchCourt assessment matched this SonarQube issue.", S_TD)],
    ]
    e.append(tbl(groups, [3.5*cm, 2.5*cm, W - 2*MARGIN - 6*cm]))
    e.append(SP(6))

    e.append(h2("8.3 Key Implementation Notes"))
    e.append(bullet("All SonarQube findings carry provenance_tier=1 (T1) regardless of severity. "
                    "Severity is SonarQube's own judgement; tier describes evidence provenance."))
    e.append(bullet("The scanner image runs as uid 1000. The workdir is chmod 755 so it can read the bind-mounted files."))
    e.append(bullet("_wait_for_ce() polls /api/ce/component every 5s up to 300s to wait for SonarQube's async Compute Engine processing."))
    e.append(bullet("Per-PR project key format: pr-{owner}-{repo}-{num} — never collides with the main patchcourt project."))
    e.append(bullet("GET /api/baseline/latest reads the newest .json by mtime — no database index needed."))
    e.append(bullet("The dashboard Baseline tab loads the latest report on mount (no SonarQube needed). "
                    "Refresh baseline button calls POST /api/baseline (needs SonarQube running, ~2-3 min)."))
    e.append(PageBreak())
    return e


def sec9_dashboard():
    e = []
    e.append(h1("9. DASHBOARD (Next.js 15)"))
    e.append(HR())
    e.append(body("The dashboard runs on port 3001 (mapped 3001:3000). "
                  "NEXT_PUBLIC_API_BASE defaults to http://localhost:8000. "
                  "Built with shadcn/ui components, Tailwind CSS, and Lucide icons."))
    e.append(SP(6))

    e.append(h2("9.1 Tab Structure"))
    tabs = [
        [Paragraph("Tab / Route", S_TH), Paragraph("Component", S_TH), Paragraph("What It Shows", S_TH)],
        [Paragraph("Overview /", S_TD_CODE),
         Paragraph("app/page.tsx", S_TD_CODE),
         Paragraph("KPI cards (score, verdict, file count), verdict banner, submit PR URL, Offline Demo button.", S_TD)],
        [Paragraph("Evidence /evidence", S_TD_CODE),
         Paragraph("app/evidence/page.tsx", S_TD_CODE),
         Paragraph("Full evidence docket — all claims with tier badges, severity, corroboration pills, "
                   "agent labels. Filter/sort by tier, severity, agent.", S_TD)],
        [Paragraph("Debate /debate", S_TD_CODE),
         Paragraph("app/debate/page.tsx", S_TD_CODE),
         Paragraph("Debate transcripts — supporting/opposing arguments per conflict, "
                   "round count, verdict summary, code snippet.", S_TD)],
        [Paragraph("Baseline /baseline", S_TD_CODE),
         Paragraph("app/baseline/page.tsx + sonar-baseline-panel.tsx", S_TD_CODE),
         Paragraph("SonarQube baseline: severity breakdown, PatchCourt verdict, "
                   "confirmed/down-tiered/sonar-missed sections with border-left cards and code snippets.", S_TD)],
        [Paragraph("Comparison /comparison", S_TD_CODE),
         Paragraph("app/comparison/page.tsx", S_TD_CODE),
         Paragraph("Finding-by-finding adjudication: SonarQube issue vs PatchCourt assessment. "
                   "Fault-risk badge, QA badge, FP/FN root cause block, taint inference section.", S_TD)],
    ]
    e.append(tbl(tabs, [3.5*cm, 4*cm, 9*cm]))
    e.append(SP(8))

    e.append(h2("9.2 Key Frontend Files"))
    files = [
        ("lib/types.ts", "All TypeScript types: Report, FindingAssessmentView, BaselineReport, FindingComparison, etc."),
        ("lib/api.ts", "API client: submitReview, runDemo, runComparisonDemo, refreshBaseline, getSonarIssues, etc."),
        ("lib/review-context.tsx", "React context: report, phase, setReport, setPhase, setError. Shared across all tabs."),
        ("components/sonar-baseline-panel.tsx", "Baseline tab panel. Loads latest on mount. Refresh button calls POST /api/baseline."),
        ("components/layout-wrapper.tsx", "Sidebar nav + tab routing wrapper."),
        ("app/comparison/page.tsx", "Full comparison page: CodeSnippet, border-left finding cards, Load Demo button."),
    ]
    ft = Table(
        [[Paragraph(f[0], sty("fk", fontSize=8, fontName="Courier", textColor=colors.HexColor("#1A237E"))),
          Paragraph(f[1], sty("fv", fontSize=8.5, fontName="Helvetica", textColor=C_BLACK))]
         for f in files],
        colWidths=[5.5*cm, W - 2*MARGIN - 5.5*cm]
    )
    ft.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[C_LIGHT, C_WHITE]),
        ("GRID",(0,0),(-1,-1),0.4,C_BORDER),
        ("LEFTPADDING",(0,0),(-1,-1),6),
        ("TOPPADDING",(0,0),(-1,-1),3),
        ("BOTTOMPADDING",(0,0),(-1,-1),3),
    ]))
    e.append(ft)
    e.append(SP(8))

    e.append(h2("9.3 Comparison Tab — Special Features"))
    e.append(bullet("CodeSnippet component: renders numbered lines around the flagged line. "
                    "Arrow (→) marks the target line with yellow highlight background."))
    e.append(bullet("Load Demo button: calls GET /api/comparison/demo fresh every click, "
                    "wraps payload into Report shape, calls setReport(). Avoids stale baseline_report."))
    e.append(bullet("Fault-risk badge: colour-coded border badge (red=high, yellow=medium, zinc=low) "
                    "from fault_correlation field on FindingAssessment."))
    e.append(bullet("QA badge: shown only when qa_verdict != VALID (INCONSISTENT=red, NEEDS_REWORK=yellow)."))
    e.append(bullet("FP/FN root cause block: orange left-border block showing root cause category and explanation."))
    e.append(bullet("Taint inference section: purple border cards for tool='taint-inference' assessments. "
                    "Labelled 'LLM-Inferred Taint Flows — Scanner Missed'."))
    e.append(bullet("NEW IN PR badge: shown when introduced_by_pr=True on the FindingAssessment."))
    e.append(PageBreak())
    return e


def sec10_datamodels():
    e = []
    e.append(h1("10. DATA MODELS (agents/schemas.py)"))
    e.append(HR())

    e.append(h2("10.1 Core Pydantic Models"))
    models = [
        [Paragraph("Model", S_TH), Paragraph("Key Fields", S_TH), Paragraph("Used By", S_TH)],
        [Paragraph("Evidence", S_TD_CODE),
         Paragraph("tier: int (1-5), text: str", S_TD),
         Paragraph("Attached to every Claim and FindingAssessment", S_TD)],
        [Paragraph("Claim", S_TD_CODE),
         Paragraph("agent, issue, file, line, severity(1-5), evidence[], confidence, tier, corroborated, source('tool'|'llm')", S_TD),
         Paragraph("Output of all three agents; input to judge", S_TD)],
        [Paragraph("DebatedClaim", S_TD_CODE),
         Paragraph("claim: Claim, supporting, opposing, rounds, code_snippet, verdict_summary", S_TD),
         Paragraph("Output of debate stage; QA-Checker validates this", S_TD)],
        [Paragraph("FindingAssessment", S_TD_CODE),
         Paragraph("tool, file, line, rule, message, severity, category, status, rationale, "
                   "corroborated, corroborating_tools, policies[], contextual_priority, contextual_action, "
                   "evidence[], fp_fn_root_cause, fp_fn_explanation, fault_correlation, "
                   "qa_verdict, qa_note, code_snippet, introduced_by_pr, pre_existing", S_TD),
         Paragraph("Output of FindingValidator; displayed in baseline and comparison tabs", S_TD)],
        [Paragraph("ReviewReport", S_TD_CODE),
         Paragraph("pr_url, overall_score, verdict, files[], claims[], debate_transcripts[], "
                   "finding_assessments[], correlations[], contextual_summary, baseline_report", S_TD),
         Paragraph("Final output of run_review(); serialized to JSON by API", S_TD)],
        [Paragraph("PRContext", S_TD_CODE),
         Paragraph("owner, repo, pr_number, title, body, diff, changed_files[], "
                   "file_contents{}, base_file_contents{}, patches{}, rag_query", S_TD),
         Paragraph("Passed through entire pipeline; populated by ingest node", S_TD)],
        [Paragraph("CorrelationGroup", S_TD_CODE),
         Paragraph("file, line, tools[], findings[], relationship, severity_range, disputed", S_TD),
         Paragraph("Output of correlate_findings(); used by FindingValidator", S_TD)],
    ]
    e.append(tbl(models, [3.5*cm, 7.5*cm, 5.5*cm]))
    e.append(SP(8))

    e.append(h2("10.2 FindingAssessment — Extended Fields (Research Features)"))
    ext = [
        [Paragraph("Field", S_TH), Paragraph("Values", S_TH), Paragraph("Set By", S_TH)],
        [Paragraph("fp_fn_root_cause", S_TD_CODE),
         Paragraph("Flawed Rule Spec | Inconsistent Rule Implementation | Unhandled Language Features | "
                   "Missing Cases | Mishandling IR | Analysis Module Error | General Programming Error", S_TD),
         Paragraph("_fp_fn_root_cause() in validator.py", S_TD)],
        [Paragraph("fault_correlation", S_TD_CODE),
         Paragraph("high | medium | low", S_TD),
         Paragraph("_fault_correlation() in validator.py", S_TD)],
        [Paragraph("qa_verdict", S_TD_CODE),
         Paragraph("VALID | INCONSISTENT | NEEDS_REWORK", S_TD),
         Paragraph("run_qa_checks() in qa_checker.py", S_TD)],
        [Paragraph("introduced_by_pr", S_TD_CODE),
         Paragraph("True if flagged line is new in this PR", S_TD),
         Paragraph("_classify_finding() in validator.py (needs base_file_contents)", S_TD)],
        [Paragraph("code_snippet", S_TD_CODE),
         Paragraph("5-line context window with → marker on flagged line", S_TD),
         Paragraph("_code_snippet() in validator.py", S_TD)],
    ]
    e.append(tbl(ext, [3.5*cm, 7*cm, 6*cm]))
    e.append(PageBreak())
    return e


def sec11_troubleshooting():
    e = []
    e.append(h1("11. TROUBLESHOOTING"))
    e.append(HR())

    issues = [
        ("502 Bad Gateway on POST /api/baseline",
         "Root cause: fetch_pr() hits GitHub rate limit (60 req/hr unauthenticated), "
         "or run_review() inside baseline_compare fails (LLM quota, network).",
         "Set GITHUB_TOKEN in .env. Check docker logs patchcourt-api-1 for the actual exception category."),
        ("SonarQube baseline shows 0 issues",
         "The container's /app/reports has an old report from a different PR/component, "
         "or GET /api/baseline/latest returned a report before the on-demand scan completed.",
         "Click Refresh baseline with the correct PR URL. Wait ~2-3 min for scanner to finish."),
        ("Score shows inflated value (e.g. 1562%)",
         "_fault_multiplier was compounding with corroboration_factor (1.75x * 1.3x = ~2.3x). "
         "Fixed: fault_multiplier is now ±15% nudge only on T1/T2 tool claims.",
         "Verify scoring.py uses _FAULT_CORR_NUDGE = {high:1.15, medium:1.0, low:0.85}."),
        ("Comparison tab shows stale data",
         "report.baseline_report is set once when runDemo() runs POST /api/review/demo. "
         "Navigating to comparison tab just reads that stale value.",
         "Use the Load Demo button — it calls GET /api/comparison/demo fresh every click."),
        ("patchcourt-sonar-sonarqube-1 not reachable from API",
         "The two compose stacks (patchcourt and patchcourt-sonar) are on separate networks. "
         "The API container is not automatically joined to patchcourt-sonar_default.",
         "Run: docker network connect patchcourt-sonar_default patchcourt-api-1 (after every restart)"),
        ("sonar-scanner-cli cannot reach SonarQube",
         "The scanner runs as a sibling container and cannot use localhost or the container hostname.",
         "_scanner_host_url() rewrites the URL to host.docker.internal automatically. "
         "Verify SONAR_URL in .env does not use a hostname only resolvable inside the patchcourt network."),
        ("Dashboard shows blank / no data after restart",
         "The dashboard container was rebuilt but the API container still has old code, "
         "or the reports volume is empty.",
         "docker compose build api && docker compose up -d api. Then click Load Demo or Refresh baseline."),
        ("LLM quota exhausted (Gemini free tier)",
         "Gemini free tier has daily and per-minute rate limits.",
         "Switch to mock mode via Settings panel (POST /api/settings/llm {use_mock_llm: true}). "
         "Or use a different API key / provider."),
        ("Celery worker not processing webhooks",
         "REDIS_URL not set, or worker container not started.",
         "docker compose --profile worker up -d. Check docker logs patchcourt-worker-1."),
        ("Sandbox scan produces no findings",
         "SANDBOX_ENABLED=false (default), or sandbox image not built.",
         "docker compose build sandbox. Set SANDBOX_ENABLED=1 in .env."),
    ]

    for title, cause, fix in issues:
        block_data = [
            [Paragraph(title, sty("it", fontSize=9, fontName="Helvetica-Bold", textColor=C_PRIMARY))],
            [Paragraph(f"<b>Cause:</b> {cause}", sty("ic", fontSize=8.5, fontName="Helvetica", textColor=C_BLACK))],
            [Paragraph(f"<b>Fix:</b> {fix}", sty("if_", fontSize=8.5, fontName="Helvetica", textColor=C_GREEN))],
        ]
        bt = Table(block_data, colWidths=[W - 2*MARGIN])
        bt.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0), C_LIGHT),
            ("BACKGROUND",(0,1),(-1,1), C_WHITE),
            ("BACKGROUND",(0,2),(-1,2), colors.HexColor("#F1F8E9")),
            ("GRID",(0,0),(-1,-1),0.4,C_BORDER),
            ("LEFTPADDING",(0,0),(-1,-1),8),
            ("TOPPADDING",(0,0),(-1,-1),4),
            ("BOTTOMPADDING",(0,0),(-1,-1),4),
        ]))
        e.append(bt)
        e.append(SP(4))
    e.append(PageBreak())
    return e


def sec12_tests():
    e = []
    e.append(h1("12. TESTS"))
    e.append(HR())
    e.append(body("Run: pytest -q (from repo root). 51+ tests. asyncio_mode=auto."))
    e.append(SP(6))

    tests = [
        [Paragraph("Test File", S_TH), Paragraph("Covers", S_TH)],
        [Paragraph("test_judge.py", S_TD_CODE),
         Paragraph("Tier weights, scoring math, BLOCK-on-T5-alone rule, safe_verdict(), fault_multiplier", S_TD)],
        [Paragraph("test_validator.py", S_TD_CODE),
         Paragraph("FindingValidator: SUPPORTED/CONTRADICTED/UNCERTAIN/OUT_OF_SCOPE, fp_fn_root_cause, fault_correlation", S_TD)],
        [Paragraph("test_evidence.py", S_TD_CODE),
         Paragraph("EvidenceEngine, normalize_findings(), corroborate_claims(), tier assignment", S_TD)],
        [Paragraph("test_conflict.py", S_TD_CODE),
         Paragraph("detect_conflicts() — conflict gating logic", S_TD)],
        [Paragraph("test_debate_context.py", S_TD_CODE),
         Paragraph("Debate context building, retrieval-gated rebuttal", S_TD)],
        [Paragraph("test_baseline.py", S_TD_CODE),
         Paragraph("SonarQube baseline: compare_findings(), compare_with_review(), markdown()", S_TD)],
        [Paragraph("test_baseline_api.py", S_TD_CODE),
         Paragraph("POST /api/baseline endpoint integration", S_TD)],
        [Paragraph("test_comparison.py", S_TD_CODE),
         Paragraph("build_review_comparison(), finding comparison groups", S_TD)],
        [Paragraph("test_pipeline.py", S_TD_CODE),
         Paragraph("Offline end-to-end: real LangGraph + RAG + judge with fake LLM", S_TD)],
        [Paragraph("test_ingest.py", S_TD_CODE),
         Paragraph("parse_pr_url(), PR URL validation", S_TD)],
        [Paragraph("test_sandbox.py", S_TD_CODE),
         Paragraph("Sandbox graceful-skip when Docker unavailable", S_TD)],
        [Paragraph("test_audit.py", S_TD_CODE),
         Paragraph("PostgreSQL audit trail: store_audit(), model schema", S_TD)],
        [Paragraph("test_llm_providers.py", S_TD_CODE),
         Paragraph("LLM provider dispatch: mock/openai/claude/gemini/ollama", S_TD)],
        [Paragraph("test_llm_settings_api.py", S_TD_CODE),
         Paragraph("GET/POST /api/settings/llm runtime config endpoints", S_TD)],
        [Paragraph("test_benchmark.py / test_benchmark_api.py", S_TD_CODE),
         Paragraph("Adjudication benchmark runner and API endpoint", S_TD)],
        [Paragraph("test_contextual.py", S_TD_CODE),
         Paragraph("assess_context(), contextual_priority, contextual_action mapping", S_TD)],
        [Paragraph("test_correlation.py", S_TD_CODE),
         Paragraph("correlate_findings(), correlation_index(), corroborating_tools()", S_TD)],
        [Paragraph("test_rules.py", S_TD_CODE),
         Paragraph("rule_for(), category_for(), match_policies(), load_repository_policies()", S_TD)],
        [Paragraph("test_tiers.py", S_TD_CODE),
         Paragraph("TIER_WEIGHTS values, tier boundary conditions", S_TD)],
    ]
    e.append(tbl(tests, [5*cm, W - 2*MARGIN - 5*cm]))
    e.append(PageBreak())
    return e


def sec13_cheatsheet():
    e = []
    e.append(h1("13. QUICK-REFERENCE CHEATSHEET"))
    e.append(HR())

    e.append(h2("13.1 Full Startup Sequence (Clean State)"))
    startup = [
        "1.  git clone <repo> && cd patchcourt",
        "2.  cp .env.example .env   # add GITHUB_TOKEN, LLM_API_KEY, SONAR_TOKEN",
        "3.  docker compose build sandbox",
        "4.  docker compose -f docker-compose.sonar.yml up -d",
        "5.  docker compose --profile dashboard --profile worker up -d",
        "6.  docker network connect patchcourt-sonar_default patchcourt-api-1",
        "7.  curl http://localhost:8000/health   # → {status: ok}",
        "8.  curl http://localhost:8000/api/sonar/health   # → {available: true}",
        "9.  Open http://localhost:3001 in browser",
        "10. Click Load Demo or paste a GitHub PR URL",
    ]
    for s in startup:
        e.append(bullet(s))
    e.append(SP(8))

    e.append(h2("13.2 Git Remotes"))
    remotes = [
        [Paragraph("Remote", S_TH), Paragraph("URL", S_TH), Paragraph("Purpose", S_TH)],
        [Paragraph("mine", S_TD_CODE), Paragraph("github.com/Baalaa06/patchcourt1", S_TD),
         Paragraph("Personal fork — push feature branches here", S_TD)],
        [Paragraph("origin", S_TD_CODE), Paragraph("github.com/sakthiMurugan03/patchcourt", S_TD),
         Paragraph("Team upstream — PRs and demo PRs here", S_TD)],
    ]
    e.append(tbl(remotes, [2.5*cm, 6*cm, 8*cm]))
    e.append(SP(8))

    e.append(h2("13.3 Key Score Thresholds"))
    thresholds = [
        [Paragraph("Threshold", S_TH), Paragraph("Value", S_TH), Paragraph("Effect", S_TH)],
        [Paragraph("block_threshold", S_TD_CODE), Paragraph("10.0", S_TD_C),
         Paragraph("overall_score >= 10.0 → BLOCK (if non_t5_score also >= 10.0)", S_TD)],
        [Paragraph("needs_review_threshold", S_TD_CODE), Paragraph("4.0", S_TD_C),
         Paragraph("overall_score >= 4.0 → NEEDS_REVIEW", S_TD)],
        [Paragraph("debate_max_rounds", S_TD_CODE), Paragraph("2", S_TD_C),
         Paragraph("Maximum debate rounds per conflict", S_TD)],
        [Paragraph("taint confidence min", S_TD_CODE), Paragraph("0.4", S_TD_C),
         Paragraph("Minimum LLM confidence to emit a taint FindingAssessment", S_TD)],
        [Paragraph("taint flow max distance", S_TD_CODE), Paragraph("50 lines", S_TD_C),
         Paragraph("Source and sink must be within 50 lines (same-function heuristic)", S_TD)],
    ]
    e.append(tbl(thresholds, [4*cm, 2*cm, W - 2*MARGIN - 6*cm]))
    e.append(SP(8))

    e.append(h2("13.4 Useful One-Liners"))
    onelines = [
        ("Offline demo (no Docker)", "python -m patchcourt review --demo"),
        ("Review a real PR", "python -m patchcourt review https://github.com/owner/repo/pull/N"),
        ("Run all tests", "pytest -q"),
        ("Check what's in latest baseline", "curl -s http://localhost:8000/api/baseline/latest | python -m json.tool | head -40"),
        ("Force mock LLM at runtime", 'curl -X POST http://localhost:8000/api/settings/llm -H "Content-Type: application/json" -d \'{"use_mock_llm":true}\''),
        ("Check SonarQube issues for PR project", "curl http://localhost:8000/api/sonar/issues?component=pr-owner-repo-N"),
        ("Tail API logs", "docker logs patchcourt-api-1 -f --tail 30"),
        ("Restart just the API", "docker compose up -d api"),
        ("Rebuild dashboard only", "docker compose build dashboard && docker compose up -d dashboard"),
        ("List all baseline reports", "dir reports\\baseline-*.json /b /o-d"),
    ]
    ol_data = [[Paragraph("Action", S_TH), Paragraph("Command", S_TH)]]
    for label, cmd in onelines:
        ol_data.append([
            Paragraph(label, sty("ol", fontSize=8.5, fontName="Helvetica-Bold", textColor=C_PRIMARY)),
            Paragraph(cmd.replace(" ", "&nbsp;"), sty("oc", fontSize=7.5, fontName="Courier",
                      textColor=C_CODE_FG, backColor=C_CODE_BG)),
        ])
    e.append(tbl(ol_data, [5*cm, W - 2*MARGIN - 5*cm]))
    e.append(SP(10))

    e.append(h2("13.5 Policies Directory (patchcourt/policies/)"))
    policies = [
        ("security-policy.md", "Hardcoded secrets forbidden. All security findings adjudicated before merge."),
        ("coding-standards.md", "Style, naming, complexity, dead-code rules."),
        ("api-boundaries.md", "Internal members stay private; visibility widening requires justification."),
        ("repository-workflow.md", "PR process, review requirements, merge criteria."),
    ]
    pt = Table(
        [[Paragraph(p[0], sty("pk3", fontSize=8.5, fontName="Courier", textColor=colors.HexColor("#1A237E"))),
          Paragraph(p[1], sty("pv3", fontSize=8.5, fontName="Helvetica", textColor=C_BLACK))]
         for p in policies],
        colWidths=[4.5*cm, W - 2*MARGIN - 4.5*cm]
    )
    pt.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[C_LIGHT, C_WHITE]),
        ("GRID",(0,0),(-1,-1),0.4,C_BORDER),
        ("LEFTPADDING",(0,0),(-1,-1),6),
        ("TOPPADDING",(0,0),(-1,-1),4),
        ("BOTTOMPADDING",(0,0),(-1,-1),4),
    ]))
    e.append(pt)
    return e


# ============================================================================
# MAIN — assemble and build PDF
# ============================================================================

def build_pdf(path="PatchCourt_Master_Reference.pdf"):
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
        title="PatchCourt Master Reference Sheet",
        author="PatchCourt Team",
    )

    story = []
    story += cover_page()
    story += sec1_overview()
    story += sec2_architecture()
    story += sec3_evidence()
    story += sec4_research()
    story += sec5_deployment()
    story += sec6_api()
    story += sec7_config()
    story += sec8_sonarqube()
    story += sec9_dashboard()
    story += sec10_datamodels()
    story += sec11_troubleshooting()
    story += sec12_tests()
    story += sec13_cheatsheet()

    doc.build(story)
    print(f"PDF written to: {path}")


if __name__ == "__main__":
    build_pdf()
