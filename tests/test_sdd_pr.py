"""Checks sdd_pr.py: open, wait (with code scanning alerts), merge, ship, land on fake gh and git (first in PATH); ship and land also on real git."""
import importlib.util
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import marks
import shared_repo
from unittest import mock

from hypothesis import example, given, settings, strategies as st

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "global/sdd_pr.py"
WT_SCRIPT = SCRIPT.parent / "sdd_worktree.py"
URL = "https://github.com/o/r/pull/7"
_spec = importlib.util.spec_from_file_location("sdd_pr", SCRIPT)
sp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sp)

STUB = f"""#!{sys.executable}
import json, os, sys
d = os.environ["FAKE_DIR"]
name, a = os.path.basename(sys.argv[0]), sys.argv[1:]
open(d + "/journal", "a").write(json.dumps([name] + a) + "\\n")
def sc(f, default=None):
    try:
        return json.load(open(d + "/" + f))
    except OSError:
        return default
fj = sc("fail.json")
if fj and fj["token"] in " ".join(a):
    sys.stderr.write("boom " + fj["token"] + "\\n")
    sys.exit(fj["code"])
if name == "git":
    if "--git-common-dir" in a:
        print(d + "/main/.git")
    elif "--show-current" in a:
        print("main")
    elif "rev-parse" in a:
        print("change/x")
    elif "log" in a:
        print("own title")
elif a[:2] == ["pr", "list"]:
    print(json.dumps(sc("list.json", [])))
elif a[:2] == ["pr", "create"]:
    print("{URL}")
elif a[:2] == ["pr", "checks"]:
    seq = sc("checks.json", ["none"])
    try:
        n = int(open(d + "/n").read())
    except OSError:
        n = 0
    open(d + "/n", "w").write(str(n + 1))
    r = seq[min(n, len(seq) - 1)]
    if r == "none":
        sys.stderr.write("no checks reported\\n")
        sys.exit(1)
    print(json.dumps(r))
elif a[:2] == ["run", "view"]:
    sys.stdout.write(open(d + "/log.txt").read())
elif a[:2] == ["pr", "view"]:
    if os.path.exists(d + "/viewfail.txt"):
        sys.stderr.write("TLS handshake timeout\\n")
        sys.exit(1)
    seq = sc("view.json", [{{"headRefOid": "abc123", "headRefName": "change/x", "baseRefName": "main",
                            "state": "OPEN", "title": "PR title"}}])
    try:
        n = int(open(d + "/vn").read())
    except OSError:
        n = 0
    open(d + "/vn", "w").write(str(n + 1))
    r = seq[min(n, len(seq) - 1)]
    if os.path.exists(d + "/body.txt"):  # the body a pr edit stored, as GitHub keeps it
        r["body"] = open(d + "/body.txt").read()
    print(json.dumps(r))
elif a[:2] == ["pr", "edit"]:
    open(d + "/body.txt", "w").write(a[a.index("--body") + 1])
elif a[:1] == ["api"]:
    if a[1].endswith("/reviews"):  # PR reviews: one JSON object per line as the --jq filter prints them; reviews.txt is raw
        if os.path.exists(d + "/reviews.txt"):
            sys.stdout.write(open(d + "/reviews.txt").read())
        else:
            for row in sc("reviews.json", []):
                print(json.dumps(row))
        sys.exit(0)
    if a[1] == "--paginate":  # PR files: one JSON object per line; files.txt is the raw output
        if os.path.exists(d + "/files.txt"):
            sys.stdout.write(open(d + "/files.txt").read())
        else:
            for row in sc("files.json", []):
                print(json.dumps(row))
        sys.exit(0)
    if "/code-scanning/" in a[1]:
        cf = sc("alertsfail.json")
        if cf:  # like gh api: the response body in stdout, "gh: <text> (HTTP <code>)" in stderr
            print(json.dumps({{"message": cf["message"], "status": str(cf["status"]),
                              "documentation_url": "https://docs.github.com/rest/code-scanning/code-scanning"}}))
            sys.stderr.write("gh: " + cf["message"] + " (HTTP " + str(cf["status"]) + ")\\n")
            sys.exit(1)
        print(open(d + "/alerts.json").read() if os.path.exists(d + "/alerts.json") else "[]")
        sys.exit(0)
    if "/branches/" in a[1]:
        f = d + ("/rules" if "/rules/" in a[1] else "/branch")
        if os.path.exists(f + "fail.txt"):
            sys.stderr.write("gh: Forbidden (HTTP 403)\\n")
            sys.exit(1)
        print(open(f + ".json").read() if os.path.exists(f + ".json") else "[]" if "/rules/" in a[1] else "{{}}")
        sys.exit(0)
    if a[1:3] in (["-X", "PUT"], ["-X", "DELETE"]):
        m = sc("merge.json" if a[2] == "PUT" else "delete.json", {{"code": 0, "err": ""}})
        sys.stderr.write(m["err"])
        sys.exit(m["code"])
    print(sc("behind.json", 0))
elif a[:2] == ["pr", "merge"]:
    sys.stderr.write("base branch policy prohibits the merge; use --admin\\n")
    sys.exit(1)
"""


def chk(bucket, link="", name="t", state=None):
    return {"name": name, "state": state or bucket.upper(), "bucket": bucket, "link": link}


LINK = "https://github.com/o/r/actions/runs/555/job/9"


class Env:
    def __init__(self, **files):
        self.d = pathlib.Path(tempfile.mkdtemp())
        bin_ = self.d / "bin"
        bin_.mkdir()
        for n in ("gh", "git"):
            (bin_ / n).write_text(STUB)
            (bin_ / n).chmod(0o755)
        for f, v in files.items():
            (self.d / f.replace("_", ".", 1)).write_text(v if isinstance(v, str) else json.dumps(v))
        self.env = dict(os.environ, PATH=f"{bin_}:{os.environ['PATH']}", FAKE_DIR=str(self.d))

    def run(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                              timeout=30, stdin=subprocess.DEVNULL, env=self.env)

    def journal(self):
        p = self.d / "journal"
        return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []

    def calls(self, name, *prefix):
        return [c for c in self.journal() if c[0] == name and c[1:1 + len(prefix)] == list(prefix)]

    def close(self):
        shutil.rmtree(self.d, ignore_errors=True)


class Base(unittest.TestCase):
    def env(self, **files):
        e = Env(**files)
        self.addCleanup(e.close)
        return e


class Open(Base):
    def setUp(self):
        self.wt = tempfile.mkdtemp()  # gh runs in the worktree folder, it must exist
        self.addCleanup(shutil.rmtree, self.wt, True)

    def test_new_pr(self):
        e = self.env()
        r = e.run("open", self.wt, "main", "Title")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, f"PR #7 {URL}"), r.stderr)
        c = e.calls("gh", "pr", "create")[0]
        for pair in (["--base", "main"], ["--head", "change/x"], ["--title", "Title"]):
            self.assertIn(pair[1], c[c.index(pair[0]) + 1:c.index(pair[0]) + 2])
        push = e.calls("git", "-C", self.wt, "push")[0]
        self.assertEqual(push[4:], ["-u", "origin", "HEAD"])
        self.assertNotIn("--force", push)

    def test_existing_pr(self):
        e = self.env(list_json=[{"number": 42, "url": "https://github.com/o/r/pull/42"}])
        r = e.run("open", self.wt, "main", "T")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "PR #42 https://github.com/o/r/pull/42"))
        self.assertEqual(e.calls("gh", "pr", "create"), [])


class Wait(Base):
    def wait(self, e, timeout="2"):
        return e.run("wait", URL, "--timeout", timeout, "--interval", "0.05")

    def test_green(self):
        e = self.env(checks_json=[[chk("pending")], [chk("pass"), chk("skipping")]])
        r = self.wait(e, timeout="10")  # the summary arrives on the second poll; a margin for a slow fake start
        self.assertEqual((r.returncode, r.stdout.strip()), (0, f"PR #7 {URL} CI: green"))
        self.assertEqual(e.calls("gh", "pr", "checks")[0][3], URL)

    def test_red(self):
        log = "\n".join(f"job\tstep\t2026-01-01T10:00:0{i}.1Z noise {i}" for i in range(30))
        log += "\njob\tstep\t2026-01-01T10:00:09.1Z FAIL: test_lines (x.T)\n"
        e = self.env(checks_json=[[chk("fail", LINK)]], log_txt=log)
        r = self.wait(e)
        self.assertEqual(r.returncode, 3)
        out = r.stdout.splitlines()
        self.assertEqual(out[0], f"PR #7 {URL} CI: red")
        self.assertIn("FAIL: test_lines (x.T)", out)
        self.assertLessEqual(len(out) - 1, 20)
        self.assertFalse(any("2026-01-01" in x or "step" in x for x in out))
        self.assertEqual(e.calls("gh", "run", "view")[0][3:], ["555", "-R", "o/r", "--log-failed"])  # without -R gh looks for the repository in the current folder

    def test_each_red_sign(self):
        for sign in ("ERROR: x", "FAILED (failures=1)", "AssertionError: y"):
            e = self.env(checks_json=[[chk("fail", LINK)]], log_txt=f"job\tstep\t2026-01-01T10:00:00Z {sign}\n")
            r = self.wait(e)
            self.assertEqual(r.returncode, 3, sign)
            self.assertIn(sign, r.stdout)

    def test_infra_no_test_sign(self):
        e = self.env(checks_json=[[chk("cancel", LINK)]],
                     log_txt="job\tstep\t2026-01-01T10:00:00Z Error: The runner has received a shutdown signal\n")
        r = self.wait(e)
        self.assertEqual(r.returncode, 4)
        self.assertEqual(r.stdout.splitlines()[0], f"PR #7 {URL} CI: infra")

    def test_infra_no_checks(self):
        r = self.wait(self.env(), timeout="0.3")
        self.assertEqual((r.returncode, r.stdout.splitlines()[0]), (4, f"PR #7 {URL} CI: infra"))

    def test_red_while_other_pending(self):
        e = self.env(checks_json=[[chk("pending"), chk("fail", LINK)]], log_txt="job\tstep\tFAIL: test_x (x.T)\n")
        r = self.wait(e, timeout="5")
        self.assertEqual(r.returncode, 3, r.stdout)

    def test_red_keeps_last_lines(self):
        log = "".join(f"job\tstep\tFAIL: test_{i} (x.T)\n" for i in range(40)) + "job\tstep\tFAILED (failures=40)\n"
        r = self.wait(self.env(checks_json=[[chk("fail", LINK)]], log_txt=log))
        out = r.stdout.splitlines()
        self.assertEqual(len(out) - 1, 20)
        self.assertEqual(out[-1], "FAILED (failures=40)")

    def test_infra_timeout_pending(self):
        r = self.wait(self.env(checks_json=[[chk("pending")]]), timeout="0.3")
        self.assertEqual(r.returncode, 4)


TITLE = "PR title"
RULES = [{"type": "update", "ruleset_id": 1},
         {"type": "required_status_checks", "ruleset_id": 2,
          "parameters": {"strict_required_status_checks_policy": False,
                         "required_status_checks": [{"context": TITLE, "integration_id": 15368}]}}]
STUCK_LINE = f"required check did not start: {TITLE}"
WARNING = "warning: branch rules not read, required checks not checked"
DONE = chk("pass", name="Checks")


