import json
import sys

import stashapi.log as log
from stashapi.stashapp import StashInterface

PAGE_SIZE = 100

# gender enum -> (noun for gendered tags or None, identity tag or None).
# Genders absent from this map (INTERSEX, unset) are skipped entirely.
# An identity tag != None means the performer is trans/non-binary.
GENDER = {
    "FEMALE": ("Woman", None),
    "MALE": ("Man", None),
    "TRANSGENDER_FEMALE": ("Woman", "Transgender (Female)"),
    "TRANSGENDER_MALE": ("Man", "Transgender (Male)"),
    "NON_BINARY": (None, "Transgender (Non-Binary)"),
}

# normalized ethnicity value -> tag names per identity. "trans" is optional;
# StashDB only has trans Race tags for some ethnicities (and they're uneven, e.g.
# "Black Trans" but "White Trans Woman"). Names match StashDB's Race category.
ETHNICITY = {
    "caucasian": {"woman": "White Woman", "man": "White Man", "trans": "White Trans Woman"},
    "white": {"woman": "White Woman", "man": "White Man", "trans": "White Trans Woman"},
    "black": {"woman": "Black Woman", "man": "Black Man", "trans": "Black Trans"},
    "african american": {"woman": "Black Woman", "man": "Black Man", "trans": "Black Trans"},
    "asian": {"woman": "Asian Woman", "man": "Asian Man", "trans": "Asian Trans"},
    "latin": {"woman": "Latina Woman", "man": "Latino Man", "trans": "Latina Trans"},
    "latina": {"woman": "Latina Woman", "man": "Latino Man", "trans": "Latina Trans"},
    "hispanic": {"woman": "Latina Woman", "man": "Latino Man", "trans": "Latina Trans"},
    "middle eastern": {"woman": "Middle Eastern Woman", "man": "Middle Eastern Man"},
    "middle-eastern": {"woman": "Middle Eastern Woman", "man": "Middle Eastern Man"},
    "mixed": {"woman": "Mixed Race Woman", "man": "Mixed Race Man", "trans": "Mixed Race Trans"},
    "mixed race": {"woman": "Mixed Race Woman", "man": "Mixed Race Man", "trans": "Mixed Race Trans"},
    "indian": {"woman": "South Asian Woman", "man": "South Asian Man"},
    "south asian": {"woman": "South Asian Woman", "man": "South Asian Man"},
    "pakistani": {"woman": "South Asian Woman", "man": "South Asian Man"},
}

# noun -> ordered height bands (upper_exclusive_cm, base). First band whose
# ceiling the height is under wins; ceiling None = no upper bound (tallest).
# Cutoffs follow StashDB's Height category (women have a "Tiny" tier, men don't).
HEIGHT_BANDS = {
    "Woman": [(155, "Tiny"), (165, "Short"), (175, "Average Height"), (None, "Tall")],
    "Man": [(170, "Short"), (182, "Average Height"), (None, "Tall")],
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
    for ceiling, base in HEIGHT_BANDS[noun]:
        if ceiling is None or height_cm < ceiling:
            return base
    return None  # unreachable: last band has ceiling None


def performer_target_tag_groups(performer: dict) -> list[list[str]]:
    """Ordered candidate groups for a performer. For each group the caller assigns
    the FIRST tag name that exists in the library (so trans Race tags fall back to
    the plain Woman/Man tag). Pure; no I/O. [] if the gender is skipped."""
    g = GENDER.get(performer.get("gender"))
    if g is None:
        return []
    noun, identity_tag = g
    is_trans = identity_tag is not None
    groups: list[list[str]] = []

    if identity_tag:
        groups.append([identity_tag])

    eth = ETHNICITY.get(_norm(performer.get("ethnicity")))
    if eth:
        cands: list[str] = []
        if is_trans and "trans" in eth:
            cands.append(eth["trans"])
        if noun == "Woman":
            cands.append(eth["woman"])
        elif noun == "Man":
            cands.append(eth["man"])
        if cands:
            groups.append(cands)

    eye = EYE_COLOR.get(_norm(performer.get("eye_color")))
    if eye:
        groups.append([eye])

    if noun:  # height tags are gendered; non-binary (no noun) gets none
        base = _height_base(performer.get("height_cm"), noun)
        if base:
            groups.append([f"{base} {noun}"])

    return groups


def choose_existing(groups: list[list[str]], name_to_id: dict[str, str]) -> list[str]:
    """First existing tag name in each candidate group."""
    chosen: list[str] = []
    for group in groups:
        for name in group:
            if name in name_to_id:
                chosen.append(name)
                break
    return chosen


def all_candidate_tag_names() -> set[str]:
    """The fixed universe of tag names the mappings can ever produce."""
    names: set[str] = set(EYE_COLOR.values())
    for m in ETHNICITY.values():
        names.update(m.values())
    for noun, bands in HEIGHT_BANDS.items():
        for _ceiling, base in bands:
            names.add(f"{base} {noun}")
    for _noun, identity_tag in GENDER.values():
        if identity_tag:
            names.add(identity_tag)
    return names


FIND_TAG = """
query ($name: String!) {
  byName: findTags(tag_filter: { name: { value: $name, modifier: EQUALS } }) {
    tags { id name }
  }
  byAlias: findTags(tag_filter: { aliases: { value: $name, modifier: EQUALS } }) {
    tags { id name }
  }
}
"""


def resolve_existing_tag_ids(stash: StashInterface, names: set[str]) -> dict[str, str]:
    """Map each candidate tag name to its id, matching the name or any alias.
    Names with no match are omitted."""
    name_to_id: dict[str, str] = {}
    for name in sorted(names):
        result = stash.call_GQL(FIND_TAG, {"name": name}) or {}
        tags = (result.get("byName") or {}).get("tags", []) \
            or (result.get("byAlias") or {}).get("tags", [])
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
            chosen = choose_existing(performer_target_tag_groups(p), name_to_id)
            target_ids = {name_to_id[n] for n in chosen}
            existing_ids = {t["id"] for t in p.get("tags", [])}
            to_add = target_ids - existing_ids
            if to_add:
                add_names = [n for n in chosen if name_to_id[n] in to_add]
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


def tag_one_performer(stash, performer_id, name_to_id, dry_run):
    """Add matching attribute tags to a single performer (Performer.Update.Post hook)."""
    p = stash.find_performer(
        performer_id, fragment="id name gender ethnicity eye_color height_cm tags { id }"
    )
    if not p:
        return
    chosen = choose_existing(performer_target_tag_groups(p), name_to_id)
    target_ids = {name_to_id[n] for n in chosen}
    to_add = target_ids - {t["id"] for t in p.get("tags", [])}
    if not to_add:
        return
    add_names = [n for n in chosen if name_to_id[n] in to_add]
    if dry_run:
        log.info(f"[dry-run] Performer {p['id']} ({p['name']}): would add {add_names}")
    else:
        # ponytail: our own update re-fires the hook, but the second pass finds
        # nothing to add and makes no update, so it terminates after one no-op.
        stash.update_performers(
            {"ids": [p["id"]], "tag_ids": {"mode": "ADD", "ids": list(to_add)}}
        )
        log.info(f"Performer {p['id']} ({p['name']}): added {add_names}")


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

    hook_context = payload.get("args", {}).get("hookContext")
    if hook_context:
        tag_one_performer(stash, str(hook_context["id"]), name_to_id, dry_run)
        return

    tag_performers(stash, name_to_id, dry_run)


if __name__ == "__main__":
    main()
