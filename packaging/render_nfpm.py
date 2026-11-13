"""Render packaging/nfpm.yaml.in for a given version/architecture."""

from __future__ import annotations

import argparse
import pathlib
import platform

ARCH_MAP = {"x86_64": "amd64", "AMD64": "amd64", "aarch64": "arm64", "arm64": "arm64"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("version")
    ap.add_argument("--arch", default=platform.machine())
    ap.add_argument("--template", default="packaging/nfpm.yaml.in")
    args = ap.parse_args()

    arch = ARCH_MAP.get(args.arch, args.arch)
    tpl = pathlib.Path(args.template).read_text(encoding="utf-8")
    print(tpl.replace("@@VERSION@@", args.version).replace("@@ARCH@@", arch), end="")


if __name__ == "__main__":
    main()
