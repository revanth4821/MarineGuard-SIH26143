/* =========================================
   MARINEGUARD — INVESTIGATION ENGINE
   Prototype / Demo Data
   ========================================= */


/* =========================================
   1. MAP INITIALIZATION
   ========================================= */

const map = L.map("map").setView([15.40, 73.80], 9);

L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        attribution: "&copy; OpenStreetMap contributors"
    }
).addTo(map);


/* =========================================
   2. OIL SLICK
   ========================================= */

const slickCoordinates = [
    [15.45, 73.80],
    [15.48, 73.82],
    [15.46, 73.86],
    [15.42, 73.88],
    [15.39, 73.84],
    [15.40, 73.79]
];

let slick = L.polygon(
    slickCoordinates,
    {
        color: "#f2a900",
        fillColor: "#f2a900",
        fillOpacity: 0.40,
        weight: 2
    }
).addTo(map);

slick.bindPopup(
    "<b>🛢️ Potential Oil Slick</b><br>" +
    "Estimated area: 12.4 km²<br>" +
    "Detection confidence: 93%"
);


/* =========================================
   3. PROBABLE ORIGIN
   ========================================= */

const originCoordinates = [15.20, 73.70];

let originMarker = null;

const originCircle = L.circle(
    originCoordinates,
    {
        radius: 3500,
        color: "#ff4d5a",
        fillColor: "#ff4d5a",
        fillOpacity: 0.12,
        weight: 2,
        dashArray: "6 6"
    }
);

originCircle.bindPopup(
    "<b>🔴 Probable Spill Origin</b><br>" +
    "Estimated from drift reconstruction"
);


/* =========================================
   4. DRIFT PATH
   ========================================= */

const driftPath = [
    [15.20, 73.70],
    [15.26, 73.73],
    [15.32, 73.76],
    [15.38, 73.79],
    [15.43, 73.82]
];

const driftLine = L.polyline(
    driftPath,
    {
        color: "#f2d34f",
        weight: 3,
        dashArray: "8 7"
    }
).addTo(map);

driftLine.bindPopup(
    "<b>🌊 Reconstructed Drift Path</b>"
);


/* =========================================
   5. VESSEL DATA
   ========================================= */

const vessels = [

    {
        name: "Vessel Alpha",
        lat: 15.24,
        lon: 73.72,
        distance: "6.2 km",
        timeMatch: 96,
        routeMatch: 94
    },

    {
        name: "Vessel Bravo",
        lat: 15.30,
        lon: 73.76,
        distance: "13.7 km",
        timeMatch: 84,
        routeMatch: 86
    },

    {
        name: "Vessel Charlie",
        lat: 15.50,
        lon: 73.90,
        distance: "31.4 km",
        timeMatch: 58,
        routeMatch: 71
    },

    {
        name: "Vessel Delta",
        lat: 15.35,
        lon: 73.65,
        distance: "28.9 km",
        timeMatch: 62,
        routeMatch: 55
    }

];


/* =========================================
   6. ADD VESSELS TO MAP
   ========================================= */

const vesselMarkers = [];

vessels.forEach(function (vessel) {

    const marker = L.circleMarker(
        [vessel.lat, vessel.lon],
        {
            radius: 7,
            color: "#48aee8",
            fillColor: "#48aee8",
            fillOpacity: 0.85,
            weight: 2
        }
    ).addTo(map);

    marker.bindPopup(
        "<b>🚢 " + vessel.name + "</b><br>" +
        "Correlation: Calculating..."
    );

    vesselMarkers.push(marker);

});


/* =========================================
   7. IMAGE PREVIEW
   ========================================= */

imageInput.addEventListener("change", function () {

    const file = this.files[0];

    if (!file) {
        imagePreview.innerHTML = "";
        return;
    }

    const reader = new FileReader();

    reader.onload = function (event) {

        imagePreview.innerHTML = `
            <img
                src="${event.target.result}"
                alt="Uploaded satellite image"
            >
        `;

    };

    reader.readAsDataURL(file);

});


/* =========================================
   8. SATELLITE ANALYSIS + AI
   ========================================= */

