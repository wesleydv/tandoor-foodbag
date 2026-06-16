import os
import uuid
import json
import threading
from flask import Flask, render_template_string, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)


app = Flask(__name__)

# Store pending import statuses by job ID
import_statuses = {}


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tandoor Recept Importeren</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f7f7f8;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 24px;
        }
        .container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 2px 16px rgba(0,0,0,0.08);
            padding: 48px 40px;
            width: 100%;
            max-width: 520px;
        }
        h1 {
            font-size: 24px;
            color: #1a1a1a;
            margin-bottom: 8px;
        }
        .subtitle {
            color: #666;
            font-size: 14px;
            margin-bottom: 32px;
        }
        input[type="url"] {
            height: 46px;
            flex: 1;
            min-width: 0;
            padding: 0 16px;
            border: 2px solid #e5e5e5;
            border-radius: 8px;
            font-size: 15px;
            outline: none;
            transition: border-color 0.2s;
        }
        input[type="url"]:focus {
            border-color: #ff6b35;
        }
        .input-row {
            display: flex;
            gap: 8px;
        }
        .qr-btn {
            height: 46px;
            width: auto;
            padding: 0 20px;
            margin: 0px;
            background: #3550a3;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
        }
        button {
            width: 100%;
            margin-top: 16px;
            padding: 14px;
            background: #ff6b35;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s;
        }
        button:hover { opacity: 0.9; }
        button:disabled { opacity: 0.6; cursor: not-allowed; }

        .result {
            margin-top: 24px;
            padding: 16px;
            border-radius: 8px;
            display: none;
        }
        .result.success { display: block; background: #e6f9ee; color: #1a7a3a; }
        .result.error { display: block; background: #fde8e8; color: #c0392b; }
        .result.info { display: block; background: #eef2fe; color: #3550a3; }
        .result strong { display: block; font-size: 15px; margin-bottom: 6px; }
        .result a { color: inherit; text-decoration: underline; font-weight: 600; }
        .spinner {
            display: inline-block;
            width: 18px; height: 18px;
            border: 2px solid rgba(106,136,253,0.3);
            border-top-color: #3550a3;
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
            vertical-align: middle;
            margin-right: 8px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
    <script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
</head>
<body>
    <div class="container">
        <h1>Tandoor Recept Importeren</h1>
        <p class="subtitle">Plak een recept URL om het te importeren in Tandoor</p>

        <form id="import-form">
            <div class="input-row">
                <input type="url" name="url" placeholder="https://foodbag.be/..." required>
                <button type="button" class="qr-btn" id="qr-btn">Scan QR</button>
            </div>
            <button type="submit" id="submit-btn">Recept Importeren</button>
        </form>

        <div class="result" id="result"></div>
    </div>

    <div id="qr-overlay" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:1000;justify-content:center;align-items:center;">
        <div style="position:relative;background:white;border-radius:12px;padding:16px;max-width:400px;width:90%;">
            <button id="qr-close" style="position:absolute;top:-10px;right:-10px;width:32px;height:32px;margin:0;padding:0;background:#ff6b35;color:white;border:none;border-radius:50%;font-size:18px;font-weight:bold;cursor:pointer;z-index:1;">&times;</button>
            <div id="qr-reader"></div>
        </div>
    </div>

    <script>
        const form = document.getElementById('import-form');
        const btn = document.getElementById('submit-btn');
        const result = document.getElementById('result');
        const input = form.querySelector('input');

        function showResult(type, message) {
            result.className = 'result ' + type;
            if (type === 'info') {
                result.innerHTML = '<strong>Bezig met importeren...</strong>' + message;
            } else if (type === 'success') {
                result.innerHTML = '<strong>Recept succesvol geïmporteerd!</strong><a href="' + message.link + '" target="_blank" rel="noopener">' + message.text + '</a>';
            } else {
                result.innerHTML = '<strong>Foutmelding</strong>' + message;
            }
            btn.disabled = false;
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const url = input.value.trim();
            if (!url) return;

            result.className = 'result';
            btn.disabled = true;
            showResult('info', '<span class="spinner"></span> Recept ophalen en importeren...');

            try {
                const res = await fetch('/import', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url})
                });
                const data = await res.json();

                if (data.status === 'queued') {
                    pollStatus(data.id);
                } else if (!res.ok) {
                    showResult('error', data.error || 'Aanvraag mislukt');
                } else {
                    showResult('success', {
                        text: "Open recept #" + data.recipe_id + " in Tandoor",
                        link: data.recipe_url
                    });
                }
            } catch (err) {
                    showResult('error', 'Kan de server niet bereiken. Zorg dat deze draait.');
            }
        });

        async function pollStatus(id) {
            for (let i = 0; i < 60; i++) {
                await new Promise(r => setTimeout(r, 2000));
                const res = await fetch('/import/status/' + id);
                const data = await res.json();

                if (data.status === 'running' || data.status === 'queued') {
                    showResult('info', '<span class="spinner"></span> Wacht een moment...');
                    continue;
                }
                if (data.status === 'complete') {
                    if (data.success) {
                    showResult('success', {
                        text: "Open recept #" + data.recipe_id + " in Tandoor",
                        link: data.recipe_url
                        });
                    } else {
                        showResult('error', data.error || 'Import mislukt');
                    }
                    return;
                }
                if (data.status === 'error' || !data.status) {
                    showResult('error', data.error || 'Onbekende fout opgetreden');
                    return;
                }
            }
            showResult('error', 'Import timed out. Try again later.');
        }

        // QR Scanner
        const qrOverlay = document.getElementById('qr-overlay');
        const qrBtn = document.getElementById('qr-btn');
        const qrClose = document.getElementById('qr-close');
        let html5QrcodeScanner = null;

        function startScanner() {
            qrOverlay.style.display = 'flex';
            qrOverlay.style.justifyContent = 'center';
            qrOverlay.style.alignItems = 'center';
            
            html5QrcodeScanner = new Html5Qrcode('qr-reader');
            const config = {
                fps: 10,
                qrbox: { width: 250, height: 250 },
                aspectRatio: 1.0
            };
            
            html5QrcodeScanner.start(
                { facingMode: 'user' },
                config,
                (decodedText) => {
                    input.value = decodedText;
                    stopScanner();
                    document.getElementById('import-form').scrollIntoView({ behavior: 'smooth' });
                },
                (errorMessage) => {
                    // Scan error - ignore
                }
            ).catch(err => {
                console.error('QR scanner failed:', err);
                alert('Geen camera gevonden of toegang geweigerd.');
                stopScanner();
            });
        }

        function stopScanner() {
            if (html5QrcodeScanner) {
                html5QrcodeScanner.stop().then(() => {
                    html5QrcodeScanner.clear();
                    html5QrcodeScanner = null;
                }).catch(err => {
                    console.error('Error stopping QR scanner:', err);
                });
                
            }
            qrOverlay.style.display = 'none';
        }

        qrBtn.addEventListener('click', startScanner);
        qrClose.addEventListener('click', stopScanner);

    </script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/import", methods=["POST"])
