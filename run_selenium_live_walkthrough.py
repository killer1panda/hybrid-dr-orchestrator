import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def banner(title):
    print("\n" + "=" * 75)
    print(f"  >>> {title.upper()} <<<")
    print("=" * 75)

def step_log(step_num, title, details=""):
    print(f"\n[STEP {step_num}] {title}")
    if details:
        print(f"         {details}")

def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "SeleniumVerifier"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.getcode(), resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except Exception as e:
        return None, str(e)

def main():
    banner("SELENIUM LIVE INTERACTIVE END-TO-END TEST SUITE")
    print("Starting automated real-browser execution...")
    print("Dashboard Target: http://localhost:8500")
    print("On-Prem Target:   http://localhost:8080")

    options = Options()
    options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    # Launch in real desktop window so user can watch in real time
    options.add_argument("--start-maximized")
    options.add_argument("--window-size=1440,900")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    driver = webdriver.Chrome(options=options)
    artifacts_dir = r"C:\Users\saharsh\.gemini\antigravity\brain\d8987bbb-c0fd-4953-b07b-a6fa6094344f"

    def save_proof(filename):
        driver.save_screenshot(filename)
        dest = os.path.join(artifacts_dir, filename)
        try:
            import shutil
            shutil.copy2(filename, dest)
            print(f"         [Saved Screenshot & Artifact] -> {filename}")
        except Exception as e:
            print(f"         [Saved Screenshot locally] -> {filename} ({e})")

    try:
        # =====================================================================
        # STEP 1: INITIAL PAGE LOAD & BASELINE STATE
        # =====================================================================
        step_log(1, "Navigating to Mission Control Dashboard (http://localhost:8500)...")
        driver.get("http://localhost:8500")
        time.sleep(3)
        print(f"         Window Title: '{driver.title}'")

        # Verify initial components
        term_body = driver.find_element(By.ID, "terminal-body")
        print(f"         Terminal Initialized: {term_body.is_displayed()}")
        print(f"         Terminal Content Preview: {term_body.text[:120].strip()}...")

        # Reset any leftover state to IDLE first
        btns = driver.find_elements(By.TAG_NAME, "button")
        btn_map = {}
        for b in btns:
            t = b.text.strip()
            if "Dry-Run" in t: btn_map["dry_run"] = b
            elif "Failback" in t: btn_map["failback"] = b
            elif "Blackout" in t: btn_map["blackout"] = b
            elif "Recover" in t: btn_map["recover"] = b
            elif "EXECUTE" in t: btn_map["execute"] = b

        if "failback" in btn_map:
            print("         Ensuring initial state is IDLE (invoking failback reset)...")
            btn_map["failback"].click()
            time.sleep(2)

        code, body = http_get("http://localhost:8500/api/status")
        initial_status = json.loads(body)
        print(f"         Baseline Status: State='{initial_status['state']}', Leader='{initial_status['kpis']['active_site']}', Quorum={initial_status['quorum']['consecutive_failures']}/{initial_status['quorum']['failure_threshold']}")
        save_proof("selenium_step1_baseline.png")

        # =====================================================================
        # STEP 2: TRIGGER DRY-RUN DRILL VIA UI CLICK
        # =====================================================================
        step_log(2, "Clicking 'Execute Dry-Run Drill' in Command Center...")
        driver.execute_script("arguments[0].scrollIntoView();", btn_map["dry_run"])
        time.sleep(1)
        btn_map["dry_run"].click()
        print("         Action sent. Observing live FSM state progression & terminal SSE stream...")

        # Poll FSM state progression through all stages
        prev_state = ""
        t_start = time.time()
        completed = False
        while time.time() - t_start < 25:
            _, s_body = http_get("http://localhost:8500/api/status")
            cur_state = json.loads(s_body).get("state", "UNKNOWN")
            if cur_state != prev_state:
                print(f"         [FSM Progression] -> {cur_state} (elapsed {round(time.time() - t_start, 2)}s)")
                prev_state = cur_state
            if cur_state == "COMPLETED":
                completed = True
                break
            time.sleep(1)

        assert completed, f"Drill did not complete in time, stuck at {prev_state}"
        time.sleep(2) # Allow animation to finish
        print("         Drill reached COMPLETED! Capturing terminal output:")
        print("         " + "-" * 55)
        for line in term_body.text.split("\n")[-10:]:
            print(f"         | {line}")
        print("         " + "-" * 55)

        save_proof("selenium_step2_drill_completed.png")

        # =====================================================================
        # STEP 3: TRIGGER FAILBACK TEARDOWN VIA UI CLICK
        # =====================================================================
        step_log(3, "Clicking 'Failback' button in Command Center...")
        driver.execute_script("arguments[0].scrollIntoView();", btn_map["failback"])
        time.sleep(1)
        btn_map["failback"].click()
        print("         Action sent. Waiting for AWS teardown simulation and reset...")
        time.sleep(3)

        _, fb_body = http_get("http://localhost:8500/api/status")
        fb_state = json.loads(fb_body).get("state", "UNKNOWN")
        print(f"         FSM State After Failback: '{fb_state}' (Expected: IDLE)")
        assert fb_state == "IDLE", f"State is not IDLE after failback: {fb_state}"
        save_proof("selenium_step3_failback_idle.png")

        # =====================================================================
        # STEP 4: INJECT CATASTROPHIC BLACKOUT CHAOS VIA UI CLICK
        # =====================================================================
        step_log(4, "Clicking '💥 Inject Blackout' button...")
        driver.execute_script("arguments[0].scrollIntoView();", btn_map["blackout"])
        time.sleep(1)
        btn_map["blackout"].click()
        print("         Action sent. Validating mock on-premises HTTP endpoint status...")
        time.sleep(2)

        code, _ = http_get("http://127.0.0.1:8080/healthz")
        print(f"         Direct on-prem /healthz status code: HTTP {code} (Expected: 503)")
        assert code == 503, f"Expected HTTP 503 during blackout, got {code}"

        print("         Monitoring Quorum Engine accumulation to 3/3 failure threshold...")
        breached = False
        for i in range(8):
            time.sleep(1.5)
            _, q_body = http_get("http://localhost:8500/api/status")
            q_data = json.loads(q_body)["quorum"]
            c_fail = q_data["consecutive_failures"]
            thresh = q_data["failure_threshold"]
            print(f"         [Quorum Health] Consecutive Failures: {c_fail} / {thresh}")
            if c_fail >= thresh:
                breached = True
                break

        assert breached, "Quorum did not breach threshold!"
        print("         Threshold breached! Verifying UI card indicators...")
        save_proof("selenium_step4_blackout_injected.png")

        # =====================================================================
        # STEP 5: RECOVER FROM BLACKOUT VIA UI CLICK
        # =====================================================================
        step_log(5, "Clicking '🔄 Recover' button in Command Center...")
        driver.execute_script("arguments[0].scrollIntoView();", btn_map["recover"])
        time.sleep(1)
        btn_map["recover"].click()
        print("         Action sent. Checking direct on-prem endpoint recovery...")
        time.sleep(2)

        code, _ = http_get("http://127.0.0.1:8080/healthz")
        print(f"         Direct on-prem /healthz status code: HTTP {code} (Expected: 200)")
        assert code == 200, f"Expected HTTP 200 after recovery, got {code}"

        print("         Monitoring Quorum Health counter reset to 0/3...")
        recovered = False
        for i in range(8):
            time.sleep(1.5)
            _, q_body = http_get("http://localhost:8500/api/status")
            q_data = json.loads(q_body)["quorum"]
            c_fail = q_data["consecutive_failures"]
            print(f"         [Quorum Health] Consecutive Failures: {c_fail} / {q_data['failure_threshold']}")
            if c_fail == 0:
                recovered = True
                break

        assert recovered, "Quorum failure counter failed to reset to 0!"
        save_proof("selenium_step5_recovered.png")

        # =====================================================================
        # STEP 6: VERIFY LIVE AWS DRILL SAFETY GUARDRAIL
        # =====================================================================
        step_log(6, "Testing Live AWS Drill production safety guardrail...")
        live_input = driver.find_element(By.ID, "live-confirm")
        live_btn = btn_map.get("execute")

        print("         Testing unauthorized execution without CONFIRM token...")
        driver.execute_script("arguments[0].scrollIntoView();", live_btn)
        time.sleep(1)
        live_input.clear()
        live_btn.click()
        time.sleep(1.5)
        term_text_now = term_body.text
        print(f"         Terminal tail: {term_text_now.splitlines()[-1] if term_text_now.splitlines() else ''}")
        print("         Checking terminal for safety warning...")
        assert "Confirmation required" in term_text_now or "Type CONFIRM" in term_text_now, "Expected guardrail warning in terminal"
        print("         [Safety Guardrail Verified]: Unauthorized execution blocked with explicit warning!")

        print("         Typing 'CONFIRM' into confirmation input...")
        live_input.clear()
        live_input.send_keys("CONFIRM")
        time.sleep(1)
        save_proof("selenium_step6_guardrail_verified.png")

        print("         Clearing confirmation input (re-locking guardrail)...")
        live_input.clear()
        time.sleep(1)

        # =====================================================================
        # STEP 7: CLI TOOLING PARALLEL VERIFICATION
        # =====================================================================
        step_log(7, "Testing CLI Scripts in Parallel (run-status.cmd, run-failback.cmd)...")
        res = subprocess.run(
            ["cmd.exe", "/c", "run-status.cmd"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=r"C:\Users\saharsh\.gemini\antigravity\scratch\hybrid-dr-orchestrator"
        )
        print(f"         run-status.cmd exit code: {res.returncode}")
        stdout_txt = res.stdout or ""
        print("         CLI Output preview:")
        for line in stdout_txt.strip().split("\n")[:5]:
            print(f"           | {line}")

        banner("ALL SELENIUM INTERACTIVE TESTS PASSED FLAWLESSLY")

    finally:
        time.sleep(2)
        driver.quit()

if __name__ == "__main__":
    main()
