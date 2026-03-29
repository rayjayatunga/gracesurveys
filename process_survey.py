#!/usr/bin/env python3
"""
Process GTC 2025 Survey Results.
Cleans the raw CSV, normalizes free-text program responses,
and exports a structured JSON file for the dashboard.
"""

import csv
import json
import re
from collections import Counter

INPUT_FILE = "GTC 2025 Survey Results(Sheet1).csv"
OUTPUT_FILE = "survey_data.json"

COLUMN_SHORT_NAMES = {
    0: "attendance_length",
    1: "service",
    2: "home_church",
    3: "inducted_member",
    4: "how_heard",
    5: "prayer_frequency",
    6: "bible_reading_frequency",
    7: "commute_method",
    8: "commute_length",
    9: "ministries_participated",
    10: "beneficial_programs_raw",
    11: "future_programs",
    12: "faith_growth_goals",
    13: "avail_weekday_evening",
    14: "avail_weekday_morning",
    15: "avail_saturday_morning",
    16: "avail_saturday_evening",
    17: "avail_sunday_before_2nd",
    18: "avail_sunday_after_1st",
    19: "avail_sunday_afternoon",
    20: "pref_email",
    21: "pref_verbal_announcements",
    22: "pref_facebook",
    23: "pref_instagram",
    24: "nps_christian",
    25: "nps_non_christian",
    26: "what_excites",
    27: "gender",
    28: "age_group",
    29: "postal_prefix",
    30: "years_in_toronto",
    31: "ethnicity",
    32: "num_languages",
    33: "languages",
    34: "marital_status",
    35: "has_children_at_gtc",
    36: "num_children",
    37: "children_ages",
    38: "children_ministries",
    39: "education",
    40: "employment_status",
    41: "industry",
    42: "income",
    43: "student_institution",
    44: "faith_description",
    45: "baptized",
}

