# Tech Stack: Cloudflare (Pages + DNS)

<tech_stack>
<cloudflare>
  <dns>
  The `CLOUDFLARE_API_TOKEN` for the wrangler CLI is stored in `.../scripts/.env`.

  It has permissions to manage DNS for:
  - `_REDACTED_.com` — production
  - `_REDACTED_.org` — staging
  </dns>

  <hosting>
  The frontend is statically hosted via Cloudflare Pages.

  Domain configuration: define the domain name in a single location (e.g., an environment variable or config file) so that all scripts and configs reference it from one place. This makes it easy to change the domain in the future without hunting through multiple files.

  Expected domains:
  - `example.com` and `www.example.com` (replace with actual domain)
  </hosting>
</cloudflare>
</tech_stack>
