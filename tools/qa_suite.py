"""
QA Automation Suite — LMS Google Apps Script backend
=====================================================
Usage:
    python tools/qa_suite.py              # all tests + load simulation
    python tools/qa_suite.py --unit       # unit tests only (POST)
    python tools/qa_suite.py --progress   # progress GET tests only
    python tools/qa_suite.py --load       # load simulation only
"""

import requests
import uuid
import time
import random
import sys
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional, Any

# ── import shared client ──────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from client import API_URL

TIMEOUT = 20          # seconds per request
LOAD_STUDENTS = 20    # parallel simulated students
LOAD_WORKERS = 10     # thread pool size

LESSON_IDS = ["lesson_01", "lesson_02", "lesson_03", "lesson_04", "lesson_05"]
TASK_IDS   = ["task_bool", "task_logic", "task_none", "task_if", "task_loop"]
FIRST_NAMES = [
    "Олексій", "Марія", "Іван", "Юлія", "Денис",
    "Катерина", "Сергій", "Анна", "Микола", "Оксана",
    "Артем", "Людмила", "Богдан", "Тетяна", "Андрій",
    "Ірина", "Дмитро", "Наталія", "Олег", "Вікторія",
]

# ══════════════════════════════════════════════════════════════════════
# Result container
# ══════════════════════════════════════════════════════════════════════

@dataclass
class TestResult:
    name: str
    passed: bool
    duration_ms: int
    detail: str = ""
    response: Optional[Any] = field(default=None, repr=False)

    def status_tag(self) -> str:
        return "PASS" if self.passed else "FAIL"


class TestRunner:
    """Collects results and prints a structured report."""

    _lock = threading.Lock()

    def __init__(self, label: str):
        self.label = label
        self.results: list[TestResult] = []

    def record(self, result: TestResult) -> TestResult:
        with self._lock:
            self.results.append(result)
        tag = "\033[32mPASS\033[0m" if result.passed else "\033[31mFAIL\033[0m"
        print(f"  [{tag}] {result.name:<40}  {result.duration_ms:>5} ms  {result.detail}")
        return result

    def summary(self) -> dict:
        total   = len(self.results)
        passed  = sum(1 for r in self.results if r.passed)
        failed  = total - passed
        avg_ms  = int(sum(r.duration_ms for r in self.results) / total) if total else 0
        max_ms  = max((r.duration_ms for r in self.results), default=0)
        return {
            "total": total, "passed": passed, "failed": failed,
            "success_rate_pct": round(100 * passed / total, 1) if total else 0,
            "failure_rate_pct": round(100 * failed / total, 1) if total else 0,
            "avg_ms": avg_ms, "max_ms": max_ms,
        }

    def print_summary(self):
        s = self.summary()
        sep = "─" * 60
        print(f"\n  {sep}")
        print(f"  {self.label}")
        print(f"  {sep}")
        print(f"  Total      : {s['total']}")
        print(f"  Passed     : {s['passed']}  ({s['success_rate_pct']}%)")
        print(f"  Failed     : {s['failed']}  ({s['failure_rate_pct']}%)")
        print(f"  Avg latency: {s['avg_ms']} ms")
        print(f"  Max latency: {s['max_ms']} ms")
        print(f"  {sep}\n")


# ══════════════════════════════════════════════════════════════════════
# Low-level helpers
# ══════════════════════════════════════════════════════════════════════

def _get_session(name: str, lesson_id: str) -> tuple[bool, dict, int]:
    """GET /exec?name=...&lesson_id=...  → (ok, data, ms)"""
    t0 = time.monotonic()
    try:
        r = requests.get(
            API_URL,
            params={"name": name, "lesson_id": lesson_id},
            timeout=TIMEOUT,
        )
        data = r.json()
    except Exception as exc:
        ms = int((time.monotonic() - t0) * 1000)
        return False, {"error": str(exc)}, ms
    ms = int((time.monotonic() - t0) * 1000)
    return True, data, ms


def _get_progress(token: str) -> tuple[bool, dict, int]:
    """GET /exec?action=progress&token=... → (http_ok, data, ms)"""
    t0 = time.monotonic()
    try:
        r = requests.get(
            API_URL,
            params={"action": "progress", "token": token},
            timeout=TIMEOUT,
        )
        data = r.json()
    except Exception as exc:
        ms = int((time.monotonic() - t0) * 1000)
        return False, {"error": str(exc)}, ms
    ms = int((time.monotonic() - t0) * 1000)
    return True, data, ms


