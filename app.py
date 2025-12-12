from shiny import App, ui, render, reactive
import requests
import json

# -------------------------------
# UI
# -------------------------------
app_ui = ui.page_fluid(

    # ⭐ 新增：三個 hidden input（JS 會把 token/pid/fhir 塞進來）
    ui.input_text("token", "", value="", hidden=True),
    ui.input_text("pid", "", value="", hidden=True),
    ui.input_text("fhir", "", value="", hidden=True),

    ui.h2("Predict In-hospital Mortality by CHARM score in Patients with Suspected Sepsis"),

    # ⭐ 顯示 FHIR Patient 信息
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
                "Hypothermia( temperature < 36 degrees Celsius)",
                choices={"No": "No", "Yes": "Yes"},
                selected="No",
                inline=True
            ),

            ui.input_radio_buttons(
                "anemia",
                "Anemia (RBC counts < 4 million per uL)",
                choices={"No": "No", "Yes": "Yes"},
                selected="No",
                inline=True
            ),

            ui.input_radio_buttons(
                "rdw",
                "RDW (RDW > 14.5%)",
                choices={"No": "No", "Yes": "Yes"},
                selected="No",
                inline=True
            ),

            ui.input_radio_buttons(
                "malignancy",
                "Malignancy (History of malignancy)",
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
# Prediction function（完全不動）
# -------------------------------
def pred_tit(chills, hypothermia, anemia, rdw, malignancy):

    inputdata = [chills, hypothermia, anemia, rdw, malignancy]

    pred_data = {
        "chills": inputdata[0],
        "hypothermia": inputdata[1],
        "anemia": inputdata[2],
        "rdw": inputdata[3],
        "malignancy": inputdata[4],
    }

    for key in pred_data:
        pred_data[key] = 0 if pred_data[key] == "No" else 1

    score = sum(pred_data.values())

    table = {
        0: 0.36,
        1: 1.89,
        2: 5.79,
        3: 12.97,
        4: 23.58,
        5: 34.15
    }
    return table[score]

# -------------------------------
# Server
# -------------------------------
def server(input, output, session):

    # -----------------------------------------
    # ⭐ 新方法：直接從 JS 傳進來的 input 讀 token/pid/fhir
    # -----------------------------------------
    @reactive.Calc
    def patient_data():

        token = input.token()
        pid   = input.pid()
        fhir  = input.fhir()

        if not (token and pid and fhir):
            return {"error": "Missing token / pid / fhir"}

        url = f"{fhir}/Patient/{pid}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/fhir+json"
        }

        try:
            res = requests.get(url, headers=headers)
            return res.json()
        except Exception as e:
            return {"error": f"FHIR request failed: {e}"}

    # -----------------------------------------
    # ⭐ 顯示 FHIR 結果
    # -----------------------------------------
    @output
    @render.text
    def patient_info():
        return json.dumps(patient_data(), indent=2)

    # -----------------------------------------
    # ⭐ 原本 CHARM prediction — 保持完全不動
    # -----------------------------------------
    @output
    @render.text
    def prob():
        return str(
            pred_tit(
                input.chills(),
                input.hypothermia(),
                input.anemia(),
                input.rdw(),
                input.malignancy(),
            )
        )

# -------------------------------
# App
# -------------------------------
app = App(app_ui, server)
