# Makefile

.PHONY: run

run:
	@echo "Running e-ink app..."
	~/EINK/venv/bin/python main.py
stop:
	sudo pkill -9 -f main.py



