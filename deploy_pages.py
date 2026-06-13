"""output/ HTML을 gh-pages 브랜치에 배포."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from config import OUTPUT_DIR, PNG_EXPORT_SUBDIR
from simulation.output_layout import dashboard_path


def _copy_html_tree(src: Path, dst: Path) -> int:
    n = 0
    if not src.is_dir():
        return 0
    for html in sorted(src.rglob("*.html")):
        rel = html.relative_to(src)
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(html, out)
        n += 1
    return n


def build_site(output_dir: Path, site_dir: Path) -> int:
    """Pages용 정적 파일만 site_dir에 복사."""
    if site_dir.exists():
        shutil.rmtree(site_dir)
    site_dir.mkdir(parents=True)

    n = 0
    index = dashboard_path(output_dir)
    if index.exists():
        shutil.copy2(index, site_dir / "index.html")
        n += 1

    for name in ("comparison.html", "history.json"):
        src = output_dir / name
        if src.exists():
            shutil.copy2(src, site_dir / name)
            if name.endswith(".html"):
                n += 1

    n += _copy_html_tree(output_dir / "runs", site_dir / "runs")
    n += _copy_html_tree(output_dir / "studies", site_dir / "studies")

    png_src = output_dir / PNG_EXPORT_SUBDIR
    if png_src.is_dir():
        png_dst = site_dir / PNG_EXPORT_SUBDIR
        png_dst.mkdir(parents=True, exist_ok=True)
        for png in sorted(png_src.glob("*.png")):
            shutil.copy2(png, png_dst / png.name)

    docs_dir = Path("docs")
    guide = docs_dir / "density_to_simulation_guide.html"
    if guide.exists():
        dst = site_dir / "docs"
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(guide, dst / guide.name)
        n += 1

    (site_dir / ".nojekyll").touch()
    return n


def deploy_with_git(site_dir: Path, message: str, *, push: bool) -> None:
    root = Path.cwd()
    worktree = root / ".gh-pages-deploy"

    if worktree.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], check=True, cwd=root)
    subprocess.run(["git", "worktree", "add", str(worktree), "gh-pages"], check=True, cwd=root)

    for item in worktree.iterdir():
        if item.name == ".git":
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    for item in site_dir.iterdir():
        dest = worktree / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    subprocess.run(["git", "add", "-A"], check=True, cwd=worktree)
    status = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, cwd=worktree
    )
    if not status.stdout.strip():
        print("변경 없음 — gh-pages 이미 최신")
    else:
        subprocess.run(["git", "commit", "-m", message], check=True, cwd=worktree)
        print("커밋 완료")

    if push:
        subprocess.run(["git", "push", "origin", "gh-pages"], check=True, cwd=worktree)
        print("푸시 완료: origin/gh-pages")

    subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], check=True, cwd=root)


def main():
    parser = argparse.ArgumentParser(description="output/ → GitHub Pages (gh-pages)")
    parser.add_argument("--output-dir", default=OUTPUT_DIR)
    parser.add_argument("--no-push", action="store_true", help="커밋만, push 생략")
    parser.add_argument("-m", "--message", default="Update GitHub Pages simulation results")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    site_dir = Path("site")
    n = build_site(output_dir, site_dir)
    png_n = len(list((site_dir / PNG_EXPORT_SUBDIR).glob("*.png"))) if (site_dir / PNG_EXPORT_SUBDIR).is_dir() else 0
    print(f"Pages 사이트 구성: HTML {n}개, PNG {png_n}개")
    deploy_with_git(site_dir, args.message, push=not args.no_push)
    shutil.rmtree(site_dir, ignore_errors=True)
    shutil.rmtree(Path(".gh-pages-deploy"), ignore_errors=True)
    print("완료 — https://codingfun02.github.io/physics-prob-v2/")


if __name__ == "__main__":
    main()
