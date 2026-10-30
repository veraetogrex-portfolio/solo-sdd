"""Проверка хука: опасные строки передаются как данные и никогда не исполняются."""
import importlib.util
import json
import pathlib
import subprocess
import unittest

from hypothesis import given, settings, strategies as st

GUARD = pathlib.Path(__file__).resolve().parents[1] / "global/process-guard.py"

_spec = importlib.util.spec_from_file_location("process_guard", GUARD)
pg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pg)

BAD_LINES = ["kill 1", "pkill node", "killall x", "osascript -e y", "launchctl list", "shutdown now"]
TEXT_LINES = BAD_LINES + ["process.kill(pid)", "shutdown()", "os.kill(1, 15)", "echo hi", ""]
PLAIN = ["cat", "cat > f.ts", "tee f", "python3 -", "node"]
# получатели, которые исполняют текст: оболочки, оболочки за любой обёрткой и незнакомые программы
SHELLS = ["bash", "sh", "zsh", "dash", "ksh", "eval", "source", ".", "xargs", "ssh host", "setsid bash", "sudo -u root bash",
          "stdbuf -o0 bash", "script -q /dev/null bash", "busybox sh", "unknowntool",
          "cat | tee >(bash)", "cat > >(sh)"]


@st.composite
def heredoc(draw, recv, lines, piped=""):
    mark = draw(st.sampled_from(["EOF", "END", "X", "_a1"]))
    quote = draw(st.sampled_from(["", "'", '"']))
    dash = draw(st.booleans())
    tabs = "\t" * draw(st.integers(0, 2)) if dash else ""
    body = draw(st.lists(st.sampled_from(lines), max_size=4))
    head = "%s <<%s%s%s%s%s" % (recv, "-" if dash else "", quote, mark, quote, piped)
    return "\n".join([head] + [tabs + b for b in body] + [tabs + mark])


