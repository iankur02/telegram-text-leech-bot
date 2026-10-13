# Telegram Text-Leech Bot

Deploy-ready Telegram bot that takes a `.txt` file with `Title : URL` lines,
downloads each video (HLS / MP4 / yt-dlp sites) and uploads it back to the chat.

## Deploy on Render
1. Push this repo to GitHub.
2. Render → New → Web Service → "Deploy from Git" → select repo.
3. Render auto-detects `render.yaml` (Docker).
4. Add env vars: `API_ID`, `API_HASH`, `BOT_TOKEN`, `OWNER_ID`.
5. Deploy. Health check: `/health`.

## Usage
- `/start` — help
- Send a `.txt` file → bot replies with index range prompt
- Reply `all` / `1-10` / `15 720` / `1-5 480`
- Send a photo → set custom thumbnail
- `/cancel` — stop batch
- `/stats` — disk status

## Notes on signed URLs
Fresh tokens only. ClassPlus/AppX tokens expire in a few hours.
If you get `403 / 410` errors the link is dead — regenerate from the app.
