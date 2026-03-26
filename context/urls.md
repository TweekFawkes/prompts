# URLs and FQDNs

<context>
<environments>
  <production>
  - _REDACTED_.com — production frontend
  - www._REDACTED_.com — redirects to _REDACTED_.com
  - api._REDACTED_.com — production backend API
  - db._REDACTED_.com — production D1 database worker
  </production>

  <staging>
  - _REDACTED_.org — staging frontend
  - www._REDACTED_.org — redirects to _REDACTED_.org
  - api._REDACTED_.org — staging backend API
  - db._REDACTED_.org — staging D1 database worker
  </staging>
</environments>
</context>

Always use the staging URLs for testing and development. Never point tests or development work at production URLs.
