# Tech Stack: Cloudflare D1 Database

<tech_stack>
<database type="Cloudflare D1">
Use Cloudflare D1 as the database. D1 is a serverless SQLite-compatible database hosted by Cloudflare.

Implementation:
- Create a Cloudflare Python Worker that acts as a proxy between the Fly.io backend and the D1 database
- The backend on Fly.io calls this worker to perform all database operations
- This architecture is necessary because D1 can only be accessed from within Cloudflare Workers
</database>
</tech_stack>
