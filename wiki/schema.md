---
title: Wiki Schema
---

# Sobriquets Wiki Schema

This document describes the three-layer structure of the Sobriquets personal knowledge wiki, following Karpathy's LLM Wiki pattern.

## Three-Layer Architecture

### Layer 1: Raw Sources (`wiki/raw-sources/`)

Immutable snapshots of authoritative source material. These files are created by the `/research` skill and are never modified after creation.

**Directory structure:**
```
wiki/raw-sources/
  <topic-slug>/
    <source-slug>.md
```

**File format:**
```markdown
---
url: <source URL>
retrieved: <ISO 8601 timestamp>
content_hash: <SHA-256 of captured content>
authority: <domain or organization name>
---

<verbatim or lightly-formatted content from the source>
```

### Layer 2: Wiki Pages (`wiki/pages/`)

Generated knowledge pages organized by topic. These are created and updated by the `/research` skill. They synthesize information from raw sources into well-structured articles.

**Directory structure:**
```
wiki/pages/
  <topic-slug>/
    _index.md          # Topic overview and page listing
    <concept>.md       # Individual wiki pages
```

**Page format:**
```markdown
---
title: <Page Title>
topic: <topic-slug>
created: <ISO 8601>
updated: <ISO 8601>
sources:
  - raw-sources/<topic-slug>/<source-slug>.md
related:
  - pages/<other-topic>/<other-page>.md
tags:
  - <tag1>
  - <tag2>
---

# <Page Title>

## Overview
<2-3 paragraph summary>

## Key Concepts
<detailed breakdown with subsections>

## See Also
- [[pages/<related-topic>/<related-page>]]

## Sources
- [Source Name](raw-sources/<topic-slug>/<source-slug>.md)
```

### Layer 3: Schema (`wiki/schema.md` + `CLAUDE.md`)

This file and the project's CLAUDE.md define the conventions, rules, and structure that govern the wiki. Manually maintained by the user.

## Front-Matter Fields

### Required Fields
- **title**: Human-readable page title
- **topic**: The topic slug (matches the directory name)

### Optional Fields
- **created**: ISO 8601 timestamp of initial creation
- **updated**: ISO 8601 timestamp of last update
- **sources**: List of relative paths to raw source files
- **related**: List of relative paths to related wiki pages
- **tags**: List of categorization tags

## Conventions

1. **Topic slugs**: Use lowercase kebab-case (e.g., `quantum-computing`)
2. **Page file names**: Use lowercase kebab-case (e.g., `superconducting-qubits.md`)
3. **Cross-references**: Use `[[pages/<topic>/<page>]]` wiki-link syntax
4. **Source references**: Use standard markdown links to `raw-sources/` paths
5. **Headings**: Use H1 for the page title (matching front-matter title), H2 for major sections, H3 for subsections
6. **Index pages**: Each topic directory should have an `_index.md` that lists and briefly describes all pages in the topic