def _post_submission(payload: dict) -> tuple[bool, dict, int]:
    """POST /exec with JSON payload → (http_ok, data, ms)"""
    t0 = time.monotonic()
    try:
        r = requests.post(API_URL, json=payload, timeout=TIMEOUT)
        data = r.json()
    except Exception as exc:
        ms = int((time.monotonic() - t0) * 1000)
        return False, {"error": str(exc)}, ms
    ms = int((time.monotonic() - t0) * 1000)
    return True, data, ms


def _rand_name() -> str:
    return random.choice(FIRST_NAMES) + f"_{random.randint(100, 999)}"


def _rand_lesson() -> str:
    return random.choice(LESSON_IDS)


def _rand_task() -> str:
    return random.choice(TASK_IDS)


def _base_payload(token: str, nonce: Optional[str] = None) -> dict:
    return {
        "token": token,
        "task_id": _rand_task(),
        "result": {"answer": "42", "correct": True},
        "progress": {"score": random.randint(50, 100)},
        "client_ts": int(time.time() * 1000),
        "nonce": nonce or str(uuid.uuid4()),
    }


# ══════════════════════════════════════════════════════════════════════
# Unit tests
# ══════════════════════════════════════════════════════════════════════

def test_start_session(runner: TestRunner) -> Optional[str]:
    """GET with valid name+lesson_id → ok:true + token present."""
    name = _rand_name()
    lesson = _rand_lesson()

    http_ok, data, ms = _get_session(name, lesson)

    passed = http_ok and data.get("ok") is True and bool(data.get("token"))
    detail = f"token={'present' if data.get('token') else 'MISSING'}  raw={_trim(data)}"
    runner.record(TestResult("test_start_session", passed, ms, detail, data))
    return data.get("token") if passed else None


def test_valid_submission(runner: TestRunner) -> Optional[str]:
    """Start session → submit valid payload → ok:true + progress echoed back."""
    name = _rand_name()
    lesson = _rand_lesson()

    http_ok, sess, ms1 = _get_session(name, lesson)
    if not (http_ok and sess.get("ok") and sess.get("token")):
        runner.record(TestResult("test_valid_submission", False, ms1, "session failed", sess))
        return None

    token = sess["token"]
    nonce = str(uuid.uuid4())
    payload = _base_payload(token, nonce)
    sent_progress = payload["progress"]

    http_ok2, data, ms2 = _post_submission(payload)
    returned_progress = data.get("progress")
    passed = (
        http_ok2
        and data.get("ok") is True
        and returned_progress is not None
        and returned_progress.get("score") == sent_progress.get("score")
    )
    detail = (
        f"ok={data.get('ok')}  "
        f"progress_in_response={'yes' if returned_progress else 'MISSING'}  "
        f"score={returned_progress.get('score') if returned_progress else '?'}"
    )
    runner.record(TestResult("test_valid_submission", passed, ms1 + ms2, detail, data))
    return nonce if passed else None


def test_replay_attack(runner: TestRunner, token: Optional[str], nonce: Optional[str]):
    """Reuse a known nonce on the same token → backend must reject it."""
    if token is None or nonce is None:
        runner.record(TestResult(
            "test_replay_attack", False, 0,
            "SKIP — no valid token/nonce from previous test",
        ))
        return

    payload = _base_payload(token, nonce)   # same nonce!
    http_ok, data, ms = _post_submission(payload)

    # success = server said NOT ok, i.e., replay was blocked
    rejected = http_ok and data.get("ok") is not True
    detail = (
        f"replay blocked={rejected}  ok={data.get('ok')}  raw={_trim(data)}"
    )
    runner.record(TestResult("test_replay_attack", rejected, ms, detail, data))


def test_invalid_token(runner: TestRunner):
    """POST with a fake token → backend must reject it."""
    fake_token = "invalid_token_" + uuid.uuid4().hex[:8]
    payload = _base_payload(fake_token)

    http_ok, data, ms = _post_submission(payload)

    rejected = http_ok and data.get("ok") is not True
    detail = f"rejected={rejected}  ok={data.get('ok')}  raw={_trim(data)}"
    runner.record(TestResult("test_invalid_token", rejected, ms, detail, data))


