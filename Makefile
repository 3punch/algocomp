.PHONY: help test demo reports matrix clean

PY ?= python3

help:
	@echo "algo-compare — make targets"
	@echo "  make test      run the unit test suite"
	@echo "  make demo      run a few example comparisons in the terminal"
	@echo "  make reports   regenerate the HTML/Markdown reports in reports/"
	@echo "  make matrix    print the sorting complexity matrix"
	@echo "  make clean     remove __pycache__ and reports"

test:
	$(PY) -m unittest discover -s tests -t . -v

demo:
	$(PY) algo-compare compare merge_sort quick_sort
	$(PY) algo-compare compare dijkstra_binary_heap bellman_ford --no-chart
	$(PY) algo-compare compare jump_search binary_search

matrix:
	$(PY) algo-compare matrix --category sorting --space

reports:
	$(PY) examples/generate_reports.py

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf reports