class RequiredChecks(Base):
    def wait(self, e, timeout="5", stuck="0.2"):
        return e.run("wait", URL, "--timeout", timeout, "--interval", "0.05", "--stuck", stuck)

    def assert_stuck(self, r):
        self.assertEqual((r.returncode, r.stdout.splitlines()),
                         (4, [f"PR #7 {URL} CI: infra", STUCK_LINE]), r.stderr)

    def assert_warned_green(self, r, msg=None):
        self.assertEqual((r.returncode, r.stdout.strip()), (0, f"PR #7 {URL} CI: green"), msg)
        self.assertEqual(r.stderr.strip(), WARNING, msg)

    def test_stuck_pending(self):
        self.assert_stuck(self.wait(self.env(rules_json=RULES, checks_json=[[DONE, chk("pending", name=TITLE, state="QUEUED")]])))

    def test_missing(self):  # green on the previous code
        self.assert_stuck(self.wait(self.env(rules_json=RULES, checks_json=[[DONE]])))

    def test_missing_classic(self):
        e = self.env(branch_json={"protected": True, "protection": {"required_status_checks": {"contexts": [TITLE], "checks": []}}},
                     checks_json=[[DONE]])
        self.assert_stuck(self.wait(e))
        self.assertFalse([c for c in e.calls("gh", "api") if "/protection" in c[2]])  # 404 and admin rights

    def test_missing_classic_checks_field(self):
        e = self.env(branch_json={"protection": {"required_status_checks": {"checks": [{"context": TITLE, "app_id": None}]}}},
                     checks_json=[[DONE]])
        self.assert_stuck(self.wait(e))

    def test_arrives_in_time(self):
        e = self.env(rules_json=RULES, checks_json=[[DONE], [DONE, chk("pass", name=TITLE)]])
        r = self.wait(e, stuck="2")
        self.assertEqual((r.returncode, r.stderr), (0, ""), r.stdout)
        self.assertEqual(len([c for c in e.calls("gh", "api") if "/branches/" in c[2]]), 2)  # the rules are read once per wait

    def test_required_skipping_is_green(self):
        r = self.wait(self.env(rules_json=RULES, checks_json=[[DONE, chk("skipping", name=TITLE)]]))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_running_is_not_stuck(self):
        running = [DONE, chk("pending", name=TITLE, state="IN_PROGRESS")]
        e = self.env(rules_json=RULES, checks_json=[running] * 8 + [[DONE, chk("pass", name=TITLE)]])
        r = self.wait(e, stuck="0.05")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_running_hits_timeout_only(self):
        e = self.env(rules_json=RULES, checks_json=[[DONE, chk("pending", name=TITLE, state="IN_PROGRESS")]])
        r = self.wait(e, timeout="0.4", stuck="0.05")
        self.assertEqual((r.returncode, r.stdout.splitlines()[1]), (4, "timeout: checks did not finish"))

    @marks.slow
    def test_other_pending_keeps_waiting(self):  # the stuck deadline counts from when the others finished
        e = self.env(rules_json=RULES, checks_json=[[chk("pending", name="Checks")]] * 8 + [[DONE]])
        r = self.wait(e, stuck="0.3")
        self.assert_stuck(r)
        self.assertGreater(len(e.calls("gh", "pr", "checks")), 8)

    def test_general_timeout_names_stuck(self):
        self.assert_stuck(self.wait(self.env(rules_json=RULES, checks_json=[[DONE]]), timeout="0.2", stuck="300"))

    def test_no_checks_at_all_names_required(self):  # there is no failed run: the dispatcher needs a name, not "no checks"
        self.assert_stuck(self.wait(self.env(rules_json=RULES), timeout="0.2", stuck="300"))

    def test_no_checks_waits_stuck_limit(self):  # with required checks an empty list waits the stuck deadline, not 180 s
        with mock.patch.object(sp, "NO_CHECKS_SEC", 0.05), mock.patch.object(sp, "checks", return_value=[]), \
                mock.patch.object(sp, "required_checks", return_value={TITLE}), \
                mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            t = time.monotonic()
            code = sp.cmd_wait(URL, 5, 0.02, 0.4)
        self.assertEqual((code, out.getvalue().splitlines()[1]), (4, STUCK_LINE))
        self.assertGreaterEqual(time.monotonic() - t, 0.4)

    def test_default_limits(self):
        with mock.patch.object(sp, "cmd_wait") as w:
            sp.main(["wait", URL])
        w.assert_called_once_with(URL, 1200.0, 15.0, 300.0)

    def test_no_required_no_warning(self):
        e = self.env(branch_json={"protected": True, "protection": {"enabled": False, "required_status_checks":
                                  {"checks": [], "contexts": [], "enforcement_level": "off"}}},
                     rules_json=RULES[:1], checks_json=[[DONE]])
        r = self.wait(e)
        self.assertEqual((r.returncode, r.stdout.strip(), r.stderr), (0, f"PR #7 {URL} CI: green", ""))

    def test_required_failed_is_red(self):
        e = self.env(rules_json=RULES, checks_json=[[DONE, chk("fail", LINK, name=TITLE)]], log_txt="job\tstep\tFAIL: t\n")
        self.assertEqual(self.wait(e).returncode, 3)

    def test_rules_unreadable(self):
        for fail in ("rulesfail_txt", "branchfail_txt", "viewfail_txt"):
            self.assert_warned_green(self.wait(self.env(checks_json=[[DONE]], **{fail: "1"})), fail)

    @marks.slow
    def test_rules_hostile(self):
        for bad in ('{"type": "required', "", "null", "7", '"text"', {"message": "x"}, [1], [None],
                    [{"no_type": 1}], [{"type": "required_status_checks"}],
                    [{"type": "required_status_checks", "parameters": None}],
                    [{"type": "required_status_checks", "parameters": {"required_status_checks": 3}}],
                    [{"type": "required_status_checks", "parameters": {"required_status_checks": [{}]}}],
                    [{"type": "required_status_checks", "parameters": {"required_status_checks": [{"context": 5}]}}],
                    [{"type": "required_status_checks", "parameters": {"required_status_checks": [{"context": ["x"]}]}}]):
            self.assert_warned_green(self.wait(self.env(rules_json=bad, checks_json=[[DONE]])), bad)

    @marks.slow
    def test_branch_hostile(self):
        for bad in ("{", "[]", '"x"', {"protection": 1}, {"protection": {"required_status_checks": 1}},
                    {"protection": {"required_status_checks": {"contexts": 5}}},
                    {"protection": {"required_status_checks": {"contexts": TITLE}}},
                    {"protection": {"required_status_checks": {"contexts": [{}]}}}):
            self.assert_warned_green(self.wait(self.env(branch_json=bad, checks_json=[[DONE]])), bad)

    def test_branch_name_quoted(self):
        for name, path in (("release/1.0", "release/1.0"), ("a#b?c", "a%23b%3Fc")):
            e = self.env(view_json=[{"baseRefName": name}], checks_json=[[DONE]])
            self.assertEqual(self.wait(e).returncode, 0)
            self.assertEqual([c[2] for c in e.calls("gh", "api") if "/branches/" in c[2]],
                             [f"repos/o/r/rules/branches/{path}?per_page=100", f"repos/o/r/branches/{path}"])


ROWS = st.lists(st.fixed_dictionaries({
    "name": st.sampled_from("abcd"),
    "bucket": st.sampled_from(["pass", "skipping", "pending", "fail", "cancel"]),
    "state": st.sampled_from(["QUEUED", "IN_PROGRESS", "SUCCESS", ""]),
}), max_size=6)


class Verdict(unittest.TestCase):
    @settings(max_examples=500, deadline=None)
    @given(rows=ROWS, required=st.sets(st.sampled_from("abcde")), sec=st.sampled_from([0, 299, 300, 301, 1200]))
    def test_required_checks_in_ci_wait_property(self, rows, required, sec):
        pending = [r for r in rows if r["bucket"] == "pending"]
        bad = any(r["bucket"] in ("fail", "cancel") for r in rows)
        passed = all(any(r["name"] == n for r in rows) and all(
            r["bucket"] in ("pass", "skipping") for r in rows if r["name"] == n) for n in required)
        quiet = all(r["name"] in required and r["state"] != "IN_PROGRESS" for r in pending)
        if bad:
            want = "bad"
        elif rows and not pending and passed:
            want = "green"
        elif quiet and not passed:
            want = "stuck" if sec >= 300 else None
        else:
            want = None
        self.assertEqual(sp.ci_verdict(rows, required, sec, 300), want)


def alert(n, rule="js/bad-code-sanitization", path="src/check.ts", line=102, text="Code construction depends on an improperly sanitized value."):
    return {"number": n, "state": "open", "rule": {"id": rule, "description": "Improper code sanitization"},
            "most_recent_instance": {"ref": "refs/pull/7/merge", "location": {"path": path, "start_line": line},
                                     "message": {"text": text}}}


ALERTS_API = "repos/o/r/code-scanning/alerts?ref=refs/pull/7/merge&state=open&per_page=100"
GREEN_LINE = f"PR #7 {URL} CI: green"
CODEQL_LINE = f"PR #7 {URL} CI: codeql"
UNCHECKED = "code scanning alerts not checked"


