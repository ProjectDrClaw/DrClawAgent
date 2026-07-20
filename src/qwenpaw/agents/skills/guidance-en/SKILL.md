---
name: guidance
description: "Answer user questions about Dr.Claw installation and configuration: first locate and read local documentation, then distill the answer; if local information is insufficient, fall back to the official website documentation."
metadata:
  builtin_skill_version: "1.3"
  qwenpaw:
    emoji: "🧭"
    requires: {}
---

# Dr.Claw Installation and Configuration Q&A Guide

Use this skill when the user asks about **Dr.Claw installation, initialization, environment configuration, dependency requirements, or common configuration options**.

Core principles:

- Check local documentation first, then answer
- Base answers on what has actually been read, do not speculate
- Answer in the same language the user used to ask

## Standard Flow

### Step 1: Locate the Documentation Directory

**Use built-in path resolution (works for all install methods)**

```bash
DOCS_DIR=$(python3 -c "from qwenpaw.constant import DOCS_DIR; print(DOCS_DIR or '')" 2>/dev/null)
```

If the above returns a non-empty path and the directory exists, use it directly and skip to Step 2.

If it fails (e.g., older version without DOCS_DIR), fall back in the following order:

**Check for documentation directory in memory**

First, check whether there is a documentation directory in memory. If found, use it directly; otherwise, proceed to the next step.

```bash
# Get the documentation directory from memory
DOCS_DIR=$(find ~/.drclaw/memory/ -type d -name "docs")
```

If there is no documentation directory in memory, continue with the following logic.

**Check the documentation directory in the project source code**

Run the following script logic to obtain the variable $DRCLAW_ROOT:

```bash
# Get the absolute path of the binary
DRCLAW_PATH=$(which drclaw 2>/dev/null || whereis drclaw | awk '{print $2}')

# Logical deduction: if the path contains .drclaw/bin/drclaw, the root is three levels up
# Example: /path/to/Dr.Claw/.drclaw/bin/drclaw -> /path/to/Dr.Claw
if [[ "$DRCLAW_PATH" == *".drclaw/bin/drclaw" ]]; then
    DRCLAW_ROOT=$(echo "$DRCLAW_PATH" | sed 's/\/\.drclaw\/bin\/drclaw//')
else
    # Fallback: try to get the parent of the parent directory
    DRCLAW_ROOT=$(dirname $(dirname "$DRCLAW_PATH") 2>/dev/null || echo ".")
fi

echo "Detected Dr.Claw Root: $DRCLAW_ROOT"
```

Verify and list the documentation directory:
Use the derived $DRCLAW_ROOT to locate the documentation:

```bash
# Construct the standard documentation path
DOCS_DIR="$DRCLAW_ROOT/docs/"

# Check if the path exists and list files
if [ -d "$DOCS_DIR" ]; then
    find "$DOCS_DIR" -type f -name "*.md" | head -n 100
else
    # If the derived path is incorrect, perform a global fuzzy search
    find "$DRCLAW_ROOT" -type d -name "docs" | grep "docs"
fi
```

**If project documentation does not exist, search the working directory**

If documentation is still not found, search for available documentation content under the Dr.Claw installation path:

```bash
# Look for characteristic Dr.Claw ops docs
FILE_PATH=$(find . -type f \( -name "DRCLAW_ENV_zh.md" -o -name "DRCLAW_OPENIM_CHANNEL_zh.md" -o -name "README.md" \) | head -n 1)
if [ -n "$FILE_PATH" ]; then
    # Use dirname to get the directory containing the file
    DOCS_DIR=$(dirname "$FILE_PATH")
fi
```

If a documentation directory is found, save it in memory in this format:

```markdown
# Documentation Directory
$DOCS_DIR = <doc_path>
```

### Step 2: Documentation Search and Matching

Repo docs are mostly `DRCLAW_*.md` / `README.md` (e.g. `DRCLAW_ENV_zh.md`, `DRCLAW_OPENIM_CHANNEL_zh.md`). Match by topic keywords.

Use find to list Markdown files and pick `<doc_path>` by filename keywords (ENV, OPENIM, CUSTOMIZATION, install, etc.).

```bash
# List Markdown under the docs directory
find $DOCS_DIR -type f -name "*.md"
```

If no suitable document is found, read all documentation contents in the next step.

### Step 3: Read the Documentation Content

After finding candidate documents, read and identify the paragraphs relevant to the question. You can use:

- `cat <doc_path>`
- `file_reader` skill (recommended for longer documents or paginated reading)

If the documentation is long, prioritize reading the sections most relevant to the question (installation steps, configuration options, example commands, notes, version requirements).

### Step 4: Extract Information and Respond

Extract key information from the documentation and organize it into an actionable answer:

- Give the direct conclusion first
- Then provide steps / commands / configuration examples
- Include necessary prerequisites and common pitfalls

Language requirement: the answer language must match the language of the user's question (answer in Chinese if asked in Chinese, answer in English if asked in English).

### Step 5 (Optional): Repository Docs Lookup

If the previous steps cannot be completed (no local documentation, missing documentation, or insufficient information), use the repository docs as a fallback:

- https://github.com/ProjectDrClaw/DrClawAgent/tree/main/docs

Answer based on the content available there, and clearly state in the answer that the conclusion comes from repository documentation.

## Output Quality Requirements

- Do not fabricate non-existent configuration options or commands
- When there are version differences, clearly note "please refer to the current documentation version"
- For paths, commands, and configuration keys, provide copy-pasteable original snippets whenever possible
- If information is still insufficient, clearly state the gaps and tell the user what additional information is needed (e.g., operating system, installation method, error logs)