def import_recipe():
    data = request.get_json() or {}
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "No URL provided."}), 400

    import_id = str(uuid.uuid4())[:8]

    def run_import():
        import_statuses[import_id] = {**import_statuses[import_id], "status": "running"}
        try:
            from extract_recipe import FoodbagScraper, get_rendered_html
            html = get_rendered_html(url)
            scraper = FoodbagScraper(url=url, html=html)
        except Exception as e:
            import_statuses[import_id]["status"] = "complete"
            import_statuses[import_id]["success"] = False
            import_statuses[import_id]["error"] = f"Scraping failed: {e}"
            return

        try:
            from create_tandoor_recipe import scraped_to_tandoor, TandoorClient
            tandoor_url = app.config["TANDOOR_URL"]
            api_token = app.config["API_TOKEN"]

            recipe_data, image_url = scraped_to_tandoor(scraper, html)
            client = TandoorClient(tandoor_url, api_token)
            recipe_id = client.create_recipe(recipe_data)

            if image_url:
                try:
                    client.upload_image(recipe_id, image_url)
                except Exception as img_err:
                    pass  # non-critical

        except Exception as e:
            import_statuses[import_id]["status"] = "complete"
            import_statuses[import_id]["success"] = False
            import_statuses[import_id]["error"] = f"Recipe creation failed: {e}"
            return

        recipe_url = f"{tandoor_url.rstrip('/')}/recipe/{recipe_id}/"
        import_statuses[import_id] = {
            "status": "complete",
            "success": True,
            "recipe_id": recipe_id,
            "recipe_url": recipe_url,
        }

    import_statuses[import_id] = {"status": "queued"}
    thread = threading.Thread(target=run_import, daemon=True)
    thread.start()

    return jsonify({"status": "queued", "id": import_id})


@app.route("/import/status/<import_id>")
def import_status(import_id):
    status = import_statuses.get(import_id, {"status": "error", "error": "Unknown job ID"})
    return jsonify(status)


def get_config():
    tandoor_url = os.getenv("TANDOOR_URL")
    api_token = os.getenv("TANDOOR_API_TOKEN", "")
    if not api_token:
        raise RuntimeError("TANDOOR_API_TOKEN is not set. Create a .env file with your Tandoor API token.")

    return tandoor_url, api_token



if __name__ == "__main__":
    tandoor_url, api_token = get_config()
    app.config["TANDOOR_URL"] = tandoor_url
    app.config["API_TOKEN"] = api_token

    import time
    print(f"Starting server at http://0.0.0.0:9615")
    print(f"Tandoor URL: {tandoor_url}")
    time.sleep(0.5)
    import webbrowser
    app.run(host="0.0.0.0", port=9615, debug=False)
