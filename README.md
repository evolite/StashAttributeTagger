# Performer Attribute Tagger

A [Stash](https://github.com/stashapp/stash) plugin that adds tags to performers
based on their built-in attributes — **ethnicity, eye color, and height**.

It only ever assigns tags that **already exist** in your library; it never
creates tags. Attributes with no matching tag are skipped silently. Run the tag
importer or create the tags yourself first.

## Mappings

| Attribute | Value | Tag (FEMALE / MALE) |
|-----------|-------|---------------------|
| Ethnicity | Caucasian / White | White Woman / White Man |
| | Black / African American | Black Woman / Black Man |
| | Asian | Asian Woman / Asian Man |
| | Latin / Latina / Hispanic | Latina Woman / Latino Man |
| | Middle Eastern | Middle Eastern Woman / Middle Eastern Man |
| | Mixed / Mixed Race | Mixed Race Woman / Mixed Race Man |
| Eye color | Brown / Green / Grey / Hazel / Blue | Brown Eyes / … / Blue Eyes (gender-neutral) |
| Height (Woman) | `< 160 / 160–174 / >= 175 cm` | Short Woman / Average Height Woman / Tall Woman |
| Height (Man) | `< 170 / 170–184 / >= 185 cm` | Short Man / Average Height Man / Tall Man |

Height bands are gender-specific (men run taller on average), so the same height
can land in different bands — e.g. 178 cm is a Tall Woman but an Average Height Man.

Performers whose gender is **not** FEMALE or MALE (trans, intersex, non-binary,
unset) are skipped — all the gendered tags say "Woman" / "Man". Unmapped
ethnicities (e.g. Indian) simply produce no ethnicity tag.

The mappings are hardcoded in `plugin/performerAttributeTagger.py`; edit the
`ETHNICITY`, `EYE_COLOR`, and `GENDER_NOUN` constants to adjust them.

## Install

Copy the `plugin/` folder into your Stash `plugins` directory (e.g.
`~/.stash/plugins/performerAttributeTagger/`) and **Reload Plugins** in Settings.
Requires `stashapp-tools` (bundled in the official Stash Docker image).

## Usage

Settings → Tasks → Plugin Tasks → **Performer Attribute Tagger**:

- **Tag Performers from Attributes (Dry Run)** — logs what *would* be added, no changes.
- **Tag Performers from Attributes** — applies the tags.

Re-running is safe: tags a performer already has are skipped.

## Development

```sh
python3 plugin/test_attribute_tags.py   # pure-logic self-check, no Stash needed
```
