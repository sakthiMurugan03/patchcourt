# Contributing to PatchCourt

Thanks for contributing! This guide covers the workflow, conventions, and how to
run the project locally before opening a PR.

## Branch naming

Create a short, semantic feature branch off `main`. Use the same prefixes as
Conventional Commits:

```
<type>/<short-kebab-description>
```

Examples:

- `feat/add-evidence-filters`
- `fix/webhook-503-on-empty-redis`
- `ci/add-github-actions-pipeline`
- `docs/update-architecture-diagram`
- `refactor/extract-scoring-helpers`
- `chore/bump-langgraph`

## Conventional Commits

All commits follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<optional-scope>): <description>
```

Allowed types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`.

Keep commits small and focused — one logical change per commit. Don't squash
related-but-distinct work into a single commit.

## Local development

### Backend (Python 3.11+)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,llm]"
pytest -q
```

The dev and llm extras install `pytest`, `pytest-asyncio`, and
`langchain-anthropic` — the full suite (including `test_claude_backend_selected`)
requires the `llm` extra. Tests live under `tests/` and run without any
credentials (mock LLM + synthetic tools by default).

### Dashboard (Next.js)

```bash
cd dashboard
npm ci
npm run dev     # dev server on http://localhost:3000
npm run build   # production build — must pass before merging
npm run lint
```

`node_modules` and `.next/` are gitignored; never commit them.

### Full stack (Docker)

```bash
docker compose build sandbox
docker compose up -d
docker compose --profile worker --profile dashboard up -d
```

## Pull request process

1. **Create a branch** off `main` using the branch naming rules above.
2. **Make focused commits** with Conventional Commit messages.
3. **Verify locally before pushing**: `pytest -q` on the backend and
   `npm run build` in `dashboard/` must both pass.
4. **Open the PR** against `main`. The pull-request template is applied
   automatically — fill in Summary, Motivation, Changes, How Tested, and tick
   the Checklist boxes.
5. **CI must pass.** The GitHub Actions
   pipeline (`.github/workflows/ci.yml`) runs backend tests and the frontend
   build on every PR; a red build blocks the merge.
6. **Request review**, address feedback in additional commits, and let a
   maintainer merge. Don't merge your own PR.

## Code style

- Follow the existing structure in `patchcourt/` (agents, ingest, rag, evidence,
  sandbox, debate, judge, db, worker, api, cli).
- Don't add comments unless they earn their place; prefer clear code.
- Keep CI and its documentation in sync (`CONTRIBUTING.md`, `README.md`).