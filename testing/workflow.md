# Testing Workflow

<instructions>
<testing_workflow>
Always verify changes in this exact order before considering work complete:

1. **Local testing**: Run the app locally using `../scripts/dev_local_macos.sh` and confirm the changes work as expected on this laptop.

2. **Staging deployment and browser testing**: Deploy to the staging server using `.../scripts/deploy_stage.sh`, then use Playwright (via the Docker MCP Toolkit) to test the deployed app in a real browser — the same way an end user would interact with it.

Do NOT deploy to production.
Do NOT run `.../scripts/deploy_prod.sh`.
</testing_workflow>
</instructions>