class CodeScanning(Base):
    """Code scanning in CI wait: code scanning alerts after green checks."""

    def wait(self, e):
        return e.run("wait", URL, "--timeout", "5", "--interval", "0.05")

    def scans(self, e):
        return [c for c in e.calls("gh", "api") if "/code-scanning/" in c[2]]

    def test_open_alert(self):  # Open alert; green on the previous code
        e = self.env(checks_json=[[DONE]], alerts_json=[alert(28)])
        r = self.wait(e)
        self.assertEqual((r.returncode, r.stdout.splitlines()), (8, [
            CODEQL_LINE, "#28 js/bad-code-sanitization src/check.ts:102 Code construction depends on an improperly sanitized value."]),
            r.stderr)

    def test_query_ref_merge(self):  # a query with the ref of the PR merge commit, once, after green checks
        e = self.env(checks_json=[[chk("pending")], [chk("pending")], [DONE]])
        self.assertEqual(self.wait(e).returncode, 0)
        self.assertEqual([c[2] for c in self.scans(e)], [ALERTS_API])
        journal = e.journal()
        self.assertEqual(journal[-1][2], ALERTS_API)  # after the last checks poll
        self.assertEqual(len(e.calls("gh", "pr", "checks")), 3)

    @marks.slow
    def test_not_asked_when_not_green(self):
        for checks, log in (([[chk("fail", LINK)]], "job\tstep\tFAIL: t\n"), ([[chk("cancel", LINK)]], "job\tstep\tshutdown\n")):
            e = self.env(checks_json=checks, log_txt=log, alerts_json=[alert(1)])
            self.assertIn(self.wait(e).returncode, (3, 4))
            self.assertEqual(self.scans(e), [])
        e = self.env(checks_json=[[chk("pending")]], alerts_json=[alert(1)])
        self.assertEqual(e.run("wait", URL, "--timeout", "0.3", "--interval", "0.05").returncode, 4)
        self.assertEqual(self.scans(e), [])

    def test_no_alerts(self):
        r = self.wait(self.env(checks_json=[[DONE]], alerts_json=[]))
        self.assertEqual((r.returncode, r.stdout.splitlines(), r.stderr), (0, [GREEN_LINE], ""))

    @marks.slow
    def test_scanning_off(self):  # Scanning not enabled / Signs of disabled scanning
        for status, message in ((403, "Advanced Security must be enabled for this repository to use code scanning."),
                                (403, "Code scanning is not enabled for this repository. Please enable code scanning in the repository settings."),
                                (404, "no analysis found"), (404, "Not Found")):
            e = self.env(checks_json=[[DONE]], alertsfail_json={"status": status, "message": message})
            r = self.wait(e)
            self.assertEqual((r.returncode, r.stdout.splitlines(), r.stderr), (0, [GREEN_LINE], ""), message)

    @marks.slow
    def test_other_failure(self):  # Query failure / Another query failure; no line on the previous code
        for status, message in ((500, "Server Error"), (502, "Bad Gateway"),
                                (403, "Resource not accessible by integration"),  # the response body has a link to code-scanning
                                (403, "API rate limit exceeded for user ID 1.")):
            e = self.env(checks_json=[[DONE]], alertsfail_json={"status": status, "message": message})
            r = self.wait(e)
            self.assertEqual((r.returncode, r.stdout.splitlines()), (0, [GREEN_LINE, UNCHECKED]), message)

    @marks.slow
    def test_hostile_body(self):  # a 200 response that is not a list of alerts also means "not checked"
        for bad in ("{", "", "null", "7", '"text"', {"message": "x"}, [1], [None], ["x"],
                    [{"number": 1, "most_recent_instance": "x"}], [{"number": 1, "rule": 5}]):
            r = self.wait(self.env(checks_json=[[DONE]], alerts_json=bad))
            self.assertEqual((r.returncode, r.stdout.splitlines()), (0, [GREEN_LINE, UNCHECKED]), bad)

    def test_many_alerts(self):  # Many alerts
        r = self.wait(self.env(checks_json=[[DONE]], alerts_json=[alert(i) for i in range(1, 46)]))
        out = r.stdout.splitlines()
        self.assertEqual((r.returncode, out[0], len(out) - 1), (8, CODEQL_LINE, 20))
        self.assertEqual([x.split()[0] for x in out[1:]], [f"#{i}" for i in range(1, 21)])

    def test_multiline_text_is_one_line(self):
        r = self.wait(self.env(checks_json=[[DONE]], alerts_json=[alert(3, text="first\nsecond\r\n  third fourth")]))
        self.assertEqual((r.returncode, r.stdout.splitlines()[1:]),
                         (8, ["#3 js/bad-code-sanitization src/check.ts:102 first second third fourth"]))

    def test_missing_fields(self):
        r = self.wait(self.env(checks_json=[[DONE]], alerts_json=[{"number": 4}]))
        self.assertEqual((r.returncode, r.stdout.splitlines()[1:]), (8, ["#4 ? ?:?"]))

    def test_rules_warning_and_alerts(self):  # a warning about rules does not change the codeql summary
        r = self.wait(self.env(checks_json=[[DONE]], rulesfail_txt="1", alerts_json=[alert(5)]))
        self.assertEqual((r.returncode, r.stdout.splitlines()[0], r.stderr.strip()), (8, CODEQL_LINE, WARNING))

    @settings(max_examples=200, deadline=None)
    @given(n=st.integers(0, 60), texts=st.lists(st.text(max_size=400), min_size=1, max_size=4))
    @example(n=45, texts=["x" * 300])
    @example(n=21, texts=["a\nb\nc"])
    def test_code_scanning_in_ci_wait_line_limit(self, n, texts):
        alerts = [alert(i, text=texts[i % len(texts)]) for i in range(1, n + 1)]
        reply = subprocess.CompletedProcess([], 0, json.dumps(alerts), "")
        with mock.patch.object(sp, "checks", return_value=[DONE]), \
                mock.patch.object(sp, "required_checks", return_value=set()), \
                mock.patch.object(sp, "sh", return_value=reply) as sh, \
                mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            code = sp.cmd_wait(URL, 5, 0.01)
        lines = out.getvalue().splitlines()
        self.assertEqual(sh.call_args.args, ("gh", "api", ALERTS_API))
        self.assertLessEqual(len(lines) - 1, 20)
        self.assertEqual(code == 8, n > 0)
        if n:
            self.assertEqual((code, lines[0]), (8, CODEQL_LINE))
            self.assertEqual([x.split()[0] for x in lines[1:]], [f"#{i}" for i in range(1, min(n, 20) + 1)])
        else:
            self.assertEqual((code, lines), (0, [GREEN_LINE]))


GREEN = [[chk("pass"), chk("skipping")]]
OPEN = {"headRefOid": "abc123", "headRefName": "change/x", "baseRefName": "main", "state": "OPEN", "author": {"login": "owner"}}
MERGE_API = "repos/o/r/pulls/7/merge"


class Merge(Base):
    def merge(self, *extra, how="squash", **files):
        files.setdefault("checks_json", GREEN)
        e = self.env(**files)
        return e, e.run("merge", URL, how, "abc123", *extra)

    def puts(self, e):
        return e.calls("gh", "api", "-X", "PUT")

    def no_merge(self, e):
        self.assertEqual(e.calls("gh", "pr", "merge"), [])
        self.assertEqual(self.puts(e), [])

    def fields(self, e):
        c = self.puts(e)[0]
        return c[4], [x for x in c[5:] if "=" in x]

    def test_owner_bypass_squash(self):  # PR closed by a rule with an owner bypass
        e, r = self.merge()
        self.assertEqual((r.returncode, r.stdout.strip()), (0, f"PR #7 {URL} merged (squash)"), r.stderr)
        self.assertEqual(len(self.puts(e)), 1)
        path, f = self.fields(e)
        self.assertEqual(path, MERGE_API)
        for x in ("merge_method=squash", "sha=abc123", "commit_title=PR title (#7)"):
            self.assertIn(x, f)
        self.assertEqual(e.calls("gh", "pr", "merge"), [])
        self.assertEqual(len(e.calls("gh", "api", "-X", "DELETE")), 1)
        self.assertEqual(e.calls("gh", "api", "-X", "DELETE")[0][4], "repos/o/r/git/refs/heads/change/x")

    @marks.slow
    def test_ci_not_green(self):  # CI not green
        for bad in ("fail", "pending", "cancel"):
            e, r = self.merge(checks_json=[[chk("pass"), chk(bad)]])
            self.assertEqual(r.returncode, 1, bad)
            self.assertIn("CI not green", r.stderr)
            self.no_merge(e)

    def test_no_checks(self):  # No checks
        e = self.env()
        r = e.run("merge", URL, "squash", "abc123")
        self.assertEqual(r.returncode, 1)
        self.assertIn("CI not green", r.stderr)
        self.no_merge(e)

    def test_github_refused(self):  # GitHub refused
        e, r = self.merge(merge_json={"code": 1, "err": "gh: Head branch was modified (HTTP 409)\n"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("Head branch was modified", r.stderr)
        self.assertEqual((r.stdout, e.calls("gh", "api", "-X", "DELETE")), ("", []))

    def test_delete_failed(self):  # Could not delete the branch
        e, r = self.merge(delete_json={"code": 1, "err": "gh: Server Error (HTTP 500)\n"})
        self.assertEqual(r.returncode, 0)
        lines = r.stdout.splitlines()
        self.assertEqual(lines[0], f"PR #7 {URL} merged (squash)")
        self.assertTrue(lines[1].startswith("branch change/x not deleted: "), r.stdout)
        self.assertEqual(len(lines), 2)

    @marks.slow
    def test_delete_already_gone(self):
        for code in (404, 422):
            e, r = self.merge(delete_json={"code": 1, "err": f"gh: Reference does not exist (HTTP {code})\n"})
            self.assertEqual((r.returncode, r.stdout.strip()), (0, f"PR #7 {URL} merged (squash)"), code)

    def test_fork_branch_kept(self):  # PR branch from a fork
        e, r = self.merge(view_json=[dict(OPEN, title="T", isCrossRepository=True)])
        self.assertEqual((r.returncode, r.stdout.strip()), (0, f"PR #7 {URL} merged (squash)"), r.stderr)
        self.assertEqual(e.calls("gh", "api", "-X", "DELETE"), [])

    @marks.slow
    def test_empty_title(self):  # Empty title
        for t in ("", "   "):
            e, r = self.merge(view_json=[dict(OPEN, title=t)])
            self.assertEqual(r.returncode, 1, repr(t))
            self.assertIn("title", r.stderr)
            self.no_merge(e)
        e, r = self.merge("--title", "")
        self.assertEqual(r.returncode, 1)
        self.no_merge(e)

    def test_view_failed(self):  # gh pr view failed
        e, r = self.merge(viewfail_txt="x")
        self.assertEqual(r.returncode, 1)
        self.assertIn("TLS handshake timeout", r.stderr)
        self.no_merge(e)

    def test_title_from_local_commit(self):  # Title from the local commit
        e, r = self.merge("--title", "fix(222-ooxml): read templates")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("commit_title=fix(222-ooxml): read templates (#7)", self.fields(e)[1])

    def test_rebase_no_title(self):
        e, r = self.merge(how="rebase", view_json=[dict(OPEN, title="")])
        self.assertEqual(r.returncode, 0, r.stderr)
        f = self.fields(e)[1]
        self.assertIn("merge_method=rebase", f)
        self.assertFalse([x for x in f if x.startswith("commit_title")])

    def test_merge_method(self):
        e, r = self.merge(how="merge")
        self.assertEqual(r.returncode, 0, r.stderr)
        f = self.fields(e)[1]
        self.assertIn("merge_method=merge", f)
        self.assertIn("commit_title=PR title (#7)", f)

    def test_behind_before_ci(self):  # order: behind before CI
        e, r = self.merge(behind_json=2, checks_json=[[chk("fail")]])
        self.assertEqual(r.returncode, 5)
        self.no_merge(e)

    def test_already_merged(self):
        e = self.env(view_json=[dict(OPEN, headRefOid="zzz", state="MERGED")])
        r = e.run("merge", URL, "squash", "abc123")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "PR #7 merged (already)"))
        self.no_merge(e)

    def test_hash_not_head(self):
        e = self.env()
        r = e.run("merge", URL, "squash", "other")
        self.assertEqual(r.returncode, 1)
        self.assertIn("hash other is not the PR head (abc123)", r.stderr)
        self.no_merge(e)

    def test_behind(self):
        e, r = self.merge(behind_json=2)
        self.assertEqual(r.returncode, 5)
        self.assertIn("behind 2", r.stdout)
        self.assertEqual(e.calls("gh", "api", "repos/o/r/compare/main...abc123")[0][2], "repos/o/r/compare/main...abc123")
        self.no_merge(e)


def frow(name, patch=None, prev=None):
    return {"filename": name, "previous_filename": prev, "patch": patch}


def agents(*items):
    return "# p\n\n## Delivery\n\n- Mode: pr\n" + "".join(f"- {x}\n" for x in items) + "\n## Other\n- Owner only: `x/**`\n"


RULE = "Owner only: `global/*.py`, `docs/**`"
PATCH_RULE = "@@ -5,1 +5,1 @@\n-- Owner only: `a`, `b`\n+- Owner only: `a`\n"


