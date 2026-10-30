"""Проверка sdd_pr.py: open, wait, merge на подмене gh и git (первыми в PATH)."""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "global/sdd_pr.py"
URL = "https://github.com/o/r/pull/7"

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
if name == "git":
    if "rev-parse" in a:
        print("change/x")
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
                            "state": "OPEN", "title": "Заголовок PR"}}])
    try:
        n = int(open(d + "/vn").read())
    except OSError:
        n = 0
    open(d + "/vn", "w").write(str(n + 1))
    print(json.dumps(seq[min(n, len(seq) - 1)]))
elif a[:1] == ["api"]:
    if a[1:3] in (["-X", "PUT"], ["-X", "DELETE"]):
        m = sc("merge.json" if a[2] == "PUT" else "delete.json", {{"code": 0, "err": ""}})
        sys.stderr.write(m["err"])
        sys.exit(m["code"])
    print(sc("behind.json", 0))
elif a[:2] == ["pr", "merge"]:
    sys.stderr.write("base branch policy prohibits the merge; use --admin\\n")
    sys.exit(1)
"""


def chk(bucket, link=""):
    return {"name": "t", "state": bucket.upper(), "bucket": bucket, "link": link}


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
        self.wt = tempfile.mkdtemp()  # gh запускается в папке worktree, она должна существовать
        self.addCleanup(shutil.rmtree, self.wt, True)

    def test_new_pr(self):
        e = self.env()
        r = e.run("open", self.wt, "main", "Заголовок")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, f"PR #7 {URL}"), r.stderr)
        c = e.calls("gh", "pr", "create")[0]
        for pair in (["--base", "main"], ["--head", "change/x"], ["--title", "Заголовок"]):
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
        r = self.wait(e)
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
        self.assertEqual(e.calls("gh", "run", "view")[0][3:], ["555", "-R", "o/r", "--log-failed"])  # без -R gh ищет репозиторий в текущей папке

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


GREEN = [[chk("pass"), chk("skipping")]]
OPEN = {"headRefOid": "abc123", "headRefName": "change/x", "baseRefName": "main", "state": "OPEN"}
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

    def test_owner_bypass_squash(self):  # PR закрыт правилом с обходом владельца
        e, r = self.merge()
        self.assertEqual((r.returncode, r.stdout.strip()), (0, f"PR #7 {URL} merged (squash)"), r.stderr)
        self.assertEqual(len(self.puts(e)), 1)
        path, f = self.fields(e)
        self.assertEqual(path, MERGE_API)
        for x in ("merge_method=squash", "sha=abc123", "commit_title=Заголовок PR (#7)"):
            self.assertIn(x, f)
        self.assertEqual(e.calls("gh", "pr", "merge"), [])
        self.assertEqual(len(e.calls("gh", "api", "-X", "DELETE")), 1)
        self.assertEqual(e.calls("gh", "api", "-X", "DELETE")[0][4], "repos/o/r/git/refs/heads/change/x")

    def test_ci_not_green(self):  # CI не зелёный
        for bad in ("fail", "pending", "cancel"):
            e, r = self.merge(checks_json=[[chk("pass"), chk(bad)]])
            self.assertEqual(r.returncode, 1, bad)
            self.assertIn("CI не зелёный", r.stderr)
            self.no_merge(e)

    def test_no_checks(self):  # Проверок нет
        e = self.env()
        r = e.run("merge", URL, "squash", "abc123")
        self.assertEqual(r.returncode, 1)
        self.assertIn("CI не зелёный", r.stderr)
        self.no_merge(e)

    def test_github_refused(self):  # GitHub отказал
        e, r = self.merge(merge_json={"code": 1, "err": "gh: Head branch was modified (HTTP 409)\n"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("Head branch was modified", r.stderr)
        self.assertEqual((r.stdout, e.calls("gh", "api", "-X", "DELETE")), ("", []))

    def test_delete_failed(self):  # Ветку удалить не удалось
        e, r = self.merge(delete_json={"code": 1, "err": "gh: Server Error (HTTP 500)\n"})
        self.assertEqual(r.returncode, 0)
        lines = r.stdout.splitlines()
        self.assertEqual(lines[0], f"PR #7 {URL} merged (squash)")
        self.assertTrue(lines[1].startswith("ветка change/x не удалена: "), r.stdout)
        self.assertEqual(len(lines), 2)

    def test_delete_already_gone(self):
        for code in (404, 422):
            e, r = self.merge(delete_json={"code": 1, "err": f"gh: Reference does not exist (HTTP {code})\n"})
            self.assertEqual((r.returncode, r.stdout.strip()), (0, f"PR #7 {URL} merged (squash)"), code)

    def test_fork_branch_kept(self):  # Ветка PR из форка
        e, r = self.merge(view_json=[dict(OPEN, title="T", isCrossRepository=True)])
        self.assertEqual((r.returncode, r.stdout.strip()), (0, f"PR #7 {URL} merged (squash)"), r.stderr)
        self.assertEqual(e.calls("gh", "api", "-X", "DELETE"), [])

    def test_empty_title(self):  # Пустой заголовок
        for t in ("", "   "):
            e, r = self.merge(view_json=[dict(OPEN, title=t)])
            self.assertEqual(r.returncode, 1, repr(t))
            self.assertIn("заголов", r.stderr)
            self.no_merge(e)
        e, r = self.merge("--title", "")
        self.assertEqual(r.returncode, 1)
        self.no_merge(e)

    def test_view_failed(self):  # gh pr view упал
        e, r = self.merge(viewfail_txt="x")
        self.assertEqual(r.returncode, 1)
        self.assertIn("TLS handshake timeout", r.stderr)
        self.no_merge(e)

    def test_title_from_local_commit(self):  # Заголовок из локального коммита
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
        self.assertIn("commit_title=Заголовок PR (#7)", f)

    def test_behind_before_ci(self):  # порядок: behind раньше CI
        e, r = self.merge(behind_json=2, checks_json=[[chk("fail")]])
        self.assertEqual(r.returncode, 5)
        self.no_merge(e)

    def test_already_merged(self):
        e = self.env(view_json=[dict(OPEN, headRefOid="zzz", state="MERGED")])
        r = e.run("merge", URL, "squash", "abc123")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "PR #7 merged (уже)"))
        self.no_merge(e)

    def test_hash_not_head(self):
        e = self.env()
        r = e.run("merge", URL, "squash", "other")
        self.assertEqual(r.returncode, 1)
        self.assertIn("hash other не голова PR (abc123)", r.stderr)
        self.no_merge(e)

    def test_behind(self):
        e, r = self.merge(behind_json=2)
        self.assertEqual(r.returncode, 5)
        self.assertIn("behind 2", r.stdout)
        self.assertEqual(e.calls("gh", "api")[0][2], "repos/o/r/compare/main...abc123")
        self.no_merge(e)


class Args(Base):
    def test_usage(self):
        e = self.env()
        for a in ([], ["open", "x"], ["wait"], ["wait", URL, "--bogus", "1"], ["wait", URL, "--timeout", "x"],
                  ["merge", URL, "fast", "h"], ["nope"],
                  ["merge", URL, "squash", "h", "--title"], ["merge", URL, "squash", "h", "--bogus", "x"]):
            r = e.run(*a)
            self.assertEqual(r.returncode, 2, a)
            self.assertIn("использование", r.stderr)


if __name__ == "__main__":
    unittest.main()
