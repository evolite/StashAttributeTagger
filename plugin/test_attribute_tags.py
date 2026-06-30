"""Self-check for the pure mapping logic. Run: python3 plugin/test_attribute_tags.py"""
from performerAttributeTagger import (
    performer_target_tag_groups,
    choose_existing,
    all_candidate_tag_names,
)

# fake library where every candidate tag exists
ALL = {n: n for n in all_candidate_tag_names()}


def p(gender=None, ethnicity=None, eye_color=None, height_cm=None):
    return {"gender": gender, "ethnicity": ethnicity, "eye_color": eye_color, "height_cm": height_cm}


def tags(perf, cache=ALL):
    return choose_existing(performer_target_tag_groups(perf), cache)


# --- cis ---
assert tags(p("FEMALE", "Caucasian", "Brown", 155)) == ["White Woman", "Brown Eyes", "Short Woman"]
assert tags(p("MALE", "Latin", "Blue", 185)) == ["Latino Man", "Blue Eyes", "Tall Man"]

# --- skipped genders ---
assert tags(p("INTERSEX", "Caucasian", "Blue", 170)) == []
assert tags(p(None, "Caucasian", "Brown", 165)) == []

# --- trans: identity tag + ethnicity trans variant + eyes + gendered height ---
assert tags(p("TRANSGENDER_FEMALE", "Caucasian", "Blue", 170)) == [
    "Transgender (Female)", "White Trans Woman", "Blue Eyes", "Average Height Woman",
]
assert tags(p("TRANSGENDER_MALE", "Asian", "Brown", 172)) == [
    "Transgender (Male)", "Asian Trans", "Brown Eyes", "Average Height Man",
]
# non-binary: identity + (noun-less) trans ethnicity + eyes; NO height (no noun)
assert tags(p("NON_BINARY", "Black", "Green", 175)) == [
    "Transgender (Non-Binary)", "Black Trans", "Green Eyes",
]

# --- trans ethnicity fallback when the X-Trans tag does not exist in the library ---
no_asian_trans = {n: n for n in ALL if n != "Asian Trans"}
assert tags(p("TRANSGENDER_MALE", "Asian", "Brown", 172), no_asian_trans) == [
    "Transgender (Male)", "Asian Man", "Brown Eyes", "Average Height Man",
]
# ethnicity with no trans variant at all (Middle Eastern) -> falls back to Woman/Man
assert tags(p("TRANSGENDER_FEMALE", "Middle Eastern", "Brown", 165)) == [
    "Transgender (Female)", "Middle Eastern Woman", "Brown Eyes", "Average Height Woman",
]

# --- Indian -> StashDB gendered South Asian ---
assert tags(p("MALE", "Indian", "Brown", 175)) == ["South Asian Man", "Brown Eyes", "Average Height Man"]
assert tags(p("FEMALE", "Pakistani", "Brown", 165)) == ["South Asian Woman", "Brown Eyes", "Average Height Woman"]

# --- gender-specific height boundaries (StashDB bands) ---
# women: <155 tiny, 155-164 short, 165-174 average, >=175 tall
assert tags(p("FEMALE", height_cm=154)) == ["Tiny Woman"]
assert tags(p("FEMALE", height_cm=155)) == ["Short Woman"]
assert tags(p("FEMALE", height_cm=164)) == ["Short Woman"]
assert tags(p("FEMALE", height_cm=165)) == ["Average Height Woman"]
assert tags(p("FEMALE", height_cm=174)) == ["Average Height Woman"]
assert tags(p("FEMALE", height_cm=175)) == ["Tall Woman"]
# men: <170 short, 170-181 average, >=182 tall (no "Tiny Man")
assert tags(p("MALE", height_cm=149)) == ["Short Man"]
assert tags(p("MALE", height_cm=169)) == ["Short Man"]
assert tags(p("MALE", height_cm=170)) == ["Average Height Man"]
assert tags(p("MALE", height_cm=181)) == ["Average Height Man"]
assert tags(p("MALE", height_cm=182)) == ["Tall Man"]
# same height, different band by gender
assert tags(p("FEMALE", height_cm=178)) == ["Tall Woman"]
assert tags(p("MALE", height_cm=178)) == ["Average Height Man"]
# "Tiny Man" is not a StashDB tag, so it must not be in the candidate universe
assert "Tiny Man" not in all_candidate_tag_names()
assert "Tiny Woman" in all_candidate_tag_names()

# --- edge cases ---
assert tags(p("MALE", "Pacific Islander", "Brown", 175)) == ["Brown Eyes", "Average Height Man"]  # unmapped ethnicity
assert tags(p("FEMALE", "", "", None)) == []  # empty attrs
assert tags(p("FEMALE", eye_color="gray")) == ["Grey Eyes"]  # alias

# --- candidate universe sanity: every produced name is in the universe ---
universe = all_candidate_tag_names()
for sample in (
    p("FEMALE", "Hispanic", "Hazel", 200),
    p("MALE", "Mixed", "Green", 100),
    p("TRANSGENDER_FEMALE", "Black", "Blue", 190),
    p("NON_BINARY", "Asian", "Grey", 150),
):
    for group in performer_target_tag_groups(sample):
        for name in group:
            assert name in universe, f"{name} missing from candidate universe"

print("All assertions passed.")
