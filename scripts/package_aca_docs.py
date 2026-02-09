from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


def main() -> int:
	parser = argparse.ArgumentParser(description="Package ACA module PDFs into a zip archive.")
	parser.add_argument("--input", default="output/pdf/aca_v4", help="Directory containing generated ACA PDFs.")
	parser.add_argument("--output", default="output/pdf/aca_v4/ACA_v4_Module_Docs.zip", help="Zip path.")
	args = parser.parse_args()

	input_dir = Path(args.input)
	output_zip = Path(args.output)
	output_zip.parent.mkdir(parents=True, exist_ok=True)

	if not input_dir.exists():
		raise SystemExit(f"Input directory not found: {input_dir}")

	pdf_paths = sorted(path for path in input_dir.glob("*.pdf") if path.is_file())
	if not pdf_paths:
		raise SystemExit(f"No PDF files found in: {input_dir}")

	with zipfile.ZipFile(output_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
		for pdf_path in pdf_paths:
			zf.write(pdf_path, arcname=pdf_path.name)
		manifest = input_dir / "build_manifest.txt"
		if manifest.exists():
			zf.write(manifest, arcname=manifest.name)

	print(f"packaged: {output_zip}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())

