# Tech Stack: Fly.io Backend Hosting

<tech_stack>
<hosting platform="Fly.io">
The FastAPI backend is hosted on Fly.io. Build it in the `backend/` folder.

Requirements:
- Include a well-documented Swagger UI at `/docs`
- Serve the OpenAPI JSON spec at `/openapi.json`
- Configure a unique subdomain via Cloudflare DNS (e.g., `api.example.com`)
- Define the subdomain in a single location (e.g., environment variable or config file) so all scripts and configs reference it from one place — this makes future domain changes trivial
</hosting>
</tech_stack>
