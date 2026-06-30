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
| | Indian / South Asian / Pakistani | South Asian Woman / South Asian Man |
| Eye color | Brown / Green / Grey / Hazel / Blue | Brown Eyes / … / Blue Eyes (gender-neutral) |
| Height (Woman) | `< 160 / 160–174 / >= 175 cm` | Short Woman / Average Height Woman / Tall Woman |
| Height (Man) | `< 170 / 170–184 / >= 185 cm` | Short Man / Average Height Man / Tall Man |

Tag names follow [StashDB](https://stashdb.org)'s **Race**, **Height**, **Face**,
and **Orientation** categories, so they match tags imported from StashDB.

Height bands are gender-specific (men run taller on average), so the same height
can land in different bands — e.g. 178 cm is a Tall Woman but an Average Height Man.

### Trans / non-binary performers

| Gender | Identity tag | Ethnicity / height |
|--------|-------------|--------------------|
| Transgender (MtF) | `Transgender (Female)` | uses the `X Trans` Race tag if it exists (e.g. `White Trans Woman`, `Asian Trans`), else the `… Woman` tag; height as a woman |
| Transgender (FtM) | `Transgender (Male)` | `X Trans` if it exists, else the `… Man` tag; height as a man |
| Non-binary | `Transgender (Non-Binary)` | `X Trans` if it exists; no height (no gendered band) |
| Intersex / unset | *skipped* | — |

Eye-color tags apply to everyone. StashDB's trans Race tags are uneven (e.g.
there's `Black Trans` and `White Trans Woman` but no `Middle Eastern Trans`), so
the fallback to the plain `… Woman` / `… Man` tag fills the gaps.

Trans and non-binary performers are handled too (see below). Only **intersex**
and gender-**unset** performers are skipped. Unmapped ethnicities simply produce
no ethnicity tag.

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
