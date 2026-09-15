MARINEGUARD SIH26143 — N-OBSERVATION / ACCESSAIS BUILD

RUN
1. Extract this folder.
2. Open the MarineGuard folder.
3. Double-click START_MARINEGUARD.bat (or run: python server.py).
4. Open http://127.0.0.1:5000 in Chrome.
5. Upload any number of satellite images.
6. Upload the NOAA/USCG AccessAIS CSV exported for the matching area/time.
7. Run Complete Investigation.

ARCHITECTURE
Each satellite frame is stored as its own Observation N with independent AI/slick values, automatic location, reconstruction, AIS candidates, evidence and report. Same filenames do not merge observations.

ACCESSAIS
This build does not fabricate vessel tracks. Vessel intelligence comes from the uploaded AccessAIS CSV. AccessAIS is historical AIS point data, not a live AIS feed.

AI
The build attempts a CLIP zero-shot visual assessment when the Transformers/Torch model can load. If unavailable, it uses a local visual fallback so the server still runs. The visual model is a prototype assessment, not a validated oil-spill segmentation model.

GEOLOCATION / RECONSTRUCTION
GPS EXIF is used automatically when present. If absent, a clearly labelled prototype image-derived georeference is used. Reverse-drift reconstruction is a transparent prototype and should use time-matched metocean fields for operational deployment.
