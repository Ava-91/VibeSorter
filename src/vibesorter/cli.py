from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from .duplicates import DEFAULT_MAX_DISTANCE, find_exact_duplicates, find_near_duplicates
from .gallery import gallery_from_file
from .history import list_history, record_batch, rollback_batch
from .operations import apply_reviewed
from .pipeline import analyze_image
from .proposal import build_proposal, proposal_from_dict, proposal_to_dict, proposal_to_json
from .review import ReviewedOperation, parse_selection, review_proposal
from .scanner import find_images
from .search import ImageQuery, search_cache
from .cache import AnalysisCache
from .vibes import VIBES, confidence_score


def _add_folder_argument(command: argparse.ArgumentParser) -> None:
    command.add_argument("folder", type=Path, help="Folder to scan or analyze.")
    command.add_argument("--no-recursive", action="store_true", help="Only use the selected folder.")


def _add_workers_argument(command: argparse.ArgumentParser) -> None:
    default_workers = min(8, max(1, os.cpu_count() or 1))
    command.add_argument("--workers", type=int, default=default_workers, help=f"Number of images to analyze concurrently (default: {default_workers}).")


def _add_filter_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument("--vibe", choices=VIBES, help="Only include images whose best vibe matches this category.")
    command.add_argument("--min-score", type=float, default=0.0, help="Ignore classifications below this score from 0 to 1 (default: 0).")
    command.add_argument("--max-text-likelihood", type=float, default=1.0, help="Skip images whose text/screenshot likelihood exceeds this value (default: 1).")


def _add_dimension_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument("--min-brightness", type=float)
    command.add_argument("--max-brightness", type=float)
    command.add_argument("--min-saturation", type=float)
    command.add_argument("--max-saturation", type=float)
    command.add_argument("--min-contrast", type=float)
    command.add_argument("--max-contrast", type=float)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vibesorter", description="Detect visual vibes in local images and safely review, apply, undo, or inspect organization plans.", epilog="Examples: vibesorter preview ./photos | vibesorter search ./photos --vibe 'Dark / Moody' | vibesorter propose ./photos --output proposal.json | vibesorter review proposal.json --accept 1,3-5 --output reviewed.json | vibesorter gallery proposal.json --output gallery.html | vibesorter apply reviewed.json --confirm | vibesorter rollback BATCH_ID --confirm")
    parser.add_argument("--version", action="version", version="VibeSorter 0.8.0")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Discover supported images (read-only)."); _add_folder_argument(scan)
    preview = subparsers.add_parser("preview", help="Detect vibes for a folder without changing files."); _add_folder_argument(preview); _add_workers_argument(preview); _add_filter_arguments(preview); preview.add_argument("--top", type=int, default=5); preview.add_argument("--json", action="store_true")
    analyze = subparsers.add_parser("analyze", help="Detect the vibe of one image and show its ranking."); analyze.add_argument("image", type=Path); analyze.add_argument("--json", action="store_true")
    stats = subparsers.add_parser("stats", help="Summarize vibe counts for a folder."); _add_folder_argument(stats); _add_workers_argument(stats); _add_filter_arguments(stats); stats.add_argument("--json", action="store_true")
    search = subparsers.add_parser("search", help="Search an existing local analysis cache without rescanning or re-analyzing images."); search.add_argument("folder", type=Path, help="Analyzed image library containing .vibesorter/analysis.json."); search.add_argument("--vibe", choices=VIBES); search.add_argument("--min-score", type=float, default=0.0); search.add_argument("--max-text-likelihood", type=float, default=1.0); search.add_argument("--path", dest="path_contains", help="Case-insensitive filename/path substring."); _add_dimension_arguments(search); search.add_argument("--limit", type=int); search.add_argument("--json", action="store_true")
    duplicates = subparsers.add_parser("duplicates", help="Find exact and visually near-duplicate images (read-only)."); _add_folder_argument(duplicates); duplicates.add_argument("--max-distance", type=int, default=DEFAULT_MAX_DISTANCE); duplicates.add_argument("--json", action="store_true")
    propose = subparsers.add_parser("propose", help="Generate a deterministic, read-only folder organization proposal."); _add_folder_argument(propose); _add_workers_argument(propose); _add_filter_arguments(propose); propose.add_argument("--output-root", type=Path, default=Path("VibeSorted")); propose.add_argument("--output", type=Path); propose.add_argument("--json", action="store_true")
    review = subparsers.add_parser("review", help="Review a saved proposal without changing files."); review.add_argument("proposal", type=Path); review.add_argument("--accept", default="", help="Accept operation IDs/ranges, e.g. 1,3-5 or all."); review.add_argument("--reject", default="", help="Reject operation IDs/ranges, e.g. 2,7-9 or all."); review.add_argument("--accept-vibe", action="append", default=[], help="Accept every operation for this vibe; repeatable."); review.add_argument("--reject-vibe", action="append", default=[], help="Reject every operation for this vibe; repeatable."); review.add_argument("--output", type=Path, help="Write the reviewed JSON to this path."); review.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    gallery = subparsers.add_parser("gallery", help="Build a local image-grid gallery from an existing proposal (no re-analysis)."); gallery.add_argument("proposal", type=Path, help="Proposal or reviewed proposal JSON."); gallery.add_argument("--output", type=Path, default=Path("vibesorter-gallery.html"), help="HTML output path.")
    apply = subparsers.add_parser("apply", help="Apply only accepted operations from a reviewed proposal."); apply.add_argument("reviewed", type=Path, help="Reviewed proposal JSON produced by the review command."); apply.add_argument("--confirm", action="store_true", help="Explicitly confirm filesystem changes."); apply.add_argument("--dry-run", action="store_true", help="Show what would move without changing files."); apply.add_argument("--history", type=Path, default=Path(".vibesorter/history.jsonl"), help="Where to record successful moves."); apply.add_argument("--json", action="store_true", help="Print machine-readable results.")
    rollback = subparsers.add_parser("rollback", help="Safely undo a completed sorting batch."); rollback.add_argument("batch_id", help="Batch ID printed by apply."); rollback.add_argument("--confirm", action="store_true", help="Explicitly confirm filesystem changes."); rollback.add_argument("--dry-run", action="store_true", help="Check what would be restored without changing files."); rollback.add_argument("--history", type=Path, default=Path(".vibesorter/history.jsonl"), help="Move history JSONL file."); rollback.add_argument("--json", action="store_true")
    history = subparsers.add_parser("history", help="Inspect recorded sorting operations."); history.add_argument("--history", type=Path, default=Path(".vibesorter/history.jsonl")); history.add_argument("--json", action="store_true")
    return parser


