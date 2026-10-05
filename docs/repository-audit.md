# Foundation audit — 5 October 2026

Before foundation edits, the repository workspace contained no files or subdirectories,
including no `.git`. Recursive filesystem inspection and `rg --files --hidden`
found no source, README, license, configuration, research material or instruction
files. `git branch --show-current`, `git status --short`, `git remote -v` and
`git log` reported that the directory was not a Git repository. Thus a current
local branch/status/history did not exist, rather than being clean on an existing branch.

The connected GitHub account was `MadB0i`. Repository search identified its public,
admin-accessible `MadB0i/AstroTrust`, with size zero and configured default branch
`main`. `git ls-remote https://github.com/MadB0i/AstroTrust.git` succeeded with no
refs. The remote was therefore empty, without an existing branch commit/history.
Other similarly named repositories were unrelated and were not used.

No reproducibility infrastructure existed: scenario taxonomy/schema, fixtures,
controlled templates, translation review process, trace records, metric definitions,
tests/CI, ethics/data governance or citation/license metadata were all absent.

## Conservative decisions

- Initialized local Git on `main` and added the verified repository as `origin`.
  No commit or push was part of that foundation task. The later instrument checkpoint
  authorizes the first verified snapshot and push.
- Used Python 3.12+ with JSON and Pydantic, plus a development dependency lock.
- Selected MIT for code, documentation and current invented fixtures because it is
  simple and permissive. Future human data do not inherit that license automatically.
- Did not infer a real-name author from global Git identity; citation metadata use
  the verified repository-owner handle. Personal attribution/release date remain
  subject to maintainer confirmation, without a DOI or paper citation.
- Used eight adult-only fictional situations and coarse profiles. This is a bounded
  engineering fixture set, not representative sampling or the final dataset.
- Left Hindi and Assamese pending. English wording is also unvalidated; no human
  review, annotation, model output or scientific result is claimed.

The taxonomy follows the user's prespecified domains. Stakes and qualitative
construct components are draft research choices documented for later review.
