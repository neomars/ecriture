import datetime
import os

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    version = "unknown"
    try:
        with open("main.py", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("CURRENT_VERSION"):
                    version = line.split("=")[1].strip().strip('"').strip("'")
                    break
    except Exception:
        pass

    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    passed = terminalreporter.stats.get('passed', [])
    failed = terminalreporter.stats.get('failed', [])
    skipped = terminalreporter.stats.get('skipped', [])
    error = terminalreporter.stats.get('error', [])

    report_lines = []
    report_lines.append(f"=== Rapport de Test ===")
    report_lines.append(f"Version : {version}")
    report_lines.append(f"Date : {date_str}")
    report_lines.append(f"Heure : {time_str}")
    report_lines.append(f"Statut : {'Succès' if exitstatus == 0 else 'Échec'}")
    report_lines.append("-" * 30)

    for test in passed:
        report_lines.append(f"[SUCCÈS] {test.nodeid}")
    for test in failed:
        report_lines.append(f"[ÉCHEC] {test.nodeid}")
    for test in error:
        report_lines.append(f"[ERREUR] {test.nodeid}")
    for test in skipped:
        report_lines.append(f"[IGNORÉ] {test.nodeid}")

    report_lines.append("=" * 30 + "\n")

    with open("rapport_tests.txt", "a", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
