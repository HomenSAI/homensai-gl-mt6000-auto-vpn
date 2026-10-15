"""Replay validated NDJSON observations; output contains no input extras/secrets."""
import argparse
import json
from pathlib import Path
from controller import Controller


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description="Offline VPN failover observer. Never applies routes.")
    parser.add_argument("observations", type=Path)
    args = parser.parse_args()
    controller = Controller()
    try:
        with args.observations.open(encoding="utf-8") as stream:
            while True:
                line = stream.readline(16385)
                if not line:
                    break
                if len(line) > 16384:
                    raise ValueError("observation too large")
                if not line.strip():
                    continue
                result = controller.step(json.loads(line, object_pairs_hook=unique_object))
                print(json.dumps(result, ensure_ascii=True, allow_nan=False))
    except (OSError, ValueError, TypeError):
        parser.exit(2, "Invalid observation stream; replay stopped.\n")


if __name__ == "__main__":
    main()
