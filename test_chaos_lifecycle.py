import os
import sys
import time
import urllib.request
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

options = Options()
options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
options.add_argument("--headless=new")
options.add_argument("--window-size=1440,900")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

print("==================================================")
print("TESTING INJECT BLACKOUT & RECOVER LIFECYCLE")
print("==================================================")

driver = webdriver.Chrome(options=options)
try:
    print("\n[Step 1] Loading Dashboard (http://localhost:8500)...")
    driver.get("http://localhost:8500")
    time.sleep(3)

    # Check on-prem service healthz directly
    h_before = urllib.request.urlopen("http://127.0.0.1:8080/healthz").read().decode()
    print("Direct On-Prem Service Check (/healthz):", h_before)

    # Check dashboard API status
    status_raw = urllib.request.urlopen("http://localhost:8500/api/status").read().decode()
    s_data = json.loads(status_raw)
    print("Baseline Status:")
    print(f"  Leader: {s_data['kpis']['active_site']}")
    print(f"  Quorum: {s_data['quorum']['consecutive_failures']} / {s_data['quorum']['failure_threshold']}")
    print(f"  Signals Healthy: {s_data['kpis']['healthy_signals']}/{s_data['kpis']['total_signals']}")
    for sig in s_data['signals']:
        print(f"    - {sig['name']}: {sig['status']} ({sig['latency_ms']} ms)")

    driver.save_screenshot("proof_1_healthy.png")
    print("Saved screenshot: proof_1_healthy.png")

    # Find buttons
    btns = driver.find_elements(By.TAG_NAME, "button")
    chaos_btn = None
    recover_btn = None
    for b in btns:
        if "Blackout" in b.text:
            chaos_btn = b
        elif "Recover" in b.text:
            recover_btn = b

    print("\n[Step 2] Clicking '💥 Inject Blackout' button in UI...")
    chaos_btn.click()
    time.sleep(3)

    # Check on-prem service healthz directly
    try:
        urllib.request.urlopen("http://127.0.0.1:8080/healthz")
        blackout_h = "200 OK (Unexpected)"
    except urllib.error.HTTPError as e:
        blackout_h = f"{e.code} {e.reason} (Expected: 503)"
    print("Direct On-Prem Service Check after Blackout:", blackout_h)

    # Check dashboard API status after blackout
    status_blackout = json.loads(urllib.request.urlopen("http://localhost:8500/api/status").read().decode())
    print("Status after Blackout:")
    print(f"  Leader: {status_blackout['kpis']['active_site']}")
    print(f"  Quorum: {status_blackout['quorum']['consecutive_failures']} / {status_blackout['quorum']['failure_threshold']}")
    print(f"  Signals Healthy: {status_blackout['kpis']['healthy_signals']}/{status_blackout['kpis']['total_signals']}")
    for sig in status_blackout['signals']:
        print(f"    - {sig['name']}: {sig['status']} ({sig['message']})")

    driver.save_screenshot("proof_2_blackout.png")
    print("Saved screenshot: proof_2_blackout.png")

    term = driver.find_element(By.ID, "terminal-body")
    print("\nTerminal output after Blackout:")
    print(term.text[-400:])

    print("\n[Step 3] Clicking '🔄 Recover' button in UI...")
    recover_btn.click()
    time.sleep(3)

    # Check on-prem service healthz directly
    h_after = urllib.request.urlopen("http://127.0.0.1:8080/healthz").read().decode()
    print("Direct On-Prem Service Check after Recover:", h_after)

    # Check dashboard API status after recover
    status_recovered = json.loads(urllib.request.urlopen("http://localhost:8500/api/status").read().decode())
    print("Status after Recover:")
    print(f"  Leader: {status_recovered['kpis']['active_site']}")
    print(f"  Quorum: {status_recovered['quorum']['consecutive_failures']} / {status_recovered['quorum']['failure_threshold']}")
    print(f"  Signals Healthy: {status_recovered['kpis']['healthy_signals']}/{status_recovered['kpis']['total_signals']}")
    for sig in status_recovered['signals']:
        print(f"    - {sig['name']}: {sig['status']} ({sig['latency_ms']} ms)")

    driver.save_screenshot("proof_3_recovered.png")
    print("Saved screenshot: proof_3_recovered.png")

    print("\nTerminal output after Recover:")
    print(term.text[-400:])

    print("\n==================================================")
    print("LIFECYCLE VERIFICATION COMPLETE: ALL PROOFS CAPTURED")
    print("==================================================")

finally:
    driver.quit()
