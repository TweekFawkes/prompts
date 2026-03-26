# Test Case Management

<instructions>
<test_case_policy>
After implementing any new feature or fixing any bug, follow these steps:

1. Check the `tests/` folder for an existing test that covers this change.
2. If no test exists, create one that verifies the new behavior or confirms the bug is fixed.
3. Ensure the test runs automatically as part of `deploy_stage.sh` (and `deploy_prod.sh` if appropriate), so regressions are caught on every deployment.

Tests exist to prevent regressions — never skip this step, even for small changes.
</test_case_policy>
</instructions>
