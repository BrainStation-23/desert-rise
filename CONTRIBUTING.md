# Contributing to Dessert Rice

Thank you for contributing to this BrainStation-23 Odoo project.

## Branching Strategy

- `main`: production-ready, protected branch
- `dev`: integration branch for validated development work
- `feature/<short-name>`: new features
- `fix/<short-name>`: bug fixes
- `hotfix/<short-name>`: urgent production corrections

Do not commit directly to `main`.

## Commit Message Convention

Use clear, imperative commit messages. Prefer:

```text
[module_name] Short description
```

Examples:

```text
[sale_custom] Add margin approval workflow
[account_report_x] Fix partner ledger domain
```

## Pull Request Process

1. Branch from `dev` unless it is a hotfix.
2. Keep changes focused and reviewable.
3. Update documentation, manifests, and changelog when needed.
4. Open a pull request with:
   - business context
   - technical summary
   - deployment or upgrade notes
   - test evidence
5. Obtain at least one reviewer approval before merge.

## Code Style

- Follow standard Odoo conventions and relevant **OCA guidelines**
- Use meaningful model, field, and method names
- Keep methods small and readable
- Avoid dead code and commented-out logic
- Add security rules, access files, and record rules where required
- Keep data files ordered and deterministic

## Testing Requirements

Before submitting a PR:

- Run tests for impacted modules
- Validate installation on a clean database when introducing a new module
- Validate module upgrade on an existing database for manifest or model changes
- Confirm views, security, reports, scheduled actions, and access rights behave as expected
- Include migration scripts when schema or data migration is required

## Review Checklist

- [ ] Manifest version and dependencies are correct
- [ ] Security files reviewed
- [ ] XML IDs are stable
- [ ] No secrets committed
- [ ] Upgrade path considered
- [ ] User-facing changes documented

## Need Help?

For project-specific guidance, coordinate with the BrainStation-23 technical lead or repository maintainers through GitHub issues or pull request discussion.
