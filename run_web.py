"""Run the CipherKeys browser interface on this computer."""

from webapp.app import create_app


if __name__ == "__main__":
    app = create_app()
    print("CipherKeys is running locally at http://127.0.0.1:8765")
    print("Keep this terminal open while using the browser interface.")
    app.run(host="127.0.0.1", port=8765, debug=False, threaded=True)
