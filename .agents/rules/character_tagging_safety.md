# Rule: Immutable Google Flow Character Tagging

## 🛑 MANDATORY FOR ALL AGENTS
**DO NOT TOUCH, MODIFY, OR BYPASS THE `@ + l + i + y + a + Enter` CHARACTER TAGGING CODE WITHOUT ASKING THE USER FIRST.**

### Key Rules:
1. **Never Paste Character Mentions**: Pasting `@liya` via clipboard or `insert_text` fails to trigger the Flow autocomplete popup and produces unanchored clips.
2. **Always Dispatch Keystrokes**:
   - `page.keyboard.type("@", delay=120)`
   - `page.wait_for_timeout(2000)`
   - `page.keyboard.type("liya", delay=100)`
   - `page.wait_for_timeout(2500)`
   - `page.keyboard.press("Enter")`
   - `page.wait_for_timeout(2500)`
3. **Credit Safety**: Never click Submit/Generate to test if a chip or UI element works. Always inspect the DOM (`.mention-chip`, `data-reference-type="entity"`) and take screenshots without generating.
4. **User Permission**: If you need to modify the character tagging logic or run a batch generation, you MUST ask the user before proceeding.