def _analyze_one(path: Path):
    try: return analyze_image(path), None
    except Exception as exc: return None, exc


def _analyze_many(images: list[Path], workers: int):
    if workers < 1: raise ValueError("--workers must be at least 1")
    with ThreadPoolExecutor(max_workers=workers) as executor: yield from executor.map(_analyze_one, images)


def _load_images(args, parser):
    try: return find_images(args.folder, recursive=not args.no_recursive)
    except (FileNotFoundError, NotADirectoryError) as exc: parser.error(str(exc))


def _validate_filters(args, parser):
    if hasattr(args, "workers") and args.workers < 1: parser.error("--workers must be at least 1")
    if hasattr(args, "min_score") and not 0 <= args.min_score <= 1: parser.error("--min-score must be between 0 and 1")
    if hasattr(args, "max_text_likelihood") and not 0 <= args.max_text_likelihood <= 1: parser.error("--max-text-likelihood must be between 0 and 1")
    if hasattr(args, "max_distance") and args.max_distance < 1: parser.error("--max-distance must be at least 1")
    if getattr(args, "top", 1) < 1: parser.error("--top must be at least 1")
    for name in ("min_brightness", "max_brightness", "min_saturation", "max_saturation", "min_contrast", "max_contrast"):
        value = getattr(args, name, None)
        if value is not None and not 0 <= value <= 1: parser.error(f"--{name.replace('_', '-')} must be between 0 and 1")
    if getattr(args, "limit", None) is not None and args.limit < 1: parser.error("--limit must be at least 1")
    if getattr(args, "min_brightness", None) is not None and getattr(args, "max_brightness", None) is not None and args.min_brightness > args.max_brightness: parser.error("--min-brightness cannot exceed --max-brightness")
    if getattr(args, "min_saturation", None) is not None and getattr(args, "max_saturation", None) is not None and args.min_saturation > args.max_saturation: parser.error("--min-saturation cannot exceed --max-saturation")
    if getattr(args, "min_contrast", None) is not None and getattr(args, "max_contrast", None) is not None and args.min_contrast > args.max_contrast: parser.error("--min-contrast cannot exceed --max-contrast")


