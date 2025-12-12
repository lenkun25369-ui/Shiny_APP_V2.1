from shiny import App, ui, render, reactive
from urllib.parse import parse_qs
import requests
import json

# -------------------------------
# UI
# -------------------------------
app_ui = ui.page_fluid(

    ui.h2("Predict In-hospital Mortality by CHARM score in Patients with Suspected Sepsis"),

    # ⭐ 新增：顯示 FHIR 資料（不改動原本 UI）
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
            )
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
# Prediction function（保持完全不動）
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

    if pred_data["chills"] == "No":
        pred_data["chills"] = 0
    else:
        pred_data["chills"] = 1

    if pred_data["hypothermia"] == "No":
        pred_data["hypothermia"] = 0
    else:
        pred_data["hypothermia"] = 1

    if pred_data["anemia"] == "No":
        pred_data["anemia"] = 0
    else:
        pred_data["anemia"] = 1

    if pred_data["rdw"] == "No":
        pred_data["rdw"] = 0
    else:
        pred_data["rdw"] = 1

    if pred_data["malignancy"] == "No":
        pred_data["malignancy"] = 0
    else:
        pred_data["malignancy"] = 1

    score = (
        pred_data["chills"]
        + pred_data["hypothermia"]
        + pred_data["anemia"]
        + pred_data["rdw"]
        + pred_data["malignancy"]
    )

    if score == 0:
        mortality_prob = 0.36
    if score == 1:
        mortality_prob = 1.89
    if score == 2:
        mortality_prob = 5.79
    if score == 3:
        mortality_prob = 12.97
    if score == 4:
        mortality_prob = 23.58
    if score == 5:
        mortality_prob = 34.15

    return mortality_prob


# -------------------------------
# Server
# -------------------------------
def server(input, output, session):

    # -----------------------------------------
    # ⭐ Step 1：讀取 Query String（Shiny 0.0.1 唯一可靠方法）
    # -----------------------------------------
    raw_qs = session._process.scope.get("query_string", b"").decode()
    qp = {k: v[0] for k, v in parse_qs(raw_qs).items()}

    print("=== QUERY PARAMS RECEIVED BY SHINY ===")
    print(qp)
    print("======================================")

    token = qp.get("token")
    pid   = qp.get("pid")
    fhir  = qp.get("fhir")

    # -----------------------------------------
    # ⭐ Step 2：FHIR Patient 呼叫
    # -----------------------------------------
    @reactive.Calc
    def patient_data():
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
    # ⭐ Step 3：顯示 FHIR 結果（新增）
    # -----------------------------------------
    @output
    @render.text
    def patient_info():
        data = patient_data()
        return json.dumps(data, indent=2)

    # -----------------------------------------
    # ⭐ 原本 CHARM prediction — 不做任何改動
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
