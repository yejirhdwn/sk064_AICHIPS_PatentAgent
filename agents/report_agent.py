"""
Report Agent - PDF 보고서 생성 (ReportLab 기반)
전문적인 투자 분석 스타일의 PDF 보고서
"""
from __future__ import annotations

import os
import json
import platform
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY, TA_CENTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    _HAS_REPORTLAB = True
except ImportError:
    _HAS_REPORTLAB = False
    print("⚠️ ReportLab not available. Install: pip install reportlab")

try:
    from langchain_openai import ChatOpenAI
    _HAS_LANGCHAIN = True
except ImportError:
    _HAS_LANGCHAIN = False

import re


class ReportAgent:
    """
    PDF 보고서 생성 Agent (ReportLab 기반)
    
    특허 분석 결과를 전문적인 PDF 보고서로 생성
    크로스 플랫폼 한글 폰트 지원 (Windows/Linux/Mac)
    """
    
    def __init__(
        self,
        tech_name: str,
        output_dir: str = "./output/reports",
        use_llm: bool = True
    ):
        if not _HAS_REPORTLAB:
            raise ImportError("ReportLab is required")
        
        self.tech_name = tech_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.use_llm = use_llm and _HAS_LANGCHAIN
        
        # LLM 초기화 (보고서 요약용)
        if self.use_llm:
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.3,
                openai_api_key=os.environ.get("OPENAI_API_KEY")
            )
        else:
            self.llm = None
        
        # 한글 폰트 등록
        self._register_fonts()
    
    def _register_fonts(self):
        """
        한글 폰트 등록 (크로스 플랫폼 지원)
        
        시도 순서:
        1. 시스템 폰트 (Windows/Linux/Mac)
        2. 프로젝트 폴더의 fonts/ 디렉토리
        3. ReportLab 내장 CID 폰트 (HYSMyeongJo, HYGothic 등)
        """
        system = platform.system()
        font_registered = False
        
        # 1. 시스템 폰트 경로 시도
        font_paths = []
        
        if system == "Windows":
            # Windows 폰트
            font_paths = [
                ("C:/Windows/Fonts/malgun.ttf", "Malgun", False),
                ("C:/Windows/Fonts/malgunbd.ttf", "MalgunBold", True),
                ("C:/Windows/Fonts/NanumGothic.ttf", "NanumGothic", False),
                ("C:/Windows/Fonts/batang.ttc", "Batang", False),
            ]
        elif system == "Darwin":  # macOS
            font_paths = [
                ("/System/Library/Fonts/AppleGothic.ttf", "AppleGothic", False),
                ("/Library/Fonts/NanumGothic.ttf", "NanumGothic", False),
                ("/System/Library/Fonts/Supplemental/AppleMyungjo.ttf", "AppleMyungjo", False),
            ]
        else:  # Linux
            font_paths = [
                ("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", "NanumGothic", False),
                ("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", "NanumGothicBold", True),
                ("/usr/share/fonts/truetype/nanum/NanumMyeongjo.ttf", "NanumMyeongjo", False),
                ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "Liberation", False),
            ]
        
        # 2. 프로젝트 fonts/ 폴더도 확인 (현재 파일 기준 및 실행 위치 기준)
        possible_font_dirs = [
            Path(__file__).parent / "fonts",  # report_agent.py와 같은 폴더의 fonts/
            Path(__file__).parent.parent / "fonts",  # 상위 폴더의 fonts/
            Path.cwd() / "fonts",  # 현재 실행 위치의 fonts/
        ]
        
        for project_fonts in possible_font_dirs:
            if project_fonts.exists():
                print(f"ℹ️  폰트 폴더 발견: {project_fonts}")
                for font_file in project_fonts.glob("*.ttf"):
                    font_name = font_file.stem
                    is_bold = "Bold" in font_name or "bold" in font_name
                    font_paths.append((str(font_file), font_name, is_bold))
                    print(f"   - 폰트 파일 발견: {font_file.name}")
                break  # 첫 번째로 발견된 fonts/ 폴더 사용
        
        # 3. 폰트 등록 시도
        for font_path, font_name, is_bold in font_paths:
            try:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    
                    if not font_registered:
                        self.korean_font = font_name
                        font_registered = True
                        print(f"✅ 한글 폰트 등록 성공: {font_name}")
                        print(f"   경로: {font_path}")
                    
                    if is_bold and not hasattr(self, 'korean_bold'):
                        self.korean_bold = font_name
                        print(f"✅ Bold 폰트 등록 성공: {font_name}")
                        print(f"   경로: {font_path}")
            except Exception as e:
                print(f"⚠️  폰트 등록 실패 ({font_name}): {e}")
                continue
        
        # 4. 폰트를 찾지 못한 경우 - ReportLab CID 폰트 사용
        if not font_registered:
            try:
                # HeiseiMin-W3는 일본어지만 한글도 일부 지원
                # 또는 사용자에게 폰트 다운로드 안내
                print("⚠️ 시스템 한글 폰트를 찾을 수 없습니다.")
                print("ℹ️  나눔고딕 설치 방법:")
                print("   Ubuntu/Debian: sudo apt-get install fonts-nanum")
                print("   macOS: brew tap homebrew/cask-fonts && brew install font-nanum")
                print("   또는 https://hangeul.naver.com/font 에서 다운로드")
                print("\n⚠️ 임시로 기본 폰트(Helvetica)를 사용합니다 - 한글이 깨질 수 있습니다.")
                
                self.korean_font = 'Helvetica'
                self.korean_bold = 'Helvetica-Bold'
            except Exception as e:
                print(f"⚠️ 폰트 설정 실패: {e}")
                self.korean_font = 'Helvetica'
                self.korean_bold = 'Helvetica-Bold'
        
        # Bold 폰트가 없으면 일반 폰트 사용
        if not hasattr(self, 'korean_bold'):
            self.korean_bold = self.korean_font
            print(f"ℹ️  Bold 폰트를 일반 폰트로 대체: {self.korean_font}")
        
        # 최종 폰트 설정 출력
        print(f"\n📝 최종 폰트 설정:")
        print(f"   일반 폰트: {self.korean_font}")
        print(f"   Bold 폰트: {self.korean_bold}")
        print(f"   등록된 폰트 목록: {', '.join(pdfmetrics.getRegisteredFontNames()[:10])}...")
        print()
    
    def generate_report(
        self,
        all_patent_results: List[Dict[str, Any]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        종합 PDF 보고서 생성
        
        Args:
            all_patent_results: 모든 특허의 분석 결과
        
        Returns:
            보고서 경로 및 메타데이터
        """
        print("\n" + "="*80)
        print("📊 Generating PDF Report (ReportLab)")
        print("="*80)
        
        # 보고서 데이터 준비
        report_data = self._prepare_report_data(all_patent_results)
        
        # PDF 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.tech_name}_patent_analysis_report_{timestamp}.pdf"
        pdf_path = self.output_dir / filename
        
        # ReportLab PDF 생성
        self._create_pdf(pdf_path, report_data)
        
        print(f"✅ PDF Report: {pdf_path}")
        
        # JSON 메타데이터
        json_filename = f"{self.tech_name}_patent_analysis_report_{timestamp}.json"
        json_path = self.output_dir / json_filename
        
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
    
    def _prepare_report_data(
        self,
        all_patent_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """보고서 데이터 준비"""
        
        patents_summary = []
        total_originality = 0
        total_market = 0
        grade_distribution = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
        
        for result in all_patent_results:
            patent_id = result.get("target_patent_id", "N/A")
            patent_title = result.get("first_item", {}).get("title", "N/A")
            
            originality = result.get("originality_score", 0) or 0
            market = result.get("market_score", 0) or 0
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
                "market_size_score": result.get("market_size_score", 0) or 0,
                "growth_potential_score": result.get("growth_potential_score", 0) or 0,
                "commercialization_readiness": result.get("commercialization_readiness", 0) or 0,
                "application_domains": result.get("application_domains", []),
                "llm_evaluation": result.get("llm_evaluation", {})
            })
        
        n = len(all_patent_results)
        avg_originality = total_originality / n if n > 0 else 0
        avg_market = total_market / n if n > 0 else 0
        
        return {
            "title": f"{self.tech_name} Technology Competitiveness Analysis Report",
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
    
    def _create_pdf(self, pdf_path: Path, report_data: Dict[str, Any]):
        """PDF 파일 생성"""
        
        # PDF 문서 생성
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # 스타일 정의
        styles = self._create_styles()
        
        # 컨텐츠 Story
        story = []
        
        # 표지
        story.extend(self._generate_cover_page(report_data, styles))
        story.append(PageBreak())
        
        # 목차 (Table of Contents)
        story.extend(self._generate_table_of_contents(report_data, styles))
        story.append(PageBreak())
        
        # 1. SUMMARY
        story.extend(self._generate_summary(report_data, styles))
        story.append(PageBreak())
        
        # 2. DETAIL ANALYSIS
        story.extend(self._generate_detail_analysis(report_data, styles))
        story.append(PageBreak())
        
        # 3. REFERENCE
        story.extend(self._generate_reference(report_data, styles))
        story.append(PageBreak())
        
        # 4. APPENDIX
        story.extend(self._generate_appendix(report_data, styles))
        
        # PDF 빌드
        doc.build(story)
    
    def _create_styles(self):
        """PDF 스타일 생성"""
        styles = getSampleStyleSheet()
        
        # 등록된 폰트 확인
        korean_font = self.korean_font
        korean_bold = self.korean_bold
        
        # Title (표지)
        styles['Title'].fontName = korean_bold
        styles['Title'].fontSize = 28
        styles['Title'].textColor = colors.HexColor('#1a1a1a')
        styles['Title'].alignment = TA_CENTER
        styles['Title'].spaceAfter = 30
        
        # Heading1 (대제목)
        styles['Heading1'].fontName = korean_bold
        styles['Heading1'].fontSize = 20
        styles['Heading1'].textColor = colors.HexColor('#2c3e50')
        styles['Heading1'].spaceAfter = 15
        styles['Heading1'].spaceBefore = 25
        
        # Heading2 (중제목)
        styles['Heading2'].fontName = korean_bold
        styles['Heading2'].fontSize = 16
        styles['Heading2'].textColor = colors.HexColor('#34495e')
        styles['Heading2'].spaceAfter = 12
        styles['Heading2'].spaceBefore = 20
        
        # Heading3 (소제목)
        if 'Heading3' not in styles:
            styles.add(ParagraphStyle(
                name='Heading3',
                parent=styles['Heading2'],
                fontName=korean_bold,
                fontSize=14,
                textColor=colors.HexColor('#7f8c8d'),
                spaceAfter=10,
                spaceBefore=15
            ))
        else:
            styles['Heading3'].fontName = korean_bold
            styles['Heading3'].fontSize = 14
        
        # Body (본문)
        styles['BodyText'].fontName = korean_font
        styles['BodyText'].fontSize = 11
        styles['BodyText'].leading = 18
        styles['BodyText'].alignment = TA_JUSTIFY
        
        # Bullet (리스트)
        if 'Bullet' not in styles:
            styles.add(ParagraphStyle(
                name='Bullet',
                parent=styles['BodyText'],
                fontName=korean_font,
                leftIndent=20,
                spaceAfter=6
            ))
        
        return styles
    
    def _generate_cover_page(self, report_data: Dict[str, Any], styles):
        """표지 페이지"""
        content = []
        
        # 상단 여백
        content.append(Spacer(1, 2 * inch))
        
        # 제목
        title = Paragraph(report_data["title"], styles['Title'])
        content.append(title)
        content.append(Spacer(1, 0.5 * inch))
        
        # 부제
        subtitle_style = ParagraphStyle(
            name='Subtitle',
            parent=styles['BodyText'],
            fontName=self.korean_font,
            fontSize=14,
            textColor=colors.HexColor('#7f8c8d'),
            alignment=TA_CENTER
        )
        subtitle = Paragraph(
            "Patent Analysis Based Technology Competitiveness Evaluation",
            subtitle_style
        )
        content.append(subtitle)
        content.append(Spacer(1, 1.5 * inch))
        
        # 통계 요약 표
        stats = report_data["statistics"]
        data = [
            ["Analyzed Patents", f"{report_data['total_patents_analyzed']} cases"],
            ["Avg Originality Score", f"{stats['avg_originality_score']:.3f}"],
            ["Avg Market Score", f"{stats['avg_market_score']:.3f}"],
            ["S-Grade Patents", f"{stats['grade_distribution']['S']} cases"]
        ]
        
        table = Table(data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), self.korean_font, 12),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), self.korean_bold),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        content.append(table)
        content.append(Spacer(1, 1 * inch))
        
        # 생성 일시
        date_text = Paragraph(
            f"<i>Report Date: {report_data['generated_at_kr']}</i>",
            subtitle_style
        )
        content.append(date_text)
        
        return content
    
    def _generate_table_of_contents(self, report_data: Dict[str, Any], styles):
        """목차 페이지 (Table of Contents)"""
        content = []
        
        # 상단 여백
        content.append(Spacer(1, 1 * inch))
        
        # 목차 제목
        toc_title_style = ParagraphStyle(
            name='TOCTitle',
            parent=styles['Title'],
            fontName=self.korean_bold,
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            alignment=TA_CENTER,
            spaceAfter=30
        )
        content.append(Paragraph("TABLE OF CONTENTS", toc_title_style))
        content.append(Spacer(1, 0.5 * inch))
        
        # 목차 항목 스타일
        toc_item_style = ParagraphStyle(
            name='TOCItem',
            parent=styles['BodyText'],
            fontName=self.korean_font,
            fontSize=12,
            leading=20,
            leftIndent=20,
            spaceAfter=8
        )
        
        toc_sub_style = ParagraphStyle(
            name='TOCSubItem',
            parent=toc_item_style,
            fontSize=11,
            leftIndent=40,
            spaceAfter=5,
            textColor=colors.HexColor('#7f8c8d')
        )
        
        # 목차 내용
        toc_items = [
            ("1. SUMMARY", [
                "1.1 Technology Competitiveness Overview",
                "1.2 Evaluation Results by Technology Keywords",
                "1.3 Strengths and Areas for Improvement"
            ]),
            ("2. DETAIL ANALYSIS", [
                f"2.{i} Patent Analysis #{i}: {patent['patent_id']}" 
                for i, patent in enumerate(report_data["patents_summary"], 1)
            ]),
            ("3. REFERENCE", [
                "3.1 Patent Data Sources",
                "3.2 Data Sources and Methodology",
                "3.3 Key References",
                "3.4 Report Generation Info"
            ]),
            ("4. APPENDIX", [
                "4.1 Evaluation Methodology",
                "4.2 Multi-Agent Analysis Process",
                "4.3 Score Weighting"
            ])
        ]
        
        # 목차 항목 출력
        for section_title, subsections in toc_items:
            # 섹션 제목
            content.append(Paragraph(f"<b>{section_title}</b>", toc_item_style))
            
            # 하위 항목 (너무 많으면 생략)
            max_subsections = 5 if "DETAIL ANALYSIS" in section_title else len(subsections)
            for subsection in subsections[:max_subsections]:
                content.append(Paragraph(f"• {subsection}", toc_sub_style))
            
            # Detail Analysis가 3개 이상이면 생략 표시
            if "DETAIL ANALYSIS" in section_title and len(subsections) > max_subsections:
                remaining = len(subsections) - max_subsections
                content.append(Paragraph(f"• ... and {remaining} more patents", toc_sub_style))
            
            content.append(Spacer(1, 0.15 * inch))
        
        return content
    
    def _generate_summary(self, report_data: Dict[str, Any], styles):
        """1. SUMMARY 섹션"""
        content = []
        
        # 섹션 제목
        content.append(Paragraph("1. SUMMARY", styles['Heading1']))
        content.append(Spacer(1, 0.3 * inch))
        
        # 1.1 기술 경쟁력 개요
        content.append(Paragraph("1.1 Technology Competitiveness Overview", styles['Heading2']))
        content.append(Spacer(1, 0.15 * inch))
        
        # LLM 요약 또는 기본 요약
        if self.use_llm and self.llm:
            summary = self._generate_llm_summary(report_data)
            content.append(Paragraph(summary, styles['BodyText']))
        else:
            stats = report_data["statistics"]
            summary_text = f"""
            This report analyzes {report_data['total_patents_analyzed']} patents in the {self.tech_name} technology field 
            to evaluate technological competitiveness. The average originality score is {stats['avg_originality_score']:.3f},
            and the average market score is {stats['avg_market_score']:.3f}. This indicates {self._interpret_scores(stats)} 
            level of innovation and market readiness in the {self.tech_name} domain.
            """
            content.append(Paragraph(summary_text, styles['BodyText']))
        
        content.append(Spacer(1, 0.3 * inch))
        
        # 1.2 주요 기술 키워드별 평가 결과
        content.append(Paragraph("1.2 Evaluation Results by Technology Keywords", styles['Heading2']))
        content.append(Spacer(1, 0.15 * inch))
        
        # 등급 분포 테이블
        grade_dist = report_data["statistics"]["grade_distribution"]
        grade_data = [["Grade", "Count", "Percentage"]]
        total = report_data['total_patents_analyzed']
        
        for grade in ["S", "A", "B", "C", "D"]:
            count = grade_dist.get(grade, 0)
            if count > 0:
                percentage = f"{(count/total)*100:.1f}%"
                grade_data.append([grade, str(count), percentage])
        
        grade_table = Table(grade_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch])
        grade_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), self.korean_font, 10),
            ('FONT', (0, 0), (-1, 0), self.korean_bold, 11),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        content.append(grade_table)
        content.append(Spacer(1, 0.3 * inch))
        
        # 1.3 강점 및 개선 필요 영역
        content.append(Paragraph("1.3 Strengths and Areas for Improvement", styles['Heading2']))
        content.append(Spacer(1, 0.15 * inch))
        
        # 강점/약점 분석
        strengths, weaknesses = self._analyze_strengths_weaknesses(report_data)
        
        content.append(Paragraph("<b>Key Strengths:</b>", styles['Heading3']))
        for strength in strengths:
            content.append(Paragraph(f"• {strength}", styles['Bullet']))
        
        content.append(Spacer(1, 0.15 * inch))
        
        content.append(Paragraph("<b>Areas for Improvement:</b>", styles['Heading3']))
        for weakness in weaknesses:
            content.append(Paragraph(f"• {weakness}", styles['Bullet']))
        
        return content
    
    def _interpret_scores(self, stats: Dict) -> str:
        """점수 해석"""
        avg_orig = stats['avg_originality_score']
        avg_market = stats['avg_market_score']
        
        if avg_orig >= 0.8 and avg_market >= 0.7:
            return "a strong"
        elif avg_orig >= 0.6 or avg_market >= 0.6:
            return "a moderate"
        else:
            return "an emerging"
    
    def _analyze_strengths_weaknesses(self, report_data: Dict[str, Any]) -> tuple:
        """강점과 약점 분석"""
        stats = report_data["statistics"]
        patents = report_data["patents_summary"]
        
        strengths = []
        weaknesses = []
        
        # 독창성 분석
        if stats['avg_originality_score'] >= 0.8:
            strengths.append(f"High technical originality (avg: {stats['avg_originality_score']:.3f})")
        elif stats['avg_originality_score'] < 0.6:
            weaknesses.append(f"Low originality score indicates need for more innovative approaches")
        
        # 시장성 분석
        if stats['avg_market_score'] >= 0.7:
            strengths.append(f"Strong market potential (avg: {stats['avg_market_score']:.3f})")
        elif stats['avg_market_score'] < 0.5:
            weaknesses.append(f"Limited market readiness requires strategic positioning")
        
        # 등급 분포 분석
        grade_dist = stats['grade_distribution']
        s_and_a = grade_dist.get('S', 0) + grade_dist.get('A', 0)
        total = report_data['total_patents_analyzed']
        
        if s_and_a / total >= 0.5:
            strengths.append(f"High proportion of S/A grade patents ({s_and_a}/{total})")
        
        # 특허별 세부 분석
        high_market_patents = [p for p in patents if p.get('market_score', 0) >= 0.8]
        if len(high_market_patents) >= 2:
            strengths.append(f"Multiple patents with strong commercialization potential")
        
        # 기본 강점/약점이 없으면 추가
        if not strengths:
            strengths.append("Solid foundation for technology development")
        
        if not weaknesses:
            weaknesses.append("Continue monitoring market trends and competition")
        
        return strengths, weaknesses
    
    def _generate_detail_analysis(self, report_data: Dict[str, Any], styles):
        """2. DETAIL ANALYSIS 섹션"""
        content = []
        
        content.append(Paragraph("2. DETAIL ANALYSIS", styles['Heading1']))
        content.append(Spacer(1, 0.3 * inch))
        
        for i, patent in enumerate(report_data["patents_summary"], 1):
            if i > 1:
                content.append(PageBreak())
            
            # 특허 제목
            title_text = f"2.{i} Patent Analysis #{i}: {patent['patent_id']}"
            content.append(Paragraph(title_text, styles['Heading2']))
            content.append(Spacer(1, 0.15 * inch))
            
            # 특허명
            patent_title = patent['title']
            if len(patent_title) > 100:
                patent_title = patent_title[:100] + "..."
            content.append(Paragraph(f"<b>Title:</b> {patent_title}", styles['BodyText']))
            content.append(Spacer(1, 0.15 * inch))
            
            # 기술성 평가 섹션
            content.append(Paragraph("Technical Evaluation", styles['Heading3']))
            content.append(Spacer(1, 0.1 * inch))
            
            tech_data = [
                ["Metric", "Score", "Grade"],
                ["Originality", f"{patent['originality_score']:.3f}", patent['final_grade']],
                ["Overall Assessment", f"{patent['originality_score']:.3f}", self._get_score_level(patent['originality_score'])]
            ]
            
            tech_table = Table(tech_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
            tech_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), self.korean_font, 10),
                ('FONT', (0, 0), (-1, 0), self.korean_bold, 11),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ecc71')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            content.append(tech_table)
            content.append(Spacer(1, 0.2 * inch))
            
            # 시장성 평가 섹션
            content.append(Paragraph("Market Evaluation", styles['Heading3']))
            content.append(Spacer(1, 0.1 * inch))
            
            market_data = [
                ["Metric", "Score", "Assessment"],
                ["Market Size", f"{patent['market_size_score']:.2f}", self._get_score_level(patent['market_size_score'])],
                ["Growth Potential", f"{patent['growth_potential_score']:.2f}", self._get_score_level(patent['growth_potential_score'])],
                ["Commercialization Readiness", f"{patent['commercialization_readiness']:.2f}", self._get_score_level(patent['commercialization_readiness'])],
                ["Overall Market Score", f"{patent.get('market_score', 0):.2f}", self._get_score_level(patent.get('market_score', 0))]
            ]
            
            market_table = Table(market_data, colWidths=[2.5*inch, 1*inch, 1.5*inch])
            market_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), self.korean_font, 10),
                ('FONT', (0, 0), (-1, 0), self.korean_bold, 11),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            content.append(market_table)
            content.append(Spacer(1, 0.2 * inch))
            
            # 적용 분야
            domains = patent.get("application_domains", [])
            if domains:
                content.append(Paragraph("Application Domains", styles['Heading3']))
                content.append(Spacer(1, 0.1 * inch))
                for domain in domains:
                    content.append(Paragraph(f"• {domain}", styles['Bullet']))
                content.append(Spacer(1, 0.15 * inch))
            
            # LLM 평가
            llm_eval = patent.get("llm_evaluation", {})
            if llm_eval:
                content.append(Paragraph("Investment Analysis", styles['Heading3']))
                content.append(Spacer(1, 0.1 * inch))
                
                investment = llm_eval.get("investment_recommendation", "N/A")
                risk = llm_eval.get("risk_level", "N/A")
                
                content.append(Paragraph(f"• <b>Investment Recommendation:</b> {investment}", styles['Bullet']))
                content.append(Paragraph(f"• <b>Risk Level:</b> {risk}", styles['Bullet']))
                
                # 추가 평가 정보
                reasoning = llm_eval.get("reasoning", "")
                if reasoning:
                    content.append(Spacer(1, 0.1 * inch))
                    content.append(Paragraph(f"<b>Rationale:</b> {reasoning}", styles['BodyText']))
        
        return content
    
    def _get_score_level(self, score: float) -> str:
        """점수를 레벨로 변환"""
        if score >= 0.8:
            return "Excellent"
        elif score >= 0.6:
            return "Good"
        elif score >= 0.4:
            return "Moderate"
        elif score >= 0.2:
            return "Fair"
        else:
            return "Limited"
    
    def _generate_llm_summary(self, report_data: Dict[str, Any]) -> str:
        """LLM 기반 요약 생성"""
        stats = report_data["statistics"]
        
        prompt = f"""You are a patent analysis expert. Please write an investment overview based on the following information.

Technology: {self.tech_name}
Number of Patents Analyzed: {report_data['total_patents_analyzed']}
Average Originality: {stats['avg_originality_score']:.3f}
Average Market Score: {stats['avg_market_score']:.3f}
Grade Distribution: S-grade {stats['grade_distribution']['S']}, A-grade {stats['grade_distribution']['A']}

Please summarize the investment attractiveness in 3-4 paragraphs, explaining the technical strengths and market outlook."""
        
        try:
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            print(f"⚠️ LLM summary failed: {e}")
            return f"Patent analysis results for {self.tech_name} technology field."
    
    def _generate_reference(self, report_data: Dict[str, Any], styles):
        """3. REFERENCE 섹션"""
        content = []
        
        content.append(Paragraph("3. REFERENCE", styles['Heading1']))
        content.append(Spacer(1, 0.3 * inch))
        
        content.append(Paragraph("3.1 Patent Data Sources", styles['Heading2']))
        content.append(Spacer(1, 0.15 * inch))
        
        # 특허 목록 테이블
        ref_data = [["No.", "Patent ID", "Title"]]
        
        for i, patent in enumerate(report_data["patents_summary"], 1):
            patent_id = patent['patent_id']
            title = patent['title']
            if len(title) > 60:
                title = title[:60] + "..."
            ref_data.append([str(i), patent_id, title])
        
        ref_table = Table(ref_data, colWidths=[0.5*inch, 1.5*inch, 4*inch])
        ref_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), self.korean_font, 9),
            ('FONT', (0, 0), (-1, 0), self.korean_bold, 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        content.append(ref_table)
        content.append(Spacer(1, 0.3 * inch))
        
        # 데이터 소스
        content.append(Paragraph("3.2 Data Sources and Methodology", styles['Heading2']))
        content.append(Spacer(1, 0.15 * inch))
        
        sources = [
            "Patent databases: USPTO, EPO, KIPO",
            "Market analysis: Industry reports and market research data",
            "Technology evaluation: Academic papers and technical documentation",
            "LLM-based analysis: GPT-4 for qualitative assessment"
        ]
        
        for source in sources:
            content.append(Paragraph(f"• {source}", styles['Bullet']))
        
        content.append(Spacer(1, 0.3 * inch))
        
        # 참고 문헌
        content.append(Paragraph("3.3 Key References", styles['Heading2']))
        content.append(Spacer(1, 0.15 * inch))
        
        references = [
            {
                "title": "Originality Index Methodology",
                "source": "Park, S.Y., & Lee, S.J. (2020). A Study on Derivation Method of Promising Industry-University Cooperation Fields Based on Patents. Ajou University."
            },
            {
                "title": "AI Semiconductor Market Data",
                "source": "ICT Market Trends by Product Category - AI Semiconductor. Global ICT Portal (2024.09.27)"
            },
            {
                "title": "AI Semiconductor Market Status and Outlook",
                "source": "Korea Eximbank - Overseas Economic Research Institute. Issue Report Vol.2024 (May 2024)"
            }
        ]
        
        for i, ref in enumerate(references, 1):
            content.append(Paragraph(f"<b>[{i}] {ref['title']}</b>", styles['BodyText']))
            content.append(Paragraph(f"    {ref['source']}", styles['Bullet']))
            content.append(Spacer(1, 0.1 * inch))
        
        content.append(Spacer(1, 0.3 * inch))
        
        # 생성 정보
        content.append(Paragraph("3.4 Report Generation Info", styles['Heading2']))
        content.append(Spacer(1, 0.15 * inch))
        
        info_data = [
            ["Report Generated", report_data['generated_at_kr']],
            ["Technology Domain", self.tech_name],
            ["Analysis Method", "Multi-Agent AI System"],
            ["Total Patents Analyzed", str(report_data['total_patents_analyzed'])]
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), self.korean_font, 10),
            ('FONTNAME', (0, 0), (0, -1), self.korean_bold),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        content.append(info_table)
        
        return content
    
    def _generate_appendix(self, report_data: Dict[str, Any], styles):
        """4. APPENDIX 섹션"""
        content = []
        
        content.append(Paragraph("4. APPENDIX", styles['Heading1']))
        content.append(Spacer(1, 0.3 * inch))
        
        # 4.1 평가 로직 설명
        content.append(Paragraph("4.1 Evaluation Methodology", styles['Heading2']))
        content.append(Spacer(1, 0.15 * inch))
        
        content.append(Paragraph("<b>Overall Scoring System</b>", styles['Heading3']))
        content.append(Spacer(1, 0.1 * inch))
        
        methodology_text = """
        The patent evaluation system uses a multi-dimensional scoring approach combining 
        quantitative metrics and qualitative assessments. Each patent is evaluated across 
        two primary dimensions: Technical Originality and Market Potential.
        """
        content.append(Paragraph(methodology_text, styles['BodyText']))
        content.append(Spacer(1, 0.2 * inch))
        
        # Originality Index 상세 설명
        content.append(Paragraph("<b>1. Technical Originality (Originality Index)</b>", styles['Heading3']))
        content.append(Spacer(1, 0.1 * inch))
        
        originality_text = """
        This methodology references the Originality Index formula proposed by Park, S.Y. & Lee, S.J. (2020) 
        from Ajou University's research on "A Study on Derivation Method of Promising Industry-University 
        Cooperation Fields Based on Patents".
        """
        content.append(Paragraph(originality_text, styles['BodyText']))
        content.append(Spacer(1, 0.1 * inch))
        
        # 공식 설명 (간단한 텍스트로)
        formula_text = """
        <b>Formula:</b> Originality = 1 - Σ(NCITED_ik / NCITED_i)²
        <br/>
        where:
        <br/>
        • NCITED_ik: Number of citations in k-th CPC (Cooperative Patent Classification) class
        <br/>
        • NCITED_i: Total citations of patent i
        <br/>
        • Score range: 0 to 1 (0 = low diversity, 1 = high diversity)
        """
        content.append(Paragraph(formula_text, styles['BodyText']))
        content.append(Spacer(1, 0.2 * inch))
        
        # Market Score 공식
        content.append(Paragraph("<b>2. Market Score Calculation</b>", styles['Heading3']))
        content.append(Spacer(1, 0.1 * inch))
        
        market_formula = """
        <b>Formula:</b> MarketScore = MarketSize + GrowthPotential + Commercialization
        <br/>
        <br/>
        This composite score evaluates the commercial viability across three key dimensions,
        each normalized to a 0-1 scale.
        """
        content.append(Paragraph(market_formula, styles['BodyText']))
        content.append(Spacer(1, 0.2 * inch))
        
        # Market Size 세부 기준
        content.append(Paragraph("<b>2.1 Market Size Scoring Criteria (0~0.4)</b>", styles['Heading3']))
        content.append(Spacer(1, 0.1 * inch))
        
        market_size_data = [
            ["Score", "TAM (Serviceable Market)", "Examples"],
            ["0.35~0.4", "$10B+", "LLM-based infrastructure $12B,\nCloud $18B"],
            ["0.25~0.35", "$3B~$10B", "Advanced system memory $5B,\nEnterprise storage $6B"],
            ["0.15~0.25", "$1B~$3B", "Specialized model optimization $1.5B"],
            ["0.1~0.15", "$300M~$1B", "Medical imaging NPU $800M"],
            ["0~0.1", "< $300M", "Experimental tech, Early POC"]
        ]
        
        market_size_table = Table(market_size_data, colWidths=[0.8*inch, 1.5*inch, 3.7*inch])
        market_size_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), self.korean_font, 8),
            ('FONT', (0, 0), (-1, 0), self.korean_bold, 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        content.append(market_size_table)
        content.append(Spacer(1, 0.2 * inch))
        
        # Growth Potential 세부 기준
        content.append(Paragraph("<b>2.2 Growth Potential Scoring Criteria (0~0.3)</b>", styles['Heading3']))
        content.append(Spacer(1, 0.1 * inch))
        
        growth_data = [
            ["Score", "CAGR / Market Forecast", "Examples"],
            ["0.25~0.3", "25%+ / 5yr 2x+", "2025: $310M → 2029: $602M"],
            ["0.2~0.25", "20~25%", "CAGR 23%, 5yr 1.8x"],
            ["0.15~0.2", "15~20%", "17% continuous growth"],
            ["0.1~0.15", "10~15%", "CAGR 11%"],
            ["0~0.1", "< 10%", "Stagnant or declining"]
        ]
        
        growth_table = Table(growth_data, colWidths=[0.8*inch, 2*inch, 3.2*inch])
        growth_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), self.korean_font, 8),
            ('FONT', (0, 0), (-1, 0), self.korean_bold, 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ecc71')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        content.append(growth_table)
        content.append(Spacer(1, 0.2 * inch))
        
        # Commercialization Readiness 세부 기준
        content.append(Paragraph("<b>2.3 Commercialization Readiness (0~0.3)</b>", styles['Heading3']))
        content.append(Spacer(1, 0.1 * inch))
        
        commercial_data = [
            ["Score", "Time to Market", "Characteristics"],
            ["0.25~0.3", "< 1 year", "Product launch, Mature tech"],
            ["0.2~0.25", "1~2 years", "Prototype validation complete"],
            ["0.15~0.2", "2~3 years", "Patent filed"],
            ["0.1~0.15", "3~5 years", "Early R&D, Standard required"],
            ["0~0.1", "5+ years", "Basic research unclear"]
        ]
        
        commercial_table = Table(commercial_data, colWidths=[0.8*inch, 1.5*inch, 3.7*inch])
        commercial_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), self.korean_font, 8),
            ('FONT', (0, 0), (-1, 0), self.korean_bold, 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e67e22')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        content.append(commercial_table)
        content.append(Spacer(1, 0.3 * inch))
        
        # 페이지 브레이크
        content.append(PageBreak())
        
        # 점수 기준 표
        content.append(Paragraph("<b>Grade Classification</b>", styles['Heading3']))
        content.append(Spacer(1, 0.1 * inch))
        
        grade_criteria = [
            ["Grade", "Score Range", "Description"],
            ["S", "0.90 - 1.00", "Exceptional - Breakthrough innovation with high market potential"],
            ["A", "0.75 - 0.89", "Excellent - Strong technical merit and commercial viability"],
            ["B", "0.60 - 0.74", "Good - Solid innovation with moderate market potential"],
            ["C", "0.40 - 0.59", "Fair - Basic innovation with limited market appeal"],
            ["D", "0.00 - 0.39", "Limited - Incremental improvement or unclear market fit"]
        ]
        
        grade_table = Table(grade_criteria, colWidths=[0.7*inch, 1.3*inch, 4*inch])
        grade_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), self.korean_font, 9),
            ('FONT', (0, 0), (-1, 0), self.korean_bold, 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        content.append(grade_table)
        content.append(Spacer(1, 0.3 * inch))
        
        # 4.2 Agent 분석 프로세스
        content.append(Paragraph("4.2 Multi-Agent Analysis Process", styles['Heading2']))
        content.append(Spacer(1, 0.15 * inch))
        
        process_text = """
        The analysis employs a multi-agent system where specialized AI agents perform 
        different analytical tasks:
        """
        content.append(Paragraph(process_text, styles['BodyText']))
        content.append(Spacer(1, 0.15 * inch))
        
        agents = [
            ("Search Agent", "Retrieves relevant patent data from multiple databases"),
            ("Analysis Agent", "Evaluates technical originality using NLP and similarity metrics"),
            ("Market Agent", "Assesses commercial potential based on market data and trends"),
            ("Suitability Agent", "Synthesizes scores and generates investment recommendations"),
            ("Report Agent", "Compiles findings into structured analytical reports")
        ]
        
        for agent_name, agent_desc in agents:
            content.append(Paragraph(f"<b>{agent_name}:</b> {agent_desc}", styles['Bullet']))
        
        content.append(Spacer(1, 0.3 * inch))
        
        # 4.3 점수 가중치
        content.append(Paragraph("4.3 Score Weighting", styles['Heading2']))
        content.append(Spacer(1, 0.15 * inch))
        
        weight_data = [
            ["Component", "Weight", "Justification"],
            ["Originality Score", "55%", "Primary indicator of innovation quality"],
            ["Market Score", "45%", "Commercial viability and market readiness"],
            ["", "", ""],
            ["Market Score Breakdown:", "", ""],
            ["- Market Size", "33%", "Total addressable market potential"],
            ["- Growth Potential", "33%", "Expected market expansion rate"],
            ["- Commercialization", "33%", "Technology readiness level"]
        ]
        
        weight_table = Table(weight_data, colWidths=[2*inch, 1*inch, 3*inch])
        weight_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), self.korean_font, 9),
            ('FONT', (0, 0), (-1, 0), self.korean_bold, 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16a085')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, 2), 1, colors.HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('SPAN', (0, 3), (2, 3)),
            ('FONTNAME', (0, 3), (0, 3), self.korean_bold),
        ]))
        
        content.append(weight_table)
        content.append(Spacer(1, 0.2 * inch))
        
        # 면책 조항
        disclaimer = """
        <b>Disclaimer:</b> This report is generated by an AI-powered analysis system and should be used 
        as a reference tool. Investment decisions should be made based on comprehensive due diligence 
        and professional consultation. The scores and grades represent relative assessments within 
        the analyzed patent set and may not reflect absolute market value.
        """
        content.append(Paragraph(disclaimer, styles['BodyText']))
        
        return content


def pdf_report_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph 노드로 사용 가능한 PDF Report Agent"""
    
    print("\n" + "="*80)
    print("📊 Step 5: PDF Report Generation")
    print("="*80)
    
    if state.get("error"):
        print(f"⚠️ Skipping due to error: {state['error']}")
        return state
    
    tech_name = state.get("tech_name", "AI Chip")
    all_patent_results = state.get("all_patent_results", [])
    
    if not all_patent_results:
        print("⚠️ No patent results")
        state["error"] = "No patent results"
        return state
    
    try:
        agent = ReportAgent(
            tech_name=tech_name,
            output_dir=state.get("output_dir", "./output/reports"),
            use_llm=state.get("use_llm", True)
        )
        
        result = agent.generate_report(all_patent_results)
        state.update(result)
        
        print(f"✅ PDF Report: {result['report_pdf_path']}")
        
    except Exception as e:
        print(f"❌ PDF Report failed: {e}")
        import traceback
        traceback.print_exc()
        state["error"] = f"PDF Report error: {e}"
    
    return state


if __name__ == "__main__":
    # 테스트
    test_results = [{
        "target_patent_id": "US20240001234",
        "first_item": {"title": "Advanced NPU Architecture"},
        "originality_score": 0.93,
        "market_score": 0.82,
        "market_size_score": 0.35,
        "growth_potential_score": 0.27,
        "commercialization_readiness": 0.20,
        "final_grade": "A",
        "application_domains": ["Edge AI", "Mobile"],
        "llm_evaluation": {
            "investment_recommendation": "Recommended",
            "risk_level": "Medium"
        }
    }]
    
    agent = ReportAgent(tech_name="NPU", use_llm=False)
    result = agent.generate_report(test_results)
    print(json.dumps(result, indent=2, ensure_ascii=False))