def _analyze_folder(images, workers, *, vibe=None, min_score=0.0, max_text_likelihood=1.0, show_progress=True):
    groups = defaultdict(list); results = []; skipped = 0
    for index, (result, error) in enumerate(_analyze_many(images, workers), start=1):
        path = images[index - 1]
        if error is not None:
            skipped += 1
            if show_progress: print(f"[{index}/{len(images)}] SKIP  {path}: {error}")
            continue
        if result.features.text_likelihood > max_text_likelihood: continue
        best = result.best
        if best.score < min_score or (vibe is not None and best.name != vibe): continue
        results.append(result); groups[best.name].append((path, best.score, result.features.text_likelihood))
        if show_progress: print(f"[{index}/{len(images)}] {best.name:<18} {best.score:>5.0%}  {path}")
    return groups, results, skipped


def _json_groups(groups, top=None):
    return {name: {"count": len(items), "examples": [{"path": str(path), "score": round(score, 4), "text_likelihood": round(text, 4)} for path, score, text in (items if top is None else items[:top])], "average_score": round(sum(score for _, score, _ in items) / len(items), 4)} for name, items in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))}


def _run_search(args, parser) -> int:
    root = args.folder.expanduser()
    cache_path = root / ".vibesorter" / "analysis.json"
    if not cache_path.is_file():
        parser.error(f"no analysis cache found at {cache_path}; run an incremental library analysis first")
    query = ImageQuery(vibe=args.vibe, min_score=args.min_score, max_text_likelihood=args.max_text_likelihood, path_contains=args.path_contains, min_brightness=args.min_brightness, max_brightness=args.max_brightness, min_saturation=args.min_saturation, max_saturation=args.max_saturation, min_contrast=args.min_contrast, max_contrast=args.max_contrast, limit=args.limit)
    results = search_cache(AnalysisCache(cache_path), query)
    if args.json:
        print(json.dumps({"count": len(results), "results": [{"path": str(r.path), "vibe": r.best.name, "score": round(r.best.score, 4), "text_likelihood": round(r.features.text_likelihood, 4), "brightness": round(r.features.brightness, 4), "saturation": round(r.features.saturation, 4), "contrast": round(r.features.contrast, 4)} for r in results]}, indent=2, ensure_ascii=False))
        return 0
    print(f"Found {len(results)} matching cached image(s).\n")
    for result in results:
        print(f"{result.best.name:<18} {result.best.score:>5.0%}  {result.path}")
    print("\nSearch is read-only; no images were analyzed, created, moved, copied, renamed, deleted, or modified.")
    return 0


def _run_review(args, parser):
    try: data = json.loads(args.proposal.expanduser().read_text(encoding="utf-8")); proposal = proposal_from_dict(data)
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc: parser.error(f"invalid proposal: {exc}")
    try:
        accepted = parse_selection(args.accept, len(proposal.operations)); rejected = parse_selection(args.reject, len(proposal.operations))
    except ValueError as exc: parser.error(str(exc))
    reviewed = review_proposal(proposal, accept_ids=accepted, reject_ids=rejected, accept_vibes=set(args.accept_vibe), reject_vibes=set(args.reject_vibe))
    output = {**proposal_to_dict(proposal), "review": [{"id": item.operation.id, "status": item.status} for item in reviewed]}
    if args.output: args.output.expanduser().write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"); print(f"Reviewed proposal written to {args.output.expanduser()}")
    elif args.json: print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"Review: {len(reviewed)} operation(s)\n")
        for item in reviewed: print(f"[{item.operation.id:>4}] {item.status:<8} {item.operation.vibe:<18} {item.operation.source} -> {item.operation.destination}")
        print("\nReview only: no files were created, moved, copied, renamed, deleted, or modified.")
    return 0


