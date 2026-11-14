"""Hook check: dangerous strings are passed as data and never executed."""
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import time
import unittest

from hypothesis import given, settings, strategies as st

GUARD = pathlib.Path(__file__).resolve().parents[1] / "global/process-guard.py"

_spec = importlib.util.spec_from_file_location("process_guard", GUARD)
pg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pg)

BAD_LINES = ["kill 1", "pkill node", "killall x", "osascript -e y", "launchctl list", "shutdown now"]
TEXT_LINES = BAD_LINES + ["process.kill(pid)", "shutdown()", "os.kill(1, 15)", "echo hi", ""]
PLAIN = ["cat", "cat > f.ts", "tee f", "python3 -", "node"]
# receivers that execute text: shells, shells behind any wrapper and unknown programs
SHELLS = ["bash", "sh", "zsh", "dash", "ksh", "eval", "source", ".", "xargs", "ssh host", "setsid bash", "sudo -u root bash",
          "stdbuf -o0 bash", "script -q /dev/null bash", "busybox sh", "unknowntool",
          "cat | tee >(bash)", "cat > >(sh)"]


NAMES = ["pkill", "killall", "kill", "osascript", "launchctl", "shutdown"]
MSG_CHARS = st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters=" :.,-_/();&|")
MSG_FORMS = ['git commit -m "%s"', "git commit -am '%s'", 'git tag v1 --message "%s"', 'gh pr create --title "%s"',
             'gh issue create -b "%s"', 'gh pr comment 1 --body="%s"']


def message_violations(forbidden, name, pre, post, form):
    """The name inside a message passes, the same name as the command of bash -c is refused."""
    found = []
    message = form % ("%s %s %s" % (pre, name, post))
    if forbidden(message):
        found.append("message refused: " + message)
    shell = 'bash -c "%s %s"' % (name, post)
    if not forbidden(shell):
        found.append("shell string passed: " + shell)
    return found


# the characters a plain parameter expansion may hold between ${ and }
PLAIN_EXPANSION = st.characters(whitelist_categories=(), whitelist_characters="abcXYZ019_#:-=+?%/.@*!,^~")


def expansion_violations(forbidden, name, op, word, bad, at, quoted):
    """A plain expansion before a commit with a forbidden word in its message passes; the same expansion with one
    character outside the allowlist inserted (bad) or without its closing brace (bad is None) is refused."""
    found = []
    body = name + op + word
    plain = "${%s}" % body
    if quoted:
        plain = '"%s"' % plain
    tail = '; git commit -m "graceful shutdown"'
    if forbidden("T=%s%s" % (plain, tail)):
        found.append("plain refused: " + plain)
    at = min(at, len(body))
    broken = "${%s}" % (body[:at] + bad + body[at:]) if bad else "${" + body
    if not forbidden("T=%s%s" % (broken, tail)):
        found.append("unreadable passed: " + broken)
    return found


ZSH_FORMS = ['git commit -m "graceful %s"', "git commit -m %s", "git commit -am 'a %s b'", 'grep -n "%s" docs/x.md', "grep %s x"]