# Mapping patterns in the free-text "beneficial programs" field to normalized categories.
# Order matters: more specific patterns first to avoid greedy matches.
PROGRAM_NORMALIZATION = [
    (r"\byoung\s*adult", "Young Adults Ministry"),
    (r"\bya\b", "Young Adults Ministry"),
    (r"\bgrad(?:uate)?\s*fellowship", "Graduate Fellowship"),
    (r"\bcgf\b", "Graduate Fellowship"),
    (r"\balpha\b", "Alpha"),
    (r"\bgrace\s*gather", "Grace Gatherings"),
    (r"\bgrace\s*group", "Grace Gatherings"),
    (r"\bgg\b", "Grace Gatherings"),
    (r"\bsmall\s*group", "Grace Gatherings"),
    (r"\bmen.?s\s*(ministry|bible|group|retreat|event|soccer|fellowship|alpha)", "Men's Ministry"),
    (r"\bgt\s*men", "Men's Ministry"),
    (r"\bmens\s*(ministry|bible|group|retreat|event|soccer|fellowship|alpha)", "Men's Ministry"),
    (r"\bmen.?s\b", "Men's Ministry"),
    (r"\bmens\b", "Men's Ministry"),
    (r"\bwom[ae]n.?s\s*(ministry|bible|group|brunch|social|event|lunch|gg)", "Women's Ministry"),
    (r"\bwomens\s*(ministry|bible|group|brunch|social|event|lunch|gg)", "Women's Ministry"),
    (r"\bwom[ae]n.?s\b", "Women's Ministry"),
    (r"\bwomens\b", "Women's Ministry"),
    (r"\bmom.?s\s*group", "Women's Ministry"),
    (r"\bgt\s*kids", "GT Kids"),
    (r"\bgtk", "GT Kids"),
    (r"\bkids\b", "GT Kids"),
    (r"\bnursery\b", "GT Kids"),
    (r"\bkids?\s*cafe", "GT Kids"),
    (r"\bkids?\s*gala", "GT Kids"),
    (r"\byouth\s*group", "Youth Group"),
    (r"\bsunday\s*school", "Sunday School"),
    (r"\badult\s*sunday\s*school", "Sunday School"),
    (r"\bfamily\s*(talk|event|ministr|program|cafe|chat|breakfast|gala|gg)", "Family Ministry"),
    (r"\bfamily\s*talks", "Family Ministry"),
    (r"\bimprint", "Family Ministry"),
    (r"\bworship\s*(night|event|team)", "Worship & Prayer Nights"),
    (r"\bprayer\s*(night|group|morning|praise|worship|ministry)", "Worship & Prayer Nights"),
    (r"\bmorning\s*prayer\b", "Worship & Prayer Nights"),
    (r"\bpraise\s*(night|worship)", "Worship & Prayer Nights"),
    (r"\bkingdom\s*come\b", "Worship & Prayer Nights"),
    (r"\bjericho", "Outreach & Missions"),
    (r"\boutreach", "Outreach & Missions"),
    (r"\bmission", "Outreach & Missions"),
    (r"\bsleeping\s*bag", "Outreach & Missions"),
    (r"\bclothing\s*drive", "Outreach & Missions"),
    (r"\bconnect", "Connections Events"),
    (r"\bnewcomer", "Connections Events"),
    (r"\btech(?:nology)?\s*(conference|seminar)", "Conferences & Seminars"),
    (r"\bconference", "Conferences & Seminars"),
    (r"\bseminar", "Conferences & Seminars"),
    (r"\brobert\s*cunningham", "Conferences & Seminars"),
    (r"\bgospel\s*&?\s*tech", "Conferences & Seminars"),
    (r"\bspeaker", "Conferences & Seminars"),
    (r"\bfaith\s*and\s*tech", "Conferences & Seminars"),
    (r"\bsexuality\s*(conference|talk)", "Conferences & Seminars"),
    (r"\bcomplementarian", "Conferences & Seminars"),
    (r"\bparish", "Parish Events"),
    (r"\bbrunch", "Social Events"),
    (r"\blunch", "Social Events"),
    (r"\bsummer\s*eats", "Social Events"),
    (r"\bsocial", "Social Events"),
    (r"\bbake\s*sale", "Social Events"),
    (r"\bbubble\s*tea", "Social Events"),
    (r"\bcoffee", "Social Events"),
    (r"\bgolf", "Social Events"),
    (r"\bbouncy\s*castle", "Social Events"),
    (r"\bfood\b", "Social Events"),
    (r"\bmeal", "Social Events"),
    (r"\beat", "Social Events"),
    (r"\bmembership\s*class", "Membership Class"),
    (r"\bbible\s*study", "Bible Study"),
    (r"\bdiscipleship", "Discipleship"),
    (r"\bdeacon", "Deacons"),
    (r"\badam\s*house", "Adam House"),
    (r"\bfriday\s*night", "Friday Nights at Grace"),
    (r"\blet.?s\s*go\s*sunday", "Let's Go Sundays"),
    (r"\beaster", "Special Services"),
    (r"\bgood\s*friday", "Special Services"),
    (r"\bchristmas", "Special Services"),
    (r"\b(?:20th|anniversary)", "Special Services"),
    (r"\bvolunteer", "Volunteering"),
    (r"\blibrary\b", "Church Library"),
]

NON_ANSWER_PATTERNS = [
    r"^n/?a$", r"^none$", r"^-$", r"^not\s*(sure|applicable|a\s*program)",
    r"^no\s*response$", r"^somewhat$", r"^can.?t\s*think",
    r"^just\s*(joined|started)", r"^new\s*to\s*the\s*church",
    r"^too\s*soon", r"^i\s*haven.?t\s*(quite|been|looked)",
    r"^we\s*haven.?t\s*been", r"^i.?m\s*just\s*starting",
    r"^i\s*just\s*started", r"^not\s*sure\s*yet",
    r"^i\s*couldn.?t\s*check", r"^honestly,?\s*everything",
    r"^all\s*(of\s*them|are\s*good)?\.?$", r"^any$",
    r"^this\s*is\s*my\s*first",
]


