# ================================================================
# ai_analytics_department/tools/reporting.py
# ================================================================
from typing import Any
from ai_analytics_department.workflows.router import _extract_event_dict

def business_input_adapter(ctx: Any) -> str:
    session_events = getattr(ctx, 'events', []) or getattr(getattr(ctx, 'session', None), 'events', [])
    context_str = "Generate Strategic Report."
    
    for raw_event in reversed(session_events):
        event = _extract_event_dict(raw_event)
        if event.get("author") == "data_scientist":
            segments = []
            content = event.get("content", {})
            for part in content.get("parts", []):
                if isinstance(part, dict) and "text" in part and not part.get("thought"):
                    text_content = part.get("text", "").strip()
                    if text_content:
                        segments.append(text_content)
            
            if segments:
                combined = "\n\n".join(segments)
                context_str = f"Data Scientist Results:\n{combined}"
                break
    return context_str

def generate_report() -> dict:
    """Generates a comprehensive corporate valuation report contract."""
    return {
        "status": "SUCCESS",
        "report_metadata": "Unified strategic analysis compiled from pipeline runs."
    }



import re
from pathlib import Path
from fpdf import FPDF
import os
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHART_DIR = PROJECT_ROOT / "outputs" / "charts"
PAGE_W = 210
MARGIN = 10
BODY_W = PAGE_W - 2 * MARGIN


def _embed_charts(pdf: FPDF, content: str) -> None:
    seen = set()
    chart_dir_str = str(CHART_DIR)
    for line in content.splitlines():
        for path in re.findall(
            rf'{re.escape(chart_dir_str)}/[^\s]+\.png',
            line,
        ):
            if path in seen or not os.path.exists(path):
                continue
            seen.add(path)
            pdf.add_page()
            pdf.set_font("Arial", "B", 11)
            name = os.path.basename(path).rsplit(".", 1)[0].replace("_", " ").title()
            pdf.cell(0, 10, name, new_x="LMARGIN", new_y="NEXT")
            pdf.image(path, x=MARGIN, y=pdf.get_y(), w=BODY_W)


def save_report_as_pdf(report_content: str) -> dict:
    try:
        pdf = FPDF()
        pdf.add_page()

        pdf.set_font("Arial", "B", 18)
        pdf.cell(0, 14, "Business Analysis Report", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Arial", size=9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(
            0, 6,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            new_x="LMARGIN", new_y="NEXT",
        )
        pdf.set_text_color(0, 0, 0)

        pdf.line(MARGIN, pdf.get_y() + 1, PAGE_W - MARGIN, pdf.get_y() + 1)
        pdf.ln(6)

        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 7, report_content)

        _embed_charts(pdf, report_content)

        output_dir = PROJECT_ROOT / "outputs" / "reports"
        os.makedirs(output_dir, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"business_report_{ts}.pdf")
        pdf.output(output_path)
        print(f"📄 Report saved: {output_path}")

        return {"status": "SUCCESS", "path": output_path}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}