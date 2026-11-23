# linkedin

LinkedIn Auto-Connect Bot — an advanced LinkedIn automation tool built with Python and Playwright, connecting to an already-running Chrome instance via CDP (no fresh login required).

Key Features:

Two search modes: hashtag search or people directory search.

Location filtering: automatically applies a country/city filter through LinkedIn's UI, picks the first suggestion, and clicks "Show results" — optimized to minimize wait time (fast polling instead of fixed sleeps, and force=True to bypass Playwright's actionability checks).

Exact name matching: extracts the name from the Invite button's aria-label (with a profile-link fallback) and matches the first name only when a single word is entered — so Ahmed matches Ahmed Almi but not Ahmad or Abdelrahman Ahmed. Full Arabic text normalization is supported.

Connection invitations: with or without a custom note, with automatic fallback to "Send without a note" if the note send fails.

Verbose logging: prints every step (extracted name, skip reason, send success/failure) for easy tracing and debugging.

Safety: runs on a dedicated Chrome profile (Chrome-Automation) and leaves the browser open after finishing.

Tech Stack: Python, Playwright (patchright), Chrome DevTools Protocol, Requests, Colorama.

Project Status: In development — the current version supports people mode with a single page, with plans for a dynamic daily connection limit (100/day), scheduled runs (9 AM and 5 PM), and an AI mode for personalized outreach messages.