def zsh_violations(forbidden, name, form, at):
    """A commit or search line with a forbidden word in its message or pattern, with =( inserted at a position outside
    that word (at the line start, end or anywhere between), is refused: the line is checked uncut."""
    line = form % name
    word = line.index(name)
    spots = [i for i in range(len(line) + 1) if not word < i < word + len(name)]
    i = spots[at % len(spots)]
    cmd = line[:i] + "=(" + line[i:]
    return [] if forbidden(cmd) else ["passed: " + cmd]


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
                self.assertIn("forbidden", result.stderr)
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
            "grep foo kill",
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
        # the tail after the marker is always a command, even for a non-shell
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
        # Requirement: Tests use the block check (shared-blocks): the shell block of work_hooks.py, copied here
        r = subprocess.run([sys.executable, str(GUARD.parents[1] / "scripts" / "sync_blocks.py"), "--check"],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    # Requirement: Messages and paths are not commands
    def test_messages_and_paths_are_not_commands_a_commit_message(self):
        for command in ('git commit -m "fix: graceful shutdown of the worker"', 'gh pr create --title "Add kill switch"',
                        "git commit -am 'stop: no killall'", 'git -C repo tag -a v1 --message="launchctl notes"',
                        'gh issue create -t "osascript bug" -b "pkill hangs"', 'gh pr edit 3 --body="kill it"'):
            with self.subTest(command=command):
                result = self.command(command)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_messages_and_paths_are_not_commands_a_file_path(self):
        for command in ("cat docs/kill.md", "grep foo kill.txt", "ls src/shutdown/x.py"):
            with self.subTest(command=command):
                result = self.command(command)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_messages_and_paths_are_not_commands_a_command_in_a_shell_string(self):
        for command in ('bash -c "kill 1"', 'git commit -m "$(pkill node)"', "git commit -m `killall x`",
                        'git commit -m "msg" && kill 1', 'git log -m "kill 1"', 'gh pr create -t "$(shutdown now)"',
                        "git commit -m $'x\\'' ; kill 1 #'", 'git commit -m "${ kill 1; }"', "grep $'x\\'' ; kill 1 #' f",
                        # the shell and the parser disagree on quotes: a comment `#'` and an earlier $'…'
                        "git commit -m #'\nkill 1 #'", "gh pr create -t #'\npkill node #'", "grep #'\nkill 1 #' f",
                        "echo $'\\''a' ; git commit -m 'x ; kill 1 #'", "echo $'\\''a' ; grep 'x ; kill 1 #' f"):
            with self.subTest(command=command):
                self.assertEqual(self.command(command).returncode, 2)

    def test_messages_and_paths_are_not_commands_a_command_by_its_path(self):
        for command in ("/bin/kill 1", "/usr/bin/pkill node", "cat docs/kill", "xargs /bin/kill"):
            with self.subTest(command=command):
                self.assertEqual(self.command(command).returncode, 2)

    @settings(max_examples=300, deadline=None)
    @given(st.sampled_from(NAMES), st.text(MSG_CHARS, max_size=20), st.text(MSG_CHARS, max_size=20), st.sampled_from(MSG_FORMS))
    def test_messages_and_paths_are_not_commands_property(self, name, pre, post, form):
        self.assertEqual(message_violations(pg.forbidden, name, pre, post, form), [])

    def test_messages_and_paths_are_not_commands_property_catches_a_mutant(self):
        # a guard that drops quoted text without parsing lets `bash -c "kill 1"` through: the property must see it
        mutant = lambda c: bool(pg.FORBIDDEN.search(re.sub(r"\"[^\"]*\"|'[^']*'", "", c)))
        self.assertNotEqual(message_violations(mutant, "kill", "", " 1", MSG_FORMS[0]), [])

    def test_messages_and_paths_are_not_commands_a_parameter_expansion_earlier_on_the_line(self):
        for command in ('T="${TMPDIR:-/tmp}"; git commit -m "graceful shutdown"', 'echo ${HOME}; git commit -m "graceful shutdown"'):
            with self.subTest(command=command):
                result = self.command(command)
                self.assertEqual(result.returncode, 0, result.stderr)

    # Requirement: Shell forms the text cut cannot read
    def test_shell_forms_the_text_cut_cannot_read_a_plain_expansion_before_a_search(self):
        result = self.command('T="${TMPDIR:-/tmp}"; grep -n "kill" docs/x.md')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_shell_forms_the_text_cut_cannot_read_a_brace_command_substitution(self):
        self.assertEqual(self.command('X=${ kill 1; }; git commit -m "done"').returncode, 2)

    def test_shell_forms_the_text_cut_cannot_read_an_expansion_the_cut_cannot_read(self):
        tail = '; git commit -m "graceful shutdown"'
        for head in ('echo ${X:-"a b"}', "echo ${X:-\\}}", "T=${X", "echo ${\tX}", "echo ${\nX}", "echo ${X:-\\}", "echo ${X:-a;b}",
                     "echo ${X:-'a'}", "echo ${X:-$Y}", "echo ${X:-`id`}", "echo ${X:-{a}}", "echo ${X:-a|b}", "echo ${X:-a b}", "echo ${"):
            with self.subTest(command=head + tail):
                self.assertEqual(self.command(head + tail).returncode, 2)
        self.assertEqual(self.command('git commit -m "graceful shutdown" ${').returncode, 2, "a ${ at the end of the line")

    def test_shell_forms_the_text_cut_cannot_read_a_long_line(self):
        line = "${X" * 33334 + '; git commit -m "graceful shutdown"'
        start = time.monotonic()
        self.assertTrue(pg.forbidden(line))
        self.assertLess(time.monotonic() - start, 1)

    @settings(max_examples=300, deadline=None)
    @given(st.text(PLAIN_EXPANSION, max_size=12), st.sampled_from(["", ":-", "-", "#", "##", "%", "%%", "/", "//", ":="]),
           st.text(PLAIN_EXPANSION, max_size=8), st.sampled_from(["'", '"', "\\", " ", "\t", "\n", ";", "$", "&", "|", "(", "{", "`", None]),
           st.integers(0, 40), st.booleans())
    def test_shell_forms_the_text_cut_cannot_read_property(self, name, op, word, bad, at, quoted):
        self.assertEqual(expansion_violations(pg.forbidden, name, op, word, bad, at, quoted), [])

    def test_shell_forms_the_text_cut_cannot_read_a_zsh_process_substitution(self):
        for command in ("git commit -m =(kill 1)", 'T="${TMPDIR:-/tmp}"; git commit -m =(kill 1)', "grep =(kill 1) x",
                        'git commit -m "graceful shutdown" =(', "git commit -m =(kill 1", 'git commit -m "x" #c =(kill 1)',
                        "echo $'x'; git commit -m =(kill 1)"):
            with self.subTest(command=command):
                self.assertEqual(self.command(command).returncode, 2)

    def test_shell_forms_the_text_cut_cannot_read_a_known_false_refusal_of_an_array_assignment(self):
        self.assertEqual(self.command('A=(x y); git commit -m "graceful shutdown"').returncode, 2,
                         "an array assignment passes now: move it to the passing tests and docs/hooks.md")

    def test_shell_forms_the_text_cut_cannot_read_a_long_line_of_zsh_substitutions(self):
        line = "=(" * 50000 + '; git commit -m "graceful shutdown"'
        start = time.monotonic()
        self.assertTrue(pg.forbidden(line))
        self.assertLess(time.monotonic() - start, 1)

    @settings(max_examples=300, deadline=None)
    @given(st.sampled_from(NAMES), st.sampled_from(ZSH_FORMS), st.one_of(st.just(0), st.just(-1), st.integers(0, 80)))
    def test_shell_forms_the_text_cut_cannot_read_property_zsh_substitution(self, name, form, at):
        self.assertEqual(zsh_violations(pg.forbidden, name, form, at), [])

    def test_known_limit_a_computed_program_name(self):
        # not a requirement: a name computed by an expansion is not analysed (docs/hooks.md); a refusal here means it is now
        result = self.command("${X:-kill} 1")
        self.assertEqual(result.returncode, 0, "a computed name is refused now: move it to the refused tests and docs/hooks.md")

    def test_shell_forms_the_text_cut_cannot_read_property_catches_mutants(self):
        # the old trigger (every ${) refuses a plain expansion; an allowlist that takes the backslash passes ${X:-\a}
        mutants = {"old": (r"\$'|\$\{|(?:^|[\s;&|()])#", ("TMPDIR", ":-", "/tmp", None, 0, True)),
                   "backslash": (r"\$'|\$\{(?![A-Za-z0-9_#:=+?%/.@*!,^~\\-]*\})|(?:^|[\s;&|()])#", ("X", ":-", "a", "\\", 3, False))}
        kept = pg.UNCUT
        try:
            for name, (trigger, case) in mutants.items():
                pg.UNCUT = re.compile(trigger)
                self.assertNotEqual(expansion_violations(pg.forbidden, *case), [], name)
            # a trigger without =( cuts the message after it: the zsh property must see it
            pg.UNCUT = re.compile(kept.pattern.replace(r"|=\(", "", 1))
            self.assertNotEqual(kept.pattern, pg.UNCUT.pattern, "the mutant must drop =(")
            self.assertNotEqual(zsh_violations(pg.forbidden, "shutdown", ZSH_FORMS[0], -1), [], "no =(")
        finally:
            pg.UNCUT = kept

    def test_monitor_is_also_guarded(self):
        self.assertEqual(self.command("pkill marker", "Monitor").returncode, 2)

    def test_invalid_input_is_blocked(self):
        for payload in ("", "{", "[]", "null", '{}', '{"tool_name":"Bash","tool_input":{"command":null}}'):
            with self.subTest(payload=payload):
                result = self.invoke(payload)
                self.assertEqual(result.returncode, 2)
                self.assertIn("forbidden", result.stderr)

    def test_non_shell_tool_is_ignored(self):
        result = self.invoke('{"tool_name":"Read","tool_input":{"file_path":"kill.md"}}')
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
