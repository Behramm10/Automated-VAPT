"""Reports API routes — generate JSON, HTML, PDF reports with Llama 3B narrative."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.session import get_db_session

router = APIRouter()


async def _generate_report_task(run_id: str, report_id: str) -> None:
    """Background task: generate full report."""
    from app.database.session import get_session_factory
    factory = get_session_factory()
    async with factory() as db:
        from app.database.models.report_model import ReportModel
        from app.database.models.run_model import RunModel
        from app.database.models.finding_model import FindingModel
        from app.database.models.attack_graph_model import AttackGraphModel

        result = await db.execute(select(ReportModel).where(ReportModel.id == report_id))
        report = result.scalar_one_or_none()
        if not report:
            return

        try:
            run_result = await db.execute(select(RunModel).where(RunModel.id == run_id))
            run = run_result.scalar_one_or_none()

            findings_result = await db.execute(select(FindingModel).where(FindingModel.run_id == run_id).order_by(FindingModel.risk_score.desc()))
            findings = findings_result.scalars().all()

            # Try Llama 3B narrative
            llm_sections = await _generate_llm_narrative(run, findings)
            report.llm_available = llm_sections.get("available", False)
            report.executive_summary = llm_sections.get("executive_summary", _deterministic_executive_summary(run, findings))
            report.risk_summary = llm_sections.get("risk_summary", _deterministic_risk_summary(findings))
            report.technical_overview = llm_sections.get("technical_overview", "")
            report.business_impact = llm_sections.get("business_impact", "")
            report.overall_assessment = llm_sections.get("overall_assessment", "")
            report.remediation_priorities = llm_sections.get("remediation_priorities", "")
            report.conclusion = llm_sections.get("conclusion", "")

            # Generate JSON report
            report_data = _build_report_data(run, findings, report)
            json_path = settings.reports_path / f"{report_id}.json"
            import json
            json_path.write_text(json.dumps(report_data, indent=2, default=str))
            report.json_path = str(json_path)

            # Generate HTML report
            html_content = _generate_html_report(report_data)
            html_path = settings.reports_path / f"{report_id}.html"
            html_path.write_text(html_content)
            report.html_path = str(html_path)

            # Generate PDF
            try:
                pdf_path = settings.reports_path / f"{report_id}.pdf"
                _generate_pdf_report(html_content, pdf_path)
                report.pdf_path = str(pdf_path)
            except Exception as pdf_err:
                import structlog
                structlog.get_logger().warning("pdf_generation_error", error=str(pdf_err))

            report.status = "complete"
            report.findings_count = len(findings)
            report.completed_at = datetime.now(timezone.utc)
            report.metrics_snapshot = {
                "total_findings": len(findings),
                "critical": sum(1 for f in findings if f.severity == "critical"),
                "high": sum(1 for f in findings if f.severity == "high"),
                "medium": sum(1 for f in findings if f.severity == "medium"),
                "low": sum(1 for f in findings if f.severity in ("low", "informational")),
            }
            await db.commit()

        except Exception as exc:
            import structlog
            structlog.get_logger().error("report_generation_failed", report_id=report_id, error=str(exc))
            report.status = "failed"
            report.error_message = str(exc)[:2000]
            await db.commit()


async def _generate_llm_narrative(run: any, findings: list) -> dict:
    """Generate narrative sections using local Llama 3B."""
    try:
        import ollama
        import json

        context = {
            "target_name": "Mock Agent",
            "assessment_date": datetime.now(timezone.utc).isoformat(),
            "run_name": run.name if run else "Assessment",
            "findings_count": len(findings),
            "critical_count": sum(1 for f in findings if f.severity == "critical"),
            "high_count": sum(1 for f in findings if f.severity == "high"),
            "findings_summary": [{"title": f.title, "severity": f.severity, "pipeline": f.pipeline} for f in findings[:5]],
        }

        prompt = f"""You are writing a professional VAPT (Vulnerability Assessment and Penetration Testing) report.

Assessment context:
{json.dumps(context, indent=2)}

Write the following sections for this security assessment report. Be professional and precise.
Do NOT invent findings or evidence not listed above.
Use only the provided findings data.

