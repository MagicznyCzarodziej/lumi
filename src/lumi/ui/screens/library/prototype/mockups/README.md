# Library home — HTML mockup (A3)

**Nie otwieraj pliku z Findera** — stary cache i brak plakatów dają czarną lewą połowę.

```bash
uv run python -m lumi.ui.screens.library.prototype.mockups
```

Otworzy się `http://127.0.0.1:8765/library-home.html?v=…` (serwer z `Cache-Control: no-store`).

Plakaty: `posters/*.jpg` (lokalne, bez TMDB).

**Serial (sezony)** — `http://127.0.0.1:8765/series-open.html`  
Parametr `?series=kusuriya` (domyślnie), `shingeki`, `severance`, `kaguya`. ↑↓ lista sezonów, Enter → odcinki (toast), Esc → biblioteka (toast).
