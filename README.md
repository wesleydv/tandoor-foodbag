# Tandoor Foodbag Importer

Tandoor Foodbag Importer is a tool to scrape recipes from foodbag.be and import them directly into your Tandoor Recipes instance.

## 🚀 Quick Start (Docker)

The easiest way to get started is using Docker Compose, which sets up both the application and the required Playwright browser environment.

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/tandoor-foodbag.git
    cd tandoor-foodbag
    ```

2.  **Configure Environment**:
    Create a `.env` file based on the example:
    ```bash
    cp .env.example .env
    ```
    Edit `.env` and provide your Tandoor API token and URL.

3.  **Launch**:
    ```bash
    docker compose up -d
    ```

4.  **Use it**:
    - **Web UI**: Open `http://localhost:9615` in your browser.
    - **CLI**: Run via `docker exec -it tandoor-foodbag-app-1 python create_tandoor_recipe.py <url>`.

## 🔐 Deploying with SOPS secrets

The maintainer's host keeps the Tandoor token in `secrets.enc.env`, encrypted with [SOPS](https://github.com/getsops/sops) + age (recipients in `.sops.yaml`). A deploy from the checkout is:

```bash
git pull
sudo SOPS_AGE_KEY_FILE=/opt/doco-cd/keys/age.key sops decrypt secrets.enc.env > .env
docker compose up -d --build
```

The Playwright client (`requirements.txt`) and server image (`compose.yaml`) must stay on the same version; bump them together.

## 🛠️ Manual Setup

If you prefer to run the project without Docker:

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Browser Requirement**:
    This tool requires a Playwright instance. You can either:
    - Run a remote Playwright server and set `PLAYWRIGHT_SERVER_URL` in your `.env`.
    - (Currently optimized for the Docker setup provided).

3.  **Configure Environment**:
    Create a `.env` file with the following keys:
    - `TANDOOR_API_TOKEN`: Your API token from Tandoor settings.
    - `TANDOOR_URL`: The URL of your Tandoor instance (e.g., `https://tandoor.example.com`).
    - `PLAYWRIGHT_SERVER_URL`: Your Playwright WebSocket URL.

4.  **Run**:
    - **UI**: `python app.py`
    - **CLI**: `python create_tandoor_recipe.py <url>`

## 📂 Project Structure

- `extract_recipe.py`: Handles scraping and rendering of foodbag.be pages.
- `create_tandoor_recipe.py`: Manages API communication with Tandoor.
- `app.py`: Flask web interface for easy importing.

## ⚖️ License

Distributed under the MIT License. See `LICENSE` for more information.