class OwnerOnlyPaths(Base):
    """Checks PR files against the "Owner only:" paths and .github/workflows before the merge request."""
    puts, no_merge = Merge.puts, Merge.no_merge

    def gate(self, files, agents_md=RULE, **kw):
        e = self.env(files_json=files, checks_json=GREEN, **kw)
        if agents_md:  # None/False: no file, the main AGENTS.md is unreadable
            (e.d / "main").mkdir()
            (e.d / "main/AGENTS.md").write_text(agents(agents_md))
        return e, e.run("merge", URL, "squash", "abc123")

    def waits(self, e, r, *paths):
        self.assertEqual(r.returncode, 8, r.stderr)
        self.assertEqual(r.stdout.strip(), "PR #7 waits for the owner: " + ", ".join(paths))
        self.no_merge(e)
        self.assertEqual(e.calls("gh", "api", "repos/o/r/compare/main...abc123"), [])  # before the behind check
        self.assertEqual(e.calls("gh", "pr", "checks"), [])

    def test_ci_edit(self):
        e, r = self.gate([frow(".github/workflows/ci.yml")], None)
        self.waits(e, r, ".github/workflows/ci.yml")

    def test_ci_edit_with_owner_rule(self):
        e, r = self.gate([frow(".github/workflows/ci.yml"), frow("README.md")])
        self.waits(e, r, ".github/workflows/ci.yml")

    def test_owner_path_star(self):
        e, r = self.gate([frow("global/work_hooks.py"), frow("README.md")])
        self.waits(e, r, "global/work_hooks.py")

    def test_owner_path_double_star(self):
        e, r = self.gate([frow("docs/a/b.md"), frow("docs/x.md")])
        self.waits(e, r, "docs/a/b.md", "docs/x.md")

    def test_star_stays_in_name(self):
        e, r = self.gate([frow("global/sub/x.py"), frow("global/x.pyc"), frow("xglobal/a.py")])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.puts(e)), 1)

    def test_no_match_merges(self):
        e, r = self.gate([frow("README.md"), frow("skills/a/SKILL.md")])
        self.assertEqual((r.returncode, r.stdout.strip()), (0, f"PR #7 {URL} merged (squash)"), r.stderr)

    def test_agents_without_rule_merges(self):
        e, r = self.gate([frow("AGENTS.md", "@@ -1 +1 @@\n-a\n+b\n")], None)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_rule_edit_in_patch(self):
        e, r = self.gate([frow("AGENTS.md", PATCH_RULE)])
        self.waits(e, r, "AGENTS.md («Owner only:»)")

    def test_other_agents_edit_merges(self):
        e, r = self.gate([frow("AGENTS.md", "@@ -1 +1 @@\n-Mode: pr\n+Mode: prod\n @@ Owner only: untouched\n")])
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_agents_without_patch(self):
        e, r = self.gate([frow("AGENTS.md")])
        self.waits(e, r, "AGENTS.md («Owner only:»)")

    def test_main_agents_unreadable(self):  # CI only: an owner path passes
        e, r = self.gate([frow("global/work_hooks.py")], False)
        self.assertEqual(r.returncode, 0, r.stderr)
        e, r = self.gate([frow(".github/workflows/ci.yml"), frow("AGENTS.md")], False)
        self.waits(e, r, ".github/workflows/ci.yml")

    def test_main_agents_not_utf8(self):
        e = self.env(files_json=[frow("global/a.py")], checks_json=GREEN)
        (e.d / "main").mkdir()
        (e.d / "main/AGENTS.md").write_bytes(b"\xff\xfe## \x80")
        self.assertEqual(e.run("merge", URL, "squash", "abc123").returncode, 0)

    def test_rename_from_protected(self):
        e, r = self.gate([frow("old/place.py", prev="docs/a.md")])
        self.waits(e, r, "docs/a.md")

    def test_rename_into_protected(self):
        e, r = self.gate([frow(".github/workflows/x.yml", prev="ci.yml")])
        self.waits(e, r, ".github/workflows/x.yml")

    @marks.slow
    def test_hostile_gh(self):
        cases = {"fail": dict(fail_json={"token": "/files", "code": 1}),
                 "not json": dict(files_txt="oops\n"),
                 "array": dict(files_txt="[1, 2]\n"),
                 "no filename": dict(files_txt='{"patch": "x"}\n'),
                 "filename number": dict(files_txt='{"filename": 5}\n'),
                 "null": dict(files_txt="null\n")}
        for name, kw in cases.items():
            e = self.env(checks_json=GREEN, **kw)
            r = e.run("merge", URL, "squash", "abc123")
            self.assertEqual(r.returncode, 1, (name, r.stderr))
            self.assertIn("not merged: PR files", r.stderr, name)
            self.no_merge(e)

    def test_odd_names_do_not_match(self):
        e, r = self.gate([frow("a b/../global/x.py"), frow("docs ../x"), frow(".github/workflowsX/a"),
                          frow("global/..\n/x.py")])
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_pagination_flag(self):
        e, r = self.gate([frow("README.md")])
        self.assertEqual(e.calls("gh", "api", "--paginate", "repos/o/r/pulls/7/files")[0][4], "--jq")

    def test_unit_helpers(self):
        self.assertIsNone(sp.owner_rule(None))
        self.assertIsNone(sp.owner_rule("## Other\n- Owner only: `x`\n"))
        self.assertEqual(sp.owner_rule(agents(RULE)), "- " + RULE)
        self.assertEqual(sp.owner_rule("## Delivery\n* Owner only: `a`\n"), "* Owner only: `a`")
        self.assertEqual(sp.owner_patterns(None), [sp.CI_PATTERN])
        self.assertEqual(sp.owner_patterns("Owner only: `/a/*.py`, ``, `b`"), [sp.CI_PATTERN, "a/*.py", "b"])
        self.assertEqual(sp.owner_hits(["b", "a", "a", "c"], ["a", "b"]), ["a", "b"])
        self.assertTrue(sp.glob_re("**/*.py").fullmatch("a/b/c.py") and not sp.glob_re("*.py").fullmatch("a/c.py"))
        self.assertIsNone(sp.read_text("/nonexistent/AGENTS.md"))
        self.assertEqual(sp.owner_patterns("Owner only: `./global/*.py`, `/./a`, `.//b`"), [sp.CI_PATTERN, "global/*.py", "a", "b"])
        for pat, path in (("docs/**/*.md", "docs/x.md"), ("**/*.py", "c.py"), ("a/**/b.py", "a/b.py"), ("a/**/b.py", "a/x/y/b.py")):
            self.assertTrue(sp.glob_re(pat).fullmatch(path), (pat, path))
        self.assertFalse(sp.glob_re("a/**/b.py").fullmatch("a/xb.py"))
        two = sp.owner_rule("## Delivery\n- Owner only: `a/*.py`\n- Owner only: `b/**`\n")
        self.assertEqual(sp.owner_hits(["a/x.py", "b/x/y.md", "c"], sp.owner_patterns(two)), ["a/x.py", "b/x/y.md"])
        self.assertEqual(sp.owner_hits(["docs/x.md", "docs/a/b.md", "docsx"], sp.owner_patterns("Owner only: `docs/`")),
                         ["docs/a/b.md", "docs/x.md"])


SEG = st.text(alphabet="ab.-_ ", min_size=0, max_size=4)


class OwnerGateProperty(unittest.TestCase):
    @settings(max_examples=200, deadline=None)
    @given(prefix=st.lists(st.text(alphabet="ab.-_", min_size=1, max_size=3), min_size=1, max_size=3),
           rest=st.lists(SEG, min_size=1, max_size=4), seg=st.text(alphabet="ab.-_", min_size=1, max_size=3),
           tail=st.lists(SEG, min_size=1, max_size=3))
    def test_owner_only_paths_gate_property(self, prefix, rest, seg, tail):
        pre = "/".join(prefix)
        self.assertTrue(sp.owner_hits([pre + "/" + "/".join(rest)], [pre + "/**"]))  # any path under prefix/
        deeper = seg + "/" + "/".join(tail[:1]) + "/" + "/".join(tail)  # after seg/ there is another "/"
        name = tail[0].replace("/", "") or "n"
        for path in (f"{pre}/{name}", f"{pre}/x/y/{name}"):  # `**/` covers zero depth too
            self.assertTrue(sp.owner_hits([path], [f"{pre}/**/{name}"]), path)
        self.assertEqual(sp.owner_hits([deeper], [seg + "/*"]), [])
        self.assertTrue(sp.owner_hits([seg + "/" + tail[0].replace("/", "")], [seg + "/*"]))


GITENV = dict(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
GENV = dict(os.environ, **GITENV)


def g(cwd, *args, check=True):
    p = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, env=GENV,
                       stdin=subprocess.DEVNULL)
    if check and p.returncode:
        raise AssertionError(f"git {args}: {p.stderr}")
    return p.stdout.strip()


def worktree(cmd, main, wt):
    return subprocess.run([sys.executable, str(WT_SCRIPT), cmd, str(main), str(wt)], capture_output=True,
                          text=True, env=GENV, stdin=subprocess.DEVNULL, timeout=30)


def build_ship_land(root):
    """The bare origin, the main folder and the set-up worktree of ShipLandRepo in root."""
    origin, main, wt = (root / n for n in ("origin.git", "main", "wt"))
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True, env=GENV)
    subprocess.run(["git", "init", "-q", "-b", "main", str(main)], check=True, env=GENV)
    ShipLandRepo.put(main, ".gitignore", "openspec/\n")
    ShipLandRepo.put(main, "docs/cli.md", "one\ntwo\nthree\n")
    ShipLandRepo.put(main, "README.md", "r\n")
    g(main, "add", "-A")
    g(main, "commit", "-qm", "init")
    g(main, "remote", "add", "origin", str(origin))
    g(main, "push", "-q", "-u", "origin", "main")
    ShipLandRepo.put(main, "openspec/a.md", "a\nb\nc\n")
    g(main, "worktree", "add", "-q", "-b", "change/x", str(wt), "origin/main")
    r = worktree("setup", main, wt)
    assert r.returncode == 0, r.stdout + r.stderr
    ShipLandRepo.put(wt, "feature.txt", "f\n")
    g(wt, "add", "-A")
    g(wt, "commit", "-qm", "own title")


class ShipLandRepo(Base):
    """ship and land on real git and the real sdd_worktree.py; only gh is faked. The repositories are a copy of ones
    built once (tests/shared_repo.py)."""

    BUILD = staticmethod(build_ship_land)  # a subclass with more fixture names its own build

    def setUp(self):
        folder, _ = shared_repo.template(("ShipLandRepo", self.BUILD), self.BUILD)
        self.root = shared_repo.copy(folder)
        self.addCleanup(shutil.rmtree, self.root, True)
        self.origin, self.main, self.wt = (self.root / n for n in ("origin.git", "main", "wt"))

    @staticmethod
    def put(base, rel, text):
        p = pathlib.Path(base) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def head(self):
        return g(self.wt, "rev-parse", "HEAD")

    def mk(self, **files):
        if "view_json" not in files:
            files["view_json"] = [dict(OPEN, headRefOid=self.head(), title="T")]
        files.setdefault("checks_json", GREEN)
        e = self.env(**files)
        (e.d / "bin/git").unlink()  # git is real, gh is faked
        e.env.update(GITENV)
        return e

    def advance_origin(self, rel="srv.txt", text="x\n", msg="squash (#7)"):
        helper = self.root / "helper"
        if not helper.exists():
            subprocess.run(["git", "clone", "-q", str(self.origin), str(helper)], check=True, env=GENV)
        self.put(helper, rel, text)
        g(helper, "add", "-A")
        g(helper, "commit", "-qm", msg)
        g(helper, "push", "-q", "origin", "main")

    def ship(self, e):
        return e.run("ship", str(self.main), str(self.wt), "main", "T")

    def land(self, e, how="squash"):
        return e.run("land", str(self.main), str(self.wt), URL, how)

    def no_branch_on_origin(self):
        self.assertEqual(g(self.origin, "branch", "--list", "change/x"), "")

    def worktrees(self):
        return g(self.main, "worktree", "list").splitlines()


