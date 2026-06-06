# Local performance checks

These scripts provide repeatable local measurements without CI pass/fail thresholds.

Generate fixture databases:

```powershell
python -m scripts.generate_perf_database .test_runtime/perf_5k.sqlite3 --projects 100 --tasks 5000 --links 1000
python -m scripts.generate_perf_database .test_runtime/perf_20k.sqlite3 --projects 400 --tasks 20000 --links 5000
```

Measure `fetch_tasks`, global search, `TasksModel.refresh()`, and task/project form construction in offscreen Qt mode:

```powershell
python -m scripts.run_perf_benchmarks .test_runtime/perf_5k.sqlite3 --iterations 10 --warmup 2 --json-output docs/perf/perf_5k.json
python -m scripts.run_perf_benchmarks .test_runtime/perf_20k.sqlite3 --iterations 10 --warmup 2 --json-output docs/perf/perf_20k.json
```

Use repeated `--query` options to control the global-search workload. Generated JSON reports include environment metadata and p50/p95, min, max, and mean durations in milliseconds.
