# vue-project

This template should help get you started developing with Vue 3 in Vite.

## Recommended IDE Setup

[VS Code](https://code.visualstudio.com/) + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Recommended Browser Setup

- Chromium-based browsers (Chrome, Edge, Brave, etc.):
  - [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd) 
  - [Turn on Custom Object Formatter in Chrome DevTools](http://bit.ly/object-formatters)
- Firefox:
  - [Vue.js devtools](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)
  - [Turn on Custom Object Formatter in Firefox DevTools](https://fxdx.dev/firefox-devtools-custom-object-formatters/)

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).

## Project Setup

```sh
npm install
```

### Frontend Environment Variables

Create `app/frontend/.env` if you want to override defaults locally:

```sh
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH=20
VITE_LIVE_ANALYSIS_WORKER_TARGET_DEPTH=26
VITE_LIVE_ANALYSIS_DISPLAY_LAG_DEPTH=2
```

You can copy `app/frontend/.env.example` as a starting point.

### Compile and Hot-Reload for Development

```sh
npm run dev
```

### Compile and Minify for Production

```sh
npm run build
```
