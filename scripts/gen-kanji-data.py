#!/usr/bin/env python3
"""
Generate kanji-data.ts from KanjiVG SVG files.

Reads all kanji from ../kanji/*.csv (relative to the project root),
fetches authoritative SVG stroke data from the KanjiVG GitHub repository,
parses each stroke path in order (s1, s2, ...), resamples to evenly-spaced
points, and writes web-client/src/templates/kanji-data.ts.

Usage:
    python3 scripts/gen-kanji-data.py
"""

import csv
import math
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Tuple

KANJIVG_BASE = "https://raw.githubusercontent.com/KanjiVG/kanjivg/master/kanji/{}.svg"
VIEWBOX_SIZE = 109.0
POINTS_PER_UNIT = 40  # points per unit of normalized arc length (coords in [0,1])
MIN_POINTS = 8        # floor so very short strokes still animate smoothly
SVG_NS = "http://www.w3.org/2000/svg"
KVG_NS = "http://kanjivg.tagaini.net"

KANJI_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "kanji")


def is_kanji(ch: str) -> bool:
    cp = ord(ch)
    return (
        0x4E00 <= cp <= 0x9FFF
        or 0x3400 <= cp <= 0x4DBF
        or 0x20000 <= cp <= 0x2A6DF
    )


def csv_label(fname: str) -> str:
    """Convert a CSV filename like 'kanji_3-6.csv' to a display label like 'Lessons 3–6'."""
    m = re.search(r"kanji_(.+)\.csv", fname)
    if not m:
        return fname
    raw = m.group(1)
    # single number → "Lesson N", range → "Lessons N–M"
    if "-" in raw:
        parts = raw.split("-", 1)
        return f"Lessons {parts[0]}–{parts[1]}"
    return f"Lesson {raw}"