Output valid JSON with these keys:
{{
  "executive_summary": "2-3 paragraph executive summary",
  "risk_summary": "Risk overview paragraph",
  "technical_overview": "Technical assessment methodology overview",
  "business_impact": "Business impact assessment",
  "overall_assessment": "Overall security posture statement",
  "remediation_priorities": "Top 3 remediation priorities",
  "conclusion": "Concluding paragraph"
}}"""

        response = ollama.chat(
            model=settings.ollama_model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1, "num_predict": 2048},
        )
        raw = response["message"]["content"]
        j_start = raw.find("{")
        j_end = raw.rfind("}") + 1
        if j_start >= 0:
            data = json.loads(raw[j_start:j_end])
            data["available"] = True
            return data
    except Exception:
        pass
    return {"available": False}


def _deterministic_executive_summary(run: any, findings: list) -> str:
    if not findings:
        return f"Security assessment of {getattr(run, 'name', 'target agent')} found no significant vulnerabilities under the tested scenarios."
    sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        sev_counts[f.severity if f.severity in sev_counts else "low"] += 1
    return (
        f"Security assessment of {getattr(run, 'name', 'the target agent')} identified {len(findings)} finding(s): "
        f"{sev_counts['critical']} critical, {sev_counts['high']} high, {sev_counts['medium']} medium, {sev_counts['low']} low. "
        f"The assessment used four attack pipelines: direct injection, indirect artifact injection, multi-turn crescendo, and tool-output injection. "
        f"Immediate remediation is recommended for critical and high severity findings."
    )


def _deterministic_risk_summary(findings: list) -> str:
    if not findings:
        return "No significant risks identified in this assessment."
    max_score = max(f.risk_score for f in findings)
    return f"Maximum AgenticRiskScore: {max_score:.1f}/10. {len(findings)} total findings detected via deterministic behavioral analysis."


def _build_report_data(run: any, findings: list, report: any) -> dict:
    return {
        "report_id": report.id,
        "run_id": run.id if run else None,
        "run_name": run.name if run else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "framework_version": settings.app_version,
        "llm_available": report.llm_available,
        "executive_summary": report.executive_summary,
        "risk_summary": report.risk_summary,
        "findings": [{"id": f.id, "title": f.title, "severity": f.severity, "risk_score": f.risk_score, "pipeline": f.pipeline, "objective": f.objective, "description": f.description, "remediation": f.remediation, "reproduction_steps": f.reproduction_steps, "deterministic_signals": f.deterministic_signals} for f in findings],
        "metrics": {"total_findings": len(findings), "critical": sum(1 for f in findings if f.severity == "critical"), "high": sum(1 for f in findings if f.severity == "high"), "medium": sum(1 for f in findings if f.severity == "medium"), "low": sum(1 for f in findings if f.severity in ("low", "informational"))},
    }


def _generate_html_report(data: dict) -> str:
    findings_html = ""
    sev_colors = {"critical": "#dc2626", "high": "#ea580c", "medium": "#d97706", "low": "#65a30d", "informational": "#6b7280"}
    for f in data.get("findings", []):
        color = sev_colors.get(f["severity"], "#6b7280")
        findings_html += f"""
        <div class="finding">
          <div class="finding-header" style="border-left:4px solid {color}">
            <span class="severity-badge" style="background:{color}">{f['severity'].upper()}</span>
            <h3>{f['title']}</h3>
          </div>
          <p><strong>Risk Score:</strong> {f['risk_score']:.1f}/10 | <strong>Pipeline:</strong> {f['pipeline']}</p>
          <p>{f['description'][:500]}</p>
          <p><strong>Remediation:</strong> {f.get('remediation', 'See technical details')}</p>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>VAPT Security Assessment Report</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 1100px; margin: 0 auto; padding: 40px; color: #1e293b; background: #f8fafc; }}
  .cover {{ background: linear-gradient(135deg, #0f172a, #1e3a5f); color: white; padding: 60px 40px; border-radius: 12px; margin-bottom: 40px; }}
  .cover h1 {{ font-size: 2.5em; margin: 0 0 10px 0; }}
  .cover p {{ opacity: 0.8; font-size: 1.1em; }}
  .section {{ background: white; padding: 30px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
  .section h2 {{ color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }}
  .finding {{ border: 1px solid #e2e8f0; border-radius: 8px; margin: 15px 0; padding: 20px; }}
  .finding-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }}
  .severity-badge {{ color: white; padding: 3px 10px; border-radius: 4px; font-size: 0.85em; font-weight: bold; }}
  .metric-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
  .metric {{ background: #f1f5f9; padding: 15px; border-radius: 8px; text-align: center; }}
  .metric .value {{ font-size: 2em; font-weight: bold; }}
  .footer {{ text-align: center; color: #64748b; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0; }}
  .llm-badge {{ background: #dbeafe; color: #1d4ed8; padding: 4px 10px; border-radius: 4px; font-size: 0.8em; }}
</style>
</head>
<body>
<div class="cover">
  <h1>🛡️ Agentic AI VAPT Security Assessment</h1>
  <p>Assessment: {data.get('run_name', 'Security Assessment')}</p>
  <p>Generated: {data.get('generated_at', '')[:10]} | Framework v{data.get('framework_version', '1.0.0')}</p>
  {'<span class="llm-badge">✓ Llama 3B Narrative</span>' if data.get('llm_available') else '<span style="opacity:0.6">Deterministic report (LLM unavailable)</span>'}
</div>

<div class="section">
  <h2>Executive Summary</h2>
  <p>{data.get('executive_summary', '')}</p>
</div>

<div class="section">
  <h2>Risk Summary</h2>
  <p>{data.get('risk_summary', '')}</p>
  <div class="metric-grid">
    <div class="metric"><div class="value" style="color:#dc2626">{data['metrics'].get('critical',0)}</div><div>Critical</div></div>
    <div class="metric"><div class="value" style="color:#ea580c">{data['metrics'].get('high',0)}</div><div>High</div></div>
    <div class="metric"><div class="value" style="color:#d97706">{data['metrics'].get('medium',0)}</div><div>Medium</div></div>
    <div class="metric"><div class="value" style="color:#65a30d">{data['metrics'].get('low',0)}</div><div>Low</div></div>
  </div>
</div>

<div class="section">
  <h2>Detailed Findings ({data['metrics']['total_findings']})</h2>
  {findings_html if findings_html else '<p>No findings detected in this assessment run.</p>'}
</div>

<div class="footer">
  <p>Generated by Agentic AI VAPT Framework v{data.get('framework_version', '1.0.0')} | Research Use Only</p>
</div>
</body>
</html>"""


def _generate_pdf_report(html_content: str, output_path: Path) -> None:
    """Generate PDF from HTML using WeasyPrint."""
    try:
        from weasyprint import HTML
        HTML(string=html_content).write_pdf(str(output_path))
    except ImportError:
        # Fallback: save as HTML with .pdf extension note
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, "VAPT Security Assessment Report", ln=True)
        pdf.cell(0, 10, f"(Full HTML report available)", ln=True)
        pdf.output(str(output_path))


@router.post("/reports/{run_id}/generate", status_code=202, summary="Generate VAPT report")
async def generate_report(run_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db_session)):
    from app.database.models.run_model import RunModel
    from app.database.models.report_model import ReportModel
    result = await db.execute(select(RunModel).where(RunModel.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, f"Run {run_id} not found")

    report = ReportModel(id=str(uuid.uuid4()), run_id=run_id, name=f"VAPT Report — {run.name}", status="generating")
    db.add(report)
    await db.flush()
    await db.commit()

    background_tasks.add_task(_generate_report_task, run_id, report.id)
    return {"report_id": report.id, "status": "generating", "message": "Report generation started"}


@router.get("/reports/{report_id}", summary="Get report details")
async def get_report(report_id: str, db: AsyncSession = Depends(get_db_session)):
    from app.database.models.report_model import ReportModel
    result = await db.execute(select(ReportModel).where(ReportModel.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, f"Report {report_id} not found")
    return {"id": report.id, "run_id": report.run_id, "name": report.name, "status": report.status, "llm_available": report.llm_available, "findings_count": report.findings_count, "json_path": report.json_path, "html_path": report.html_path, "pdf_path": report.pdf_path, "created_at": report.created_at.isoformat(), "completed_at": report.completed_at.isoformat() if report.completed_at else None}


@router.get("/reports/{report_id}/download", summary="Download report file")
async def download_report(report_id: str, format: str = "pdf", db: AsyncSession = Depends(get_db_session)):
    from app.database.models.report_model import ReportModel
    result = await db.execute(select(ReportModel).where(ReportModel.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, f"Report {report_id} not found")
    if report.status != "complete":
        raise HTTPException(400, f"Report is not yet complete (status: {report.status})")

    path_map = {"pdf": report.pdf_path, "html": report.html_path, "json": report.json_path}
    file_path = path_map.get(format)
    if not file_path or not Path(file_path).exists():
        raise HTTPException(404, f"Report file not found for format: {format}")

    return FileResponse(file_path, filename=f"vapt_report_{report_id}.{format}")