def _load_reviewed(path: Path, parser) -> tuple[ReviewedOperation, ...]:
    try: data = json.loads(path.expanduser().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: parser.error(f"invalid reviewed proposal: {exc}")
    try:
        proposal = proposal_from_dict(data)
        statuses = {int(item["id"]): item["status"] for item in data.get("review", [])}
        if set(statuses) != {operation.id for operation in proposal.operations}: raise ValueError("reviewed proposal must contain one status for every operation")
        if any(status not in {"accepted", "rejected", "pending"} for status in statuses.values()): raise ValueError("invalid review status")
        return tuple(ReviewedOperation(operation, statuses[operation.id]) for operation in proposal.operations)
    except (KeyError, TypeError, ValueError) as exc: parser.error(f"invalid reviewed proposal: {exc}")


def _run_apply(args, parser):
    if not args.confirm and not args.dry_run: parser.error("refusing to change files without --confirm (use --dry-run to preview)")
    reviewed = _load_reviewed(args.reviewed, parser)
    results = apply_reviewed(reviewed, confirm=args.confirm, dry_run=args.dry_run)
    if args.confirm and not args.dry_run:
        batch_id = uuid4().hex[:12]; recorded = record_batch(batch_id, results, args.history)
    else: recorded = 0; batch_id = None
    if args.json:
        print(json.dumps({"batch_id": batch_id, "recorded": recorded, "results": [{"id": r.operation_id, "status": r.status, "source": str(r.source), "destination": str(r.destination), "detail": r.detail} for r in results]}, indent=2, ensure_ascii=False))
    else:
        for result in results: print(f"[{result.operation_id:>4}] {result.status:<8} {result.source} -> {result.destination}" + (f" ({result.detail})" if result.detail else ""))
        moved = sum(result.status == "moved" for result in results); print(f"\n{moved} file(s) moved; conflicts and missing sources were never overwritten.")
        if batch_id: print(f"Batch: {batch_id}\nHistory: {args.history.expanduser()}")
    return 0


def _run_rollback(args, parser):
    if not args.confirm and not args.dry_run: parser.error("refusing to change files without --confirm (use --dry-run to preview)")
    try: results = rollback_batch(args.history, args.batch_id, confirm=args.confirm, dry_run=args.dry_run)
    except (OSError, ValueError, json.JSONDecodeError) as exc: parser.error(str(exc))
    if args.json: print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for result in results: print(f"[{result['operation_id']:>4}] {result['status']:<9} {result['destination']} -> {result['source']} ({result['detail']})")
        print(f"\nRollback check complete for batch {args.batch_id}.")
    return 0


def _run_history(args):
    records = list_history(args.history)
    if args.json: print(json.dumps(records, indent=2, ensure_ascii=False)); return 0
    if not records: print(f"No history recorded in {args.history}"); return 0
    for item in records: print(f"{item.get('timestamp','')}  {item.get('batch_id','')}  op {item.get('operation_id','?')}  {item.get('source','')} -> {item.get('destination','')}")
    return 0


def main() -> int:
    parser = build_parser(); args = parser.parse_args()
    if args.command == "search": _validate_filters(args, parser); return _run_search(args, parser)
    if args.command == "review": return _run_review(args, parser)
    if args.command == "gallery":
        try: output = gallery_from_file(args.proposal, args.output)
        except (OSError, json.JSONDecodeError, ValueError) as exc: parser.error(f"invalid gallery source: {exc}")
        print(f"Gallery written to {output}"); return 0
    if args.command == "apply": return _run_apply(args, parser)
    if args.command == "rollback": return _run_rollback(args, parser)
    if args.command == "history": return _run_history(args)
    if args.command == "analyze":
        result, error = _analyze_one(args.image.expanduser())
        if error is not None: parser.error(str(error))
        if args.json: print(json.dumps({"path": str(result.path), "best": {"name": result.best.name, "score": result.best.score}, "confidence": confidence_score(result.scores), "text_likelihood": result.features.text_likelihood, "ranking": [{"name": s.name, "score": s.score} for s in result.scores]}, indent=2))
        else: print(f"Image: {result.path}\nBest vibe: {result.best.name} ({result.best.score:.0%})\nConfidence: {confidence_score(result.scores):.0%}\nText/screenshot likelihood: {result.features.text_likelihood:.0%}\n\nVibe ranking:"); [print(f"  {s.name:<18} {s.score:.0%}") for s in result.scores]
        return 0
    images = _load_images(args, parser)
    if args.command == "scan": print(f"Found {len(images)} image(s) in {args.folder.expanduser()}"); [print(image) for image in images]; return 0
    _validate_filters(args, parser)
    if args.command == "duplicates":
        exact = find_exact_duplicates(images); near = find_near_duplicates(images, max_distance=args.max_distance)
        if args.json: print(json.dumps({"total": len(images), "exact_duplicates": [{"hash": d, "paths": [str(p) for p in ps]} for d, ps in exact.items()], "near_duplicates": [{"left": str(l), "right": str(r), "distance": d} for l, r, d in near]}, indent=2)); return 0
        print(f"Scanned {len(images)} image(s) for duplicates.\n\n=== Exact duplicate groups: {len(exact)} ===")
        for paths in exact.values(): print("\n".join(f"  {path}" for path in paths), "")
        print(f"=== Near-duplicate pairs (distance <= {args.max_distance}): {len(near)} ==="); [print(f"  {d:>2}  {l}  <->  {r}") for l, r, d in near]; print("\nNo files were created, moved, copied, renamed, deleted, or modified."); return 0
    groups, results, skipped = _analyze_folder(images, args.workers, vibe=args.vibe, min_score=args.min_score, max_text_likelihood=args.max_text_likelihood, show_progress=not args.json and args.command != "propose")
    if args.command == "propose":
        proposal = build_proposal(results, args.output_root); data = proposal_to_json(proposal)
        if args.output: args.output.expanduser().write_text(data, encoding="utf-8"); print(f"Proposal written to {args.output.expanduser()}")
        elif args.json: print(data, end="")
        else:
            print(f"Proposed organization: {len(proposal.operations)} image(s) -> {proposal.output_root}\n")
            for op in proposal.operations: print(f"[{op.id:>4}] {op.vibe:<18} {op.score:>5.0%}  {op.source}\n       -> {op.destination}")
            print("\nRead-only proposal: no files were created, moved, copied, renamed, deleted, or modified.")
        return 0
    if args.command == "stats":
        if args.json: print(json.dumps({"total": len(images), "analyzed": len(images)-skipped, "skipped": skipped, "vibes": _json_groups(groups)}, indent=2)); return 0
        print(f"Analyzing {len(images)} image(s) for vibe statistics...\n\n=== Vibe statistics ==="); [print(f"{n:<18} {len(i):>5} image(s)  avg confidence {sum(s for _,s,_ in i)/len(i):.0%}") for n,i in sorted(groups.items(), key=lambda x:(-len(x[1]),x[0]))]; print(f"\nTotal: {len(images)-skipped} analyzed, {skipped} skipped."); return 0
    if args.json: print(json.dumps({"total": len(images), "analyzed": len(images)-skipped, "skipped": skipped, "vibes": _json_groups(groups, args.top)}, indent=2, ensure_ascii=False)); return 0
    print(f"Analyzing {len(images)} image(s) locally in {args.folder.expanduser()}\n\n=== Proposed vibe folders ===")
    for name, items in sorted(groups.items(), key=lambda x:(-len(x[1]),x[0])):
        print(f"\n{name} — {len(items)} image(s)"); [print(f"  {s:>5.0%}  {p}") for p,s,_ in items[:args.top]]
        if len(items) > args.top: print(f"  ... and {len(items)-args.top} more")
    print(f"\nAnalysis complete — {len(images)-skipped} analyzed, {skipped} skipped.\nNo files were created, moved, copied, or modified."); return 0


if __name__ == "__main__": raise SystemExit(main())