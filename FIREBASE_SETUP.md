# Healthcare Bill Challenge: Firebase setup

`healthcare.html` is a single page with three views:

| View | URL | Who uses it |
|---|---|---|
| Main screen | `healthcare.html` | Projected for the room: the 4 characters, live progress, the debrief |
| Team page | `healthcare.html?view=team&slot=1` to `slot=4` | Team phones, opened by scanning the QR code on the main screen |
| Admin | `healthcare.html?view=admin`, or triple-click the 🏥 icon on the main screen, or press Shift+A | Facilitator: character library, slot setup, start/pause, reveal answers |

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
publishes the page and the rules (see `firebase.json`). The site is then at
`https://<project-id>.web.app/` (main screen). Open admin from the main screen (triple-click 🏥) or at `https://<project-id>.web.app/healthcare.html?view=admin`.

**Option B: GitHub Pages.** Enable Pages for this repo under **Settings → Pages**, using the default branch and
the root folder. Then open `https://<org>.github.io/induction/healthcare.html`. Only do this if the repo can be
public. If you use this option, still publish the rules in Firebase (step 4 above).

The QR codes are generated automatically from whatever URL the main screen was opened from.

## 3. Running a session

1. Open **Admin**: triple-click the 🏥 icon on the main screen, press **Shift+A**, or go to `?view=admin`.
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
hc_progress/{0..3}   step, wrong, attempts, hintStep, lastAnswer, lastResult, lastAt, finishedAt, history[]
```

When you assign a character, it is copied into `hc_game/state`. Library edits therefore don't change a game
that's already running unless you re-sync.

**Note:** there is no login. Anyone who has the page address could open the admin screen or change game data,
and anyone who opens the browser developer tools could see the answers. That's fine for an induction
activity, but don't put sensitive or personal data in the characters. `ADMIN_PIN` hides the admin screen
from casual visitors, but it is not real security.
