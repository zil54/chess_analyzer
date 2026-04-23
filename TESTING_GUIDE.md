# Testing Guide for Board and Pieces UI Improvements

## Verification Checklist

### 1. Board Color Orientation
- [ ] Start the application
- [ ] Look at the chess board from White's perspective
- [ ] Verify that **bottom-left square (a1) is DARK** (not light)
- [ ] Verify that **bottom-right square (h1) is LIGHT** (not dark)
- [ ] Verify that **top-left square (a8) is LIGHT** (not dark)
- [ ] Verify that **top-right square (h8) is DARK** (not light)

**What to look for**: Standard chess orientation where a1 should be a dark square.

---

### 2. Piece Set Selection
- [ ] Click the "Settings" or board settings icon (⚙️)
- [ ] Open the Board Settings panel
- [ ] Locate the "Piece Sets" section (should be below "Board Colors")
- [ ] Verify you can see 5 piece set options:
  - [ ] Classic
  - [ ] Leipzig
  - [ ] Cases
  - [ ] Merida
  - [ ] Alpha
- [ ] Each option should show chess piece symbols (♔ ♚)

---

### 3. Piece Set Switching
- [ ] Select different piece sets
- [ ] Verify that the board pieces update immediately
- [ ] Try switching between Classic, Leipzig, and other sets
- [ ] Verify pieces display correctly with each set

**Expected behavior**: Pieces should instantly update on the board when a different set is selected.

---

### 4. Persistence
- [ ] Change the piece set and close the settings
- [ ] Refresh the page or navigate away
- [ ] Open settings again
- [ ] Verify that your selected piece set is still selected

**Expected behavior**: Settings should be saved in localStorage and persist across sessions.

---

### 5. Board Color Themes Work With New Piece Sets
- [ ] Select different board color themes (Classic, Midnight, Forest, etc.)
- [ ] For each board theme, try different piece sets
- [ ] Verify that pieces display correctly on all board colors

**Expected behavior**: Piece visibility should be good on all board/piece combinations.

---

## Troubleshooting

### If pieces don't show up on the board:
1. Check browser console for errors (F12 → Console tab)
2. Verify that `/pieces/classic/*.svg` files exist in the public folder
3. Clear browser cache and refresh
4. Check that piece SVG files are valid (can be opened in browser)

### If board colors are still incorrect:
1. Hard refresh the page (Ctrl+Shift+R or Cmd+Shift+R)
2. Clear browser cache completely
3. Check that `BoardDisplay.vue` has the corrected conic-gradient

### If piece sets don't change:
1. Check browser console for JavaScript errors
2. Try selecting a different piece set
3. Open browser DevTools → Network tab to see if piece SVG files are loading
4. Verify that `injectPieceSetCSS` is being called (add console.log if needed)

---

## Expected Visual Results

### Board Colors (for White orientation):
```
  a  b  c  d  e  f  g  h
8 ░ . ░ . ░ . ░ .    (top row)
7 . ░ . ░ . ░ . ░
6 ░ . ░ . ░ . ░ .
5 . ░ . ░ . ░ . ░
4 ░ . ░ . ░ . ░ .
3 . ░ . ░ . ░ . ░
2 ░ . ░ . ░ . ░ .
1 . ░ . ░ . ░ . ░    (bottom row)
  a1 is . (DARK), h1 is . (LIGHT)
```

(░ = dark square, . = light square)

---

## Performance Notes
- Piece SVG loading should be instant
- CSS injection happens on board creation and piece set change
- No external API calls needed for piece sets
- All assets are served locally

---

## Contact Support
If you encounter any issues:
1. Check the browser console for error messages
2. Verify all piece SVG files are present in `/public/pieces/*/`
3. Try clearing browser cache and restarting
4. Report the specific issue with console error messages

