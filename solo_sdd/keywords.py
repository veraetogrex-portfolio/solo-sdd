"""AGENTS.md keywords: the migration table of pre-English headings and items.

The block between the keywords markers is copied into global/sdd_worktree.py, global/sdd_dispatch_plan.py
and global/sdd_pr.py (they are laid out as separate files) by python3 scripts/sync_blocks.py: edit it here.
"""
import os
import re

# keywords:begin
# Pre-English AGENTS.md headings and items -> English. The old names live only here, as \u escapes,
# so the repository holds no Cyrillic letter. Scripts read only the English names.
OLD_SECTIONS = {
    "\u0420\u0430\u0431\u043e\u0447\u0430\u044f \u043a\u043e\u043f\u0438\u044f": "Working copy",
    "\u041f\u043e\u0441\u0442\u0430\u0432\u043a\u0430": "Delivery",
    "\u041a\u043e\u043c\u0430\u043d\u0434\u044b": "Commands",
}
OLD_ITEMS = {  # English section -> ((old item, English item), ...)
    "Working copy": (
        ("\u041f\u0443\u0442\u0438:", "Paths:"),
        ("\u041f\u043e\u0434\u0433\u043e\u0442\u043e\u0432\u043a\u0430:", "Prepare:"),
        ("\u041f\u043e\u0441\u043b\u0435 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u044f:", "After refresh:"),
        ("\u041e\u0431\u0449\u0438\u0435:", "Shared:"),
        ("\u041e\u0440\u043a\u0435\u0441\u0442\u0440\u0430\u0442\u043e\u0440\u043e\u0432:", "Orchestrators:"),
        ("\u041e\u0440\u043a\u0435\u0441\u0442\u0440\u0430\u0442\u043e\u0440: \u0441\u0430\u043c", "Orchestrator: solo"),
    ),
    "Delivery": (
        ("\u0420\u0435\u0436\u0438\u043c:", "Mode:"),
        ("\u0417\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a PR:", "PR title:"),
        ("\u0414\u0435\u043f\u043b\u043e\u0439:", "Deploy:"),
        ("\u0422\u043e\u043b\u044c\u043a\u043e \u0432\u043b\u0430\u0434\u0435\u043b\u0435\u0446:", "Owner only:"),
    ),
    "Commands": (("\u0422\u0435\u0441\u0442\u044b", "Tests"),),  # row of the commands table
}


def migrate_agents(text):
    """(text with the old headings and items renamed to English, English names found in order).

    Items are renamed only inside their section, at the start of a list item or a table row;
    every other byte stays as it was."""
    out, found, section = [], [], None
    for line in re.split(r"(?<=\n)", text):  # lines end only at \n, as in the file
        if line.startswith("## "):
            title = line[3:].strip()
            if title in OLD_SECTIONS:
                line = line.replace(title, OLD_SECTIONS[title], 1)
                title = OLD_SECTIONS[title]
                found.append(title)
            section = title
        else:
            for old, new in OLD_ITEMS.get(section, ()):
                m = re.match(r"(\s*(?:[-*]\s+|\|\s*))" + re.escape(old) + r"(?!\w)", line)
                if m:
                    line = m.group(1) + new + line[m.end():]
                    found.append(new)
                    break
        out.append(line)
    return "".join(out), list(dict.fromkeys(found))


def migrate_hint(path, found):
    """One line for a reader of an AGENTS.md with old keywords: the file, what was found, the command."""
    return "%s: pre-English keywords (%s) are ignored; run: solo-sdd migrate-agents %s" % (
        path, ", ".join(found), os.path.dirname(os.path.abspath(path)))
# keywords:end
