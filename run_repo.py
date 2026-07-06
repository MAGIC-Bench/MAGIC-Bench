"""Run one repo through the CLI differential-oracle loop.

    python run_repo.py --config configs/<repo>.json

See configs/_template.json for the config schema and configs/_drafts.template.json
for the input-draft schema.
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent / "engine"))
import cli_loop


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="path to a repo config JSON")
    args = ap.parse_args()
    config = json.loads(pathlib.Path(args.config).read_text(encoding="utf-8"))
    cli_loop.run(config)


if __name__ == "__main__":
    main()
