PYTHON ?= python3

.PHONY: build test validate simulate check

build:
	$(PYTHON) scripts/build_profiles.py

test:
	$(PYTHON) -m unittest discover -s tests -v

validate:
	$(PYTHON) scripts/build_profiles.py --check
	$(PYTHON) scripts/validate_repository.py
	$(PYTHON) scripts/check_report_current.py
	$(PYTHON) scripts/publish.py --check --ref "$$(cat dist/RELEASE_REF)"

simulate:
	$(PYTHON) scripts/simulate_routing.py

check: test validate simulate