def normalize_programs(raw_text):
    """Extract normalized program categories from free-text response."""
    if not raw_text or not raw_text.strip():
        return []

    text = raw_text.strip().lower()
    text = text.replace("\x92", "'").replace("\x93", '"').replace("\x94", '"')
    text = text.replace("\u2019", "'").replace("\u2018", "'")

    for pat in NON_ANSWER_PATTERNS:
        if re.match(pat, text, re.IGNORECASE):
            return []

    found = set()
    for pattern, category in PROGRAM_NORMALIZATION:
        if re.search(pattern, text, re.IGNORECASE):
            found.add(category)

    if not found and len(text) > 3:
        found.add("Other")

    return sorted(found)


def parse_bool(val):
    if not val:
        return None
    v = val.strip().upper()
    if v in ("TRUE", "YES", "1"):
        return True
    if v in ("FALSE", "NO", "0"):
        return False
    return None


def parse_int(val):
    if not val or not val.strip():
        return None
    try:
        return int(val.strip())
    except ValueError:
        cleaned = re.sub(r"[^0-9]", "", val.strip())
        if cleaned:
            return int(cleaned)
        return None


COMPOUND_OPTIONS = [
    "Adherence to Scripture, Gospel-centered, and Teaching",
    "Community, Congregational culture, Small groups",
]


def parse_multi_select(val, compound_aware=False):
    """Split comma-separated multi-select values, respecting parenthetical text."""
    if not val or not val.strip():
        return []

    text = val.strip()

    placeholders = {}
    if compound_aware:
        for i, phrase in enumerate(COMPOUND_OPTIONS):
            token = f"__COMPOUND_{i}__"
            if phrase in text:
                text = text.replace(phrase, token)
                placeholders[token] = phrase

    items = []
    current = ""
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
            current += ch
        elif ch == ")":
            depth -= 1
            current += ch
        elif ch == "," and depth == 0:
            item = current.strip()
            if item:
                items.append(item)
            current = ""
        else:
            current += ch
    item = current.strip()
    if item:
        items.append(item)

    if placeholders:
        items = [placeholders.get(it, it) for it in items]

    return items


def clean_postal(val):
    if not val or not val.strip():
        return None
    p = val.strip().upper()[:3]
    if len(p) >= 3 and p[0].isalpha() and p[1].isdigit() and p[2].isalpha():
        return p
    return p if len(p) >= 2 else None


def process_row(row, header):
    record = {}
    for i, val in enumerate(row):
        key = COLUMN_SHORT_NAMES.get(i, header[i] if i < len(header) else f"col_{i}")
        val = val.strip() if val else ""

        if key in ("home_church", "inducted_member", "has_children_at_gtc", "baptized"):
            record[key] = parse_bool(val)
        elif key in ("avail_weekday_evening", "avail_weekday_morning",
                      "avail_saturday_morning", "avail_saturday_evening",
                      "avail_sunday_before_2nd", "avail_sunday_after_1st",
                      "avail_sunday_afternoon", "pref_email",
                      "pref_verbal_announcements", "pref_facebook",
                      "pref_instagram", "nps_christian", "nps_non_christian",
                      "num_languages", "num_children"):
            record[key] = parse_int(val)
        elif key in ("ministries_participated", "future_programs",
                      "faith_growth_goals", "what_excites",
                      "languages", "children_ages", "children_ministries"):
            record[key] = parse_multi_select(val, compound_aware=(key == "what_excites"))
        elif key == "commute_method":
            record[key] = [m.strip() for m in val.split(",") if m.strip()] if val else []
        elif key == "beneficial_programs_raw":
            record[key] = val
            record["beneficial_programs"] = normalize_programs(val)
        elif key == "postal_prefix":
            record[key] = clean_postal(val)
        else:
            record[key] = val if val else None
    return record


