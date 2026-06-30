"""Self-check for the pure mapping logic. Run: python3 plugin/test_attribute_tags.py"""
from performerAttributeTagger import performer_target_tag_names, all_candidate_tag_names


def p(gender=None, ethnicity=None, eye_color=None, height_cm=None):
    return {"gender": gender, "ethnicity": ethnicity, "eye_color": eye_color, "height_cm": height_cm}


# female: ethnicity + eye + short
assert performer_target_tag_names(
    p("FEMALE", "Caucasian", "Brown", 155)
) == ["White Woman", "Brown Eyes", "Short Woman"]

# male: latino + blue + tall
assert performer_target_tag_names(
    p("MALE", "Latin", "Blue", 185)
) == ["Latino Man", "Blue Eyes", "Tall Man"]

# skipped genders -> nothing
assert performer_target_tag_names(p("TRANSGENDER_FEMALE", "Caucasian", "Blue", 170)) == []
assert performer_target_tag_names(p(None, "Caucasian", "Brown", 165)) == []
assert performer_target_tag_names(p("NON_BINARY", "Asian", "Green", 170)) == []

# height boundaries: <160 short, 160-179 average, >=180 tall
assert performer_target_tag_names(p("FEMALE", height_cm=159)) == ["Short Woman"]
assert performer_target_tag_names(p("FEMALE", height_cm=160)) == ["Average Height Woman"]
assert performer_target_tag_names(p("FEMALE", height_cm=179)) == ["Average Height Woman"]
assert performer_target_tag_names(p("MALE", height_cm=180)) == ["Tall Man"]

# unmapped ethnicity (indian) -> no ethnicity tag, other attrs still apply
assert performer_target_tag_names(
    p("MALE", "Indian", "Brown", 175)
) == ["Brown Eyes", "Average Height Man"]

# empty / missing attributes -> omitted, no crash
assert performer_target_tag_names(p("FEMALE", "", "", None)) == []
assert performer_target_tag_names(p("FEMALE")) == []

# grey/gray alias both map to Grey Eyes
assert performer_target_tag_names(p("FEMALE", eye_color="gray")) == ["Grey Eyes"]

# candidate universe covers every name the mapping can emit
universe = all_candidate_tag_names()
for sample in (p("FEMALE", "Hispanic", "Hazel", 200), p("MALE", "Mixed", "Green", 100)):
    for name in performer_target_tag_names(sample):
        assert name in universe, f"{name} missing from candidate universe"

print("All assertions passed.")
