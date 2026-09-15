MARINEGUARD SIH26143 - RUN FIRST

1. Open this folder in VS Code.
2. Open Terminal.
3. Run: python -m pip install -r MarineGuard\requirements.txt
4. Run: python MarineGuard\server.py
5. Open Chrome: http://127.0.0.1:5000

You can also double-click MarineGuard\START_MARINEGUARD.bat.

IMPORTANT:
- Keep the Python terminal open while using the dashboard.
- This build uses an absolute backend address, so accidental file:// opening will not produce the previous 'Failed to fetch' origin error, although http://127.0.0.1:5000 is still the recommended URL.
- Load a NOAA/USCG AccessAIS historical CSV in Vessel Intelligence for real AccessAIS vessel data.
