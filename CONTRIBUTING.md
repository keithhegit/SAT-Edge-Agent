# Contributing / 贡献指南

Thank you for contributing to this repository.

## Scope

This repository contains the intranet deployment snapshot for the OGLINK remote
sensing agent project.

Please keep contributions aligned to:

- the current technical whitepaper scope
- focused frontend or backend improvements
- reproducible intranet deployment behavior

## Contribution Process

1. Fork or branch from the latest active branch.
2. Keep changes focused on one logical update.
3. Update related docs together with code changes.
4. Include short verification notes with the change.

## Change Requirements

- Do not reintroduce Cloudflare tunnel or external proxy files unless the
  project scope changes explicitly.
- Do not commit full NWPU image and label assets.
- Keep local runtime files, secrets, and private lab material out of git.
- Preserve the documented intranet addresses or explain why they changed.

## PR Checklist

- [ ] Change scope is clear and minimal
- [ ] README or whitepaper updated if behavior changed
- [ ] No secrets or private data included
- [ ] Intranet-only assumptions still hold
- [ ] Verification notes are included

## Code of Conduct

By participating, you agree to follow [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md).
