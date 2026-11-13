#!/usr/bin/env bash
# Build the frozen binary and Linux packages (.deb, .rpm, .tar.gz).
#
#   NFPM=/usr/local/bin/nfpm packaging/build-linux.sh 0.1.0
#
# Requires: pyinstaller, nfpm (https://github.com/goreleaser/nfpm).
set -euo pipefail

VERSION="${1:-$(python -c 'import pdftoall; print(pdftoall.__version__)')}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NFPM="${NFPM:-nfpm}"
cd "$ROOT"

echo "== version $VERSION, $(uname -m) =="
rm -rf build/pyinstaller dist
mkdir -p dist/packages

# --collect-all: python-pptx/python-docx ship .pptx/.docx templates inside the
# package; pdfminer ships cmap data. Missing any of them fails at runtime, not at
# build time, so they are all collected explicitly.
python -m PyInstaller \
  --noconfirm --clean --onedir --console \
  --name pdftoall \
  --paths src \
  --collect-all pdfplumber \
  --collect-all pdfminer \
  --collect-all pptx \
  --collect-all docx \
  --collect-all openpyxl \
  --collect-data pypdf \
  --distpath dist --workpath build/pyinstaller --specpath build/pyinstaller \
  packaging/pyinstaller_entry.py

echo "== smoke test =="
./dist/pdftoall/pdftoall --version
./dist/pdftoall/pdftoall info samples/quarterly-review.pdf

echo "== packages =="
python packaging/render_nfpm.py "$VERSION" > dist/packages/nfpm.yaml
for fmt in deb rpm; do
  "$NFPM" package -f dist/packages/nfpm.yaml -p "$fmt" -t dist/packages/
done
tar -czf "dist/packages/pdftoall-${VERSION}-linux-$(uname -m).tar.gz" -C dist pdftoall

ls -lh dist/packages/
