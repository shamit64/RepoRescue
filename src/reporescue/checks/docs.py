"""Documentation and project hygiene checks."""

from reporescue.checks import Status, check


@check("docs.readme", "docs", "README")
def readme(ctx):
    path = ctx.top_level("readme", "readme.md", "readme.rst", "readme.txt")
    if path is None:
        return Status.FAIL, "No README found at the repository root."
    text = ctx.read_text(path.relative_to(ctx.root)) or ""
    words = len(text.split())
    if words < 50:
        return Status.WARN, f"{path.name} is very short ({words} words)."
    return Status.PASS, f"{path.name} present ({words} words)."


@check("docs.license", "docs", "License")
def license_file(ctx):
    path = ctx.top_level("license", "licence", "copying")
    if path is None:
        return Status.FAIL, "No LICENSE file. Others cannot legally reuse the code."
    return Status.PASS, f"{path.name} present."


@check("docs.gitignore", "docs", ".gitignore")
def gitignore(ctx):
    if (ctx.root / ".gitignore").is_file():
        return Status.PASS, ".gitignore present."
    return Status.WARN, "No .gitignore at the repository root."


@check("docs.contributing", "docs", "Contributing guide")
def contributing(ctx):
    for base in (ctx.root, ctx.root / ".github", ctx.root / "docs"):
        if base.is_dir() and any(p.stem.lower() == "contributing" for p in base.iterdir()):
            return Status.PASS, "Contributing guide present."
    return Status.WARN, "No CONTRIBUTING guide."
