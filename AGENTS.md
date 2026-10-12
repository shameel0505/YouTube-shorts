# Google Flow Character Tagging & Credit Preservation Rules

> [!CRITICAL]
> **RULE FOR ALL AI ASSISTANTS AND AGENTS:**
> **DO NOT ALTER OR REMOVE THE `@ + l + i + y + a + Enter` CHARACTER TAGGING FLOW UNDER ANY CIRCUMSTANCES WITHOUT EXPLICIT PERMISSION FROM THE USER.**

---

## 1. Character Tagging Mechanism (`@liya`)

On Google Flow (`https://flow.google.com`), characters are **NOT** recognized if you paste `@liya` as text into the composer (e.g. via `insert_text` or `fill`). Pasting plain text leaves `@liya` as unparsed characters and will NOT attach the character entity chip.

### The Mandatory Sequence:
1. Focus the contenteditable composer (`[contenteditable='true']`).
2. Type `@` with a delay (dispatches actual key events: `keydown`, `keypress`, `keyup`).
3. Wait ~2.0 seconds for Flow's mention picker popover to open.
4. Type the character name character by character (`l`, `i`, `y`, `a`) with ~100ms key delay.
5. Wait ~2.5 seconds for the autocomplete dropdown options (`button.asset-item[role='option']`) to filter and show `LiyaCharacter`.
6. Press `Enter` to commit the character chip.
7. Confirm that `.mention-chip` is present in the DOM with `data-reference-type="entity"` and `entity_id="76ae8c1f-3f9f-4299-bc24-112a234c1f0c"`.
8. Add a space (` `) and append the prompt text (wardrobe, action, dialogue) after the chip.

Verified Reference implementation: [scripts/test_tag_liya.py](file:///Users/shameel/Desktop/youtube/scripts/test_tag_liya.py).

---

## 2. Zero-Wastage & Credit Preservation Policy

- **DO NOT** execute unconfirmed full video runs that consume Flow credits when testing or modifying prompts or UI logic.
- **ALWAYS** test UI gestures, chips, and selectors using dry-runs or zero-credit headless/headed verification scripts (stopping **before** clicking submit/generate).
- **ALWAYS** ask the user before starting batch video generation runs.
- **NEVER** replace character chips with description-only text embeddings unless explicitly ordered by the user. Description-only prompts cause face and wardrobe drift across scene cuts.
