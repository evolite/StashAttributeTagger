import json
import sys

import stashapi.log as log
from stashapi.stashapp import StashInterface

PAGE_SIZE = 100

# gender enum -> noun used in gendered tag names. Anything else (trans, intersex,
# non-binary, unset) is skipped entirely.
GENDER_NOUN = {"FEMALE": "Woman", "MALE": "Man"}

# normalized ethnicity value -> (female tag name, male tag name)
ETHNICITY = {
    "caucasian": ("White Woman", "White Man"),
    "white": ("White Woman", "White Man"),
    "black": ("Black Woman", "Black Man"),
    "african american": ("Black Woman", "Black Man"),
    "asian": ("Asian Woman", "Asian Man"),
    "latin": ("Latina Woman", "Latino Man"),
    "latina": ("Latina Woman", "Latino Man"),
    "hispanic": ("Latina Woman", "Latino Man"),
    "middle eastern": ("Middle Eastern Woman", "Middle Eastern Man"),
    "middle-eastern": ("Middle Eastern Woman", "Middle Eastern Man"),
    "mixed": ("Mixed Race Woman", "Mixed Race Man"),
    "mixed race": ("Mixed Race Woman", "Mixed Race Man"),
}

# noun -> (short_below, tall_at_or_above) cm thresholds. Men run taller, so the
# bands are shifted up; between the two values is "Average Height".
HEIGHT_THRESHOLDS = {
    "Woman": (160, 175),
    "Man": (170, 185),
}

# normalized eye color value -> tag name (gender-neutral)
EYE_COLOR = {
    "brown": "Brown Eyes",
    "green": "Green Eyes",
    "grey": "Grey Eyes",
    "gray": "Grey Eyes",
    "hazel": "Hazel Eyes",
    "blue": "Blue Eyes",
}


def _norm(value) -> str:
    return (value or "").strip().lower()


def _height_base(height_cm, noun: str) -> str | None:
    if not height_cm:
        return None
    short_below, tall_at = HEIGHT_THRESHOLDS[noun]
    if height_cm < short_below:
        return "Short"
    if height_cm >= tall_at:
        return "Tall"
    return "Average Height"


def performer_target_tag_names(performer: dict) -> list[str]:
    """Existing-tag NAMES this performer's attributes map to. [] if gender skipped."""
    noun = GENDER_NOUN.get(performer.get("gender"))
    if noun is None:
        return []

    names: list[str] = []

    eth = ETHNICITY.get(_norm(performer.get("ethnicity")))
    if eth:
        names.append(eth[0] if noun == "Woman" else eth[1])

    eye = EYE_COLOR.get(_norm(performer.get("eye_color")))
    if eye:
        names.append(eye)

    base = _height_base(performer.get("height_cm"), noun)
    if base:
        names.append(f"{base} {noun}")

    return names


def all_candidate_tag_names() -> set[str]:
    """The fixed universe of tag names the mappings can ever produce."""
    names: set[str] = set(EYE_COLOR.values())
    for female, male in ETHNICITY.values():
        names.update((female, male))
    for base in ("Short", "Average Height", "Tall"):
        names.add(f"{base} Woman")
        names.add(f"{base} Man")
    return names


FIND_TAG = """
query ($name: String!) {
  findTags(tag_filter: { name: { value: $name, modifier: EQUALS } }) {
    tags { id name }
  }
}
"""


def resolve_existing_tag_ids(stash: StashInterface, names: set[str]) -> dict[str, str]:
    """Map each candidate tag name to its id. Names with no match are omitted."""
    name_to_id: dict[str, str] = {}
    for name in sorted(names):
        result = stash.call_GQL(FIND_TAG, {"name": name})
        tags = (result or {}).get("findTags", {}).get("tags", [])
        if tags:
            name_to_id[name] = tags[0]["id"]
    missing = names - name_to_id.keys()
    if missing:
        log.info(f"{len(missing)} mapped tag(s) not present in Stash (skipped): {sorted(missing)}")
    return name_to_id


def tag_performers(stash: StashInterface, name_to_id: dict[str, str], dry_run: bool) -> None:
    page = 1
    count = stash.find_performers(
        filter={"page": 1, "per_page": 1}, fragment="id", get_count=True
    )
    total = count[0] if isinstance(count, tuple) else 0
    processed = 0
    tagged_count = 0

    while True:
        performers = stash.find_performers(
            filter={"page": page, "per_page": PAGE_SIZE},
            fragment="id name gender ethnicity eye_color height_cm tags { id }",
        )
        if not performers:
            break

        for p in performers:
            target_ids = {name_to_id[n] for n in performer_target_tag_names(p) if n in name_to_id}
            existing_ids = {t["id"] for t in p.get("tags", [])}
            to_add = target_ids - existing_ids
            if to_add:
                add_names = [n for n in performer_target_tag_names(p) if name_to_id.get(n) in to_add]
                if dry_run:
                    log.info(f"[dry-run] Performer {p['id']} ({p['name']}): would add {add_names}")
                else:
                    stash.update_performers(
                        {
                            "ids": [p["id"]],
                            "tag_ids": {"mode": "ADD", "ids": list(to_add)},
                        }
                    )
                    log.info(f"Performer {p['id']} ({p['name']}): added {add_names}")
                tagged_count += 1

        processed += len(performers)
        if total > 0:
            log.progress(min(processed / total, 1.0))

        if len(performers) < PAGE_SIZE:
            break
        page += 1

    action = "would tag" if dry_run else "tagged"
    log.info(f"Done. {action} {tagged_count} performer(s).")


def main() -> None:
    payload = json.loads(sys.stdin.read())
    stash = StashInterface(payload["server_connection"])

    raw_dry = payload.get("args", {}).get("dry_run", False)
    dry_run = raw_dry if isinstance(raw_dry, bool) else str(raw_dry).lower() not in ("false", "0", "no", "")

    log.info(f"Performer Attribute Tagger | dry_run={dry_run}")
    name_to_id = resolve_existing_tag_ids(stash, all_candidate_tag_names())
    if not name_to_id:
        log.warning("None of the mapped tags exist in Stash. Create them first; nothing to do.")
        return

    tag_performers(stash, name_to_id, dry_run)


if __name__ == "__main__":
    main()
