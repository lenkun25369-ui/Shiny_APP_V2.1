from shiny import App, ui, render, reactive
import requests
import json

# -------------------------------
# UI
# -------------------------------
app_ui = ui.page_fluid(

    # -----------------------------------------------
    # ⭐ 方法 C：讀取 URL #hash，將 token/pid/fhir 傳入 Shiny input
    # -----------------------------------------------
    ui.tags.script("""
    (function () {
      const hash = window.location.hash.substring(1);
      const params = new URLSearchParams(hash);

      const token = params.get("token");
      const pid   = params.get("pid");
      const fhir  = params.get("fhir");

      function sendToShiny() {
        if (window.Shiny && Shiny.setInputValue) {
          Shiny.setInputValue("token", token);
          Shiny.setInputValue("pid", pid);
          Shiny.setInputValue("fhir", fhir);
          console.log("✔ Sent to Shiny:", { token, pid, fhir });
        } else {
          setTimeout(sendToShiny, 300);
        }
      }

      sendToShiny();
    })();
    """),

    # Hidden inputs so Shiny can receive values
    ui.tags.style("""
    #token, #pid, #fhir { display: none !important; }
    """),
    ui.input_text("token", ""),
    ui.input_text("pid", ""),
    ui.input_text("fhir", ""),

    ui.h2("Predict In-hospital Mortality by CHARM score in Patients with Suspected Sepsis"),

    ui.h4("FHIR Patient Data"),
    ui.tags.pre(ui.output_text("patient_info")),

    ui.layout_sidebar(

        ui.sidebar(
            ui.p("Please fill the below details"),

            ui.input_radio_buttons(
                "chills",
                "noChills (absence of Chills)",
                choices={"No": "No", "Yes": "Yes"},
                selected="No",
                inline=True
            ),

            ui.input_radio_buttons(
                "hypothermia",
                "Hypothermia (temperature < 36 °C)",
                choices={"No": "No", "Yes": "Yes"},
                selected="No",
                inline=True
            ),

            ui.input_radio_buttons(
                "anemia",
                "Anemia (RBC < 4M/uL)",
                choices={"No": "No", "Yes": "Yes"},
                selected="No",
                inline=True
            ),

            ui.input_radio_buttons(
                "rdw",
                "RDW > 14.5%",
                choices={"No": "No", "Yes": "Yes"},
                selected="No",
                inline=True
            ),

            ui.input_radio_buttons(
                "malignancy",
                "Malignancy (history)",
                choices={"No": "No", "Yes": "Yes"},
                selected="No",
                inline=True
            ),
        ),

        ui.div(
            ui.h3("Predicted in-hospital mortality (%):"),
            ui.h4(ui.output_text("prob")),
            ui.help_text(
                ui.a(
                    "Click here to see the reference",
                    href="https://www.ncbi.nlm.nih.gov/pubmed/?term=27832977"
                )
            ),
            ui.help_text("Produced by Dr.Chin-Chieh Wu")
        )
    )
)

# -------------------------------
# Prediction function
# -------------------------------
def pred_tit(chills, hypothermia, anemia, rdw, malignancy):

    pred_data = {
        "chills": 0 if chills == "No" else 1,
        "hypothermia": 0 if hypothermia == "No" else 1,
        "anemia": 0 if anemia == "No" else 1,
        "rdw": 0 if
