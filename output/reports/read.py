from __future__ import annotations
import sys, os, subprocess, shutil
from pathlib import Path

# ✅ 올바른 PDF 경로 입력 (하나만!)
TARGET_PDF = Path(
    r"C:\workspace\skala_gai\Patent-analysis-report\output\reports\한국_NPU_기술경쟁력보고서_20251023_151132.pdf"
)

def _is_wsl() -> bool:
    try:
        with open("/proc/version", "r", encoding="utf-8") as f:
            return "microsoft" in f.read().lower()
    except Exception:
        return False

def open_pdf(pdf_path: Path) -> None:
    pdf = pdf_path.resolve()
    if not pdf.exists():
        raise FileNotFoundError(f"PDF not found: {pdf}")

    if sys.platform.startswith("win"):
        os.startfile(str(pdf))  # type: ignore[attr-defined]
        return

    if _is_wsl():
        if shutil.which("wslview"):
            subprocess.run(["wslview", str(pdf)], check=False)
            return
        try:
            win_path = subprocess.check_output(["wslpath", "-w", str(pdf)], text=True).strip()
            subprocess.run(["explorer.exe", win_path], check=False)
            return
        except Exception:
            pass

    if sys.platform.startswith("darwin"):
        subprocess.run(["open", str(pdf)], check=False)
        return

    if shutil.which("xdg-open"):
        subprocess.run(["xdg-open", str(pdf)], check=False)
        return

    print(f"⚠️ 자동으로 열 수 없습니다. 직접 열어주세요: {pdf}")

def main() -> int:
    try:
        print(f"📖 Opening: {TARGET_PDF}")
        open_pdf(TARGET_PDF)
        print("✅ PDF가 열렸습니다!")
        return 0
    except Exception as e:
        print(f"❌ Failed to open PDF: {e}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())