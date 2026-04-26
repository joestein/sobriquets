# Coding Agent Notes - Fix Skill Path

## Summary
Relocated the `/research` slash command from `skills/research/prompt.md` to `.claude/commands/research.md` so Claude Code can discover and invoke it as `/research`.

## Files Modified
- `.claude/commands/research.md` -- created with identical content from old location
- `skills/` -- entire directory removed
- `CLAUDE.md` -- updated three references from `skills/research/prompt.md` to `.claude/commands/research.md`, and updated project structure listing from `skills/` to `.claude/commands/`

## Notes
- `wiki/schema.md` was checked but contains no references to the old path; no changes needed there.
- The prompt content is unchanged; only the file location moved.
