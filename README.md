# 🍜 PAC FEAST

A food-themed **Pac-Man** built with vanilla HTML/CSS/JS and the HTML5 Canvas —
no build step, no dependencies. Open `index.html` in any modern browser and play.

The visual style is inspired by a neon arcade mural: a pitch-black background,
rounded **neon-blue maze walls**, white pellet dots, and hand-drawn **pixel-art
food** (ramen, sushi, pizza, burger, ice cream, coffee, fried egg) as the
collectible power-ups and bonus treats.

## How to play

- Munch every **white dot** to clear the level (10 pts each).
- Grab a **food power-up** in the corners (ramen / sushi / pizza / burger) to turn
  the ghosts blue and edible — eat them for escalating points (200 → 400 → 800 → 1600).
- Snack on the **bonus treats** that appear mid-level for 500 pts.
- Avoid the ghosts while they're hunting. Run out of lives and it's game over.

### Controls

| Action | Keys |
| --- | --- |
| Move | Arrow keys or `W` `A` `S` `D` |
| Pause | `P` |
| Start / Restart | `Enter` or `Space` |
| Mute | `M` |

On touch devices, use the on-screen D-pad or swipe on the maze.

## Features

- Four classic ghosts with distinct chase personalities (Blinky, Pinky, Inky, Clyde),
  scatter/chase wave timing, frightened mode, and eyes-only "return home" behaviour.
- Grid-accurate movement with queued turns and a wrap-around side tunnel.
- Score, high score (saved in `localStorage`), lives, and increasing levels.
- Everything — maze, food sprites, characters — drawn procedurally on canvas.

## Run it

```bash
# just open the file
open index.html        # macOS
xdg-open index.html    # Linux
# …or serve it
python3 -m http.server
```

Then visit `http://localhost:8000`.