def test_missing_task_id(runner: TestRunner):
    """POST without task_id → validation error expected."""
    # grab a real token so token check passes and we reach field validation
    name = _rand_name()
    http_ok, sess, _ = _get_session(name, _rand_lesson())
    if not (http_ok and sess.get("token")):
        runner.record(TestResult(
            "test_missing_task_id", False, 0,
            "SKIP — could not obtain token",
        ))
        return

    payload = _base_payload(sess["token"])
    del payload["task_id"]          # intentionally omit required field

    http_ok2, data, ms = _post_submission(payload)
    rejected = http_ok2 and data.get("ok") is not True
    detail = f"rejected={rejected}  ok={data.get('ok')}  raw={_trim(data)}"
    runner.record(TestResult("test_missing_task_id", rejected, ms, detail, data))


def test_concurrent_submissions(runner: TestRunner):
    """Two submissions in parallel on the same token → both handled correctly."""
    name = _rand_name()
    http_ok, sess, _ = _get_session(name, _rand_lesson())
    if not (http_ok and sess.get("token")):
        runner.record(TestResult(
            "test_concurrent_submissions", False, 0,
            "SKIP — could not obtain token",
        ))
        return

    token = sess["token"]
    results: list[tuple[bool, dict, int]] = []

    def submit_one():
        res = _post_submission(_base_payload(token))
        with threading.Lock():
            results.append(res)

    t0 = time.monotonic()
    t1 = threading.Thread(target=submit_one)
    t2 = threading.Thread(target=submit_one)
    t1.start(); t2.start()
    t1.join(); t2.join()
    total_ms = int((time.monotonic() - t0) * 1000)

    ok_count = sum(1 for (http_ok, data, _) in results if http_ok and data.get("ok") is True)
    # at least one must succeed; backend may reject the other as replay
    passed = ok_count >= 1
    detail = (
        f"ok_count={ok_count}/2  "
        f"r1={results[0][1].get('ok')}  r2={results[1][1].get('ok')}"
    )
    runner.record(TestResult("test_concurrent_submissions", passed, total_ms, detail))


# ══════════════════════════════════════════════════════════════════════
# Progress GET tests
# ══════════════════════════════════════════════════════════════════════

def test_progress_invalid_token(runner: TestRunner):
    """GET progress with fake token → ok:false + error."""
    fake = "invalid_token_" + uuid.uuid4().hex[:8]
    http_ok, data, ms = _get_progress(fake)

    rejected = http_ok and data.get("ok") is not True
    detail = f"rejected={rejected}  error={data.get('error')}  raw={_trim(data)}"
    runner.record(TestResult("test_progress_invalid_token", rejected, ms, detail, data))


def test_progress_missing_token(runner: TestRunner):
    """GET progress without token param → ok:false."""
    t0 = time.monotonic()
    try:
        r = requests.get(API_URL, params={"action": "progress"}, timeout=TIMEOUT)
        data = r.json()
    except Exception as exc:
        ms = int((time.monotonic() - t0) * 1000)
        runner.record(TestResult("test_progress_missing_token", False, ms, str(exc)))
        return
    ms = int((time.monotonic() - t0) * 1000)

    rejected = data.get("ok") is not True
    detail = f"rejected={rejected}  error={data.get('error')}  raw={_trim(data)}"
    runner.record(TestResult("test_progress_missing_token", rejected, ms, detail, data))


def test_progress_no_data(runner: TestRunner):
    """Fresh session with no submissions → ok:true, progress:null."""
    name = _rand_name()
    lesson = _rand_lesson()

    http_ok, sess, ms_sess = _get_session(name, lesson)
    if not (http_ok and sess.get("token")):
        runner.record(TestResult(
            "test_progress_no_data", False, ms_sess,
            "SKIP — could not obtain token",
        ))
        return

    http_ok2, data, ms_get = _get_progress(sess["token"])
    passed = (
        http_ok2
        and data.get("ok") is True
        and "progress" in data
        and data["progress"] is None
    )
    detail = (
        f"ok={data.get('ok')}  "
        f"progress={data.get('progress')!r}  "
        f"raw={_trim(data)}"
    )
    runner.record(TestResult(
        "test_progress_no_data", passed, ms_sess + ms_get, detail, data,
    ))