def compute_summary(records):
    """Compute aggregate statistics for the dashboard."""
    summary = {
        "total_responses": len(records),
        "distributions": {},
        "numeric_averages": {},
        "multi_select_counts": {},
        "program_counts": {},
    }

    dist_fields = [
        "attendance_length", "service", "how_heard", "prayer_frequency",
        "bible_reading_frequency", "commute_length", "gender", "age_group",
        "years_in_toronto", "ethnicity", "marital_status", "education",
        "employment_status", "industry", "income", "faith_description",
    ]
    for field in dist_fields:
        counter = Counter()
        for r in records:
            v = r.get(field)
            if v:
                counter[v] += 1
        summary["distributions"][field] = dict(counter.most_common())

    bool_fields = ["home_church", "inducted_member", "has_children_at_gtc", "baptized"]
    for field in bool_fields:
        yes = sum(1 for r in records if r.get(field) is True)
        no = sum(1 for r in records if r.get(field) is False)
        na = sum(1 for r in records if r.get(field) is None)
        summary["distributions"][field] = {"Yes": yes, "No": no}
        if na > 0:
            summary["distributions"][field]["No Response"] = na

    num_fields = [
        "avail_weekday_evening", "avail_weekday_morning",
        "avail_saturday_morning", "avail_saturday_evening",
        "avail_sunday_before_2nd", "avail_sunday_after_1st",
        "avail_sunday_afternoon", "pref_email",
        "pref_verbal_announcements", "pref_facebook",
        "pref_instagram", "nps_christian", "nps_non_christian",
    ]
    for field in num_fields:
        vals = [r[field] for r in records if r.get(field) is not None]
        if vals:
            summary["numeric_averages"][field] = {
                "mean": round(sum(vals) / len(vals), 2),
                "count": len(vals),
                "distribution": dict(Counter(vals).most_common()),
            }

    multi_fields = [
        "ministries_participated", "future_programs",
        "faith_growth_goals", "what_excites", "commute_method", "languages",
    ]
    for field in multi_fields:
        counter = Counter()
        for r in records:
            for item in r.get(field, []):
                counter[item] += 1
        summary["multi_select_counts"][field] = dict(counter.most_common())

    program_counter = Counter()
    for r in records:
        for p in r.get("beneficial_programs", []):
            program_counter[p] += 1
    summary["program_counts"] = dict(program_counter.most_common())

    nps_christian = [r["nps_christian"] for r in records if r.get("nps_christian") is not None]
    nps_non_christian = [r["nps_non_christian"] for r in records if r.get("nps_non_christian") is not None]
    for label, vals in [("nps_christian", nps_christian), ("nps_non_christian", nps_non_christian)]:
        if vals:
            promoters = sum(1 for v in vals if v >= 9)
            detractors = sum(1 for v in vals if v <= 6)
            n = len(vals)
            score = round(((promoters - detractors) / n) * 100, 1)
            summary["numeric_averages"][label]["nps_score"] = score

    return summary


def main():
    with open(INPUT_FILE, "r", encoding="latin-1") as f:
        reader = csv.reader(f)
        header = next(reader)
        records = []
        for row in reader:
            if any(cell.strip() for cell in row):
                records.append(process_row(row, header))

    summary = compute_summary(records)

    output = {
        "metadata": {
            "survey_name": "Grace Toronto Church - 2025 Annual Pulse Survey",
            "total_responses": len(records),
            "columns": list(COLUMN_SHORT_NAMES.values()),
        },
        "summary": summary,
        "records": records,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Processed {len(records)} records -> {OUTPUT_FILE}")
    print(f"Normalized program categories found: {len(summary['program_counts'])}")
    for prog, count in sorted(summary["program_counts"].items(), key=lambda x: -x[1]):
        print(f"  {prog}: {count}")


if __name__ == "__main__":
    main()