async function analyzeImage() {

    const file =
        document.getElementById("imageInput").files[0];

    const result =
        document.getElementById("analysisResult");


    if (!file) {

        result.innerHTML =
            "⚠️ Please select a satellite image first.";

        return;
    }


    result.innerHTML =
        "🔄 Sending satellite image for AI analysis...";


    try {

        const formData = new FormData();

        formData.append("image", file);


        const response = await fetch(
            "http://127.0.0.1:5000/analyze",
            {
                method: "POST",
                body: formData
            }
        );


        const data = await response.json();


        if (!data.success) {

            result.innerHTML =
                "❌ " + data.message;

            return;
        }


        /*
        ========================================
        AI RESULT VALUES
        ========================================
        */

        const aiPrediction =
            data.ai_prediction || "AI analysis unavailable";

        const aiConfidence =
            data.ai_confidence !== undefined
                ? data.ai_confidence
                : "N/A";


        /*
        ========================================
        DISPLAY COMPLETE RESULT
        ========================================
        */

        result.innerHTML = `

            <div class="success">

                🛢️ <b>Potential Oil Slick Detected</b>

                <br><br>

                Detection Confidence:
                <b>${data.confidence}%</b>

                <br>

                Estimated Area:
                <b>${data.area} km²</b>

                <br>

                Location:
                <b>${data.location}</b>


                <br><br>

                <hr
                    style="
                    margin:15px 0;
                    border-color:rgba(255,255,255,0.25);
                    "
                >


                <strong>
                    🤖 AI Image Analysis
                </strong>


                <br><br>


                AI Prediction:
                <b>${aiPrediction}</b>


                <br>

                AI Confidence:
                <b>${aiConfidence}%</b>


                <br><br>


                <small>
                    AI-assisted image analysis
                </small>

            </div>

        `;


        /*
        ========================================
        UPDATE DASHBOARD SLICK INFORMATION
        ========================================
        */

        document.getElementById(
            "slickInfo"
        ).innerHTML =

            `${data.area} km²<br>
             <small>
                 Confidence: ${data.confidence}%
             </small>`;


        /*
        ========================================
        OPTIONAL CONSOLE INFORMATION
        ========================================
        */

        console.log(
            "AI Prediction:",
            aiPrediction
        );

        console.log(
            "AI Confidence:",
            aiConfidence
        );


    }

    catch (error) {

        console.error(error);

        result.innerHTML = `

            <div class="empty-state">

                ❌ Unable to connect to
                MarineGuard analysis server.

                <br><br>

                Make sure the Python server is running.

            </div>

        `;

    }

}


/* =========================================
   9. RECONSTRUCT ORIGIN
   ========================================= */

function reconstructOrigin() {

    const originInfo =
        document.getElementById("originInfo");

    const status =
        document.getElementById("incidentStatus");


    originInfo.innerHTML =
        "🔄 Calculating...";

    status.innerHTML =
        "● Reconstructing probable spill origin";


    setTimeout(function () {

        if (originMarker) {

            map.removeLayer(originMarker);

        }


        originMarker = L.marker(
            originCoordinates
        ).addTo(map);


        originMarker.bindPopup(

            "<b>🔴 Probable Spill Origin</b><br>" +
            "15.20°N, 73.70°E"

        ).openPopup();


        originCircle.addTo(map);


        map.flyTo(
            originCoordinates,
            10,
            {
                duration: 1.5
            }
        );


        originInfo.innerHTML =
            "15.20°N, 73.70°E";


        status.innerHTML =
            "● Probable origin reconstructed";


    }, 1300);

}


/* =========================================
   10. VESSEL ANALYSIS
   ========================================= */