class ShipLand(ShipLandRepo):
    def test_ship_push_failed(self):
        g(self.wt, "remote", "set-url", "--push", "origin", "/no/such/path")
        e = self.mk()
        r = self.ship(e)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("push", r.stderr)
        self.assertEqual(e.calls("gh", "pr", "checks"), [])

    def test_ship_update_conflict(self):
        self.put(self.wt, "docs/cli.md", "one\nWT\nthree\n")
        g(self.wt, "commit", "-qam", "wt edit")
        self.put(self.main, "docs/cli.md", "one\nMAIN\nthree\n")
        g(self.main, "commit", "-qam", "main edit")
        g(self.main, "push", "-q", "origin", "main")
        r = self.ship(self.mk())
        self.assertEqual(r.returncode, 6, r.stderr)
        self.assertIn("docs/cli.md", r.stderr)
        self.assertEqual(g(self.wt, "status", "--porcelain"), "")
        self.assertNotEqual(subprocess.run(["git", "-C", str(self.wt), "rev-parse", "-q", "--verify", "MERGE_HEAD"],
                                           capture_output=True).returncode, 0)
        self.no_branch_on_origin()

    def test_ship_refresh_conflict(self):
        self.put(self.main, "openspec/a.md", "a\nMAIN\nc\n")
        self.put(self.wt, "openspec/a.md", "a\nWT\nc\n")
        r = self.ship(self.mk())
        self.assertEqual(r.returncode, 6, r.stderr)
        self.assertIn("openspec/a.md", r.stderr)
        self.assertIn("<<<<<<<", (self.wt / "openspec/a.md").read_text())  # the markers stayed in WORKTREE
        self.no_branch_on_origin()

    @marks.slow
    def test_ship_no_worktree_script(self):
        e = self.mk()
        lone = self.root / "lone"
        lone.mkdir()
        shutil.copy(SCRIPT, lone / "sdd_pr.py")
        args = ["ship", str(self.main), str(self.wt), "main", "T"]
        run = lambda d: subprocess.run([sys.executable, str(d / "sdd_pr.py"), *args], capture_output=True,
                                       text=True, env=e.env, stdin=subprocess.DEVNULL, timeout=30)
        r = run(lone)
        self.assertEqual(r.returncode, 1)
        self.assertIn("refresh", r.stderr)
        for name in ("sdd-worktree.py", "sdd_worktree.py"):  # both names are found
            d = self.root / name
            d.mkdir()
            shutil.copy(SCRIPT, d / "sdd_pr.py")
            (d / name).write_text("import sys\nsys.exit(0)\n")
            r = run(d)
            self.assertEqual((r.returncode, r.stdout.strip()), (0, f"PR #7 {URL} CI: green"), (name, r.stderr))

    def test_ship_refresh_build_failed(self):  # refresh code 4: the summary line reaches the dispatcher even when printed to stderr
        e = self.mk()
        d = self.root / "built"
        d.mkdir()
        shutil.copy(SCRIPT, d / "sdd_pr.py")
        (d / "sdd-worktree.py").write_text(
            "import sys\nprint('warning: x', file=sys.stderr)\n"
            "print('refreshed: copied 0, merged 0, deleted 0')\nprint('boom')\n"
            "print('after refresh: sh build.sh — code 1')\nsys.exit(4)\n")
        r = subprocess.run([sys.executable, str(d / "sdd_pr.py"), "ship", str(self.main), str(self.wt), "main", "T"],
                           capture_output=True, text=True, env=e.env, stdin=subprocess.DEVNULL, timeout=30)
        self.assertEqual(r.returncode, 1, r.stderr)
        tail = r.stderr.strip().splitlines()
        self.assertEqual(tail[-1], "after refresh: sh build.sh — code 1", r.stderr)
        self.assertIn("boom", tail)
        self.no_branch_on_origin()

    @marks.slow
    def test_ship_codes(self):
        r = self.ship(self.mk())
        self.assertEqual((r.returncode, r.stdout), (0, f"PR #7 {URL} CI: green\n"), r.stderr)
        log = "job\tstep\t2026-01-01T10:00:00Z FAIL: test_x (x.T)\n"
        r = self.ship(self.mk(checks_json=[[chk("fail", LINK)]], log_txt=log))
        self.assertEqual(r.returncode, 3, r.stderr)
        r = self.ship(self.mk(checks_json=[[chk("cancel", LINK)]], log_txt="job\tstep\tError: runner shutdown\n"))
        self.assertEqual(r.returncode, 4, r.stderr)

    def test_ship_passes_codeql(self):  # ship passes code 8; 0 on the previous code
        r = self.ship(self.mk(alerts_json=[alert(28)]))
        out = r.stdout.splitlines()
        self.assertEqual((r.returncode, out[0], out[1].split()[:3]),
                         (8, CODEQL_LINE, ["#28", "js/bad-code-sanitization", "src/check.ts:102"]), r.stderr)

    def test_land_merge_refused(self):
        self.advance_origin()
        before = (g(self.main, "rev-parse", "main"), g(self.main, "rev-parse", "origin/main"))
        e = self.mk(merge_json={"code": 1, "err": "gh: nope (HTTP 405)\n"})
        r = self.land(e)
        self.assertEqual(r.returncode, 1)
        self.assertIn("not merged: merge", r.stderr)
        self.assertIn("nope", r.stderr)
        self.assertEqual((g(self.main, "rev-parse", "main"), g(self.main, "rev-parse", "origin/main")), before)
        self.assertTrue(self.wt.is_dir() and not pathlib.Path(str(self.wt) + ".undo").exists())

    def test_land_behind(self):
        e = self.mk(behind_json=2)
        r = self.land(e)
        self.assertEqual(r.returncode, 5, r.stderr)
        self.assertEqual(e.calls("gh", "api", "-X", "PUT"), [])
        self.assertTrue(self.wt.is_dir())
        self.assertIn("change/x", g(self.main, "branch", "--list", "change/x"))

    @marks.slow
    def test_land_success(self):
        self.advance_origin()
        e = self.mk()
        r = self.land(e)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines()[-1], f"PR #7 {URL} land: done")
        self.assertEqual(g(self.main, "rev-parse", "main"), g(self.main, "rev-parse", "origin/main"))
        self.assertEqual(len(self.worktrees()), 1)
        self.assertEqual(g(self.main, "branch", "--list", "change/x"), "")

    def test_land_passes_not_carried_line(self):
        self.put(self.main, ".git/info/exclude", "notes.md\n")  # an individually ignored document, different in MAIN and WORKTREE
        self.put(self.main, "notes.md", "main\n")
        self.put(self.wt, "notes.md", "wt\n")
        e = self.mk()
        r = self.land(e)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("not transported: notes.md", r.stdout)  # the dispatcher reads this line
        self.assertEqual(r.stdout.splitlines()[-1], f"PR #7 {URL} land: done")

    @marks.slow
    def test_land_failure_after_merge_then_resume(self):
        self.put(self.main, "openspec/a.md", "a\nMAIN\nc\n")
        self.put(self.wt, "openspec/a.md", "a\nWT\nc\n")
        e = self.mk()
        r = self.land(e)
        self.assertEqual(r.returncode, 7, r.stderr)
        self.assertIn("merged, not finished: transport", r.stderr)
        self.assertTrue(self.wt.is_dir())
        self.put(self.main, "openspec/a.md", "a\nb\nc\n")
        (e.d / "view.json").write_text(json.dumps([dict(OPEN, headRefOid=self.head(), state="MERGED")]))
        r = self.land(e)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(e.calls("gh", "api", "-X", "PUT")), 1)
        self.assertEqual(len(self.worktrees()), 1)

    def test_land_again_when_all_gone(self):
        head = self.head()
        self.assertEqual(worktree("remove", self.main, self.wt).returncode, 0)
        g(self.main, "branch", "-D", "change/x")
        e = self.mk(view_json=[dict(OPEN, headRefOid=head, state="MERGED")])
        r = self.land(e)
        self.assertEqual((r.returncode, r.stdout.splitlines()[-1]), (0, f"PR #7 {URL} land: done"), r.stderr)
        self.assertEqual(e.calls("gh", "api", "-X", "PUT"), [])

    @marks.slow
    def test_land_title_from_own_commit(self):
        self.advance_origin()
        g(self.wt, "fetch", "-q", "origin")
        g(self.wt, "merge", "-q", "--no-edit", "origin/main")
        g(self.wt, "commit", "-q", "--allow-empty", "-m", "ci rerun")
        head = self.head()
        e = self.mk()
        r = self.land(e)
        self.assertEqual(r.returncode, 0, r.stderr)
        put = e.calls("gh", "api", "-X", "PUT")[0]
        self.assertIn("commit_title=own title (#7)", put)
        self.assertIn(f"sha={head}", put)

    def test_land_no_own_commit(self):
        g(self.wt, "checkout", "-q", "--orphan", "z")
        g(self.wt, "rm", "-rfq", ".")
        g(self.wt, "commit", "-q", "--allow-empty", "-m", "root")
        e = self.mk()
        r = self.land(e)
        self.assertEqual(r.returncode, 1)
        self.assertIn("title", r.stderr)
        self.assertEqual(e.calls("gh", "api", "-X", "PUT"), [])

    def test_land_keeps_foreign_branch(self):
        g(self.main, "branch", "main2")
        e = self.mk(view_json=[dict(OPEN, headRefOid=self.head(), headRefName="main2", title="T")])
        r = self.land(e)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("main2", g(self.main, "branch", "--list", "main2"))


class LandOwnerPaths(ShipLand):
    def test_land_wt_agents_rule_differs(self):  # AGENTS.md outside git: the item in WORKTREE differs from the main folder
        self.put(self.main, "AGENTS.md", agents("Owner only: `a`, `b`"))
        self.put(self.wt, "AGENTS.md", agents("Owner only: `a`"))
        e = self.mk(files_json=[frow("feature.txt")])
        r = self.land(e)
        self.assertEqual(r.returncode, 8, r.stderr)
        self.assertIn("AGENTS.md («Owner only:»)", r.stdout)
        self.assertEqual(e.calls("gh", "api", "-X", "PUT"), [])
        self.assertTrue(self.wt.is_dir())

    def test_land_wt_agents_same_merges(self):
        self.put(self.main, ".git/info/exclude", "AGENTS.md\n")  # ignored by git: remove does not see it as an edit
        self.put(self.main, "AGENTS.md", agents("Owner only: `a`"))
        self.put(self.wt, "AGENTS.md", agents("Owner only: `a`"))
        e = self.mk(files_json=[frow("feature.txt")])
        r = self.land(e)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(e.calls("gh", "api", "-X", "PUT")), 1)

    def test_land_owner_path(self):
        e = self.mk(files_json=[frow(".github/workflows/ci.yml")])
        r = self.land(e)
        self.assertEqual(r.returncode, 8, r.stderr)
        self.assertEqual(e.calls("gh", "api", "-X", "PUT"), [])


WT_STUB = f"""#!{sys.executable}
import json, os, sys
d = os.environ["FAKE_DIR"]
a = sys.argv[1:]
open(d + "/journal", "a").write(json.dumps(["sdd-worktree", a[0]]) + "\\n")
try:
    fj = json.load(open(d + "/fail.json"))
except OSError:
    fj = None
if fj and fj["token"] in " ".join(a):
    sys.stderr.write("boom " + fj["token"] + "\\n")
    sys.exit(fj["code"])
"""

SHIP_STEPS = [("git", " fetch "), ("git", " merge -q --no-edit "), ("sdd-worktree", "refresh"),
              ("git", " push "), ("gh", "pr list"), ("gh", "pr create")]
LAND_STEPS = [("gh", "-X PUT"), ("git", " fetch -q origin"), ("git", "--ff-only"),
              ("sdd-worktree", "transport"), ("sdd-worktree", "remove"), ("git", "branch -D")]
TOKENS = {"ship": ["fetch", "merge", "refresh", "push", "pr list", "pr create"],
          "land": ["-X PUT", "fetch", "--ff-only", "transport", "remove", "branch -D"]}


def build_delivery(root):
    """ShipLandRepo's fixture plus a dev branch on origin, fetched into main."""
    build_ship_land(root)
    helper = root / "helper"
    subprocess.run(["git", "clone", "-q", str(root / "origin.git"), str(helper)], check=True, env=GENV)
    g(helper, "checkout", "-q", "-b", "dev")
    ShipLandRepo.put(helper, "dev.txt", "d\n")
    g(helper, "add", "-A")
    g(helper, "commit", "-qm", "on dev")
    g(helper, "push", "-q", "origin", "dev")
    g(root / "main", "fetch", "-q", "origin")


