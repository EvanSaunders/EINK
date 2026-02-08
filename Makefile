# Makefile

.PHONY: run

run:
	@echo "Running e-ink app..."
	~/EINK/venv/bin/python main.py
stop:
	sudo pkill -9 -f main.py


run_dash:
	@echo "Running e-ink app..."
	~/EINK/venv/bin/python dashboardMain.py
stop_dash:
	sudo pkill -9 -f dashboardMain.py



