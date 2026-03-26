# LLM Model Configuration

<constraints>
<model_policy>
The LLM model is configured once in the `.env` file and must not be changed during development.

Current model: `openrouter/google/gemini-3-flash-preview`
Environment variable: `LITELLM_MODEL=openrouter/google/gemini-3-flash-preview`

This model value is read by the deployment scripts (`deploy_stage.sh`, `deploy_prod.sh`) and set as a secret environment variable in the Fly.io backend app.

Do NOT change the model. Do NOT suggest changing the model. If something isn't working, the fix is in the code or the prompt — not in switching models.
</model_policy>
</constraints>