def load_kanji_from_csvs() -> tuple[List[Tuple[str, str]], List[Tuple[str, List[str]]]]:
    """
    Read all kanji/*.csv files and return:
      - A deduplicated list of (kanji_char, reading) pairs in first-seen order.
      - A list of (lesson_label, [kanji_chars]) lesson groups in file order.

    Reading is taken from the first single-kanji entry for that character,
    falling back to the first compound entry that contains it.
    """
    single_readings: dict[str, str] = {}
    fallback_readings: dict[str, str] = {}
    order: list[str] = []
    lesson_groups: list[tuple[str, list[str]]] = []

    csv_dir = os.path.realpath(KANJI_DIR)
    for fname in sorted(os.listdir(csv_dir)):
        if not fname.endswith(".csv"):
            continue
        label = csv_label(fname)
        group_chars: list[str] = []

        with open(os.path.join(csv_dir, fname), encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entry = row.get("Kanji", "").strip().lstrip("★")
                reading = row.get("Hiragana", "").strip()
                kanji_chars = [ch for ch in entry if is_kanji(ch)]
                is_single = len(kanji_chars) == 1

                for ch in kanji_chars:
                    if ch not in fallback_readings:
                        fallback_readings[ch] = reading
                        order.append(ch)
                        group_chars.append(ch)
                    if is_single and ch not in single_readings:
                        single_readings[ch] = reading

        lesson_groups.append((label, group_chars))

    all_kanji = []
    seen: set[str] = set()
    for ch in order:
        if ch not in seen:
            seen.add(ch)
            reading = single_readings.get(ch) or fallback_readings.get(ch, "")
            all_kanji.append((ch, reading))

    return all_kanji, lesson_groups


def kanji_to_codepoint(char: str) -> str:
    return f"{ord(char):05x}"


def fetch_kanjivg(char: str) -> str:
    code = kanji_to_codepoint(char)
    url = KANJIVG_BASE.format(code)
    with urllib.request.urlopen(url) as resp:
        return resp.read().decode("utf-8")


def parse_path_d(d: str) -> List[Tuple[str, List[float]]]:
    """Tokenize an SVG path 'd' attribute into (command, args) pairs."""
    tokens = re.findall(
        r"[MLCSQTAZHVmlcsqtazhv]|[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", d
    )
    commands = []
    i = 0
    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
            args: List[float] = []
            while i < len(tokens) and not tokens[i].isalpha():
                args.append(float(tokens[i]))
                i += 1
            commands.append((cmd, args))
        else:
            i += 1
    return commands


def sample_cubic_bezier(
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    n: int = 4,
) -> List[Tuple[float, float]]:
    points = []
    for i in range(n + 1):
        t = i / n
        mt = 1 - t
        x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
        y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
        points.append((x, y))
    return points


def path_to_points_dense(d: str) -> List[Tuple[float, float]]:
    """Convert an SVG path string to a dense list of (x, y) points."""
    commands = parse_path_d(d)
    points: List[Tuple[float, float]] = []
    current = (0.0, 0.0)
    last_ctrl: Tuple[float, float] | None = None

    for cmd, args in commands:
        if cmd == "M":
            current = (args[0], args[1])
            points.append(current)
            last_ctrl = None
        elif cmd == "m":
            current = (current[0] + args[0], current[1] + args[1])
            points.append(current)
            last_ctrl = None
        elif cmd == "L":
            for i in range(0, len(args), 2):
                current = (args[i], args[i + 1])
                points.append(current)
            last_ctrl = None
        elif cmd == "l":
            for i in range(0, len(args), 2):
                current = (current[0] + args[i], current[1] + args[i + 1])
                points.append(current)
            last_ctrl = None
        elif cmd == "C":
            for i in range(0, len(args), 6):
                p1 = (args[i], args[i + 1])
                p2 = (args[i + 2], args[i + 3])
                p3 = (args[i + 4], args[i + 5])
                pts = sample_cubic_bezier(current, p1, p2, p3, n=8)
                points.extend(pts[1:])
                last_ctrl = p2
                current = p3
        elif cmd == "c":
            for i in range(0, len(args), 6):
                p1 = (current[0] + args[i], current[1] + args[i + 1])
                p2 = (current[0] + args[i + 2], current[1] + args[i + 3])
                p3 = (current[0] + args[i + 4], current[1] + args[i + 5])
                pts = sample_cubic_bezier(current, p1, p2, p3, n=8)
                points.extend(pts[1:])
                last_ctrl = p2
                current = p3
        elif cmd == "S":
            for i in range(0, len(args), 4):
                p1 = (
                    (2 * current[0] - last_ctrl[0], 2 * current[1] - last_ctrl[1])
                    if last_ctrl
                    else current
                )
                p2 = (args[i], args[i + 1])
                p3 = (args[i + 2], args[i + 3])
                pts = sample_cubic_bezier(current, p1, p2, p3, n=8)
                points.extend(pts[1:])
                last_ctrl = p2
                current = p3
        elif cmd == "s":
            for i in range(0, len(args), 4):
                p1 = (
                    (2 * current[0] - last_ctrl[0], 2 * current[1] - last_ctrl[1])
                    if last_ctrl
                    else current
                )
                p2 = (current[0] + args[i], current[1] + args[i + 1])
                p3 = (current[0] + args[i + 2], current[1] + args[i + 3])
                pts = sample_cubic_bezier(current, p1, p2, p3, n=8)
                points.extend(pts[1:])
                last_ctrl = p2
                current = p3
        else:
            if cmd not in ("C", "c", "S", "s"):
                last_ctrl = None

    return points


def arc_length(points: List[Tuple[float, float]]) -> float:
    total = 0.0
    for i in range(1, len(points)):
        dx = points[i][0] - points[i - 1][0]
        dy = points[i][1] - points[i - 1][1]
        total += math.sqrt(dx * dx + dy * dy)
    return total


def resample_by_arc_length(
    points: List[Tuple[float, float]], n: int
) -> List[Tuple[float, float]]:
    """Resample a polyline to exactly n evenly-spaced points by arc length."""
    if len(points) <= 1:
        return points * n

    cum: List[float] = [0.0]
    for i in range(1, len(points)):
        dx = points[i][0] - points[i - 1][0]
        dy = points[i][1] - points[i - 1][1]
        cum.append(cum[-1] + math.sqrt(dx * dx + dy * dy))

    total = cum[-1]
    resampled = []
    for k in range(n):
        target = total * k / (n - 1)
        for i in range(1, len(cum)):
            if cum[i] >= target - 1e-10:
                seg = cum[i] - cum[i - 1]
                t = (target - cum[i - 1]) / seg if seg > 1e-10 else 0.0
                x = points[i - 1][0] + t * (points[i][0] - points[i - 1][0])
                y = points[i - 1][1] + t * (points[i][1] - points[i - 1][1])
                resampled.append((x, y))
                break

    return resampled


def get_stroke_numbers_in_group(elem: ET.Element) -> List[int]:
    """Recursively collect all 1-based stroke numbers from paths within a group."""
    numbers = []
    for child in elem.iter(f"{{{SVG_NS}}}path"):
        m = re.search(r"-s(\d+)$", child.get("id", ""))
        if m:
            numbers.append(int(m.group(1)))
    return sorted(numbers)


def get_radical_groups(root: ET.Element, char: str) -> List[dict]:
    """
    Extract one-level-deep radical groups from a KanjiVG SVG root.

    Finds the root <g> for `char`, then returns its direct child <g> elements
    that have a kvg:element attribute, along with the 0-based stroke indices
    owned by each group.
    """
    codepoint = kanji_to_codepoint(char)
    root_group = None
    for elem in root.iter(f"{{{SVG_NS}}}g"):
        if elem.get("id", "") == f"kvg:{codepoint}":
            root_group = elem
            break

    if root_group is None:
        return []

    groups = []
    for child in root_group:
        if child.tag != f"{{{SVG_NS}}}g":
            continue
        element = child.get(f"{{{KVG_NS}}}element", "")
        position = child.get(f"{{{KVG_NS}}}position") or None

        if not element:
            continue

        stroke_numbers = get_stroke_numbers_in_group(child)
        if stroke_numbers:
            groups.append({
                "element": element,
                "position": position,
                # Convert to 0-based indices
                "strokeIndices": [n - 1 for n in stroke_numbers],
            })

    return groups


def get_strokes_from_svg(svg_text: str) -> tuple:
    """Extract normalized stroke paths and radical groups from a KanjiVG SVG."""
    root = ET.fromstring(svg_text)

    stroke_paths = []
    for elem in root.iter(f"{{{SVG_NS}}}path"):
        elem_id = elem.get("id", "")
        m = re.search(r"-s(\d+)$", elem_id)
        if m:
            stroke_paths.append((int(m.group(1)), elem.get("d", "")))

    stroke_paths.sort(key=lambda x: x[0])

    strokes = []
    for _, d in stroke_paths:
        if not d:
            continue
        dense = path_to_points_dense(d)
        arc_len_normalized = arc_length(dense) / VIEWBOX_SIZE
        n = max(MIN_POINTS, round(arc_len_normalized * POINTS_PER_UNIT))
        resampled = resample_by_arc_length(dense, n)
        normalized = [
            [round(x / VIEWBOX_SIZE, 4), round(y / VIEWBOX_SIZE, 4)]
            for x, y in resampled
        ]
        strokes.append(normalized)

    return strokes, root


def escape_ts_string(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


def generate_ts(kanji_data: list, lesson_groups: List[Tuple[str, List[str]]]) -> str:
    lines = [
        "/**",
        " * Pre-processed kanji stroke templates.",
        " *",
        " * Generated from KanjiVG (https://github.com/KanjiVG/kanjivg).",
        " * Each stroke is an array of normalized points (0-1 range, 109x109 viewBox).",
        " *",
        " * DO NOT edit manually — regenerate with: python3 scripts/gen-kanji-data.py",
        " */",
        "",
        "export interface RadicalGroup {",
        "  element: string;       // radical character, e.g. '言'",
        "  position?: string;     // 'left' | 'right' | 'top' | 'bottom' | undefined",
        "  strokeIndices: number[]; // 0-based indices into strokes[]",
        "}",
        "",
        "export interface KanjiTemplate {",
        "  character: string;",
        "  reading: string;       // hiragana reading from Genki vocab",
        "  strokeCount: number;",
        "  strokes: number[][][]; // [stroke][point][x,y]",
        "  radicals: RadicalGroup[];",
        "}",
        "",
        "export const KANJI_TEMPLATES: Record<string, KanjiTemplate> = {",
    ]

    for char, reading, strokes, radical_groups in kanji_data:
        safe_reading = escape_ts_string(reading)
        lines.append(f"  // {char} ({reading})")
        lines.append(f"  '{char}': {{")
        lines.append(f"    character: '{char}',")
        lines.append(f"    reading: '{safe_reading}',")
        lines.append(f"    strokeCount: {len(strokes)},")
        lines.append(f"    strokes: [")
        for stroke in strokes:
            pts_str = ", ".join(f"[{p[0]}, {p[1]}]" for p in stroke)
            lines.append(f"      [{pts_str}],")
        lines.append(f"    ],")
        lines.append(f"    radicals: [")
        for g in radical_groups:
            pos = f"'{g['position']}'" if g["position"] else "undefined"
            idx_str = ", ".join(str(i) for i in g["strokeIndices"])
            lines.append(f"      {{ element: '{g['element']}', position: {pos}, strokeIndices: [{idx_str}] }},")
        lines.append(f"    ],")
        lines.append(f"  }},")
        lines.append("")

    lines += ["};", ""]

    # Lesson groups
    lines.append("// Kanji grouped by Genki lesson, in curriculum order.")
    lines.append("export const LESSON_GROUPS: Array<{ label: string; characters: string[] }> = [")
    for label, chars in lesson_groups:
        escaped = "".join(chars)
        lines.append(f"  {{ label: '{label}', characters: [")
        for ch in chars:
            lines.append(f"    '{ch}',")
        lines.append(f"  ] }},")
    lines += [
        "];",
        "",
        "export function getTemplate(character: string): KanjiTemplate | undefined {",
        "  return KANJI_TEMPLATES[character];",
        "}",
        "",
        "export function getAvailableCharacters(): string[] {",
        "  return Object.keys(KANJI_TEMPLATES);",
        "}",
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    kanji_list, lesson_groups = load_kanji_from_csvs()
    print(f"Found {len(kanji_list)} unique kanji across all CSV files.")

    kanji_data = []
    failed = []
    for char, reading in kanji_list:
        print(f"Fetching {char} ({reading})... ", end="", flush=True)
        try:
            svg = fetch_kanjivg(char)
            strokes, root = get_strokes_from_svg(svg)
            radical_groups = get_radical_groups(root, char)
            print(f"✓  {len(strokes)} stroke(s), {len(radical_groups)} radical(s)")
            kanji_data.append((char, reading, strokes, radical_groups))
        except Exception as e:
            print(f"✗  {e}")
            failed.append((char, str(e)))

    # Remove failed kanji from lesson groups so the TS output stays consistent
    failed_chars = {ch for ch, _ in failed}
    clean_groups = [
        (label, [ch for ch in chars if ch not in failed_chars])
        for label, chars in lesson_groups
    ]

    out_path = "web-client/src/templates/kanji-data.ts"
    ts = generate_ts(kanji_data, clean_groups)
    with open(out_path, "w") as f:
        f.write(ts)

    print(f"\nWrote {len(kanji_data)} kanji to {out_path}")
    if failed:
        print(f"\nFailed ({len(failed)}):")
        for char, err in failed:
            print(f"  {char}: {err}")


if __name__ == "__main__":
    main()
