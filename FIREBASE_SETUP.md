# Healthcare Bill Challenge: Firebase setup

`healthcare.html` is a single page with three views:

| View | URL | Who uses it |
|---|---|---|
| Main screen | `healthcare.html` | Projected for the room: the 4 characters, live progress, the debrief |
| Team page | `healthcare.html?view=team&slot=1` to `slot=4` | Team phones, opened by scanning the QR code on the main screen |
| Admin | `healthcare.html?view=admin`, or the ⚙ button on the main screen, or press Shift+A | Facilitator: character library, slot setup, start/pause, reveal answers |

Until you paste a Firebase config, the page runs in **demo mode**. Demo mode stores everything in the current
browser, so you can try it on one computer using several tabs. Phones only work once Firebase is connected.

## 1. Create the Firebase project (about 10 minutes)

1. Go to <https://console.firebase.google.com> and click **Add project**. Name it, for example `cpf-induction-game`.
   Google Analytics isn't needed.
2. **Firestore:** open **Build → Firestore Database → Create database**.
   - Location: `asia-southeast1 (Singapore)`.
   - Start in **production mode**. You'll replace the rules in step 4.
3. **Security rules:** open **Firestore Database → Rules**, paste in the contents of [`firestore.rules`](firestore.rules),
   and click **Publish**. No login is used, so the rules open only this game's three collections.
4. **Web app config:** open **Project settings (⚙) → General → Your apps → Web (`</>`)**. Register an app
   (no hosting checkbox needed) and copy the `firebaseConfig` object.
5. Open `healthcare.html`, find `const firebaseConfig = {` near the top of the `<script>`, and replace the
   placeholder values with your config.

   > The web `apiKey` is not a secret. It only identifies the project.

## 2. Host the page

Phones must be able to open the page from the QR code, so it needs a public `https://` URL.
A `file://` path or `localhost` won't work.

**Option A: Firebase Hosting** (recommended, free tier is enough)

```bash
npm install -g firebase-tools
```

```bash
firebase login
```

```bash
firebase use --add
```

```bash
firebase deploy
```

Run these from this folder. `firebase use --add` asks you to pick the project you created. `firebase deploy`
publishes the pages and the rules (see `firebase.json`). The site is then at
`https://<project-id>.web.app/` (the Induction Hub, which links to every app) and the game's main screen at `https://<project-id>.web.app/healthcare.html`. Open admin from the main screen (⚙ button, top right) or at `https://<project-id>.web.app/healthcare.html?view=admin`.

**Option B: GitHub Pages.** Enable Pages for this repo under **Settings → Pages**, using the default branch and
the root folder. Then open `https://<org>.github.io/induction/healthcare.html`. Only do this if the repo can be
public. If you use this option, still publish the rules in Firebase (step 4 above).

The QR codes are generated automatically from whatever URL the main screen was opened from.

## 3. Running a session

1. Open **Admin**: click the ⚙ button on the main screen, press **Shift+A**, or go to `?view=admin`.
   To keep casual visitors out, set `ADMIN_PIN` near the top of `healthcare.html`.
2. **Character library:** click **+ New character**, or **Add 4 sample characters** to start from examples.
   For each character, set the name, age, gender, medical situation, and the questions. Each question has:
   - **Correct answer(s):** for example `1200`. `$1,200` and `1200.00` are also accepted. Separate alternatives
     with `|`, for example `Yes|Y`.
   - **Allowed ± margin:** optional. For example, `1` accepts anything within $1.
   - **Hint:** shown on the team's phone, and briefly on the main screen, after a wrong answer.
   - **Debrief explanation:** shown when you reveal answers.
   - Use **+ Add question** to add more questions, ↑/↓ to reorder them, and **Remove** to delete one.
   - Characters are saved in Firestore, so you can reuse them in later sessions. **Export** and **Import**
     back the library up to a JSON file.
3. **Live game:** pick a character and enter a team name for each of the 4 slots. Changing a slot's character
   resets that slot's progress.
