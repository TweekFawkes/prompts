# Deployment Scripts

<instructions>
Create deployment and testing scripts in the `scripts/` folder. Each script should be self-contained, executable, and include clear error handling so failures are immediately visible.

1. **Local development script** (`scripts/dev_local_macos.sh`):
   - Start all services locally on this macOS laptop
   - Install any missing dependencies automatically
   - Print the local URL where the app can be accessed when ready

2. **VM deployment script** (`scripts/deploy_stage.sh`):
   - Deploy the application to the staging VM
   - Run a basic smoke test after deployment to confirm the app is reachable
   - Print the deployed URL on success
</instructions>