def test_progress_after_submission(runner: TestRunner):
    """Submit progress → GET progress → matches what was submitted."""
    name = _rand_name()
    lesson = _rand_lesson()

    http_ok, sess, ms1 = _get_session(name, lesson)
    if not (http_ok and sess.get("token")):
        runner.record(TestResult(
            "test_progress_after_submission", False, ms1,
            "SKIP — could not obtain token",
        ))
        return

    token = sess["token"]
    expected_progress = {"score": 77, "attempts": 3, "marker": "qa_test"}

    payload = {
        "token": token,
        "task_id": _rand_task(),
        "result": {"answer": "42", "correct": True},
        "progress": expected_progress,
        "client_ts": int(time.time() * 1000),
        "nonce": str(uuid.uuid4()),
    }
    http_ok2, submit_data, ms2 = _post_submission(payload)
    if not (http_ok2 and submit_data.get("ok")):
        runner.record(TestResult(
            "test_progress_after_submission", False, ms1 + ms2,
            f"submission failed  raw={_trim(submit_data)}",
        ))
        return

    http_ok3, prog_data, ms3 = _get_progress(token)
    total_ms = ms1 + ms2 + ms3

    returned = prog_data.get("progress") or {}
    passed = (
        http_ok3
        and prog_data.get("ok") is True
        and returned.get("score") == expected_progress["score"]
        and returned.get("attempts") == expected_progress["attempts"]
    )
    detail = (
        f"ok={prog_data.get('ok')}  "
        f"got={returned}  "
        f"expected={expected_progress}  "
        f"match={passed}"
    )
    runner.record(TestResult(
        "test_progress_after_submission", passed, total_ms, detail, prog_data,
    ))


def test_progress_returns_latest(runner: TestRunner):
    """Submit twice with different scores → GET returns the most recent one."""
    name = _rand_name()
    lesson = _rand_lesson()

    http_ok, sess, _ = _get_session(name, lesson)
    if not (http_ok and sess.get("token")):
        runner.record(TestResult(
            "test_progress_returns_latest", False, 0,
            "SKIP — could not obtain token",
        ))
        return

    token = sess["token"]
    t0 = time.monotonic()

    # first submission — score 40
    payload1 = {
        "token": token,
        "task_id": _rand_task(),
        "result": {"correct": False},
        "progress": {"score": 40, "attempt": 1},
        "client_ts": int(time.time() * 1000),
        "nonce": str(uuid.uuid4()),
    }
    _post_submission(payload1)

    # small sleep so timestamps differ (GAS writes to sheet with 1s resolution)
    time.sleep(1.2)

    # second submission — score 95
    payload2 = {
        "token": token,
        "task_id": _rand_task(),
        "result": {"correct": True},
        "progress": {"score": 95, "attempt": 2},
        "client_ts": int(time.time() * 1000),
        "nonce": str(uuid.uuid4()),
    }
    _post_submission(payload2)

    http_ok3, prog_data, _ = _get_progress(token)
    total_ms = int((time.monotonic() - t0) * 1000)

    returned_score = (prog_data.get("progress") or {}).get("score")
    passed = http_ok3 and prog_data.get("ok") is True and returned_score == 95
    detail = (
        f"ok={prog_data.get('ok')}  "
        f"latest_score={returned_score}  expected=95  "
        f"raw={_trim(prog_data)}"
    )
    runner.record(TestResult(
        "test_progress_returns_latest", passed, total_ms, detail, prog_data,
    ))


# ══════════════════════════════════════════════════════════════════════
# Load simulation — 20 students in parallel
# ══════════════════════════════════════════════════════════════════════

def _student_workflow(student_id: int) -> TestResult:
    """Full workflow for one simulated student: start → submit."""
    name = f"{FIRST_NAMES[student_id % len(FIRST_NAMES)]}_s{student_id:03d}"
    lesson = _rand_lesson()

    t0 = time.monotonic()

    http_ok, sess, _ = _get_session(name, lesson)
    if not (http_ok and sess.get("ok") and sess.get("token")):
        ms = int((time.monotonic() - t0) * 1000)
        return TestResult(
            f"student_{student_id:03d}", False, ms,
            f"session failed  raw={_trim(sess)}",
        )

    token = sess["token"]
    task  = _rand_task()
    payload = {
        "token": token,
        "task_id": task,
        "result": {"answer": str(random.randint(0, 100)), "correct": random.choice([True, False])},
        "progress": {"score": random.randint(0, 100), "attempts": random.randint(1, 5)},
        "client_ts": int(time.time() * 1000),
        "nonce": str(uuid.uuid4()),
    }

    http_ok2, sub_data, _ = _post_submission(payload)
    ms = int((time.monotonic() - t0) * 1000)

    if not (http_ok2 and sub_data.get("ok")):
        detail = (
            f"name={name:<20}  lesson={lesson}  task={task}  "
            f"submit_ok={sub_data.get('ok')}  raw={_trim(sub_data)}"
        )
        return TestResult(f"student_{student_id:03d}", False, ms, detail, sub_data)

    # progress must be returned directly in POST response (no GET needed)
    returned = sub_data.get("progress")
    progress_ok = returned is not None and returned.get("score") == payload["progress"]["score"]
    passed = progress_ok
    detail = (
        f"name={name:<20}  lesson={lesson}  task={task}  "
        f"submit_ok=True  "
        f"progress_in_response={'yes' if returned else 'MISSING'}  "
        f"score={returned.get('score') if returned else '?'}"
    )
    return TestResult(f"student_{student_id:03d}", passed, ms, detail, sub_data)


