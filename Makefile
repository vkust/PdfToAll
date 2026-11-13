.PHONY: install test lint sample api package-linux clean

install:
	python -m pip install -e ".[dev,api]"

test:
	python -m pytest -q

lint:
	python -m ruff check src tests

sample:
	python -c "import sys; sys.path.insert(0,'tests'); from conftest import build_sample_pdf; build_sample_pdf('samples/quarterly-review.pdf')"
	pdftoall convert samples/quarterly-review.pdf -o samples/out

api:
	uvicorn pdftoall.api:app --host 127.0.0.1 --port 8765

package-linux:
	NFPM=$${NFPM:-nfpm} bash packaging/build-linux.sh

clean:
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info samples/out