function analyzeVessels() {

    const vesselInfo =
        document.getElementById("vesselInfo");

    const results =
        document.getElementById("vesselResults");


    vesselInfo.innerHTML =
        "🔄 Analyzing...";


    results.innerHTML = `

        <div class="empty-state">

            🔄 Comparing vessel trajectories...

        </div>

    `;


    setTimeout(function () {


        vesselInfo.innerHTML =
            "17 vessels analyzed";


        results.innerHTML = "";


        vessels.forEach(function (vessel) {

            const distanceKm =
                parseFloat(vessel.distance);


            const distanceScore =
                Math.max(
                    0,
                    100 - (distanceKm * 2)
                );


            vessel.score = Math.round(

                (distanceScore * 0.4) +

                (vessel.timeMatch * 0.3) +

                (vessel.routeMatch * 0.3)

            );

        });


        vessels.sort(function (a, b) {

            return b.score - a.score;

        });


        vessels.forEach(function (vessel, index) {


            let rank;


            if (index === 0) {

                rank = "🥇";

            }

            else if (index === 1) {

                rank = "🥈";

            }

            else if (index === 2) {

                rank = "🥉";

            }

            else {

                rank = "🚢";

            }


            const row =
                document.createElement("div");


            row.className =
                "vessel-row";


            row.innerHTML = `

                <div class="vessel-rank">

                    ${rank}

                </div>


                <div>

                    <div class="vessel-name">

                        ${vessel.name}

                    </div>


                    <div class="vessel-details">

                        <span>

                            Distance:
                            ${vessel.distance}

                        </span>


                        <span>

                            Time Match:
                            ${vessel.timeMatch}%

                        </span>


                        <span>

                            Route Match:
                            ${vessel.routeMatch}%

                        </span>

                    </div>

                </div>


                <div class="vessel-score">

                    <strong>

                        ${vessel.score}%

                    </strong>


                    <div class="score-bar">

                        <div
                            class="score-fill"
                            style="width:${vessel.score}%"
                        ></div>

                    </div>

                </div>

            `;


            results.appendChild(row);


        });


        /*
        Update vessel map popups
        */

        vessels.forEach(function (vessel) {

            const markerIndex =
                vessels.indexOf(vessel);

            if (vesselMarkers[markerIndex]) {

                vesselMarkers[
                    markerIndex
                ].bindPopup(

                    "<b>🚢 " +
                    vessel.name +
                    "</b><br>" +

                    "Correlation: " +
                    vessel.score +
                    "%"

                );

            }

        });


        document.getElementById(
            "incidentStatus"
        ).innerHTML =
            "● Vessel correlation analysis complete";


    }, 1500);

}


/* =========================================
   11. INCIDENT RECONSTRUCTION
   ========================================= */

function playIncident() {

    const status =
        document.getElementById("incidentStatus");


    status.innerHTML =
        "● Playing incident reconstruction";


    let step = 0;


    const animation =
        setInterval(function () {


            if (step >= driftPath.length) {

                clearInterval(animation);


                status.innerHTML =
                    "● Incident reconstruction complete";

                return;

            }


            map.flyTo(

                driftPath[step],

                10,

                {
                    duration: 1
                }

            );


            step++;


        }, 1300);

}


/* =========================================
   12. GENERATE REPORT
   ========================================= */

function generateReport() {

    const report =
        document.getElementById("report");


    report.innerHTML = `

        <div class="report-section">

            <h3>

                🌊 MARINEGUARD INCIDENT REPORT

            </h3>


            <p>

                <b>Investigation type:</b>

                Maritime oil spill
                intelligence analysis

            </p>

        </div>


        <div class="report-section">

            <b>🛢️ Satellite Findings</b>


            <p>

                Potential oil slick detected
                with an estimated affected area
                of <b>12.4 km²</b>.

            </p>


            <p>

                Detection confidence:
                <b>93%</b>

            </p>

        </div>


        <div class="report-section">

            <b>🔴 Probable Origin</b>


            <p>

                Estimated coordinates:

                <b>15.20°N, 73.70°E</b>

            </p>


            <p>

                Origin estimation is based on
                simulated reverse-drift analysis.

            </p>

        </div>


        <div class="report-section">

            <b>⏱️ Estimated Time Window</b>


            <p>

                10:00 – 12:00

            </p>

        </div>


        <div class="report-section">

            <b>🚢 Vessel Correlation</b>


            <p>

                Highest calculated correlation:

                <b>
                    ${vessels[0].name}
                    —
                    ${vessels[0].score || 0}%
                </b>

            </p>


            <p>

                Supporting factors:

            </p>


            <p>

                ✓ Spatial proximity
                <br>

                ✓ Temporal overlap
                <br>

                ✓ Trajectory similarity

            </p>

        </div>


        <div class="report-section">

            <b>🤖 AI Analysis</b>


            <p>

                AI-assisted satellite image
                analysis was performed.

            </p>


            <p>

                AI result is displayed in the
                Satellite Intelligence module.

            </p>

        </div>


        <div class="report-section">

            <b>⚠️ Investigation Disclaimer</b>


            <p>

                This is a prototype using simulated
                investigation data.

                Correlation scores do not establish
                responsibility or legal liability.

            </p>

        </div>

    `;

}


/* =========================================
   13. INITIAL STATUS
   ========================================= */

document.getElementById(
    "incidentStatus"
).innerHTML =
    "● Ready for investigation";