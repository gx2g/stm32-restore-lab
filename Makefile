.PHONY: install test lint fmt clean cycle-nucleo cycle-bl475 help

PYTHON   := python
PIP      := pip
VENV     := .venv
ACTIVATE := source $(VENV)/bin/activate

# Default target
help:
	@echo "restore-tools-lab — available targets"
	@echo ""
	@echo "  install        Create venv and install package in editable mode"
	@echo "  test           Run the full test suite"
	@echo "  lint           Run ruff linter"
	@echo "  fmt            Run ruff formatter (auto-fix)"
	@echo "  clean          Remove build artefacts and caches"
	@echo ""
	@echo "  cycle-nucleo   Run a full flash+verify cycle on the NUCLEO-F411RE"
	@echo "  cycle-bl475    Run a full flash+verify cycle on the B-L475E-IOT01A"
	@echo ""
	@echo "Board configs:  configs/nucleo_f411re.yaml"
	@echo "                configs/bl475e_iot01a.yaml"

# ---- Environment ---------------------------------------------------------- #

install:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -e .[dev]
	@echo ""
	@echo "Done. Activate with:  source $(VENV)/bin/activate"

# ---- Quality -------------------------------------------------------------- #

test:
	pytest -v

lint:
	ruff check src/ tests/

fmt:
	ruff check --fix src/ tests/
	ruff format src/ tests/

# ---- Board workflows ------------------------------------------------------ #

NUCLEO_CFG := configs/nucleo_f411re.yaml
BL475_CFG  := configs/bl475e_iot01a.yaml
IMAGE      ?= firmware/blink/blink.bin

cycle-nucleo:
	restore-tools-lab cycle --config $(NUCLEO_CFG) --image $(IMAGE)

cycle-bl475:
	restore-tools-lab cycle --config $(BL475_CFG) --image $(IMAGE)

# Flash only (no verify)
flash-nucleo:
	restore-tools-lab flash --config $(NUCLEO_CFG) --image $(IMAGE)

flash-bl475:
	restore-tools-lab flash --config $(BL475_CFG) --image $(IMAGE)

# Serial log only
log-nucleo:
	restore-tools-lab log --config $(NUCLEO_CFG) --duration 30 \
	    --output logs/raw/nucleo_f411re.log

log-bl475:
	restore-tools-lab log --config $(BL475_CFG) --duration 30 \
	    --output logs/raw/bl475e_iot01a.log

# ---- Cleanup -------------------------------------------------------------- #

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
