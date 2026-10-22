from __future__ import annotations

from pathlib import Path

from vibesorter.cli import build_parser


def test_search_command_parses_filters() -> None:
    args = build_parser().parse_args([
        "search",
        "photos",
        "--vibe",
        "retro",
        "--min-score",
        "0.75",
        "--path",
        "billie",
        "--min-brightness",
        "0.4",
        "--max-saturation",
        "0.9",
        "--limit",
        "25",
        "--json",
    ])

    assert args.command == "search"
    assert args.folder == Path("photos")
    assert args.vibe == "retro"
    assert args.min_score == 0.75
    assert args.path_contains == "billie"
    assert args.min_brightness == 0.4
    assert args.max_saturation == 0.9
    assert args.limit == 25
    assert args.json is True


def test_search_command_has_no_workers_or_recursive_scan_options() -> None:
    help_text = build_parser().format_help()
    search = build_parser()._subparsers._group_actions[0].choices["search"].format_help()

    assert "search" in help_text
    assert "--workers" not in search
    assert "--no-recursive" not in search
    assert "--json" in search



def test_search_command_parses_profile_and_uncertainty_filters() -> None:
    args = build_parser().parse_args([
        "search",
        "photos",
        "--media-type",
        "photograph",
        "--color",
        "blue",
        "--color",
        "red",
        "--temperature",
        "cool",
        "--saturation-label",
        "muted",
        "--brightness-label",
        "dark",
        "--profile-vibe",
        "dreamy",
        "--include-secondary-vibes",
        "--uncertain-margin",
        "0.08",
    ])
    assert args.media_type == "photograph"
    assert args.color == ["blue", "red"]
    assert args.temperature == "cool"
    assert args.profile_saturation == "muted"
    assert args.profile_brightness == "dark"
    assert args.profile_vibes == ["dreamy"]
    assert args.include_secondary_vibes is True
    assert args.uncertain_margin == 0.08
