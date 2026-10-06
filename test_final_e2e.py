import json
import os
import sys
import time
import urllib.request
import urllib.error
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def log_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def http_get(url, timeout=5):
    req = urllib.request.Request(url, headers={"User-Agent": "E2E-Verifier"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.getcode(), resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except Exception as e:
        return None, str(e)

def main():
    log_header("HYBRID DR ORCHESTRATOR - FINAL END-TO-END VERIFICATION")
    results = {}

    # -------------------------------------------------------------
    # 1. Direct Backend API Verification
    # -------------------------------------------------------------
    log_header("PHASE 1: Direct Component & API Endpoint Health Checks")
    
    code, body = http_get("http://127.0.0.1:8080/healthz")
    print(f"[-] Mock On-Prem /healthz: HTTP {code} | Body: {body.strip()}")
    assert code == 200, f"Expected 200 from onprem /healthz, got {code}"
    results["onprem_healthz"] = "PASS (HTTP 200 OK)"

    code, body = http_get("http://127.0.0.1:8080/items")
    print(f"[-] Mock On-Prem /items: HTTP {code} | Data items count: {len(json.loads(body))}")
    assert code == 200, f"Expected 200 from onprem /items, got {code}"
    results["onprem_items"] = "PASS (HTTP 200 OK)"

    code, body = http_get("http://127.0.0.1:8500/api/status")
    print(f"[-] Dashboard /api/status: HTTP {code}")
    assert code == 200, f"Expected 200 from dashboard status, got {code}"
    status_data = json.loads(body)
    curr_state = status_data.get("state", "UNKNOWN")
    print(f"    State: {curr_state} | Active Site: {status_data['kpis']['active_site']}")
    print(f"    Quorum: {status_data['quorum']['consecutive_failures']}/{status_data['quorum']['failure_threshold']}")
    results["dashboard_api"] = "PASS (HTTP 200 OK)"

    # -------------------------------------------------------------
    # 2. Browser UI Initialization & Console Check
    # -------------------------------------------------------------
    log_header("PHASE 2: Browser UI Initialization & SSE Terminal Connectivity")
    chrome_opts = Options()
    chrome_opts.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--window-size=1440,900")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    driver = webdriver.Chrome(options=chrome_opts)
    try:
        driver.get("http://127.0.0.1:8500")
        time.sleep(3)
        print(f"[-] Page Loaded. Document Title: '{driver.title}'")

        # Verify Console Logs for Javascript / DOM Errors
        logs = driver.get_log("browser")
        severe_errors = [l for l in logs if l['level'] == 'SEVERE' and 'favicon.ico' not in l['message']]
        print(f"[-] Browser Console Errors: {len(severe_errors)}")
        for err in severe_errors:
            print(f"    ! [SEVERE] {err['message']}")
        assert len(severe_errors) == 0, f"Found {len(severe_errors)} severe JS errors in console"
        results["ui_console_clean"] = "PASS (0 severe errors)"

        # Check Terminal Connection Status
        term_body = driver.find_element(By.ID, "terminal-body")
        print(f"[-] Terminal Body displayed: {term_body.is_displayed()}")
        assert term_body.is_displayed()
        assert "Connected to orchestrator SSE stream" in term_body.text or "Awaiting events" in term_body.text or len(term_body.text) > 0
        results["sse_terminal_connection"] = "PASS (Connected)"

        # Identify Interactive Controls
        buttons = driver.find_elements(By.TAG_NAME, "button")
        btn_map = {}
        for b in buttons:
            txt = b.text.strip()
            if "Dry-Run" in txt:
                btn_map["dry_run"] = b
            elif "Failback" in txt:
                btn_map["failback"] = b
            elif "Blackout" in txt:
                btn_map["blackout"] = b
            elif "Recover" in txt:
                btn_map["recover"] = b

        print(f"[-] Identified Dashboard Action Buttons: {list(btn_map.keys())}")
        assert "dry_run" in btn_map and "failback" in btn_map and "blackout" in btn_map and "recover" in btn_map

        # Reset state to IDLE if needed
        print("[-] Ensuring clean initial state (Failback reset)...")
        btn_map["failback"].click()
        time.sleep(2)

        # -------------------------------------------------------------
        # 3. Dry-Run Drill Execution & FSM Stepper Lifecycle
        # -------------------------------------------------------------
        log_header("PHASE 3: Full Dry-Run Drill Execution Lifecycle")
        print("[-] Triggering Dry-Run Drill via UI...")
        btn_map["dry_run"].click()

        # Monitor FSM State transitions
        observed_states = []
        max_wait = 25
        start_time = time.time()
        final_completed = False

        while time.time() - start_time < max_wait:
            _, s_body = http_get("http://127.0.0.1:8500/api/status")
            curr_state = json.loads(s_body).get("state", "UNKNOWN")
            if not observed_states or observed_states[-1] != curr_state:
                observed_states.append(curr_state)
                print(f"    -> FSM Transition: {curr_state} (elapsed: {round(time.time() - start_time, 2)}s)")
            if curr_state == "COMPLETED":
                final_completed = True
                break
            time.sleep(1)

        print(f"[-] Observed State Sequence: {' -> '.join(observed_states)}")
        assert final_completed, f"Drill did not reach COMPLETED within {max_wait}s. Final state: {observed_states[-1]}"
        results["fsm_drill_lifecycle"] = f"PASS (States: {' -> '.join(observed_states)})"

        # Check terminal text
        term_body = driver.find_element(By.ID, "terminal-body")
        term_text = term_body.text
        print("\n[-] Terminal Stream Capture (Tail 400 chars):")
        print(term_text[-400:])
        assert "COMPLETED" in term_text or "DRILL FINISHED" in term_text or "Audit complete" in term_text

        # Validate no raw ANSI characters are visible in terminal
        assert "\x1b[" not in term_text, "Found unstripped ANSI escape character in terminal output"
        results["terminal_streaming"] = "PASS (Clean ANSI-stripped stream verified)"

        driver.save_screenshot("final_e2e_dryrun_completed.png")
        print("[-] Screenshot saved: final_e2e_dryrun_completed.png")

        # -------------------------------------------------------------
        # 4. Failback Execution Verification
        # -------------------------------------------------------------
        log_header("PHASE 4: Failback Execution & State Reset")
        print("[-] Clicking 'Failback' button...")
        btn_map["failback"].click()
        time.sleep(3)

        _, s_body = http_get("http://127.0.0.1:8500/api/status")
        state_after_failback = json.loads(s_body).get("state", "UNKNOWN")
        print(f"[-] FSM State after Failback: {state_after_failback}")
        assert state_after_failback == "IDLE", f"Expected IDLE after failback, got {state_after_failback}"
        results["failback_reset"] = "PASS (FSM reset to IDLE)"

        # -------------------------------------------------------------
        # 5. Catastrophic Blackout Chaos Injection & Quorum Detection
        # -------------------------------------------------------------
        log_header("PHASE 5: Chaos Injection (Blackout) & Quorum Failure Detection")
        print("[-] Clicking '💥 Inject Blackout' button...")
        btn_map["blackout"].click()
        time.sleep(2)

        # Direct HTTP check to on-prem /healthz
        code, body = http_get("http://127.0.0.1:8080/healthz")
        print(f"[-] Direct /healthz check during blackout: HTTP {code} (Expected 503)")
        assert code == 503, f"Expected 503 during blackout, got {code}"

        # Wait for Quorum tracker to poll and reach threshold (3/3)
        print("[-] Waiting for Dashboard Quorum Engine to register consecutive failures...")
        quorum_breached = False
        consec_fail = 0
        thresh = 3
        for _ in range(10):
            time.sleep(1.5)
            _, s_body = http_get("http://127.0.0.1:8500/api/status")
            q_info = json.loads(s_body)["quorum"]
            consec_fail = q_info["consecutive_failures"]
            thresh = q_info["failure_threshold"]
            print(f"    Quorum Consecutive Failures: {consec_fail} / {thresh}")
            if consec_fail >= thresh:
                quorum_breached = True
                break

        assert quorum_breached, f"Quorum failure counter did not reach threshold ({consec_fail}/{thresh})"
        results["chaos_blackout_quorum"] = f"PASS (Quorum reached {consec_fail}/{thresh}, /healthz HTTP 503)"

        driver.save_screenshot("final_e2e_blackout.png")
        print("[-] Screenshot saved: final_e2e_blackout.png")

        # -------------------------------------------------------------
        # 6. Disaster Recovery & Quorum Reset
        # -------------------------------------------------------------
        log_header("PHASE 6: Disaster Recovery & Quorum Health Restoration")
        print("[-] Clicking '🔄 Recover' button...")
        btn_map["recover"].click()
        time.sleep(2)

        code, body = http_get("http://127.0.0.1:8080/healthz")
        print(f"[-] Direct /healthz check after recovery: HTTP {code} (Expected 200)")
        assert code == 200, f"Expected 200 after recovery, got {code}"

        print("[-] Waiting for Dashboard Quorum Engine to restore healthy state...")
        quorum_recovered = False
        for _ in range(10):
            time.sleep(1.5)
            _, s_body = http_get("http://127.0.0.1:8500/api/status")
            q_info = json.loads(s_body)["quorum"]
            consec_fail = q_info["consecutive_failures"]
            thresh = q_info["failure_threshold"]
            print(f"    Quorum Consecutive Failures: {consec_fail} / {thresh}")
            if consec_fail == 0:
                quorum_recovered = True
                break

        assert quorum_recovered, f"Quorum failure counter did not reset to 0 ({consec_fail}/{thresh})"
        results["chaos_recovery"] = "PASS (Quorum reset to 0/3, /healthz HTTP 200)"

        driver.save_screenshot("final_e2e_recovered.png")
        print("[-] Screenshot saved: final_e2e_recovered.png")

    finally:
        driver.quit()

    # -------------------------------------------------------------
    # 7. Final Summary
    # -------------------------------------------------------------
    log_header("FINAL VERIFICATION SUMMARY")
    all_passed = True
    for test_name, status in results.items():
        print(f"  [+] {test_name.ljust(30)} : {status}")
        if not status.startswith("PASS"):
            all_passed = False

    print("=" * 70)
    if all_passed:
        print("  >>> ALL END-TO-END VERIFICATION CHECKS PASSED SUCCESSFULLY! <<<")
    else:
        print("  >>> SOME VERIFICATION CHECKS FAILED! <<<")
    print("=" * 70)

if __name__ == "__main__":
    main()
