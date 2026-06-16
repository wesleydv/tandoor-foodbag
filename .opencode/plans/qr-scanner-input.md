# QR Scanner in URL Input

## Approach
Use `html5-qrcode` library from CDN to add a camera-based QR scanner button next to the URL input field. When it detects a QR code, auto-fills the input and closes the scanner overlay.

## Changes to `app.py`

### 1. Add QR button styling (after `.input-row` styles)
- New CSS classes for a side-by-side input row: `.input-row` flex container with the URL input taking remaining space (`flex: 1`) and a blue QR button next to it
- The "Importeren" submit button stays below, full width

### 2. Wrap the input in a flex row
- Replace the flat `<input>` line with:
  ```html
  <div class="input-row">
      <input type="url" name="url" placeholder="https://foodbag.be/..." required>
      <button type="button" class="qr-btn" id="qr-btn">@fa-camera (QR)</button>
  </div>
  ```

### 3. Add QR scanner overlay
- Full-screen modal (`display:none` by default) with:
  - A `#qr-reader` div for the camera viewport
  - A close "X" button in the corner
  - Backdrop + centered reader with max-width ~400px
- Style overlay to cover full page with semi-transparent backdrop

### 4. Load html5-qrcode from CDN
- Add `<script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>` in the head

### 5. QR scanner JS logic
- `startScanner()` — called from `#qr-btn`: makes overlay visible, initializes `Html5Qrcode` with rear camera preference (`facing-mode: user`)
- On successful decode: auto-fills `input.value = decodedText`, closes scanner, triggers form submission focus
- On scanner error (no camera/grant denied): alerts the user and closes overlay
- Close button clears the scanner instance and hides overlay

### 6. Camera permissions note
- html5-qrcode needs HTTPS for live camera (browser security). Since this runs at `127.0.0.1:9615`, it will use `http://` localhost which bypasses the HTTPS requirement for getUserMedia — so it works fine for local use.
