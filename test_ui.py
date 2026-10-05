import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

options = Options()
options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
options.add_argument("--headless=new")
options.add_argument("--window-size=1440,900")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

print("Launching Chrome...")
driver = webdriver.Chrome(options=options)
try:
    print("Navigating to http://localhost:8500 ...")
    driver.get("http://localhost:8500")
    time.sleep(2)
    print("Title:", driver.title)

    logs = driver.get_log("browser")
    print("\n--- BROWSER CONSOLE LOGS ---")
    for entry in logs:
        print(f"[{entry['level']}] {entry['message']}")
    print("--- END CONSOLE LOGS ---\n")

    btns = driver.find_elements(By.TAG_NAME, "button")
    print(f"\nFound {len(btns)} buttons:")
    for b in btns:
        safe_text = b.text.encode("ascii", "replace").decode("ascii")
        print(f"  Button: '{safe_text}' (displayed: {b.is_displayed()}, enabled: {b.is_enabled()})")

    # Check terminal content
    terminal_body = driver.find_element(By.ID, "terminal-body")
    print(f"\nTerminal displayed: {terminal_body.is_displayed()}")
    print("Terminal text preview:")
    print(terminal_body.text[:300])

    # Find buttons by text
    dry_run_btn = None
    failback_btn = None
    chaos_btn = None
    recover_btn = None
    live_btn = None

    for b in btns:
        t = b.text
        if "Dry-Run" in t:
            dry_run_btn = b
        elif "Failback" in t:
            failback_btn = b
        elif "Blackout" in t:
            chaos_btn = b
        elif "Recover" in t:
            recover_btn = b
        elif "EXECUTE" in t:
            live_btn = b

    # Test Failback first (to reset from COMPLETED to IDLE)
    if failback_btn:
        print("\n--- Testing Failback button ---")
        failback_btn.click()
        time.sleep(2)

    # Test Dry-Run drill
    if dry_run_btn:
        print("\n--- Testing Dry-Run Drill button ---")
        dry_run_btn.click()
        print("Waiting 5 seconds for execution...")
        time.sleep(5)

    logs_after = driver.get_log("browser")
    print("\n--- CONSOLE LOGS AFTER DRILL ---")
    for entry in logs_after:
        print(f"[{entry['level']}] {entry['message']}")
    print("--- END CONSOLE LOGS ---\n")

    print("\nTerminal text after drill:")
    print(terminal_body.text)

    # Test typing CONFIRM into Live Drill and clicking EXECUTE
    confirm_input = driver.find_element(By.ID, "live-confirm")
    confirm_input.clear()
    confirm_input.send_keys("CONFIRM")
    print("\nTyped CONFIRM into input.")
    if live_btn:
        print("Clicking Live Drill EXECUTE button...")
        live_btn.click()
        time.sleep(4)

    logs_live = driver.get_log("browser")
    print("\n--- CONSOLE LOGS AFTER LIVE DRILL ---")
    for entry in logs_live:
        print(f"[{entry['level']}] {entry['message']}")

    print("\nTerminal text after live drill:")
    print(terminal_body.text)

    driver.save_screenshot("test_full_run.png")
    print("\nScreenshot saved to test_full_run.png")

finally:
    driver.quit()
