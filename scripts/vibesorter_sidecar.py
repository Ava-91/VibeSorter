import sys

from vibesorter.entrypoint import main


def run() -> int:
    try:
        return int(main())
    except KeyboardInterrupt:
        print("VibeSorter sidecar interrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"VibeSorter sidecar failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
