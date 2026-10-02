# HP Tailwind build

`../hp.css` is **generated** — do not edit it by hand. The 6 `HP/*.html` pages
link it instead of the old `cdn.tailwindcss.com` runtime compiler (which
render-blocked). Theme (custom colors, fonts, spacing) lives in
`tailwind.config.js`.

## Rebuild after editing classes in any HP/*.html

From this folder:

```
npm install tailwindcss@3 @tailwindcss/forms @tailwindcss/container-queries
npx tailwindcss -c tailwind.config.js -i input.css -o ../hp.css --minify
```

Then re-run `python manage.py collectstatic` so the compressed `hp.css.br`/`.gz`
siblings regenerate.

- `content` in the config scans `../*.html`, so any class used in those pages
  (including literal classes inside inline `<script>`) is picked up.
- Classes built by JS string concatenation are NOT auto-detected — add them to a
  `safelist` in the config if you introduce any.
- `node_modules/` is not committed; `npm install` recreates it.
