# Euler Method — interactive web edition

A static HTML/Canvas/JavaScript port of the supplied **Euler_Method** C++/SFML source.
Works on GitHub Pages without SFML, a backend, npm, or third-party JavaScript libraries.

## Features

- Default sharp 2 px **pixel/dot raster** plot (Bresenham; no antialiasing) matching the original SFML aesthetic
- Switchable **Smooth** renderer and adjustable 1/2/3/4 px pixel sizes
- Dense bright-blue pixel direction field, red pixel Euler curve, pixel parametric/tracer curves
- All eight built-in first-order ODEs from `euler_method.h`
- Explicit Euler solution curves `y[n+1] = y[n] + h*f(x[n], y[n])`
- Editable initial value `(x0, y0)` and numerical step `h`
- Optional slope/direction field (new in the web version)
- Optional dashed RK4 numerical comparison (new; **not an exact solution** or certified error bound)
- Parametric curve with moving marker, play/pause, time scrubbing, speed and tracer
- Mouse/touch drag to pan, mouse wheel to zoom, double-click to set initial value
- Click near the parametric curve to seek time
- Keyboard controls (1–8, A/D, W/S, F, T, Q/E, R)
- Responsive layout; no external dependencies

## Installing into blueinkfountain.github.io

Unzip the package. If you downloaded `euler_method_pixel_web.zip` into Downloads, run:

```sh
cd /Users/persist/math-blog
unzip -o ~/Downloads/euler_method_pixel_web.zip -d ~/Downloads
python3 ~/Downloads/euler_method_pixel_web/install_euler_method.py \
  --repo /Users/persist/math-blog
```

Only **new files** are installed:

```text
docs/Works/Euler-Method.html
assets/euler-method/math.mjs
assets/euler-method/pixel.mjs
assets/euler-method/app.mjs
assets/euler-method/style.css
assets/euler-method/preview.html
```

Existing changed files are backed up once under `.euler_pixel_backup/` (automatically excluded from Git via `.git/info/exclude`).
Existing `Untexed.md`, Daily Record, handwritten ink builder, `_config.yml`, and `update!` are not touched.

Publish with:

```sh
cd /Users/persist/math-blog
git status
git add docs/Works/Euler-Method.html assets/euler-method/
git commit -m "Add interactive Euler Method lab"
git push
```

Expected URL after GitHub Pages builds:

**https://blueinkfountain.github.io/docs/Works/Euler-Method.html**

After pushing, use **Cmd+Shift+R** if the browser shows an older cached version.

The page uses Just the Docs `layout: default` and has `nav_order: 4`, making it a top-level navigation page.

## Local preview

```sh
cd /Users/persist/math-blog
python3 -m http.server 8000
```

Open `http://localhost:8000/assets/euler-method/preview.html`.
To preview the **Jekyll wrapper** itself, use `bundle exec jekyll serve` if available.

## Math fidelity note

The source file `parameter_function.h` uses C++ integer division for `1/2*t`, `1/3*t`, and `sin(1/12)`.
Consequently, as compiled, all these fractional expressions become zero, yielding

```text
x(t) = sin(4t) * (e - 2 cos(18t))
y(t) = cos(5t) * (e - 2 cos(11t))
```

The default option reproduces this **actual C++ runtime behavior**. The separate
“Fractional arguments” option implements the likely intended real fractions.
The original `Error_size` routine isn't a valid general error bound for
`f(x,y)`; rather than reproduce it as a certified bound, the web edition
provides an **optional numerical RK4 comparison**, clearly labelled an estimate.

## Developer tests

With Node.js 18+:

```sh
node --test tests/math.test.mjs
```

The main app uses no npm packages and can be deployed as plain static files.

## Display choices

The page defaults to **Pixel dots / original style** with **2 px** dots. Select **Smooth curves** under *View* to reproduce the previous browser rendering. The **P** keyboard shortcut switches between the renderers. Step sizes and all ODE calculations are unchanged.