class ProcessGuardTests(unittest.TestCase):
    def invoke(self, payload):
        return subprocess.run(
            ["/usr/bin/python3", str(GUARD)], input=payload,
            capture_output=True, text=True, timeout=3,
        )

    def command(self, command, tool="Bash"):
        return self.invoke(json.dumps({"tool_name": tool, "tool_input": {"command": command}}))

    def test_normal_commands_pass(self):
        for command in ("git status", "npm test", "rg skill .", "echo kill-switch", "cat README.md < /dev/null"):
            with self.subTest(command=command):
                result = self.command(command)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_process_commands_are_blocked(self):
        for command in (
            "pkill -f Applications", "killall Chrome", "kill 12345", "kill -0 12345",
            "/bin/kill -TERM 12345", "bash -c 'pkill -f marker'", "printf 12345 | xargs kill",
            'echo "$(killall Chrome)"', "true && /usr/bin/pkill marker", "p'kill' marker",
            "p\\kill marker", "pki\\\nll marker", "osascript -e 'quit app'",
            "launchctl stop anything", "shutdown -h now", "python3 -c 'import os; os.kill(12345, 15)'",
        ):
            with self.subTest(command=command):
                result = self.command(command)
                self.assertEqual(result.returncode, 2)
                self.assertIn("запрещ", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_heredoc_text_is_not_a_command(self):
        for command in (
            "cat > check.ts <<'EOF'\nprocess.kill(pid)\nshutdown()\nEOF",
            "python3 - <<'EOF'\nimport os\nos.kill(1, 15)\nEOF",
            'cat <<"X" > f\npkill node\nX\nls',
            "cat <<-EOF\n\tkill 1\n\tEOF\n",
            'grep -rn "shutdown" packages/mcp/src',
            "rg -e launchctl src",
        ):
            with self.subTest(command=command):
                result = self.command(command)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_heredoc_for_shell_or_tail_is_blocked(self):
        for command in (
            "bash <<'EOF'\npkill node\nEOF",
            "cat <<'EOF' | sh\nkill 1234\nEOF",
            "cat <<'EOF'\nhello\nEOF\nkill 1234",
            "cat <<'EOF' && kill 1234\nhello\nEOF",
            "grep foo kill.txt",
            "grep -e foo shutdown",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.command(command).returncode, 2)

    @settings(max_examples=300, deadline=None)
    @given(st.lists(st.tuples(st.sampled_from(PLAIN), st.data()), min_size=1, max_size=2))
    def test_heredoc_text_is_not_a_command_property(self, blocks):
        cmd = "\n".join(d.draw(heredoc(r, TEXT_LINES)) for r, d in blocks)
        self.assertFalse(pg.forbidden(cmd), cmd)

    @settings(max_examples=300, deadline=None)
    @given(st.data(), st.sampled_from(SHELLS), st.sampled_from(PLAIN), st.sampled_from(BAD_LINES), st.booleans())
    def test_heredoc_for_shell_is_a_command_property(self, data, shell, plain, bad, piped):
        recv, tail = (plain, " | " + shell) if piped else (shell, "")
        cmd = data.draw(heredoc(recv, ["echo hi"], tail))
        head, rest = cmd.split("\n", 1)
        with_bad = "\n".join([head, bad, rest])
        self.assertTrue(pg.forbidden(with_bad), with_bad)
        # хвост после маркера всегда команда, даже для необолочки
        plain_cmd = data.draw(heredoc(plain, ["echo hi"]))
        h2, r2 = plain_cmd.split("\n", 1)
        for tail_cmd in (plain_cmd + "\n&& kill 1", h2 + " && kill 1\n" + r2):
            self.assertTrue(pg.forbidden(tail_cmd), tail_cmd)

    def test_quotes_sed_and_substitution(self):
        for command in (
            "grep -nE 'zshrc|profile|bashrc|PATH|daemon|nohup|launchctl' $D/codex-install.sh | head -50",
            'grep -rln "run-prepared\\|runPrepared" packages apps --include="*.test.ts"; grep -n "spawnExecutor\\|shutdown" packages/mcp/src/*.ts | head -40',
            "sed -i '' 's|process.kill(-child.pid, sig);|child.kill(sig);|' packages/core/src/cli-agents/process.ts",
            "cat > f <<'EOF'\n$(pkill node)\nEOF",
        ):
            with self.subTest(command=command):
                result = self.command(command)
                self.assertEqual(result.returncode, 0, result.stderr)
        for command in (
            "cat <<EOF\n$(pkill node)\nEOF",
            "cat > f <<EOF\n`pkill node`\nEOF",
            'grep "$(pkill node)" f',
            "grep 'a|b' f; kill 1",
            "echo 'a\n<<EOF'\nkill 1\nEOF",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.command(command).returncode, 2)

    def test_shell_heredoc_through_prefixes_is_blocked(self):
        for head in ("timeout 5 bash", "timeout -s KILL 5 bash", "nice -n 5 bash", "! bash", "env A=1 sudo bash"):
            with self.subTest(head=head):
                self.assertEqual(self.command(head + " <<'EOF'\npkill node\nEOF").returncode, 2)
        for command in (
            "(bash <<'EOF'\npkill node\nEOF\n)",
            "{ bash <<'EOF'\npkill node\nEOF\n}",
            "if true; then bash <<'EOF'\npkill node\nEOF\nfi",
            "rg --pre 'pkill node' x .",
            "rg --pre=pkill x .",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.command(command).returncode, 2)
        self.assertEqual(self.command("timeout 5 cat <<'EOF'\npkill node\nEOF").returncode, 0)
        for command in ("bash<<'EOF'\npkill node\nEOF", "sh<<EOF\nkill 1234\nEOF", "caffeinate -i bash <<'EOF'\nkill 1\nEOF",
                        "grep -f /dev/null kill", "grep --file=/dev/null kill"):
            with self.subTest(command=command):
                self.assertEqual(self.command(command).returncode, 2)

    def test_process_substitution_and_escaped_redirect(self):
        for command in ("grep <(pkill node) f", "grep -e <(pkill node) f", "rg <(pkill node) .",
                        "cat \\<<X\nkill 1", "cat \\<<X\nkill 1\nX", "cat <<'EOF' \\\n| bash\nkill 1\nEOF",
                        "grep kill f | sh", "cat f | grep kill | sh", "cat <<'A'; cat <<'B' | sh\nx\nA\nkill 1\nB",
                        "cat <<'A'; bash <<'B'\nx\nA\nkill 1\nB", "sed -n '1w kill' f"):
            with self.subTest(command=command):
                self.assertEqual(self.command(command).returncode, 2)

    def test_text_block_is_same_in_both_hooks(self):
        # блок разбора скопирован в work_hooks.py: копии не должны разойтись
        wh = GUARD.with_name("work_hooks.py").read_text()
        own = GUARD.read_text()
        cut = lambda t, end: t[t.index("TEXT_SINKS = "):t.index(end)]
        self.assertEqual(cut(own, "def forbidden("), cut(wh, "def command_text("))

    def test_monitor_is_also_guarded(self):
        self.assertEqual(self.command("pkill marker", "Monitor").returncode, 2)

    def test_invalid_input_is_blocked(self):
        for payload in ("", "{", "[]", "null", '{}', '{"tool_name":"Bash","tool_input":{"command":null}}'):
            with self.subTest(payload=payload):
                result = self.invoke(payload)
                self.assertEqual(result.returncode, 2)
                self.assertIn("запрещ", result.stderr)

    def test_non_shell_tool_is_ignored(self):
        result = self.invoke('{"tool_name":"Read","tool_input":{"file_path":"kill.md"}}')
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