4. Open the **main screen** on the projector. Press `F` for full screen and `Q` to show or hide the QR codes.
5. Click **▶ Live**. Teams scan their QR code and answer. The main screen updates within about a second:
   - Correct answer: the character becomes happier and the marker moves along the track.
   - Wrong answer: the character looks confused, asks "Hmm… are you sure? 🤔", and shows the hint.
   - Finished: the character celebrates, and the finishing order (🥇🥈🥉) appears.
6. **Debrief:** turn on **Reveal answers** to show every character's questions, answers and explanations
   on the main screen.
7. Before the next session, click **Reset all progress**.

If you edit a character that's already in the game, the admin page offers to update the live game.
You can also click **↻ Re-sync characters**.

## Data model (Firestore)

```
hc_characters/{id}   name, age, gender, situation, questions[{q, answer, tolerance, hint, explain}]   (admin only)
hc_game/state        status: waiting|live|paused, reveal: bool,
                     slots[4]{teamName, characterId, character (copy of the character)}
hc_progress/{0..3}   step, wrong, attempts, hintStep, lastAnswer, lastResult, lastAt, finishedAt, history[],
                     expireAt (14 days after the last change; see below)
```

When you assign a character, it is copied into `hc_game/state`. Library edits therefore don't change a game
that's already running unless you re-sync.

### Automatic clean-up of team progress (14 days)

Every write to a team's progress sets `expireAt` to 14 days later, so the date moves forward while a team is
still playing. Progress that hasn't changed for 14 days is cleared in two ways:

- **On the server (recommended, one-time setup):** a Firestore TTL policy deletes expired progress docs even if
  nobody opens the game. In the Firebase console open **Firestore Database → Time-to-live (TTL)** (in some
  consoles it's under the Google Cloud console's Firestore page), click **Create policy**, and enter collection
  group `hc_progress` and timestamp field `expireAt`. Firestore usually deletes expired docs within a day of
  their expiry. The admin page recreates blank progress docs when it next opens.
- **In the app:** when the admin page or main screen opens, it resets any expired team progress it finds. This
  works without the TTL policy.

To change the window, edit `PROGRESS_KEEP_DAYS` near the top of the `<script>` in `healthcare.html`.
Characters, team names and game settings are not affected.

**Note:** there is no login. Anyone who has the page address could open the admin screen or change game data,
and anyone who opens the browser developer tools could see the answers. That's fine for an induction
activity, but don't put sensitive or personal data in the characters. `ADMIN_PIN` hides the admin screen
from casual visitors, but it is not real security.

## Induction Hub (`index.html`)

The site's home page is a tile board linking to every induction app and its guide. Anyone with the page can
click **✎** on a tile to edit it, or **＋ Add app** to add one. Tiles are stored in the Firestore collection
`portal_apps`, so the whole team sees the same board. Make sure the published Firestore rules include the
`portal_apps` block from [`firestore.rules`](firestore.rules); otherwise saving shows a permission error.
To require a PIN before editing, set `EDIT_PIN` near the top of the `<script>` in `index.html`.

Old links to the site root with game parameters (for example `/?view=team&slot=2`) are forwarded to
`healthcare.html` automatically.

## Induction setup checklist (`setup.html`)

A page for the induction team: each month's agenda, the setup needed before each day, which agenda items need
their own setup, and who is doing what. Full instructions are in [`setup-guide.html`](setup-guide.html)
(also linked from the page's 📘 Guide button).

- **Months:** each month has its own agenda, tasks, ticks and people. New months can copy an earlier month
  (keeping or clearing the names), start from the sample agenda, or start blank, and can be created in advance.
  Past months stay as a history.
- **Namelist (👥 Team):** one list of people for all months. Drag names onto agenda items (as the lead) or tasks;
  on phones, tap a name and then the target.
- **Email draft:** builds the month's setup as an email to copy into Outlook, or downloads it as an Outlook
  draft (`.eml`).
- Set `EDIT_PIN` near the top of the `<script>` to ask for a PIN before Edit mode (not real security).

Everything (all months and the namelist) is stored in one Firestore document, `su_setup/main`, covered by the
`su_setup` block in [`firestore.rules`](firestore.rules). Older data with a single agenda and free-text "owner"
names is upgraded automatically: it becomes the current month, and the names join the namelist.