class DeliveryBase(ShipLandRepo):
    """Requirement: Base branch from settings; Promotion line in the report (the line of land)."""

    BUILD = staticmethod(build_delivery)

    def setUp(self):
        super().setUp()
        self.config("delivery.base: dev\ndelivery.promote: staging, release/*, main\n")

    def config(self, text):
        self.put(self.main, "solo-sdd/config", text)

    def dev_view(self, **kw):
        return [dict(OPEN, headRefOid=self.head(), title="T", baseRefName="dev", **kw)]

    def advance_dev(self):
        helper = self.root / "helper"
        self.put(helper, "srv.txt", "x\n")
        g(helper, "add", "-A")
        g(helper, "commit", "-qm", "squash (#7)")
        g(helper, "push", "-q", "origin", "dev")

    @marks.slow
    def test_ship_targets_and_updates_from_base(self):
        e = self.mk()
        r = self.ship(e)  # the argument names main, the setting wins
        self.assertEqual((r.returncode, r.stdout), (0, f"PR #7 {URL} CI: green\n"), r.stderr)
        c = e.calls("gh", "pr", "create")[0]
        self.assertEqual(c[c.index("--base") + 1], "dev")
        self.assertTrue((self.wt / "dev.txt").exists(), "ship merged origin/dev into the branch")
        g(self.wt, "merge-base", "--is-ancestor", "origin/dev", "HEAD")  # raises when origin/dev is not in the branch

    def test_without_the_key_the_argument_stays(self):
        self.config("")
        e = self.mk()
        self.assertEqual(self.ship(e).returncode, 0)
        c = e.calls("gh", "pr", "create")[0]
        self.assertEqual(c[c.index("--base") + 1], "main")
        self.assertFalse((self.wt / "dev.txt").exists())

    @marks.slow
    def test_land_on_base_and_promotion_line(self):
        g(self.main, "checkout", "-q", "-b", "dev", "origin/dev")
        self.advance_dev()
        e = self.mk(view_json=self.dev_view())
        r = self.land(e)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines()[-2:], [f"PR #7 {URL} land: done",
                                                       "promotion: dev → staging: sdd-pr.py promote dev staging"])
        self.assertEqual(g(self.main, "rev-parse", "HEAD"), g(self.main, "rev-parse", "origin/dev"))
        self.assertEqual(g(self.main, "branch", "--show-current"), "dev")
        self.assertEqual(e.calls("gh", "pr", "create"), [])  # the promotion is only a line

    @marks.slow
    def test_land_main_folder_on_another_branch(self):
        main_before = g(self.main, "rev-parse", "main")
        g(self.main, "branch", "dev", "origin/dev")
        self.advance_dev()
        r = self.land(self.mk(view_json=self.dev_view()))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(g(self.main, "rev-parse", "main"), main_before, "main is not moved by a merge into dev")
        self.assertEqual(g(self.main, "rev-parse", "dev"), g(self.main, "rev-parse", "origin/dev"))

    @marks.slow
    def test_no_promotion_line_off_the_base(self):
        g(self.main, "checkout", "-q", "-b", "dev", "origin/dev")
        self.config("delivery.base: dev\n")  # no delivery.promote
        r = self.land(self.mk(view_json=self.dev_view()))
        self.assertEqual((r.returncode, r.stdout.splitlines()[-1]), (0, f"PR #7 {URL} land: done"), r.stderr)

    @marks.slow
    def test_no_promotion_line_for_a_pr_outside_the_base(self):
        g(self.main, "checkout", "-q", "-b", "dev", "origin/dev")
        self.config("delivery.base: staging\ndelivery.promote: main\n")  # a PR into dev is not a merge into the base
        r = self.land(self.mk(view_json=self.dev_view()))
        self.assertEqual((r.returncode, r.stdout.splitlines()[-1]), (0, f"PR #7 {URL} land: done"), r.stderr)

    def test_broken_settings_exit_1(self):
        self.config("# c\ndelivery.base dev\n")
        before = g(self.origin, "branch", "--list")
        e = self.mk()
        r = self.ship(e)
        self.assertEqual(r.returncode, 1)
        self.assertIn("settings: solo-sdd/config:2", r.stderr)
        self.assertEqual(e.calls("gh", "pr", "create"), [])
        self.assertEqual(g(self.origin, "branch", "--list"), before, "nothing pushed")
        e = self.mk(view_json=self.dev_view())
        r = self.land(e)
        self.assertEqual(r.returncode, 1)
        self.assertIn("settings: solo-sdd/config:2", r.stderr)
        self.assertEqual(e.calls("gh", "api", "-X", "PUT"), [])


class HumanMerge(ShipLandRepo):
    """Requirement: Human merge mode: merge and land leave the PR open; land --after-merge finishes after a person."""

    def setUp(self):
        super().setUp()
        self.put(self.main, "solo-sdd/config", "mode: team\n")  # the team default is delivery.merge-by: human

    def after(self, e):
        return e.run("land", str(self.main), str(self.wt), URL, "--after-merge")

    def test_land_refuses_then_after_merge_finishes(self):
        e = self.mk()
        r = self.land(e)
        self.assertEqual((r.returncode, r.stdout.strip()), (8, f"PR #7 waits for human merge: {URL}"), r.stderr)
        self.assertEqual(e.calls("gh", "api", "-X", "PUT"), [])
        self.assertTrue(self.wt.is_dir())
        r = self.after(e)  # the PR is still open: nothing moves
        self.assertEqual((r.returncode, r.stdout.strip()), (8, f"PR #7 waits for human merge: {URL}"), r.stderr)
        self.assertTrue(self.wt.is_dir())
        self.advance_origin()  # a person merged the PR on the server
        (e.d / "view.json").write_text(json.dumps([dict(OPEN, headRefOid=self.head(), state="MERGED")]))
        r = self.after(e)
        self.assertEqual((r.returncode, r.stdout.splitlines()[-1]), (0, f"PR #7 {URL} land: done"), r.stderr)
        self.assertEqual(g(self.main, "rev-parse", "main"), g(self.main, "rev-parse", "origin/main"))
        self.assertEqual(len(self.worktrees()), 1)
        self.assertEqual(g(self.main, "branch", "--list", "change/x"), "")
        self.assertEqual(e.calls("gh", "api", "-X", "PUT"), [], "the agent merged nothing")

    def test_merge_refuses(self):
        e = self.mk()
        e.env["GIT_DIR"] = str(self.main / ".git")  # merge reads the settings of the main folder of the current repository
        r = e.run("merge", URL, "squash", self.head())
        self.assertEqual((r.returncode, r.stdout.strip()), (8, f"PR #7 waits for human merge: {URL}"), r.stderr)
        self.assertEqual(e.calls("gh", "api"), [])

    def test_agent_mode_merges_as_before(self):
        self.put(self.main, "solo-sdd/config", "mode: team\ndelivery.merge-by: agent\n")
        r = self.land(self.mk())
        self.assertEqual((r.returncode, r.stdout.splitlines()[-1]), (0, f"PR #7 {URL} land: done"), r.stderr)

    def test_after_merge_in_agent_mode_never_merges(self):
        self.put(self.main, "solo-sdd/config", "")
        e = self.mk()
        r = self.after(e)
        self.assertEqual(r.returncode, 8, r.stderr)
        self.assertEqual(e.calls("gh", "api", "-X", "PUT"), [])

    def test_broken_settings_exit_1(self):
        self.put(self.main, "solo-sdd/config", "delivery.merge-by: bot\n")
        e = self.mk()
        r = self.land(e)
        self.assertEqual(r.returncode, 1)
        self.assertIn("settings: solo-sdd/config:1", r.stderr)
        self.assertEqual(e.calls("gh", "api", "-X", "PUT"), [])


class OpenBase(Base):
    """Requirement: Base branch from settings (open; settings of the main folder of the worktree)."""

    def test_open_takes_the_base(self):
        e = self.env()
        (e.d / "main/solo-sdd").mkdir(parents=True)
        (e.d / "main/solo-sdd/config").write_text("delivery.base: dev\n")
        r = e.run("open", str(e.d), "main", "T")
        self.assertEqual(r.returncode, 0, r.stderr)
        c = e.calls("gh", "pr", "create")[0]
        self.assertEqual(c[c.index("--base") + 1], "dev")

    def test_open_broken_settings(self):
        e = self.env()
        (e.d / "main/solo-sdd").mkdir(parents=True)
        (e.d / "main/solo-sdd/config").write_text("delivery.base: -x\n")
        r = e.run("open", str(e.d), "main", "T")
        self.assertEqual(r.returncode, 1)
        self.assertIn("settings: solo-sdd/config:1", r.stderr)
        self.assertEqual(e.calls("gh", "pr", "create"), [])
        self.assertEqual(e.calls("git", "-C", str(e.d), "push"), [])


def build_promote(root):
    """The bare origin and the work folder of Promote in root."""
    origin, work = root / "origin.git", root / "work"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True, env=GENV)
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)], check=True, env=GENV)
    (work / "r").write_text("r\n")
    g(work, "add", "-A")
    g(work, "commit", "-qm", "init")
    g(work, "remote", "add", "origin", str(origin))


