from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List


def _load_markdown_paths(modules_dir: Path) -> List[Path]:
	return sorted(path for path in modules_dir.glob("module_*.md") if path.is_file())


def _render_pdf(markdown_path: Path, output_path: Path) -> None:
	try:
		from reportlab.lib.pagesizes import LETTER
		from reportlab.lib.styles import getSampleStyleSheet
		from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
	except ImportError as exc:
		raise RuntimeError("reportlab is required. Install with: pip install reportlab") from exc

	styles = getSampleStyleSheet()
	story = []
	lines = markdown_path.read_text(encoding="utf-8").splitlines()
	for raw in lines:
		line = raw.rstrip()
		if not line:
			story.append(Spacer(1, 8))
			continue
		if line.startswith("# "):
			story.append(Paragraph(line[2:].strip(), styles["Heading1"]))
			continue
		if line.startswith("## "):
			story.append(Paragraph(line[3:].strip(), styles["Heading2"]))
			continue
		if line.startswith("- "):
			story.append(Paragraph(f"&bull; {line[2:].strip()}", styles["BodyText"]))
			continue
		if line.startswith("```"):
			# Keep fences out of output.
			continue
		story.append(Paragraph(line, styles["BodyText"]))

	doc = SimpleDocTemplate(str(output_path), pagesize=LETTER, title=markdown_path.stem)
	doc.build(story)


def _write_manifest(paths: Iterable[Path], manifest_path: Path) -> None:
	lines = ["ACA v4 PDF Build Manifest", ""]
	for path in paths:
		lines.append(str(path))
	manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
	parser = argparse.ArgumentParser(description="Build ACA module PDFs from markdown sources.")
	parser.add_argument("--source", default="docs/aca_v4/modules", help="Path to module markdown docs.")
	parser.add_argument("--output", default="output/pdf/aca_v4", help="Output directory for generated PDFs.")
	args = parser.parse_args()

	source_dir = Path(args.source)
	output_dir = Path(args.output)
	output_dir.mkdir(parents=True, exist_ok=True)

	if not source_dir.exists():
		raise SystemExit(f"Source directory not found: {source_dir}")

	markdown_paths = _load_markdown_paths(source_dir)
	if not markdown_paths:
		raise SystemExit(f"No module markdown files found in: {source_dir}")

	generated: List[Path] = []
	for markdown_path in markdown_paths:
		pdf_name = f"ACA_v4_{markdown_path.stem}.pdf"
		pdf_path = output_dir / pdf_name
		_render_pdf(markdown_path, pdf_path)
		generated.append(pdf_path)
		print(f"generated: {pdf_path}")

	manifest_path = output_dir / "build_manifest.txt"
	_write_manifest(generated, manifest_path)
	print(f"manifest: {manifest_path}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())

