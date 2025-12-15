from shiny import App, ui, render, reactive
import requests
import json

# -------------------------------
# UI
# -------------------------------
app_ui = ui.page_fluid(

    # -----------------------------------------------
    # 從 URL #hash 讀取 token / pid / fhir / obs
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

    ui.tags.details(
        ui.tags.summary("FHIR Patient & Observation Data (click to expand)"),
        ui.tags.pre(ui.output_text("patient_info"))
    ),

    ui.layout_sidebar(

        ui.sidebar(
            ui.p("Please fill the below details (auto-populated from FHIR, editable)"),

            ui.input_radio_buttons("chills", "noChills (absence of Chills)",
                                   choices={"No": "No", "Yes": "Yes"},
                                   selected="No", inline=True),

            ui.input_radio_buttons("hypothermia", "Hypothermia (temperature < 36 °C)",
                                   choices={"No": "No", "Yes": "Yes"},
                                   selected="No", inline=True),

            ui.input_radio_buttons("anemia", "Anemia (RBC < 4M/uL)",
                                   choices={"No": "No", "Yes": "Yes"},
                                   selected="No", inline=True),

            ui.input_radio_buttons("rdw", "RDW > 14.5%",
                                   choices={"No": "No", "Yes": "Yes"},
                                   selected="No", inline=True),

            ui.input_radio_buttons("malignancy", "Malignancy (history)",
                                   choices={"No": "No", "Yes": "Yes"},
                                   selected="No", inline=True),
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
# CHARM risk table
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
    # 讀取 Patient + Observation
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

        result["patient"] = requests.get(
            f"{fhir}/Patient/{pid}",
            headers=headers,
            verify=False
        ).json()

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
    # ⭐ 用 FHIR Observation 設定「預設值」
    # -----------------------------------------
    @reactive.Effect
    def init_ui_from_fhir():

        data = fhir_data()
        obs = data.get("observation")

        if not obs or "component" not in obs:
            return

        ui_vals = {
            "chills": "No",
            "hypothermia": "No",
            "anemia": "No",
            "rdw": "No",
            "malignancy": "No",
        }

        for c in obs["component"]:
            code = c.get("code", {}).get("coding", [{}])[0].get("code")

            if code == "chills" and c.get("valueInteger", 0) == 1:
                ui_vals["chills"] = "Yes"

            elif code == "malignancy" and c.get("valueInteger", 0) == 1:
                ui_vals["malignancy"] = "Yes"

            elif code == "789-8":
                if c.get("valueQuantity", {}).get("value", 999) < 4.0:
                    ui_vals["anemia"] = "Yes"

            elif code == "788-0":
                if c.get("valueQuantity", {}).get("value", 0) > 14.5:
                    ui_vals["rdw"] = "Yes"

            elif code == "8310-5":
                if c.get("valueQuantity", {}).get("value", 99) < 36:
                    ui_vals["hypothermia"] = "Yes"

        for k, v in ui_vals.items():
            session.send_input_message(k, {"value": v})

    # -----------------------------------------
    # ⭐ 永遠用「目前 radio buttons」計算
    # -----------------------------------------

    def prob():
    
        data = fhir_data()
    
        # ⭐ 尚未讀到 Patient / Observation → 顯示 Calculating
        if not data or "error" in data:
            return "Calculating..."
    
        # ⭐ Observation 尚未 ready（保險）
        if "observation" not in data:
            return "Calculating..."
    
        # ⭐ radio buttons 尚未同步完成（保險）
        if not all([
            input.chills(),
            input.hypothermia(),
            input.anemia(),
            input.rdw(),
            input.malignancy()
        ]):
            return "Calculating..."
    
        # ⭐ 使用「目前 UI 狀態」計算（FHIR auto-fill + user override）
        score = sum([
            1 if input.chills() == "Yes" else 0,
            1 if input.hypothermia() == "Yes" else 0,
            1 if input.anemia() == "Yes" else 0,
            1 if input.rdw() == "Yes" else 0,
            1 if input.malignancy() == "Yes" else 0,
        ])
    
        return str(CHARM_TABLE.get(score, "NA"))

# -------------------------------
# App
# -------------------------------
app = App(app_ui, server)