class Promote(Base):
    """Requirement: Promotion PR. The repositories are a copy of ones built once (tests/shared_repo.py)."""

    def setUp(self):
        folder, _ = shared_repo.template("Promote", build_promote)
        self.repo = shared_repo.copy(folder)
        self.addCleanup(shutil.rmtree, self.repo, True)
        self.work = self.repo / "work"

    def push(self, *branches):
        for b in branches:
            g(self.work, "push", "-q", "origin", "HEAD:refs/heads/" + b)

    def promote(self, e, frm, to):
        (e.d / "bin/git").unlink()  # git is real, gh is faked
        return subprocess.run([sys.executable, str(SCRIPT), "promote", frm, to], capture_output=True, text=True,
                              timeout=30, stdin=subprocess.DEVNULL, env=dict(e.env, **GITENV), cwd=self.work)

    def no_merge(self, e):
        self.assertEqual([c for c in e.journal() if c[0] == "gh" and ("merge" in c or "PUT" in c)], [])

    def test_opens_the_next_step(self):
        self.push("dev", "staging")
        e = self.env()
        r = self.promote(e, "dev", "staging")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, f"PR #7 {URL} dev → staging: open, not merged"), r.stderr)
        c = e.calls("gh", "pr", "create")[0]
        self.assertEqual((c[c.index("--base") + 1], c[c.index("--head") + 1]), ("staging", "dev"))
        self.no_merge(e)

    def test_already_open_prints_the_same_url(self):
        e = self.env(list_json=[{"number": 42, "url": "https://github.com/o/r/pull/42"}])
        r = self.promote(e, "dev", "staging")
        self.assertEqual((r.returncode, r.stdout.strip()),
                         (0, "PR #42 https://github.com/o/r/pull/42 dev → staging: open, not merged"), r.stderr)
        lst = e.calls("gh", "pr", "list")[0]
        self.assertEqual((lst[lst.index("--head") + 1], lst[lst.index("--base") + 1]), ("dev", "staging"))
        self.assertEqual(e.calls("gh", "pr", "create"), [])
        self.no_merge(e)

    def test_release_pattern_takes_the_newest_version(self):
        self.push("staging", "release/1.9.0", "release/1.10.0", "release/1.2.0", "release/next", "releases/9.0.0",
                  "release/1.10.0-rc1")
        e = self.env()
        r = self.promote(e, "staging", "release/*")
        self.assertEqual(r.returncode, 0, r.stderr)
        c = e.calls("gh", "pr", "create")[0]
        self.assertEqual(c[c.index("--base") + 1], "release/1.10.0")
        self.no_merge(e)

    def test_option_like_names_refused(self):
        e = self.env()
        for frm, to in (("-x", "staging"), ("dev", "--upload-pack=x*")):
            r = e.run("promote", frm, to)  # fake git and gh: any call would show in the journal
            self.assertEqual(r.returncode, 1, (frm, to))
            self.assertIn("not a branch name", r.stderr)
        self.assertEqual(e.journal(), [])

    def test_no_release_branch(self):
        self.push("staging")
        e = self.env()
        r = self.promote(e, "staging", "release/*")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no branch matches release/* on origin", r.stderr)
        self.assertEqual(e.calls("gh", "pr"), [])

    def test_promotion_line_quotes_a_pattern(self):
        self.assertEqual(sp.promotion("staging", "release/*"),
                         "promotion: staging → release/*: sdd-pr.py promote staging 'release/*'")


LIST = "- [ ] amounts are in minor units\n- [x] refunds are idempotent\n* [ ] the charge is logged\nnot an item\n- [ ]   \n"
CONFIG = "checklist.money-safety.paths: billing/**\nchecklist.money-safety.file: docs/checklists/money-safety.md\n"
SECTION = "## Checklist: money-safety\n\n- [ ] amounts are in minor units\n- [ ] refunds are idempotent\n- [ ] the charge is logged\n"


TEXTS = ["amounts are in minor units", "refunds are idempotent", "the charge is logged", "keys are rotated",
         "limits are checked"]


def body(*ticks, head="Branch change/x, opened by sdd-pr.py\n\n"):
    """A body whose section holds the first len(ticks) items of TEXTS, ticked or not."""
    return head + "## Checklist: money-safety\n\n" + "".join("- [%s] %s\n" % ("x" if t else " ", TEXTS[i])
                                                             for i, t in enumerate(ticks))


def review(sha="abc123", login="person", state="APPROVED"):
    return {"login": login, "state": state, "commit_id": sha}


class PathChecklists(Base):
    """Requirement: Path checklists: open and ship add the section, merge and land gate on unticked items."""
    puts, no_merge = Merge.puts, Merge.no_merge

    def project(self, config=CONFIG, checklist=LIST, **files):
        files.setdefault("checks_json", GREEN)
        e = self.env(**files)
        (e.d / "main/solo-sdd").mkdir(parents=True)
        (e.d / "main/solo-sdd/config").write_text(config)
        if checklist is not None:
            (e.d / "main/docs/checklists").mkdir(parents=True)
            (e.d / "main/docs/checklists/money-safety.md").write_text(checklist)
        return e

    def edits(self, e):
        return e.calls("gh", "pr", "edit")

    def test_open_adds_the_section(self):  # Billing touched
        e = self.project(files_json=[frow("billing/charge.py")])
        r = e.run("open", str(e.d), "main", "T")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines(), [f"PR #7 checklist money-safety: 3 open items", f"PR #7 {URL}"])
        self.assertEqual(self.edits(e)[0][3:], [URL, "--body", SECTION])

    def test_no_match_no_section(self):  # No checklist path
        e = self.project(files_json=[frow("README.md"), frow("docs/billing/x.md")])
        r = e.run("open", str(e.d), "main", "T")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, f"PR #7 {URL}"), r.stderr)
        self.assertEqual(self.edits(e), [])
        r = e.run("merge", URL, "squash", "abc123")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_no_checklists_no_calls(self):  # a project without checklists: no extra gh calls
        e = self.env()
        e.run("open", str(e.d), "main", "T")
        self.assertEqual(e.calls("gh", "api"), [])
        self.assertEqual(e.calls("gh", "pr", "view"), [])

    def test_existing_body_kept_and_section_appended(self):
        e = self.project(files_json=[frow("billing/a.py")], view_json=[dict(OPEN, title="T", body="My notes\r\n")])
        e.run("open", str(e.d), "main", "T")
        self.assertEqual(self.edits(e)[0][5], "My notes\n\n" + SECTION)

    def test_repeated_ship_keeps_the_ticks(self):  # A repeated ship keeps the ticks
        e = self.project(files_json=[frow("billing/a.py")], view_json=[dict(OPEN, title="T", body=body(True, True, False))])
        r = e.run("open", str(e.d), "main", "T")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, f"PR #7 {URL}"), r.stderr)
        self.assertEqual(self.edits(e), [])

    @marks.slow
    def test_own_file_is_a_path(self):  # The PR edits the checklist itself
        for f in ("docs/checklists/money-safety.md", "solo-sdd/config"):
            e = self.project(files_json=[frow(f)])
            e.run("open", str(e.d), "main", "T")
            self.assertEqual(self.edits(e)[0][5], SECTION, f)

    @marks.slow
    def test_broken_checklist_stops_before_the_push(self):  # A broken checklist
        for config, checklist, why in (
                ("checklist.money-safety.paths: billing/**\n", LIST, "set both checklist.money-safety.paths and checklist.money-safety.file"),
                (CONFIG, None, "docs/checklists/money-safety.md not readable"),
                (CONFIG, "# no items\n- [ ]\n", "docs/checklists/money-safety.md holds no `- [ ]` item")):
            e = self.project(config, checklist, files_json=[frow("billing/a.py")])
            for args in (("open", str(e.d), "main", "T"), ("merge", URL, "squash", "abc123")):
                r = e.run(*args)
                self.assertEqual(r.returncode, 1, (why, args))
                self.assertIn(f"checklist money-safety: {why}", r.stderr)
            self.assertEqual(e.calls("git", "-C", str(e.d), "push"), [])
            self.no_merge(e)

    def test_open_items_refuse(self):  # Open items: two of five unticked
        five = "".join("- [ ] %s\n" % x for x in TEXTS)
        e = self.project(checklist=five, files_json=[frow("billing/a.py")],
                         view_json=[dict(OPEN, title="T", body=body(True, False, True, False, True))])
        r = e.run("merge", URL, "squash", "abc123")
        self.assertEqual((r.returncode, r.stdout.strip()), (8, "PR #7 checklist money-safety: 2 open items"), r.stderr)
        self.no_merge(e)
        self.assertEqual(e.calls("gh", "pr", "checks"), [], "the gate goes before CI and the merge request")

    def test_all_ticked_merges(self):  # All ticked
        e = self.project(files_json=[frow("billing/a.py")], view_json=[dict(OPEN, title="T", body=body(True, True, True))],
                         reviews_json=[review()])
        r = e.run("merge", URL, "squash", "abc123")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, f"PR #7 {URL} merged (squash)"), r.stderr)

    def test_section_edited_away(self):  # A section edited away
        e = self.project(files_json=[frow("billing/a.py")], view_json=[dict(OPEN, title="T", body="no section\n")])
        r = e.run("merge", URL, "squash", "abc123")
        self.assertEqual((r.returncode, r.stdout.strip()), (8, "PR #7 checklist money-safety: 3 open items"), r.stderr)
        self.no_merge(e)

    @marks.slow
    def test_the_file_items_count_not_the_marks(self):  # an emptied, cut or replaced section stays open
        for text, want in (("## Checklist: money-safety\n", 3),
                           ("## Checklist: money-safety\n- [x] fine\n", 3),
                           (body(True, True), 1),
                           (body(True, True, True) + "- [ ] one more check\n", 1),
                           (body(True, True, True).replace("refunds are", "refunds  are"), 0),
                           (body(True, True, True).replace("refunds are idempotent", "refunds are fine"), 1),
                           (body(True, True, True, head="## Checklist: money-safety\n- [ ] x\n"), 1),
                           (body(True, True, True), 0)):
            e = self.project(files_json=[frow("billing/a.py")], view_json=[dict(OPEN, title="T", body=text)],
                             reviews_json=[review()])
            r = e.run("merge", URL, "squash", "abc123")
            if want:
                self.assertEqual((r.returncode, r.stdout.strip()), (8, f"PR #7 checklist money-safety: {want} open items"), text)
                self.no_merge(e)
            else:
                self.assertEqual(r.returncode, 0, (text, r.stderr))

    def test_a_repeated_item_needs_each_tick(self):
        e = self.project(checklist="- [ ] check\n- [ ] check\n", files_json=[frow("billing/a.py")],
                         view_json=[dict(OPEN, title="T", body="## Checklist: money-safety\n- [x] check\n- [ ] check\n")])
        r = e.run("merge", URL, "squash", "abc123")
        self.assertEqual((r.returncode, r.stdout.strip()), (8, "PR #7 checklist money-safety: 1 open items"), r.stderr)

    def test_a_heading_without_a_name_is_no_section(self):
        e = self.env(checks_json=GREEN, view_json=[dict(OPEN, title="T", body="## Checklist:\n- [ ] template item\n")])
        self.assertEqual(e.run("merge", URL, "squash", "abc123").returncode, 0)

    def test_a_section_gates_without_settings(self):  # a person's section gates even when no checklist is set
        e = self.env(checks_json=GREEN, view_json=[dict(OPEN, title="T", body=body(False, head=""))])
        r = e.run("merge", URL, "squash", "abc123")
        self.assertEqual((r.returncode, r.stdout.strip()), (8, "PR #7 checklist money-safety: 1 open items"), r.stderr)

    def test_hostile_bodies(self):  # Hostile input: the body parser
        self.assertEqual(sp.sections(None), {})
        self.assertEqual(sp.sections(["## Checklist: a", "- [ ] x"]), {})
        self.assertEqual(sp.sections("## Checklist: a\r\n- [ ] x\r\n- [X] y\r\n- [x] z\r\n"), {"a": 1})
        self.assertEqual(sp.sections("## Checklist: a\n- [ ] x\n## Checklist: a\n- [ ] y\n"), {"a": 2})
        self.assertEqual(sp.sections("## Checklist: a\n- [ ] x\n### Notes\n- [ ] not an item of a\n"), {"a": 1})
        self.assertEqual(sp.sections("- [ ] before\n#hashtag line\n## Checklist: a\n#not-a-heading\n- [ ] x\n"), {"a": 1})
        start = time.monotonic()
        self.assertEqual(sp.sections("## Checklist: big\n" + "- [ ] " + "a " * 20000 + "\n" + "- [ ] x\n" * 10000),
                         {"big": 10001})
        self.assertLess(time.monotonic() - start, 2)


def first_section_only(body):
    """A mutant of sections: counts only the first section. The property must reject it."""
    found = sp.sections(body)
    return dict(list(found.items())[:1])


def check_sections(fn, blocks, eol):
    """Every section's count is exactly its unticked items, whatever the bullets, tick case, noise and line endings."""
    text, want = "", {}
    for name, items, noise in blocks:
        text += f"## Checklist: {name}" + eol + noise + eol
        for bullet, tick in items:
            text += f"{bullet} [{tick}] item" + eol
        want[name] = want.get(name, 0) + sum(t == " " for _, t in items)
        text += "## Other" + eol + "- [ ] outside" + eol
    assert fn(text) == want, (text, fn(text), want)


BLOCKS = st.lists(st.tuples(st.sampled_from(["money", "privacy", "a-1"]),
                            st.lists(st.tuples(st.sampled_from(["-", "*", "  -"]), st.sampled_from([" ", "x", "X"])), max_size=6),
                            st.sampled_from(["", "text", "    code", "#tag"])), max_size=5)


class ChecklistApproval(Base):
    """Requirement: Checklist approval: a ticked checklist also needs an approving review on the head commit by an
    account other than the PR author."""
    project, puts, no_merge = PathChecklists.project, Merge.puts, Merge.no_merge

    def merge(self, reviews=None, raw=None, ticks=(True, True, True), view=None, **files):
        if raw is not None:
            files["reviews_txt"] = raw
        elif reviews is not None:
            files["reviews_json"] = reviews
        e = self.project(files_json=[frow("billing/a.py")],
                         view_json=[view or dict(OPEN, title="T", body=body(*ticks))], **files)
        return e, e.run("merge", URL, "squash", "abc123")

    def refused(self, reviews=None, why="", **kw):
        e, r = self.merge(reviews, **kw)
        self.assertEqual((r.returncode, r.stdout.strip()), (8, "PR #7 checklist money-safety: no approval on abc123" + why),
                         (reviews, kw, r.stderr))
        self.no_merge(e)
        return e

    def test_ticked_not_approved(self):  # Ticked but not approved
        e = self.refused([])
        self.assertEqual(e.calls("gh", "pr", "checks"), [], "the gate goes before CI and the merge request")

    def test_approved_on_the_head_merges(self):  # Approved on the head commit
        e, r = self.merge([review()])
        self.assertEqual((r.returncode, r.stdout.strip()), (0, f"PR #7 {URL} merged (squash)"), r.stderr)
        c = e.calls("gh", "api", "repos/o/r/pulls/7/reviews")
        self.assertEqual(len(c), 1)
        self.assertIn("--paginate", c[0])

    def test_approval_before_a_new_commit(self):  # Approval before a new commit
        self.refused([review("old111")])

    @marks.slow
    def test_the_authors_own_review(self):  # The author's own review
        self.refused([review(login="owner")])
        self.refused([review(), review(state="CHANGES_REQUESTED")])
        self.refused([review(), review(state="COMMENTED")])
        self.refused([review(), review(state="DISMISSED")])
        e, r = self.merge([review(state="CHANGES_REQUESTED"), review(login="owner"), review()])
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_open_items_come_first(self):
        e, r = self.merge([], ticks=(True, False, True))
        self.assertEqual((r.returncode, r.stdout.strip()), (8, "PR #7 checklist money-safety: 1 open items"), r.stderr)
        self.assertEqual(e.calls("gh", "api", "repos/o/r/pulls/7/reviews"), [], "no review read while items are open")

    def test_reviews_cannot_be_read(self):  # Reviews cannot be read
        e = self.refused([review()], " (reviews not read: boom /reviews)", fail_json={"token": "/reviews", "code": 1})
        with mock.patch.object(sp, "sh", side_effect=subprocess.TimeoutExpired("gh", sp.REVIEWS_SEC)):
            ok, why = sp.read_reviews("o/r", "7")
        self.assertEqual((ok, why), (None, f"gh api: no answer in {sp.REVIEWS_SEC} s"))

    def test_author_not_read(self):
        self.refused([review()], " (reviews not read: no PR author)", view=dict(OPEN, title="T", body=body(True, True, True), author=None))

    @marks.slow
    def test_hostile_reviews(self):  # Hostile input: the reviews answer
        rows = json.dumps(review())
        for raw in (rows[:-5] + "\n", "not json\n", "[" + rows + "]\n", "5\n", "null\n", '"APPROVED"\n',
                    json.dumps({"state": "APPROVED", "commit_id": "abc123"}) + "\n",
                    json.dumps({"login": "person", "commit_id": "abc123"}) + "\n",
                    json.dumps({"login": "person", "state": "APPROVED"}) + "\n",
                    json.dumps({"login": "person", "state": ["APPROVED"], "commit_id": "abc123"}) + "\n",
                    json.dumps({"login": "person", "state": "APPROVED", "commit_id": 5}) + "\n",
                    rows + "\n" + json.dumps({"login": "x", "state": 1, "commit_id": "abc123"}) + "\n"):
            e, r = self.merge(raw=raw)
            self.assertEqual(r.returncode, 8, (raw, r.stdout, r.stderr))
            self.assertTrue(r.stdout.startswith("PR #7 checklist money-safety: no approval on abc123 (reviews not read: "),
                            (raw, r.stdout))
            self.no_merge(e)
        start = time.monotonic()
        many = "".join(json.dumps(review(login="p%d" % i, state="COMMENTED")) + "\n" for i in range(10000))
        e, r = self.merge(raw=many)
        self.assertEqual((r.returncode, r.stdout.strip()), (8, "PR #7 checklist money-safety: no approval on abc123"))
        e, r = self.merge(raw=many + rows + "\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertLess(time.monotonic() - start, 20)

    @marks.slow
    def test_null_login_or_commit(self):  # GitHub data: a deleted account (user null), a commit gone after a force-push
        for rows in ([{"login": None, "state": "CHANGES_REQUESTED", "commit_id": "abc123"}, review()],
                     [{"login": "ann", "state": "COMMENTED", "commit_id": None}, review()]):
            e, r = self.merge(rows)
            self.assertEqual(r.returncode, 0, (rows, r.stdout, r.stderr))
        self.refused([{"login": None, "state": "APPROVED", "commit_id": "abc123"}])
        self.refused([review(), {"login": "person", "state": "COMMENTED", "commit_id": None}])

    @marks.slow
    def test_a_settings_edit_needs_the_approval(self):  # an edit of solo-sdd/config is a path of every checklist
        e = self.project(files_json=[frow("solo-sdd/config")], view_json=[dict(OPEN, title="T")])
        r = e.run("merge", URL, "squash", "abc123")
        self.assertEqual((r.returncode, r.stdout.strip()), (8, "PR #7 checklist money-safety: 3 open items"), r.stderr)
        self.no_merge(e)
        for rows, want in (([], 8), ([review()], 0)):
            e = self.project(files_json=[frow("solo-sdd/config")], view_json=[dict(OPEN, title="T", body=body(True, True, True))],
                             reviews_json=rows)
            self.assertEqual(e.run("merge", URL, "squash", "abc123").returncode, want, rows)

    def test_no_checklist_path_needs_no_review(self):  # No checklist path
        e = self.project(files_json=[frow("README.md")], view_json=[dict(OPEN, title="T")])
        r = e.run("merge", URL, "squash", "abc123")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(e.calls("gh", "api", "repos/o/r/pulls/7/reviews"), [])


def first_review_wins(reviews, author, sha):
    """A mutant of approved: takes the first review of each account instead of the latest. The property must reject it."""
    first = {}
    for r in reviews:
        first.setdefault(r["login"], r)
    return any(a != author and r["state"] == "APPROVED" and r["commit_id"] == sha for a, r in first.items())


def check_approval(fn, reviews, author, sha):
    """The gate opens exactly when some account other than the author has, as its latest review, an APPROVED one on sha."""
    want = False
    for i, r in enumerate(reviews):
        later = [x for x in reviews[i + 1:] if x["login"] == r["login"]]
        want = want or (not later and r["login"] != author and r["state"] == "APPROVED" and r["commit_id"] == sha)
    assert fn(reviews, author, sha) == want, (reviews, author, sha, want)


REVIEWS = st.lists(st.builds(lambda a, s, c: {"login": a, "state": s, "commit_id": c},
                             st.sampled_from(["owner", "ann", "bob"]),
                             st.sampled_from(["APPROVED", "CHANGES_REQUESTED", "COMMENTED", "DISMISSED", "PENDING"]),
                             st.sampled_from(["head", "old"])), max_size=8)


class ChecklistApprovalProperty(unittest.TestCase):
    """Requirement: Checklist approval (property): only the latest review of each non-author account counts."""

    @settings(max_examples=500, deadline=None)
    @given(REVIEWS, st.sampled_from(["owner", "ann"]))
    def test_checklist_approval_property(self, reviews, author):
        check_approval(sp.approved, reviews, author, "head")

    def test_first_review_mutant_fails(self):
        @settings(max_examples=500, deadline=None, database=None)
        @given(REVIEWS, st.sampled_from(["owner", "ann"]))
        def mutant(reviews, author):
            check_approval(first_review_wins, reviews, author, "head")
        with self.assertRaises(AssertionError):
            mutant()


class PathChecklistsProperty(unittest.TestCase):
    """Requirement: Path checklists (property): the gate counts exactly the unticked items of every section."""

    @settings(max_examples=300, deadline=None)
    @given(BLOCKS, st.sampled_from(["\n", "\r\n"]))
    def test_path_checklists_property(self, blocks, eol):
        check_sections(sp.sections, blocks, eol)

    def test_first_section_mutant_fails(self):
        @settings(max_examples=300, deadline=None, database=None)
        @given(BLOCKS, st.sampled_from(["\n", "\r\n"]))
        def mutant(blocks, eol):
            check_sections(first_section_only, blocks, eol)
        with self.assertRaises(AssertionError):
            mutant()


class LandChecklist(ShipLandRepo):
    """Requirement: Path checklists: land on real git stops at open items, then at no approval, and leaves the worktree."""

    @marks.slow
    def test_land_open_items_then_ticked(self):
        self.put(self.main, "solo-sdd/config", CONFIG)
        self.put(self.main, "docs/checklists/money-safety.md", LIST)
        e = self.mk(files_json=[frow("billing/charge.py")],
                    view_json=[dict(OPEN, headRefOid=self.head(), title="T", body=body(False, True, False))])
        r = self.land(e)
        self.assertEqual((r.returncode, r.stdout.strip()), (8, "PR #7 checklist money-safety: 2 open items"), r.stderr)
        self.assertEqual(e.calls("gh", "api", "-X", "PUT"), [])
        self.assertTrue(self.wt.is_dir())
        (e.d / "body.txt").write_text(body(True, True, True))  # a person ticked every item on GitHub
        r = self.land(e)  # Requirement: Checklist approval: ticked, not approved
        self.assertEqual((r.returncode, r.stdout.strip()), (8, f"PR #7 checklist money-safety: no approval on {self.head()}"),
                         r.stderr)
        self.assertTrue(self.wt.is_dir())
        (e.d / "reviews.json").write_text(json.dumps([review(self.head())]))  # another account approved the head
        r = self.land(e)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(e.calls("gh", "api", "-X", "PUT")), 1)


class StopProperty(unittest.TestCase):
    def run_one(self, cmd, fail_at):
        e = Env(view_json=[dict(OPEN, headRefOid="change/x", title="T")], checks_json=GREEN)
        try:
            copy = e.d / "sdd_pr.py"
            shutil.copy(SCRIPT, copy)
            (e.d / "sdd-worktree.py").write_text(WT_STUB)
            if fail_at is not None:
                step = TOKENS[cmd][fail_at]
                # ponytail: refresh with code 3 is a conflict (code 6), so the failing steps get codes 1 and 2
                (e.d / "fail.json").write_text(json.dumps({"token": step, "code": 1 + fail_at % 2}))
            args = ["ship", str(e.d), str(e.d), "main", "T"] if cmd == "ship" else ["land", str(e.d), str(e.d), URL, "squash"]
            p = subprocess.run([sys.executable, str(copy), *args], capture_output=True, text=True, timeout=60,
                               stdin=subprocess.DEVNULL, env=e.env)
            steps = SHIP_STEPS if cmd == "ship" else LAND_STEPS
            seen = []
            for c in e.journal():
                joined = " ".join(c[1:]) + " "
                if c[0] == "sdd-worktree":
                    joined = c[1]
                for i, (n, tok) in enumerate(steps):
                    if c[0] == n and tok in (" " + joined if n == "git" else joined):
                        seen.append(i)
            return p, seen
        finally:
            e.close()

    @marks.slow
    @settings(max_examples=marks.examples(25), deadline=None)
    @given(cmd=st.sampled_from(["ship", "land"]), fail_at=st.one_of(st.none(), st.integers(0, 5)))
    def test_ship_and_land_stop_property(self, cmd, fail_at):
        p, seen = self.run_one(cmd, fail_at)
        if fail_at is None:
            self.assertEqual((p.returncode, seen), (0, list(range(6))), p.stderr)
            return
        self.assertEqual(seen, list(range(fail_at + 1)), p.stderr)  # those before the failed one were called, those after were not
        want = 7 if cmd == "land" and fail_at > 0 else 1
        self.assertEqual(p.returncode, want, p.stderr)


class Args(Base):
    def test_usage(self):
        e = self.env()
        for a in ([], ["open", "x"], ["wait"], ["wait", URL, "--bogus", "1"], ["wait", URL, "--timeout", "x"], ["wait", URL, "--stuck", "x"],
                  ["merge", URL, "fast", "h"], ["nope"],
                  ["merge", URL, "squash", "h", "--title"], ["merge", URL, "squash", "h", "--bogus", "x"]):
            r = e.run(*a)
            self.assertEqual(r.returncode, 2, a)
            self.assertIn("usage", r.stderr)


if __name__ == "__main__":
    unittest.main()
