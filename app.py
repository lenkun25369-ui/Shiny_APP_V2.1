from shiny import App, ui, render, reactive
import requests
import json

# -------------------------------
# UI
# -------------------------------
app_ui = ui.page_fluid(

    # -----------------------------------------------
    # ⭐ 從 URL #hash 讀取 token / pid / fhir / obs
    # -----------------------------------------------
    ui.tags.script("""
    (function () {
      const hash = window.location.hash.substring(1);
      const params = new URLSearchParams(hash);

      const token = params.get("token");
      const pid   = params.get("pid");
      const fhir  = params.get("fhir");
      const obs   = params.get("obs");

      function sendToShiny() {
        if (window.Shiny && Shiny.setInputValue) {
          Shiny.setInputValue("token", token);
          Shiny.setInputValue("pid", pid);
          Shiny.setInputValue("fhir", fhir);
          Shiny.setInputValue("obs", obs);
          console.log("✔ Sent to Shiny:", { token, pid, fhir, obs });
        } else {
          setTimeout(sendToShiny, 300);
        }
      }
      sendToShiny();
    })();
    """),

    ui.tags.style("""
    #token, #pid, #fhir, #obs { display: none !important; }
    """),
    ui.input_text("token", ""),
    ui.input_text("pid", ""),
    ui.input_text("fhir", ""),
    ui.input_text("obs", ""),

    ui.h2("Predict In-hospital Mortality by CHARM score in Patients with Suspected Sepsis"),

    ui.h4("FHIR Patient Data"),
    ui.tags.pre(ui.output_text("patient_info")),

    ui.layout_sidebar(

        ui.sidebar(
            ui.p("Please fill the below details"),

            ui.input_radio_buttons("chills", "noChills (absence of Chills)",
                                   choices={"No": "No", "Yes": "Yes"}, selected="No", inline=True),

            ui.input_radio_buttons("hypothermia", "Hypothermia (temperature < 36 °C)",
                                   choices={"No": "No", "Yes": "Yes"}, selected="No", inline=True),

            ui.input_radio_buttons("anemia", "Anemia (RBC < 4M/uL)",
                                   choices={"No": "No", "Yes": "Yes"}, selected="No", inline=True),

            ui.input_radio_buttons("rdw", "RDW > 14.5%",
                                   choices={"No": "No", "Yes": "Yes"}, selected="No", inline=True),

            ui.input_radio_buttons("malignancy", "Malignancy (history)",
                                   choices={"No": "No", "Yes": "Yes"}, selected="No", inline=True),
        ),

        ui.div(
            ui.h3("Predicted in-hospital mortality (%):"),
            ui.h4(ui.output_text("prob")),
            ui.help_text(
                ui.a("Click here to see the reference",
                     href="https://www.ncbi.nlm.nih.gov/pubmed/?term=27832977")
            ),
            ui.help_text("Produced by Dr. Chin-Chieh Wu")
        )
    )
)

# -------------------------------
# Prediction table（不動）
# -------------------------------
CHARM_TABLE = {
    0: 0.36,
    1: 1.89,
    2: 5.79,
    3: 12.97,
    4: 23.58,
    5: 34.15
}

# -------------------------------
# Server
# -------------------------------
def server(input, output, session):

    # -----------------------------------------
    # 取得 Patient + Observation
    # -----------------------------------------
    @reactive.Calc
    def fhir_data():

        token = input.token()
        pid   = input.pid()
        fhir  = input.fhir()
        obs   = input.obs()

        if not (token and pid and fhir):
            return {"error": "Missing token / pid / fhir"}

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/fhir+json"
        }

        result = {}

        # Patient
        result["patient"] = requests.get(
            f"{fhir}/Patient/{pid}",
            headers=headers,
            verify=False
        ).json()

        # Observation
        if obs:
            result["observation"] = requests.get(
                obs,
                headers=headers,
                verify=False
            ).json()

        return result

    # -----------------------------------------
    # 顯示 FHIR JSON
    # -----------------------------------------
    @output
    @render.text
    def patient_info():
        return json.dumps(fhir_data(), indent=2)

    # -----------------------------------------
    # ⭐ 自動計算 CHARM 預測值
    # -----------------------------------------
    @output
    @render.text
    def prob():

        data = fhir_data()
        obs = data.get("observation")

        # 若有 Observation → 自動計算
        if obs and "component" in obs:

            chills = hypothermia = anemia = rdw = malignancy = 0

            for c in obs["component"]:
                code = c.get("code", {}).get("coding", [{}])[0].get("code")

                if code == "chills":
                    chills = c.get("valueInteger", 0)

                elif code == "malignancy":
                    malignancy = c.get("valueInteger", 0)

                elif code == "789-8":  # RBC
                    val = c.get("valueQuantity", {}).get("value")
                    if val is not None and val < 4.0:
                        anemia = 1

                elif code == "788-0":  # RDW
                    val = c.get("valueQuantity", {}).get("value")
                    if val is not None and val > 14.5:
                        rdw = 1

                elif code == "8310-5":  # Temperature
                    val = c.get("valueQuantity", {}).get("value")
                    if val is not None and val < 36:
                        hypothermia = 1

            score = chills + hypothermia + anemia + rdw + malignancy
            return str(CHARM_TABLE.get(score, "NA"))

        # fallback（理論上不會用到）
        return "NA"

# -------------------------------
# App
# -------------------------------
app = App(app_ui, server)
