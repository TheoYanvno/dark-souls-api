"""Start the API on http://127.0.0.1:5000 (works the same on Windows, macOS and Linux)."""
from souls import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