def run_load_simulation(runner: TestRunner):
    print(f"\n  Launching {LOAD_STUDENTS} students in parallel "
          f"(pool={LOAD_WORKERS} threads)...\n")

    futures = {}
    with ThreadPoolExecutor(max_workers=LOAD_WORKERS) as pool:
        for sid in range(LOAD_STUDENTS):
            f = pool.submit(_student_workflow, sid)
            futures[f] = sid

        for f in as_completed(futures):
            result = f.result()
            runner.record(result)


# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════

def _trim(data: Any, max_len: int = 80) -> str:
    s = str(data)
    return s if len(s) <= max_len else s[:max_len] + "…"


def _section(title: str):
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")


# ══════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════

def run_progress_tests() -> TestRunner:
    _section("PROGRESS GET TESTS")
    runner = TestRunner("Progress GET Suite")

    test_progress_invalid_token(runner)
    test_progress_missing_token(runner)
    test_progress_no_data(runner)
    test_progress_after_submission(runner)
    test_progress_returns_latest(runner)

    runner.print_summary()
    return runner


def run_unit_tests() -> TestRunner:
    _section("UNIT TESTS")
    runner = TestRunner("Unit Test Suite")

    # 1. start session (get token + nonce for downstream tests)
    token = test_start_session(runner)

    # 2. valid submission (also captures the nonce for replay test)
    # run independently so we have a fresh nonce
    name = _rand_name()
    http_ok, sess, _ = _get_session(name, _rand_lesson())
    replay_token = sess.get("token") if http_ok and sess.get("ok") else None
    replay_nonce = None

    if replay_token:
        nonce = str(uuid.uuid4())
        payload = _base_payload(replay_token, nonce)
        http_ok2, data, ms = _post_submission(payload)
        passed = http_ok2 and data.get("ok") is True
        detail = f"submit ok={data.get('ok')}  raw={_trim(data)}"
        runner.record(TestResult("test_valid_submission", passed, ms, detail, data))
        if passed:
            replay_nonce = nonce

    # 3. replay attack — reuse the nonce from test_valid_submission
    test_replay_attack(runner, replay_token, replay_nonce)

    # 4. invalid token
    test_invalid_token(runner)

    # 5. missing task_id
    test_missing_task_id(runner)

    # 6. concurrency (2 parallel)
    test_concurrent_submissions(runner)

    runner.print_summary()
    return runner


def run_load_tests() -> TestRunner:
    _section(f"LOAD SIMULATION — {LOAD_STUDENTS} students")
    runner = TestRunner("Load Simulation")
    run_load_simulation(runner)
    runner.print_summary()
    return runner


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--all"

    t_start = time.monotonic()

    unit_runner = progress_runner = load_runner = None

    if mode in ("--all", "--unit"):
        unit_runner = run_unit_tests()

    if mode in ("--all", "--progress"):
        progress_runner = run_progress_tests()

    if mode in ("--all", "--load"):
        load_runner = run_load_tests()

    elapsed = time.monotonic() - t_start

    # ── combined summary ──────────────────────────────────────────────
    if mode == "--all":
        _section("COMBINED SUMMARY")
        all_results = (
            (unit_runner.results     if unit_runner     else []) +
            (progress_runner.results if progress_runner else []) +
            (load_runner.results     if load_runner     else [])
        )
        total  = len(all_results)
        passed = sum(1 for r in all_results if r.passed)
        failed = total - passed
        avg_ms = int(sum(r.duration_ms for r in all_results) / total) if total else 0
        max_ms = max((r.duration_ms for r in all_results), default=0)

        print(f"  Wall time   : {elapsed:.1f} s")
        print(f"  Total tests : {total}")
        print(f"  Passed      : {passed}  ({100*passed//total if total else 0}%)")
        print(f"  Failed      : {failed}  ({100*failed//total if total else 0}%)")
        print(f"  Avg latency : {avg_ms} ms")
        print(f"  Max latency : {max_ms} ms")

        if failed:
            print("\n  Failed tests:")
            for r in all_results:
                if not r.passed:
                    print(f"    ✗ {r.name:<44} {r.detail}")
        print()


if __name__ == "__main__":
    main()