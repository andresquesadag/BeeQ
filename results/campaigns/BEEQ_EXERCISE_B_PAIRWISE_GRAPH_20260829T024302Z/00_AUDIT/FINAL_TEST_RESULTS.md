# Final test results

- Targeted Exercise A + CR8 + Exercise B tests: **11 passed** in 20.47 s.
- Full repository suite: **24 passed, 2 failed** in 23.70 s.
- Both failures are historical audit hash checks caused exclusively by physical
  CRLF line endings on Windows. Canonicalizing CRLF to LF makes all eight
  mismatching files equal their recorded SHA-256 values (five versioned datasets
  and three retained-campaign outputs).
- Historical expectations, datasets, and retained manifests were not modified.

Command: `.\.venv\Scripts\python.exe -m pytest -q`

