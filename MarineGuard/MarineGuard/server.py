from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
from transformers import pipeline
import numpy as np


# =========================================================
# MARINEGUARD - AI ASSISTED OIL SPILL ANALYSIS
# =========================================================

app = Flask(__name__)
CORS(app)


# =========================================================
# LOAD AI MODEL
# =========================================================

print("Loading AI model...")

ai_model = pipeline(
    "image-classification",
    model="google/vit-base-patch16-224"
)

print("AI model loaded successfully!")


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return "MarineGuard backend is running!"


# =========================================================
# IMAGE ANALYSIS
# =========================================================

@app.route("/analyze", methods=["POST"])
def analyze():

    # -----------------------------------------------------
    # CHECK IMAGE
    # -----------------------------------------------------

    if "image" not in request.files:
        return jsonify({
            "success": False,
            "message": "No image uploaded"
        }), 400

    image_file = request.files["image"]

    if image_file.filename == "":
        return jsonify({
            "success": False,
            "message": "No image selected"
        }), 400

    try:

        # -------------------------------------------------
        # OPEN IMAGE
        # -------------------------------------------------

        original_image = Image.open(
            image_file
        ).convert("RGB")

        width, height = original_image.size

        print("\n--------------------------------")
        print("MarineGuard image analysis")
        print("Image:", image_file.filename)
        print("Size:", width, "x", height)
        print("--------------------------------")


        # =================================================
        # GENERIC AI VISION ANALYSIS
        # =================================================

        ai_predictions = ai_model(
            original_image
        )

        top_prediction = ai_predictions[0]

        vision_prediction = top_prediction["label"]

        vision_confidence = round(
            top_prediction["score"] * 100,
            2
        )

        print(
            "Vision model:",
            vision_prediction
        )

        print(
            "Vision confidence:",
            vision_confidence
        )


        # =================================================
        # IMAGE PROCESSING
        # =================================================

        image = original_image.copy()

        image.thumbnail(
            (800, 800)
        )

        img_array = np.array(
            image
        ).astype(float)


        # =================================================
        # RGB CHANNELS
        # =================================================

        r = img_array[:, :, 0]
        g = img_array[:, :, 1]
        b = img_array[:, :, 2]


        # =================================================
        # BRIGHTNESS
        # =================================================

        brightness = (
            r + g + b
        ) / 3

        average_brightness = float(
            np.mean(brightness)
        )


        # =================================================
        # DARK PIXELS
        # =================================================

        dark_mask = (
            brightness < 100
        )

        very_dark_mask = (
            brightness < 70
        )

        dark_percentage = (
            np.mean(dark_mask) * 100
        )

        very_dark_percentage = (
            np.mean(very_dark_mask) * 100
        )


        # =================================================
        # IMAGE CONTRAST / TEXTURE
        # =================================================

        brightness_std = float(
            np.std(brightness)
        )

        texture_score = min(
            100,
            brightness_std * 2
        )


        # =================================================
        # COLOR VARIATION
        # =================================================

        color_range = (
            np.maximum(
                r,
                np.maximum(g, b)
            )
            -
            np.minimum(
                r,
                np.minimum(g, b)
            )
        )

        average_color_range = float(
            np.mean(color_range)
        )


        # =================================================
        # DARK REGION SCORE
        # =================================================

        dark_score = min(
            100,
            dark_percentage * 1.8
        )


        # =================================================
        # VERY DARK REGION SCORE
        # =================================================

        very_dark_score = min(
            100,
            very_dark_percentage * 2.5
        )


        # =================================================
        # TEXTURE SCORE
        # =================================================

        texture_score = min(
            100,
            texture_score
        )


        # =================================================
        # PROTOTYPE SLICK SCORE
        # =================================================

        slick_score = (

            dark_score * 0.50

            +

            very_dark_score * 0.25

            +

            texture_score * 0.15

            +

            min(
                100,
                average_color_range
            ) * 0.10

        )

        slick_score = round(
            max(
                0,
                min(
                    100,
                    slick_score
                )
            ),
            2
        )


        # =================================================
        # OIL SLICK DETECTION
        # =================================================

        if slick_score >= 55:

            slick_detected = True

        else:

            slick_detected = False


        # =================================================
        # DETECTION CONFIDENCE
        # =================================================

        if slick_detected:

            confidence = round(
                min(
                    98,
                    max(
                        55,
                        slick_score
                    )
                )
            )

        else:

            confidence = round(
                max(
                    10,
                    100 - slick_score
                )
            )


        # =================================================
        # ESTIMATED AREA
        # =================================================

        if slick_detected:

            area = round(
                max(
                    0.5,
                    dark_percentage * 0.20
                ),
                2
            )

        else:

            area = 0


        # =================================================
        # MARINEGUARD AI RESULT
        # =================================================

        if slick_detected:

            marineguard_prediction = (
                "Potential Oil Spill Detected"
            )

        else:

            marineguard_prediction = (
                "No Significant Oil Spill Detected"
            )


        # =================================================
        # ANALYSIS LEVEL
        # =================================================

        if confidence >= 85:

            analysis_level = "HIGH"

        elif confidence >= 65:

            analysis_level = "MEDIUM"

        else:

            analysis_level = "LOW"


        # =================================================
        # COMBINED PROTOTYPE SCORE
        # =================================================

        combined_score = round(
            (
                slick_score * 0.70
                +
                vision_confidence * 0.30
            ),
            2
        )


        # =================================================
        # PROTOTYPE LOCATION
        # =================================================

        # This is a demo location.
        # Actual satellite geolocation requires
        # georeferenced Sentinel-1/Sentinel-2 data.

        location = "15.42°N, 73.81°E"


        # =================================================
        # FINAL RESULT
        # =================================================

        result = {

            "success": True,


            # ---------------------------------------------
            # MARINEGUARD AI RESULT
            # ---------------------------------------------

            "ai_enabled": True,

            "ai_prediction":
                marineguard_prediction,

            "ai_confidence":
                confidence,

            "ai_model_type":
                "AI-Assisted Oil Spill Prototype",


            # ---------------------------------------------
            # ACTUAL GENERIC VISION MODEL RESULT
            # ---------------------------------------------

            "vision_prediction":
                vision_prediction,

            "vision_confidence":
                vision_confidence,


            # ---------------------------------------------
            # OIL SLICK ANALYSIS
            # ---------------------------------------------

            "slick_detected":
                slick_detected,

            "confidence":
                confidence,

            "slick_score":
                slick_score,

            "combined_score":
                combined_score,


            # ---------------------------------------------
            # AREA
            # ---------------------------------------------

            "area":
                area,

            "area_unit":
                "km²",

            "area_type":
                "Prototype estimate",


            # ---------------------------------------------
            # LOCATION
            # ---------------------------------------------

            "location":
                location,

            "location_type":
                "Demo location",


            # ---------------------------------------------
            # IMAGE INFORMATION
            # ---------------------------------------------

            "image_width":
                width,

            "image_height":
                height,


            # ---------------------------------------------
            # IMAGE STATISTICS
            # ---------------------------------------------

            "brightness":
                round(
                    average_brightness,
                    2
                ),

            "dark_percentage":
                round(
                    dark_percentage,
                    2
                ),

            "very_dark_percentage":
                round(
                    very_dark_percentage,
                    2
                ),

            "brightness_variation":
                round(
                    brightness_std,
                    2
                ),

            "color_variation":
                round(
                    average_color_range,
                    2
                ),


            # ---------------------------------------------
            # ANALYSIS LEVEL
            # ---------------------------------------------

            "analysis_level":
                analysis_level,


            # ---------------------------------------------
            # MESSAGE
            # ---------------------------------------------

            "message":
                "MarineGuard AI-assisted prototype analysis completed."

        }


        # =================================================
        # TERMINAL OUTPUT
        # =================================================

        print("\n========== MARINEGUARD RESULT ==========")

        print(
            "Oil spill detected:",
            slick_detected
        )

        print(
            "Slick score:",
            slick_score
        )

        print(
            "Confidence:",
            confidence,
            "%"
        )

        print(
            "Estimated area:",
            area,
            "km²"
        )

        print(
            "Analysis level:",
            analysis_level
        )

        print(
            "MarineGuard prediction:",
            marineguard_prediction
        )

        print(
            "Vision model prediction:",
            vision_prediction
        )

        print(
            "Vision confidence:",
            vision_confidence,
            "%"
        )

        print("========================================\n")


        return jsonify(result)


    # =====================================================
    # ERROR HANDLING
    # =====================================================

    except Exception as error:

        print(
            "\nMARINEGUARD ERROR:",
            error
        )

        return jsonify({

            "success": False,

            "message":
                str(error)

        }), 500


# =========================================================
# START FLASK SERVER
# =========================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )