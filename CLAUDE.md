# Notes for Claude

## Workflow
- **Always merge to `main` after a change.** Once a change is done and tested, commit it, then merge it
  into `main` and push (`git push origin HEAD:main`) without asking first. Fetch and merge `origin/main`
  into the working branch before pushing.
- The site is served from `main` (GitHub Pages at https://codlnd.github.io/induction/, plus the Firebase
  Hosting deploy in `.github/workflows/deploy.yml`).

## Project
- Static single-file pages, no build step: `index.html` (Induction Hub), `healthcare.html` + `guide.html`
  (Healthcare Bill Challenge), `setup.html` + `setup-guide.html` (Induction Setup Checklist).
- All pages share one Firebase project (`induction-5725a`) and fall back to a browser-only demo mode.
  `firestore.rules` must be pasted into the Firebase console by hand; the deploy workflow doesn't publish it.
  If a change needs a new collection, update the rules and tell the user to publish them.
- Keep the shared look: Plus Jakarta Sans and the same design tokens (`--brand: #1b6082`, etc.).
- When a page changes, update its guide page (and the screenshots in `guide-img/` if the UI changed).
- Test in demo mode by copying the page with `apiKey: "PASTE"`, so tests never write to the live database.
