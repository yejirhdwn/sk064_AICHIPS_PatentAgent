# report_agent_country.py
"""
Report Agent (Country-Comparison Only)
- 국가비교 전용 PDF 보고서 생성기 (ReportLab 기반)
- 섹션 번호: 1 SUMMARY / 2 DETAIL / 3 COUNTRY / 4 GAP / 5 REFERENCE / 6 APPENDIX
"""

from __future__ import annotations

import os
import json
import platform
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

# ReportLab
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY, TA_CENTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    _HAS_REPORTLAB = True
except ImportError:
    _HAS_REPORTLAB = False
    print("⚠️ ReportLab not available. Install: pip install reportlab")


class ReportAgent:
    """
    Multi-country PDF Report Agent (국가 비교형 전용)
    - 단일 보고서 생성 로직 제거
    - 국가 비교/격차 분석 전용 섹션 포함
    """

    def __init__(self, tech_name: str, output_dir: str = "./output/reports"):
        if not _HAS_REPORTLAB:
            raise ImportError("ReportLab is required: pip install reportlab")

        self.tech_name = tech_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._register_fonts()

    # ------------------------ Font & Style ------------------------
    def _register_fonts(self):
        """크로스플랫폼 한글 폰트 등록"""
        system = platform.system()
        font_registered = False
        font_paths = []

        if system == "Windows":
            font_paths = [
                ("C:/Windows/Fonts/malgun.ttf", "Malgun", False),
                ("C:/Windows/Fonts/malgunbd.ttf", "MalgunBold", True),
                ("C:/Windows/Fonts/NanumGothic.ttf", "NanumGothic", False),
            ]
        elif system == "Darwin":
            font_paths = [
                ("/System/Library/Fonts/AppleGothic.ttf", "AppleGothic", False),
                ("/Library/Fonts/NanumGothic.ttf", "NanumGothic", False),
            ]
        else:
            font_paths = [
                ("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", "NanumGothic", False),
                ("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", "NanumGothicBold", True),
                ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "Liberation", False),
            ]

        possible_font_dirs = [
            Path(__file__).parent / "fonts",
            Path(__file__).parent.parent / "fonts",
            Path.cwd() / "fonts",
        ]
        for project_fonts in possible_font_dirs:
            if project_fonts.exists():
                for font_file in project_fonts.glob("*.ttf"):
                    font_name = font_file.stem
                    is_bold = "Bold" in font_name or "bold" in font_name
                    font_paths.append((str(font_file), font_name, is_bold))
                break

        for font_path, font_name, is_bold in font_paths:
            try:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    if not font_registered:
                        self.korean_font = font_name
                        font_registered = True
                    if is_bold and not hasattr(self, "korean_bold"):
                        self.korean_bold = font_name
            except Exception:
                continue

        if not font_registered:
            self.korean_font = "Helvetica"
            self.korean_bold = "Helvetica-Bold"
        if not hasattr(self, "korean_bold"):
            self.korean_bold = self.korean_font

    def _create_styles(self):
        styles = getSampleStyleSheet()

        # 기본 제공 스타일들(TITLE/H1/H2 등) 속성만 덮어쓰기
        styles["Title"].fontName = self.korean_bold
        styles["Title"].fontSize = 28
        styles["Title"].textColor = colors.HexColor("#1a1a1a")
        styles["Title"].alignment = TA_CENTER
        styles["Title"].spaceAfter = 30

        styles["Heading1"].fontName = self.korean_bold
        styles["Heading1"].fontSize = 20
        styles["Heading1"].textColor = colors.HexColor("#2c3e50")
        styles["Heading1"].spaceAfter = 15
        styles["Heading1"].spaceBefore = 25

        styles["Heading2"].fontName = self.korean_bold
        styles["Heading2"].fontSize = 16
        styles["Heading2"].textColor = colors.HexColor("#34495e")
        styles["Heading2"].spaceAfter = 12
        styles["Heading2"].spaceBefore = 20

        # ── 문제된 Heading3: 있으면 수정, 없으면 추가
        if "Heading3" in styles:
            h3 = styles["Heading3"]
            h3.parent = styles["Heading2"]
            h3.fontName = self.korean_bold
            h3.fontSize = 14
            h3.textColor = colors.HexColor("#7f8c8d")
            h3.spaceAfter = 10
            h3.spaceBefore = 15
        else:
            styles.add(ParagraphStyle(
                name="Heading3",
                parent=styles["Heading2"],
                fontName=self.korean_bold,
                fontSize=14,
                textColor=colors.HexColor("#7f8c8d"),
                spaceAfter=10,
                spaceBefore=15
            ))

        # 본문
        styles["BodyText"].fontName = self.korean_font
        styles["BodyText"].fontSize = 11
        styles["BodyText"].leading = 18
        styles["BodyText"].alignment = TA_JUSTIFY

        # ── Bullet도 샘플 스타일시트에 기본 포함되어 있음: 존재 시 속성만 조정
        if "Bullet" in styles:
            b = styles["Bullet"]
            b.parent = styles["BodyText"]
            b.fontName = self.korean_font
            b.leftIndent = 20
            b.spaceAfter = 6
        else:
            styles.add(ParagraphStyle(
                name="Bullet",
                parent=styles["BodyText"],
                fontName=self.korean_font,
                leftIndent=20,
                spaceAfter=6
            ))

        return styles


    # ------------------------ Public API ------------------------
    def generate_report_with_country_comparison(
        self,
        all_patents: List[Dict[str, Any]],
        country_summaries: List[Dict[str, Any]],
        gap_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        국가비교형 보고서 생성 (유일한 퍼블릭 API)
        - 입력:
          - all_patents: 특허별 원시/집계 데이터 (title, scores 등 포함)
          - country_summaries: 국가별 평균/분포 요약
          - gap_analysis: 한국 기준 격차 분석 결과
        """
        print("\n📊 Generating Multi-Country Comparison Report...")

        # 보고서 데이터 구성
        report_data = self._prepare_report_data_for_country(all_patents)
        report_data["country_summaries"] = country_summaries
        report_data["gap_analysis"] = gap_analysis
        report_data["is_multi_country"] = True
        report_data["title"] = f"한국의 {self.tech_name} 기술 경쟁력 보고서"

        # 파일 경로
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_pdf = f"한국_{self.tech_name}_기술경쟁력보고서_{timestamp}.pdf"
        filename_json = f"한국_{self.tech_name}_기술경쟁력보고서_{timestamp}.json"
        pdf_path = self.output_dir / filename_pdf
        json_path = self.output_dir / filename_json

        # PDF 생성
        self._create_pdf_with_country_comparison(pdf_path, report_data)
        print(f"✅ PDF Report: {pdf_path}")

        # JSON 저장
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        return {
            "report_pdf_path": str(pdf_path),
            "report_json_path": str(json_path),
            "report_title": report_data["title"],
            "report_generated_at": report_data["generated_at"],
            "total_patents_analyzed": report_data["total_patents_analyzed"],
            "avg_originality_score": report_data["statistics"]["avg_originality_score"],
            "avg_market_score": report_data["statistics"]["avg_market_score"],
            "grade_distribution": report_data["statistics"]["grade_distribution"]
        }

    # ------------------------ Builder Methods ------------------------
    def _prepare_report_data_for_country(self, all_patent_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """국가비교 보고서를 위한 공통 요약 생성"""
        patents_summary = []
        total_originality, total_market = 0.0, 0.0
        grade_distribution = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}

        for result in all_patent_results:
            patent_id = result.get("target_patent_id") or result.get("patent_id", "N/A")
            patent_title = (result.get("first_item") or {}).get("title") or result.get("title", "N/A")
            originality = float(result.get("originality_score") or 0.0)
            market = float(result.get("market_score") or 0.0)
            grade = result.get("final_grade", "N/A")

            total_originality += originality
            total_market += market

            if grade in grade_distribution:
                grade_distribution[grade] += 1

            patents_summary.append({
                "patent_id": patent_id,
                "title": patent_title,
                "originality_score": originality,
                "market_score": market,
                "final_grade": grade,
                "market_size_score": float(result.get("market_size_score") or 0.0),
                "growth_potential_score": float(result.get("growth_potential_score") or 0.0),
                "commercialization_readiness": float(result.get("commercialization_readiness") or 0.0),
                "application_domains": result.get("application_domains", []),
                "llm_evaluation": result.get("llm_evaluation", {}),
                "market_rationale": result.get("market_rationale", "")
            })

        n = len(all_patent_results)
        avg_originality = (total_originality / n) if n else 0.0
        avg_market = (total_market / n) if n else 0.0

        return {
            "title": f"{self.tech_name} Technology Competitiveness (Country Comparison)",
            "tech_name": self.tech_name,
            "generated_at": datetime.now().isoformat(),
            "generated_at_kr": datetime.now().strftime("%Y-%m-%d"),
            "total_patents_analyzed": n,
            "patents_summary": patents_summary,
            "statistics": {
                "avg_originality_score": avg_originality,
                "avg_market_score": avg_market,
                "grade_distribution": grade_distribution
            }
        }

    def _create_pdf_with_country_comparison(self, pdf_path: Path, report_data: Dict[str, Any]):
        """국가비교 보고서 전용 PDF 생성"""
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        styles = self._create_styles()
        story: List[Any] = []

        # 표지
        story.extend(self._generate_multi_country_cover(report_data, styles))
        story.append(PageBreak())

        # 목차
        story.extend(self._generate_multi_country_toc(report_data, styles))
        story.append(PageBreak())

        # 1. SUMMARY
        story.extend(self._generate_summary(report_data, styles))
        story.append(PageBreak())

        # 2. DETAIL ANALYSIS
        story.extend(self._generate_detail_analysis(report_data, styles))
        story.append(PageBreak())

        # 3. COUNTRY COMPARISON
        story.extend(self._generate_country_comparison_section(report_data, styles))
        story.append(PageBreak())

        # 4. TECHNOLOGY GAP ANALYSIS
        story.extend(self._generate_gap_analysis_section(report_data, styles))
        story.append(PageBreak())

        # 5. REFERENCE
        story.extend(self._generate_reference(report_data, styles, section_no=5))
        story.append(PageBreak())

        # 6. APPENDIX
        story.extend(self._generate_appendix(report_data, styles, section_no=6))

        doc.build(story)

    # ------------------------ Sections ------------------------
    def _generate_multi_country_cover(self, report_data: Dict[str, Any], styles):
        content = []
        content.append(Spacer(1, 2 * inch))
        title = Paragraph(report_data["title"], styles["Title"])
        content.append(title)
        content.append(Spacer(1, 0.3 * inch))

        subtitle = f"{report_data['tech_name']} Technology Global Competitiveness Analysis"
        content.append(Paragraph(subtitle, styles["Normal"]))
        content.append(Spacer(1, 0.5 * inch))

        countries = [c["country_name"] for c in report_data.get("country_summaries", []) if not c.get("error")]
        if countries:
            content.append(Paragraph(f"<b>분석 국가:</b> {', '.join(countries)}", styles["Normal"]))
            content.append(Spacer(1, 0.15 * inch))

        content.append(Paragraph(f"<b>분석 특허 수:</b> {report_data['total_patents_analyzed']}개", styles["Normal"]))
        content.append(Spacer(1, 0.15 * inch))

        content.append(Paragraph(f"<b>보고서 생성일:</b> {report_data['generated_at_kr']}", styles["Normal"]))
        return content

    def _generate_multi_country_toc(self, report_data: Dict[str, Any], styles):
        content = []
        content.append(Paragraph("TABLE OF CONTENTS", styles["Heading1"]))
        content.append(Spacer(1, 0.3 * inch))
        toc = [
            "1. SUMMARY",
            "   1.1 Technology Competitiveness Overview",
            "   1.2 Evaluation Results by Technology Keywords",
            "   1.3 Strengths and Areas for Improvement",
            "",
            "2. DETAIL ANALYSIS",
            "   2.1 Patent-by-Patent Analysis",
            "   2.2 Technical Evaluation",
            "   2.3 Market Evaluation",
            "",
            "3. COUNTRY COMPARISON",
            "   3.1 Country-wise Statistics",
            "   3.2 Country Details",
            "",
            "4. TECHNOLOGY GAP ANALYSIS",
            "   4.1 Korea's Baseline Scores",
            "   4.2 Technology Gap by Country",
            "   4.3 Strategic Recommendations",
            "",
            "5. REFERENCE",
            "6. APPENDIX"
        ]
        for item in toc:
            content.append(Paragraph(item, styles["Normal"]) if item else Spacer(1, 0.1 * inch))
        return content

    def _generate_summary(self, report_data: Dict[str, Any], styles):
        content = []
        content.append(Paragraph("1. SUMMARY", styles["Heading1"]))
        content.append(Spacer(1, 0.3 * inch))

        # 1.1 개요
        content.append(Paragraph("1.1 Technology Competitiveness Overview", styles["Heading2"]))
        stats = report_data["statistics"]
        overview = (
            f"This report analyzes <b>{report_data['total_patents_analyzed']}</b> patents in the "
            f"<b>{report_data['tech_name']}</b> domain. "
            f"Average Originality: <b>{stats['avg_originality_score']:.3f}</b>, "
            f"Average Market Score: <b>{stats['avg_market_score']:.3f}</b>."
        )
        content.append(Paragraph(overview, styles["BodyText"]))
        content.append(Spacer(1, 0.2 * inch))

        # 1.2 등급 분포
        content.append(Paragraph("1.2 Evaluation Results by Technology Keywords", styles["Heading2"]))
        grade_dist = stats.get("grade_distribution", {})
        total = int(report_data.get("total_patents_analyzed", 0) or 0)
        data = [["Grade", "Count", "Percentage"]]
        for g in ["S", "A", "B", "C", "D"]:
            cnt = int(grade_dist.get(g, 0) or 0)
            pct = f"{(cnt / total) * 100:.1f}%" if total else "0.0%"
            data.append([g, str(cnt), pct])

        table = Table(data, colWidths=[1.5 * inch, 1.5 * inch, 1.5 * inch])
        table.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), self.korean_font, 10),
            ("FONT", (0, 0), (-1, 0), self.korean_bold, 11),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498db")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
        ]))
        content.append(table)
        content.append(Spacer(1, 0.2 * inch))

        # 1.3 강점/개선
        content.append(Paragraph("1.3 Strengths and Areas for Improvement", styles["Heading2"]))
        strengths, weaknesses = self._analyze_strengths_weaknesses(stats, report_data)
        content.append(Paragraph("<b>Key Strengths:</b>", styles["Heading3"]))
        for s in strengths:
            content.append(Paragraph(f"• {s}", styles["Bullet"]))
        content.append(Spacer(1, 0.05 * inch))
        content.append(Paragraph("<b>Areas for Improvement:</b>", styles["Heading3"]))
        for w in weaknesses:
            content.append(Paragraph(f"• {w}", styles["Bullet"]))

        return content

    def _analyze_strengths_weaknesses(self, stats: Dict[str, Any], report_data: Dict[str, Any]) -> tuple[list[str], list[str]]:
        strengths, weaknesses = [], []
        ao, am = stats["avg_originality_score"], stats["avg_market_score"]
        if ao >= 0.8: strengths.append(f"High technical originality (avg: {ao:.3f})")
        if am >= 0.7: strengths.append(f"Strong market potential (avg: {am:.3f})")
        if ao < 0.6: weaknesses.append("Originality requires more breakthrough R&D focus")
        if am < 0.5: weaknesses.append("Market readiness needs clearer GTM and partnerships")

        grade_dist = stats.get("grade_distribution", {})
        total = int(report_data.get("total_patents_analyzed", 0) or 0)
        s_a = grade_dist.get("S", 0) + grade_dist.get("A", 0)
        if total and (s_a / total) >= 0.5:
            strengths.append(f"High share of S/A grade patents ({s_a}/{total})")

        if not strengths: strengths.append("Solid foundation for technology development")
        if not weaknesses: weaknesses.append("Continue monitoring market dynamics and competitors")
        return strengths, weaknesses

    def _generate_detail_analysis(self, report_data: Dict[str, Any], styles):
        content = []
        content.append(Paragraph("2. DETAIL ANALYSIS", styles["Heading1"]))
        content.append(Spacer(1, 0.3 * inch))

        for i, patent in enumerate(report_data["patents_summary"], 1):
            if i > 1:
                content.append(PageBreak())
            content.append(Paragraph(f"2.{i} Patent Analysis #{i}: {patent['patent_id']}", styles["Heading2"]))
            content.append(Spacer(1, 0.1 * inch))

            title = patent["title"]
            if len(title) > 100:
                title = title[:100] + "..."
            content.append(Paragraph(f"<b>Title:</b> {title}", styles["BodyText"]))
            content.append(Spacer(1, 0.1 * inch))

            # Technical table
            tech_data = [
                ["Metric", "Score", "Grade/Level"],
                ["Originality", f"{patent['originality_score']:.3f}", patent.get("final_grade", "N/A")],
                ["Overall Tech", f"{patent['originality_score']:.3f}", self._get_score_level(patent['originality_score'])],
            ]
            tech_table = Table(tech_data, colWidths=[2 * inch, 1.5 * inch, 1.5 * inch])
            tech_table.setStyle(TableStyle([
                ("FONT", (0, 0), (-1, -1), self.korean_font, 10),
                ("FONT", (0, 0), (-1, 0), self.korean_bold, 11),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2ecc71")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
            ]))
            content.append(tech_table)
            content.append(Spacer(1, 0.15 * inch))

            # Market table
            market_data = [
                ["Metric", "Score", "Assessment"],
                ["Market Size", f"{patent['market_size_score']:.2f}", self._get_score_level(patent['market_size_score'])],
                ["Growth Potential", f"{patent['growth_potential_score']:.2f}", self._get_score_level(patent['growth_potential_score'])],
                ["Commercialization Readiness", f"{patent['commercialization_readiness']:.2f}", self._get_score_level(patent['commercialization_readiness'])],
                ["Overall Market", f"{patent.get('market_score', 0):.2f}", self._get_score_level(patent.get('market_score', 0))],
            ]
            market_table = Table(market_data, colWidths=[2.5 * inch, 1 * inch, 1.5 * inch])
            market_table.setStyle(TableStyle([
                ("FONT", (0, 0), (-1, -1), self.korean_font, 10),
                ("FONT", (0, 0), (-1, 0), self.korean_bold, 11),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498db")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
            ]))
            content.append(market_table)
            content.append(Spacer(1, 0.15 * inch))

            # Domains
            domains = patent.get("application_domains", [])
            if domains:
                content.append(Paragraph("Application Domains", styles["Heading3"]))
                for d in domains:
                    content.append(Paragraph(f"• {d}", styles["Bullet"]))
                content.append(Spacer(1, 0.1 * inch))

            # Investment info (optional)
            llm_eval = patent.get("llm_evaluation", {})
            market_rationale = patent.get("market_rationale", "")
            if llm_eval or market_rationale:
                content.append(Paragraph("Investment Analysis", styles["Heading3"]))
                if llm_eval:
                    inv = llm_eval.get("investment_recommendation", "N/A")
                    risk = llm_eval.get("risk_level", "N/A")
                    content.append(Paragraph(f"• <b>Investment Recommendation:</b> {inv}", styles["Bullet"]))
                    content.append(Paragraph(f"• <b>Risk Level:</b> {risk}", styles["Bullet"]))
                if market_rationale:
                    content.append(Paragraph("<b>Market Analysis:</b>", styles["BodyText"]))
                    content.append(Paragraph(market_rationale, styles["BodyText"]))

        return content

    def _get_score_level(self, score: float) -> str:
        if score >= 0.8: return "Excellent"
        if score >= 0.6: return "Good"
        if score >= 0.4: return "Moderate"
        if score >= 0.2: return "Fair"
        return "Limited"

    def _generate_country_comparison_section(self, report_data: Dict[str, Any], styles):
        content = []
        content.append(Paragraph("3. COUNTRY COMPARISON", styles["Heading1"]))
        content.append(Spacer(1, 0.3 * inch))

        countries = report_data.get("country_summaries", [])
        if not countries:
            content.append(Paragraph("No country data available.", styles["BodyText"]))
            return content

        # 3.1 Country-wise Statistics
        content.append(Paragraph("3.1 Country-wise Statistics", styles["Heading2"]))
        stats_data = [["Country", "Patents", "Avg Orig", "Avg Market", "Avg Suit", "Top Grade"]]
        for c in countries:
            if c.get("error") or c.get("successful_analyses", 0) == 0:
                continue
            grade_dist = c.get("grade_distribution", {})
            top_grade = max(grade_dist, key=lambda k: grade_dist[k]) if grade_dist else "N/A"
            stats_data.append([
                c["country_name"],
                str(c["successful_analyses"]),
                f"{c['avg_originality_score']:.3f}",
                f"{c['avg_market_score']:.3f}",
                f"{c['avg_suitability_score']:.3f}",
                f"{top_grade} ({grade_dist.get(top_grade, 0)})"
            ])
        table = Table(stats_data, colWidths=[1.5*inch, 0.8*inch, 0.9*inch, 1.0*inch, 0.9*inch, 1.0*inch])
        table.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), self.korean_font, 9),
            ("FONT", (0, 0), (-1, 0), self.korean_bold, 10),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498db")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
        ]))
        content.append(table)
        content.append(Spacer(1, 0.2 * inch))

        # 3.2 Country Details
        content.append(Paragraph("3.2 Country Details", styles["Heading2"]))
        for c in countries:
            if c.get("error") or c.get("successful_analyses", 0) == 0:
                continue
            content.append(Paragraph(f"<b>{c['country_name']}</b>", styles["Heading3"]))
            details = (
                f"분석 특허: {c['successful_analyses']}개 | "
                f"평균 독창성: {c['avg_originality_score']:.3f} | "
                f"평균 시장성: {c['avg_market_score']:.3f}"
            )
            content.append(Paragraph(details, styles["BodyText"]))
            content.append(Spacer(1, 0.1 * inch))

        return content

    def _generate_gap_analysis_section(self, report_data: Dict[str, Any], styles):
        content = []
        content.append(Paragraph("4. TECHNOLOGY GAP ANALYSIS", styles["Heading1"]))
        content.append(Spacer(1, 0.3 * inch))

        gap = report_data.get("gap_analysis", {})
        if gap.get("error"):
            content.append(Paragraph("Gap analysis not available.", styles["BodyText"]))
            return content

        # 4.1 Korea's Baseline Scores
        content.append(Paragraph("4.1 Korea's Baseline Scores", styles["Heading2"]))
        ks = gap.get("korea_scores", {})
        k_data = [
            ["Metric", "Score"],
            ["Originality", f"{float(ks.get('originality', 0)):.4f}"],
            ["Market", f"{float(ks.get('market', 0)):.4f}"],
            ["Suitability", f"{float(ks.get('suitability', 0)):.4f}"],
        ]
        k_table = Table(k_data, colWidths=[2 * inch, 1.5 * inch])
        k_table.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), self.korean_font, 10),
            ("FONT", (0, 0), (-1, 0), self.korean_bold, 11),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2ecc71")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
        ]))
        content.append(k_table)
        content.append(Spacer(1, 0.2 * inch))

        # 4.2 Technology Gap by Country
        content.append(Paragraph("4.2 Technology Gap by Country", styles["Heading2"]))
        comps = gap.get("comparisons", [])
        if comps:
            g_data = [["Country", "Orig Gap", "Market Gap", "Suit Gap", "Overall", "Status"]]
            for c in comps:
                g_data.append([
                    c["country_name"],
                    f"{float(c['originality_gap']):+.4f}",
                    f"{float(c['market_gap']):+.4f}",
                    f"{float(c['suitability_gap']):+.4f}",
                    f"{float(c['overall_gap']):+.4f}",
                    c["status"],
                ])
            g_table = Table(g_data, colWidths=[1.5*inch, 1.0*inch, 1.0*inch, 1.0*inch, 1.0*inch, 0.9*inch])
            g_table.setStyle(TableStyle([
                ("FONT", (0, 0), (-1, -1), self.korean_font, 9),
                ("FONT", (0, 0), (-1, 0), self.korean_bold, 10),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e74c3c")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
            ]))
            content.append(g_table)
            content.append(Spacer(1, 0.2 * inch))

        # 4.3 Recommendations
        content.append(Paragraph("4.3 Strategic Recommendations for Korea", styles["Heading2"]))
        for i, rec in enumerate(self._generate_korea_recommendations(gap), 1):
            content.append(Paragraph(f"<b>{i}. {rec['title']}</b>", styles["Heading3"]))
            content.append(Paragraph(rec["description"], styles["BodyText"]))
            content.append(Spacer(1, 0.1 * inch))

        return content

    def _generate_korea_recommendations(self, gap_analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        recommendations: List[Dict[str, str]] = []
        comps = gap_analysis.get("comparisons", []) or []
        leaders = [c for c in comps if c.get("status") == "Leading"]

        if leaders:
            top = leaders[0]
            recommendations.append({
                "title": "선도 국가 벤치마킹",
                "description": (
                    f"{top['country_name']}가 전반에서 선도(격차 {float(top['overall_gap']):+.4f}). "
                    "혁신 접근/시장 포지셔닝을 벤치마킹해 로드맵에 반영할 필요가 있습니다."
                )
            })
            if float(top.get("originality_gap", 0)) > 0.05:
                recommendations.append({
                    "title": "독창성 강화",
                    "description": "기초 R&D·원천특허 중심의 투자 확대와 브레이크스루 과제 확보가 필요합니다."
                })
            if float(top.get("market_gap", 0)) > 0.05:
                recommendations.append({
                    "title": "상업화 전략 고도화",
                    "description": "명확한 GTM, 공동개발 파트너십, 레퍼런스 구축으로 시장성 격차 축소가 필요합니다."
                })
        recommendations.append({
            "title": "지역 협력 확대",
            "description": "인접국·산학연 컨소시엄으로 R&D 리스크 분담 및 초기 시장 레퍼런스 확보를 추진합니다."
        })
        return recommendations[:4]

    def _generate_reference(self, report_data: Dict[str, Any], styles, section_no: int = 5):
        content = []
        content.append(Paragraph(f"{section_no}. REFERENCE", styles["Heading1"]))
        content.append(Spacer(1, 0.3 * inch))

        # 5.1 Patent Data Sources
        content.append(Paragraph(f"{section_no}.1 Patent Data Sources", styles["Heading2"]))
        ref_data = [["No.", "Patent ID", "Title"]]
        for i, p in enumerate(report_data["patents_summary"], 1):
            t = p["title"]
            if len(t) > 60: t = t[:60] + "..."
            ref_data.append([str(i), p["patent_id"], t])
        table = Table(ref_data, colWidths=[0.5*inch, 1.5*inch, 4.0*inch])
        table.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), self.korean_font, 9),
            ("FONT", (0, 0), (-1, 0), self.korean_bold, 10),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
        ]))
        content.append(table)
        content.append(Spacer(1, 0.2 * inch))

        # 5.2~5.4 기타 정보
        content.append(Paragraph(f"{section_no}.2 Data Sources and Methodology", styles["Heading2"]))
        for s in [
            "Patent databases: Google Patent",
            "Market analysis: Industry reports and market research",
            "Technology evaluation: Academic/technical documentation"
        ]:
            content.append(Paragraph(f"• {s}", styles["Bullet"]))
        content.append(Spacer(1, 0.2 * inch))

        content.append(Paragraph(f"{section_no}.3 Key References", styles["Heading2"]))
        refs = [
            "[1] Park, S.Y., & Lee, S.J. (2020). Originality Index methodology (Ajou Univ.).",
            "[2] Global ICT Portal (2024-09-27): AI Semiconductor market trends.",
            "[3] Korea Eximbank OERI (2024-05): AI Semiconductor outlook."
        ]
        for r in refs:
            content.append(Paragraph(r, styles["BodyText"]))
        content.append(Spacer(1, 0.2 * inch))

        content.append(Paragraph(f"{section_no}.4 Report Generation Info", styles["Heading2"]))
        info = [
            ["Report Generated", report_data["generated_at_kr"]],
            ["Technology Domain", report_data["tech_name"]],
            ["Analysis Method", "Multi-Agent AI System (Country Comparison)"],
            ["Total Patents Analyzed", str(report_data["total_patents_analyzed"])],
        ]
        it = Table(info, colWidths=[2.0*inch, 3.0*inch])
        it.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), self.korean_font, 10),
            ("FONTNAME", (0, 0), (0, -1), self.korean_bold),
            ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
        ]))
        content.append(it)
        return content

    def _generate_appendix(self, report_data: Dict[str, Any], styles, section_no: int = 6):
        content = []
        content.append(Paragraph(f"{section_no}. APPENDIX", styles["Heading1"]))
        content.append(Spacer(1, 0.3 * inch))

        # 6.1 Methodology
        content.append(Paragraph(f"{section_no}.1 Evaluation Methodology", styles["Heading2"]))
        content.append(Paragraph(
            "We combine Technical Originality and Market Potential into a composite assessment. "
            "Each is normalized to 0–1, and summarized across the patent set.",
            styles["BodyText"]
        ))
        content.append(Spacer(1, 0.1 * inch))

        # Originality formula
        content.append(Paragraph("<b>Originality (Diversity-based):</b> Originality = 1 - Σ(NCITED_ik / NCITED_i)^2", styles["BodyText"]))
        content.append(Spacer(1, 0.15 * inch))

        # 6.2 Score Weighting
        content.append(Paragraph(f"{section_no}.2 Score Weighting", styles["Heading2"]))
        data = [
            ["Component", "Weight", "Justification"],
            ["Originality Score", "55%", "Primary indicator of innovation quality"],
            ["Market Score", "45%", "Commercial viability and market readiness"],
            ["", "", ""],
            ["Market Breakdown", "", ""],
            ["- Market Size", "33%", "TAM / SAM context"],
            ["- Growth Potential", "33%", "CAGR / expansion rate"],
            ["- Commercialization", "33%", "Technology readiness (time-to-market)"],
        ]
        wt = Table(data, colWidths=[2.0*inch, 1.0*inch, 3.0*inch])
        wt.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), self.korean_font, 9),
            ("FONT", (0, 0), (-1, 0), self.korean_bold, 10),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16a085")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("GRID", (0, 0), (-1, 2), 1, colors.HexColor("#bdc3c7")),
            ("SPAN", (0, 3), (2, 3)),
            ("FONTNAME", (0, 3), (0, 3), self.korean_bold),
        ]))
        content.append(wt)
        content.append(Spacer(1, 0.15 * inch))

        # Disclaimer
        content.append(Paragraph(
            "<b>Disclaimer:</b> This AI-generated report is for reference. "
            "Decisions should be based on professional due diligence.",
            styles["BodyText"]
        ))
        return content


# ------------------------ LangGraph Node (Country-only) ------------------------
def pdf_report_agent_node_country(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    국가비교 보고서 전용 LangGraph 노드
    필요한 state 키:
      - tech_name: str
      - all_patent_results: List[Dict]        # 특허 상세/점수
      - country_summaries: List[Dict]         # 국가별 요약
      - gap_analysis: Dict                    # 한국 기준 격차 분석
      - output_dir: str (optional)
    """
    print("\n" + "="*80)
    print("📊 Step 5: PDF Report Generation (Country-Comparison Only)")
    print("="*80)

    if state.get("error"):
        print(f"⚠️ Skip: {state['error']}")
        return state

    tech_name = state.get("tech_name", "AI Chip")
    all_patent_results = state.get("all_patent_results", [])
    country_summaries = state.get("country_summaries", [])
    gap_analysis = state.get("gap_analysis", {})

    if not all_patent_results:
        state["error"] = "No patent results"
        return state
    if not country_summaries:
        state["error"] = "No country_summaries provided"
        return state

    try:
        agent = ReportAgent(
            tech_name=tech_name,
            output_dir=state.get("output_dir", "./output/reports"),
        )
        result = agent.generate_report_with_country_comparison(
            all_patent_results, country_summaries, gap_analysis
        )
        state.update(result)
        print(f"✅ PDF Report: {result['report_pdf_path']}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        state["error"] = f"PDF Report error: {e}"

    return state


__all__ = ["ReportAgent", "pdf_report_agent_node_country"]
