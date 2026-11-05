# Character art prompts (Gemini)

Make each character in two steps in the **same Gemini chat**:
1. The base character (Prompt A).
2. Its animation sprite sheet (Prompt B), using the base character as the reference.

Start a **new chat for each of the 6 characters**. In each new chat, upload your best finished character as a
style reference, so all 6 match.

Rules that let the game use the images:
- **Skin uses two exact key colours:** base `#C68A5E` and shadow `#A86F48`. The game swaps these for the
  skin tone chosen in admin.
- **Solid magenta `#FF00FF` background.** The game cuts it out to make it transparent.
- **Same size, same baseline, and a fixed grid in every frame.** This keeps the animation from jumping around.

---

## Shared style block (pasted into every prompt below)

```
STYLE: Retro pixel-art character sprite, front-facing, full body, standing straight.
Chunky, clearly visible square pixels on a strict grid (character about 32 px wide x 64 px tall,
scaled up with nearest-neighbour so pixels stay crisp). Flat colours only, each colour with at most
one slightly darker shade for simple shading. NO black outlines, NO anti-aliasing, NO gradients,
NO dithering, NO texture. Cute, friendly proportions: big rounded head about 1/3 of total height,
simple face with two small solid black square eyes, short thick eyebrows, small simple mouth.
Arms hang at the sides, hands are simple skin-coloured blocks, feet are simple dark blocks.

SKIN (very important): all visible skin (face, ears, neck, arms, hands, legs) must use exactly two
colours: base #C68A5E and shadow #A86F48. Do not use these two colours, or similar browns,
anywhere else (not in hair, clothes or shoes).

BACKGROUND: one solid flat magenta #FF00FF filling the whole image. Nothing else: no floor,
no shadow, no text, no logo, no border, no watermark.
```

---

## Prompt A: base character (pick one of the six)

```
Create a single pixel-art character sprite.

[PASTE THE SHARED STYLE BLOCK HERE]

CHARACTER: [PASTE ONE CHARACTER DESCRIPTION FROM THE LIST BELOW]

Output: one character, centred, in a square image.
```

### The six characters (everyday Singapore look)

**1. Teenage boy (about 15)**
```
A Singaporean secondary-school boy, about 15. Short spiky black hair. Short-sleeved white school
shirt, dark navy shorts, white socks and white sports shoes. Thin dark backpack straps over both
shoulders. Slightly slouched, youthful.
```

**2. Teenage girl (about 15)**
```
A Singaporean secondary-school girl, about 15. Black hair in a high ponytail with a small dark-blue
hair tie. White short-sleeved blouse under a light-blue school pinafore, white socks, black school
shoes. Youthful and energetic.
```

**3. Adult man (about 40)**
```
A Singaporean office worker, about 40. Short neat black hair. Light-blue short-sleeved collared
shirt, dark grey trousers, black belt, black shoes. A red lanyard with a small white staff pass
on his chest.
```

**4. Adult woman (about 40)**
```
A Singaporean office worker, about 40. Shoulder-length straight black hair. Teal short-sleeved
blouse, black trousers, black flat shoes. A small dark-red handbag hanging from one hand.
```

**5. Elderly man (about 72)**
```
A Singaporean uncle, about 72. Bald on top with tufts of white hair on both sides, thick white
eyebrows and a white moustache. Mustard-yellow short-sleeved polo shirt, dark brown long trousers,
dark slippers. Slightly hunched, holding a simple dark-grey walking stick in one hand.
```

**6. Elderly woman (about 72)**
```
A Singaporean auntie, about 72. Grey-white hair tied in a neat bun, thin round reading glasses.
Short-sleeved floral blouse (pale pink with small red flowers), loose dark-green long pants,
dark slippers. Holding a small woven market bag in one hand.
```

---

## Prompt B: animation sprite sheet (same chat, right after Prompt A)

```
Using EXACTLY this character (same pixel grid, same size, same proportions, same colours, same
clothes; skin still only #C68A5E and #A86F48; background still solid #FF00FF), create a sprite
sheet.

Layout: a grid of 4 columns x 4 rows of equal square cells. No gaps, no borders, no labels,
no text. In every cell the character is the same size, centred horizontally, with feet on the
same baseline.

Row 1 - TALKING (front-facing, calm): mouth closed; mouth slightly open; mouth wide open;
mouth slightly open.
Row 2 - IMPATIENT: tapping one foot (foot lifted 2 pixels); foot down; arms crossed with a frown;
looking at a wristwatch with one eyebrow lowered.
Row 3 - EMOTIONS: worried (eyebrows raised in the middle, small blue sweat drop); confused (one
eyebrow up, one hand scratching head, small orange "?" beside the head); sad (downturned mouth,
eyebrows sloping down); neutral (small straight mouth).
Row 4 - HAPPY: gentle smile; big open-mouth grin with rosy cheeks; both arms raised cheering;
jumping with both arms raised (whole body 3 pixels higher, small yellow sparkles).
```

If Gemini can't keep 16 frames consistent, split the sheet into two requests: rows 1-2, then rows 3-4,
each as a **4 x 2** grid.

---

## Tips
- Use Gemini's image generation (in the Gemini app, ask it to create an image).
- Regenerate until the base character is clean, **before** you ask for the sprite sheet.
- Use the same words for the style every time, and upload your best character as a reference in each
  new chat.
- Don't upload stock images with watermarks as references. Use the descriptions above, or your own
  earlier Gemini output.
- Save the images as PNG with these names:

| File | Character |
|---|---|
| `sprites/male-teen.png` | Teenage boy |
| `sprites/female-teen.png` | Teenage girl |
| `sprites/male-adult.png` | Adult man |
| `sprites/female-adult.png` | Adult woman |
| `sprites/male-elderly.png` | Elderly man |
| `sprites/female-elderly.png` | Elderly woman |

Send the sheets to Claude (or add them to the repo's `sprites/` folder) to wire them into the game. Each
character's sprite is picked automatically from its gender and age: under 20 uses the teen sprite, 20-59
uses the adult sprite, and 60+ uses the elderly sprite. The skin colour is swapped to the tone chosen in
admin, and the frames are animated: talking while asking a question, impatient when idle, confused after
a wrong answer, and cheering when finished.
