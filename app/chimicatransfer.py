"""
Servizio To-Gru (inventario per traslocco)
"""

from flask import (
    Flask,
    request,
    render_template,
    redirect,
    url_for,
    flash,
    send_file,
    session,
    send_from_directory
)

from functools import wraps
from io import BytesIO
from markupsafe import Markup
from requests_oauthlib import OAuth2Session
from sqlalchemy import bindparam, create_engine, text
import pandas as pd
import json
import os
import datetime
from pathlib import Path
import subprocess
# from werkzeug.utils import secure_filename

__version__ = "2025-09-26 09:46"

APP_ROOT = "/chimicatransfer"

app = Flask(__name__, static_url_path="/chimicatransfer/static", static_folder="static")
app.secret_key = "sldjhalsdasd2435"  # needed for flash messages


DATABASE_URL = "postgresql://chem_togru_user:chempassword456@localhost:5432/chimicatransfer"
engine = create_engine(DATABASE_URL)

# Carico le credenziali dal JSON
try:

    app.config["UPLOAD_FOLDER"] = "static/images"


except Exception:
    raise


BOOLEAN_FIELDS = [
    # "microscopia",
    # "catena_del_freddo",
    # "alta_specialistica",
    # "da_movimentare",
    # "trasporto_in_autonomia",
    # "da_disinventariare",
    # "rosso_fase_alimentazione_privilegiata",
    # "didattica",


    # "collegamento_autonomia",
    # "difficolta",
]

# Creazione tabella
with engine.connect() as conn:
    conn.execute(
        text("""
        CREATE TABLE IF NOT EXISTS inventario (
            id SERIAL PRIMARY KEY,
            
            indirizzo TEXT,
            piano TEXT,
            codice_sipi_torino TEXT,
            nome_strumento TEXT,
            responsabile_strumento TEXT,
            dimensioni TEXT,
            peso TEXT,
            collegamento_autonomia TEXT,
            ditta_collegamento TEXT,
            delicatezza TEXT,
            difficolta TEXT,
            quale_difficolta TEXT,
            codice_sipi_grugliasco TEXT,
            note TEXT,
            categoria TEXT
        )
    """)
    )
    conn.commit()


# descrizione_inventario TEXT,
# num_inventario TEXT,
# num_inventario_ateneo TEXT,
# data_carico TEXT,
# descrizione_bene TEXT,
# codice_sipi_torino TEXT,
# codice_sipi_grugliasco TEXT,
# destinazione TEXT,
# rosso_fase_alimentazione_privilegiata TEXT,
# didattica boolean default false,
# valore_convenzionale TEXT,
# esercizio_bene_migrato TEXT,
# responsabile_strumento TEXT,
# denominazione_fornitore TEXT,
# anno_fabbricazione TEXT,
# numero_seriale TEXT,
# categoria_inventoriale TEXT,
# catalogazione_materiale_strumentazione TEXT,
# peso TEXT,
# dimensioni TEXT,
# ditta_costruttrice_fornitrice TEXT,
# note TEXT,
# deleted TIMESTAMP DEFAULT NULL



def check_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "email" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def check_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        with engine.connect() as conn:
            if "email" not in session:
                return redirect(url_for("index"))
            if session.get("admin", False):
                return f(*args, **kwargs)
            else:
                return redirect(url_for("index"))

    return decorated_function



# Visualizza home page
@app.route(APP_ROOT)
@app.route(APP_ROOT + "/")
def index():
    with engine.connect() as conn:
        n_beni = conn.execute(
            text("SELECT COUNT(*) AS n FROM inventario WHERE deleted IS NULL")
        ).scalar()
       


    return render_template(
        "index.html",
        n_records=n_beni,
        n_beni_senza_responsabile=0,
    )


# Visualizza record
@app.route(APP_ROOT + "/tutti")
def tutti():
    """
    visualizza tutti i beni dell'inventario
    """
    with engine.connect() as conn:
        result = conn.execute(
            text(
                'SELECT id AS "ID", '
               
               
                'indirizzo AS "Indirizzo", '
                'piano AS "Piano", '
                'codice_sipi_torino AS "Codice SIPI Torino", '
                'nome_strumento AS "Nome Strumentazione",'
                'responsabile_strumento AS "Responsabile", '
                'collegamento_autonomia, ditta_collegamento AS "Ditta che si occupa del collegamento", '
                'delicatezza AS "Delicatezza", '
                'difficolta, quale_difficolta AS "Quale difficoltà", '
                'codice_sipi_grugliasco AS "Simil Sipi Grugliasco", '
                'categoria AS "Categoria", '
                "(peso = '' OR peso ~ '^-?[0-9]+(\.[0-9]+)?$') AS peso_numeric, "
                "(dimensioni = '' OR dimensioni ~ '^[0-9]+x[0-9]+x[0-9]+$') AS dimensioni_ok "
                "FROM inventario WHERE deleted IS NULL "
                "ORDER BY id "
            )
        )
        records = result.fetchall()
        #print("table results", result.keys())
    return render_template(
        "tutti_record.html",
        records=records,
        query_string="tutti",
        columns=result.keys(),
    )
                # 'SELECT id AS "ID", '
                # 'quantita as "Quantità", '
                # 'descrizione_bene AS "Descrizione bene", '
                # 'responsabile_strumento AS "Responsabile Laboratorio / Ufficio", '
                # "da_movimentare, catena_del_freddo, trasporto_in_autonomia, microscopia, alta_specialistica, "
                # 'codice_sipi_torino AS "Codice SIPI Torino", '
                # 'codice_sipi_grugliasco AS "Codice SIPI Grugliasco", '
                # 'destinazione AS "Destinazione", '
                # 'note AS "Note", '
                # "(peso = '' OR peso ~ '^-?[0-9]+(\.[0-9]+)?$') AS peso_numeric, "
                # "(dimensioni = '' OR dimensioni ~ '^[0-9]+x[0-9]+x[0-9]+$') AS dimensioni_ok "
                # "FROM inventario WHERE deleted IS NULL "
                # "ORDER BY responsabile_strumento, descrizione_bene, id "
                

@app.route(APP_ROOT + "/view/<int:record_id>")
@app.route(APP_ROOT + "/view/<int:record_id>/")
@app.route(APP_ROOT + "/view/<int:record_id>/<path:query_string>")
# @check_login
def view(record_id: int, query_string: str = ""):
    """
    visualizza bene
    """
    with engine.connect() as conn:
        sql = text(
            (
                """SELECT id AS "ID", """
                """indirizzo, piano,"""
                """responsabile_strumento AS "Responsabile del laboratorio/ufficio", """
                """codice_sipi_torino AS "Codice SIPI Torino", codice_sipi_grugliasco AS "Codice SIPI Grugliasco", """
                """collegamento_autonomia AS "Collegamento Autonomo","""
                "ditta_collegamento, "
                """nome_strumento AS  "Nome Strumento","""
                """delicatezza  AS "Grado di Delicatezza dello strumento","""
                """difficolta  AS "Difficoltà","""
                """quale_difficolta AS "Quale difficoltà", """
                "peso, dimensioni, categoria "
                "FROM inventario "
                "WHERE id = :id"
            )
        )
        result = conn.execute(sql, {"id": record_id}).fetchone()
        if not result:
            return f"Bene con ID {record_id} non trovato", 404

        record_dict = dict(result._mapping)

        #record_dict["note"] = Markup(record_dict["note"].replace("\r", "<br>"))

        # check for images
        img_list = [
            x.name for x in list(Path(app.config["UPLOAD_FOLDER"]).glob("*_*.*"))
        ]
        #print("table results", record_dict)

    return render_template(
        "view.html", record=record_dict, query_string=query_string, img_list=img_list
    )


@app.route(APP_ROOT + "/search", methods=["GET"])
# @check_login
def search():
    # Lista di tutti i campi su cui cercare
    fields = [
        # "descrizione_inventario",
        "responsabile_strumento",
        "codice_sipi_torino",
        "codice_sipi_grugliasco",
        # "destinazione",
        # "microscopia",
        # "catena_del_freddo",
        # "alta_specialistica",
        # "da_movimentare",
        # "trasporto_in_autonomia",
        # "da_disinventariare",
        # "rosso_fase_alimentazione_privilegiata",
        # "didattica",
        # # "valore_convenzionale",
        # # "esercizio_bene_migrato",
        # "denominazione_fornitore",
        # "anno_fabbricazione",
        # "numero_seriale",
        # "categoria_inventoriale",
        # "catalogazione_materiale_strumentazione",
        # "peso",
        # "dimensioni",
        "collegamento_autonomia",
        "ditta_collegamento",
        "delicatezza",
        "difficolta",
        "indirizzo",
        "piano",
        "nome_strumento",
        "categoria",
    ]

    query_string = request.query_string.decode("utf-8")

    # Controlla se almeno un parametro di ricerca è presente e non vuoto
    has_filter = any(request.args.get(field, "").strip() for field in fields)

    if not has_filter:
        # Nessun filtro: non eseguire query, ritorna lista vuota o messaggio
        records = []
        keys = fields
    else:
        # query = (
        #     'SELECT id AS "ID", '
        #     'quantita as "Quantità", '
        #     'descrizione_bene AS "Descrizione bene", '
        #     'responsabile_strumento AS "Responsabile Laboratorio / Ufficio", '
        #     "da_movimentare, catena_del_freddo, trasporto_in_autonomia, microscopia, alta_specialistica, "
        #     'codice_sipi_torino AS "Codice SIPI Torino", '
        #     'codice_sipi_grugliasco AS "Codice SIPI Grugliasco", '
        #     'destinazione AS "Destinazione", '
        #     'note AS "Note", '
        #     "(peso = '' OR peso ~ '^-?[0-9]+(\.[0-9]+)?$')  AS peso_numeric, "
        #     "(dimensioni = '' OR dimensioni ~ '^[0-9]+x[0-9]+x[0-9]+$') AS dimensioni_ok "
        #     "FROM inventario WHERE deleted IS NULL "
        # )
        query = (
            'SELECT id AS "ID", '
            'indirizzo AS "Indirizzo", piano AS "Piano", '
            'nome_strumento AS "Nome Strumentazione", '
            'responsabile_strumento AS "Responsabile", '
            'codice_sipi_torino AS "Codice SIPI Torino", '
            'codice_sipi_grugliasco AS "Codice SIPI Grugliasco", '
            'categoria AS "Categoria", '
            "(peso = '' OR peso ~ '^-?[0-9]+(\.[0-9]+)?$')  AS peso_numeric, "
            "(dimensioni = '' OR dimensioni ~ '^[0-9]+x[0-9]+x[0-9]+$') AS dimensioni_ok "
            "FROM inventario WHERE deleted IS NULL"
        )
        params = {}
        #print('fields: ', fields)
        for field in fields:
            if field in BOOLEAN_FIELDS:
                if not request.args.get(field, ""):
                    continue
                value = request.args.get(field, "") == "true"
                query += f" AND {field} IS {value}"
            else:
                value = request.args.get(field, "").strip()
                if value:
                    # add senza responsabile
                    if field == "responsabile_strumento":
                        if value == "SENZA":
                            query += f" AND ({field} = '' OR {field} IS NULL)"
                            continue
                        if "," in value:
                            subquery = ""
                            for resp in [x.strip() for x in value.split(",")]:
                                if subquery:
                                    subquery += " OR "
                                subquery += f"{field} ILIKE '%{resp}%' "
                            query += f" AND ({subquery})"
                            continue

                    if value == "SENZA":
                        # add senza Codice SIPI Torino
                        if field == "codice_sipi_torino":
                            query += f" AND ({field} = '' OR {field} IS NULL)"
                            continue
                        # add senza Codice SIPI Grugliasco
                        if field == "codice_sipi_grugliasco":
                            query += f" AND ({field} = '' OR {field} IS NULL)"
                            continue

                    # Per testo, ricerca con ILIKE e wildcard %
                    # if field == "piano":
                    #     query += f" AND {field} = :{field}"
                    # else:
                    query += f" AND {field} ILIKE :{field}"
                    #print(request.args.get(field))
                    params[field] = f"%{value}%"

        query += " ORDER BY id ASC"
        #print("query: ",query)
        
        sql = text(query)
        with engine.connect() as conn:
            result = conn.execute(sql, params)
            records = result.fetchall()
            keys = result.keys()
            # print("search keys", (keys))
            # print("search records", records[0])
    
    return render_template(
        "search.html",
        records=records,
        request_args=request.args,
        fields=fields,
        query_string=query_string,
        boolean_fields=BOOLEAN_FIELDS,
        columns=keys,
    )

@app.route(APP_ROOT + "/search_resp")
# @check_login
def search_resp():
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "( SELECT DISTINCT ON (LOWER(responsabile_strumento)) responsabile_strumento from inventario WHERE responsabile_strumento != '') ORDER by LOWER(responsabile_strumento)"
            )
        )
        resp = result.fetchall()
    #print('resp', resp)
    return render_template(
        "search_responsabile.html",
        resp=resp,
    )

@app.route(APP_ROOT + "/search_sipi_torino")
# @check_login
def search_sipi_torino():
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "( SELECT DISTINCT codice_sipi_torino FROM inventario WHERE codice_sipi_torino != '') ORDER BY codice_sipi_torino"
            )
        )
        sipi_list = result.fetchall()

    return render_template(
        "search_sipi_torino.html",
        sipi_list=sipi_list,
    )

@app.route(APP_ROOT + "/search_sipi_grugliasco")
# @check_login
def search_sipi_grugliasco():
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "( SELECT DISTINCT codice_sipi_grugliasco FROM inventario WHERE codice_sipi_grugliasco != '') ORDER BY codice_sipi_grugliasco"
            )
        )
        sipi_list = result.fetchall()

    return render_template(
        "search_sipi_grugliasco.html",
        sipi_list=sipi_list,
    )


@app.route(APP_ROOT + "/search_struttura")
# @check_login
def search_struttura():
    return render_template(
        "search_struttura.html",
    )


@app.route(APP_ROOT + "/view_qrcode/<int:record_id>")
def view_qrcode(record_id: int):
    with engine.connect() as conn:
        sql = text((
                """SELECT id AS "ID", """
                """indirizzo, piano,"""
                """responsabile_strumento AS "Responsabile del laboratorio/ufficio", """
                """codice_sipi_torino AS "Codice SIPI Torino", codice_sipi_grugliasco AS "Codice SIPI Grugliasco", """
                """collegamento_autonomia AS "Collegamento Autonomo","""
                "ditta_collegamento, "
                """nome_strumento AS  "Nome Strumento","""
                """delicatezza  AS "Grado di Delicatezza dello strumento","""
                """difficolta  AS "Difficoltà","""
                """quale_difficolta AS "Quale difficoltà", """
                "peso, dimensioni, categoria "
                "FROM inventario "
                "WHERE id = :id"
            ))
        result = conn.execute(sql, {"id": record_id}).fetchone()
        if not result:
            return f"Bene con ID {record_id} non trovato", 404

        record_dict = dict(result._mapping)
 
    return render_template("view.html", record=record_dict, query_string="")

def label(record_list: list) -> str:
    """
    create typst label for records
    """
    with engine.connect() as conn:
        ids = ",".join([str(x) for x in record_list])
        sql = text(f"SELECT * FROM inventario WHERE id in ({ids})")
        records = conn.execute(sql).mappings().all()
        if not records:
            return f"Error in record list {', '.join(record_list)}", 404

        label_header = (
            '#import "@preview/cades:0.3.1": qr-code\n'
            "\n"
            "#set page(margin: (top: 1cm, bottom: 1cm, x:1cm))\n"
            "\n"
            "#set text(\n"
            '  font: "Libertinus Serif",\n'
            "  size: 11pt,\n"
            ")\n"
        )

    out = [label_header]

    for record in records:
        out.append("#block(breakable: false)[")

        out.append(
            f"""#text(size: 12pt)[*`{record["nome_strumento"].replace("`", "'") if record["nome_strumento"] else " "}`*] """
        )

        out.append("")
        out.append("#grid(columns: (14cm, 5cm),")
        out.append("[")
        if record["responsabile_strumento"]:
            out.append(f"`Responsabile lab:` *`{record['responsabile_strumento']}`*")
        else:
            out.append("*`SENZA RESPONSABILE`*")
        out.append("")

        out.append("#grid(columns: (7cm, 7cm),")
        # if record["num_inventario"]:
        #     out.append(f"[`Num inv:` *`{record['num_inventario']}`*],")
        # else:
        #     out.append("[`Num inventario` *`ASSENTE`*],")
        out.append(f"[`TRANSFER id:` *`{record['id']}`*],")
        out.append(")")
        out.append("")

        out.append("#grid(columns: (7cm, 7cm),")
        out.append("")
        out.append(
            f"""[`SIPI TO:` *`{record["codice_sipi_torino"] if record["codice_sipi_torino"] else "-"}`*],"""
        )
        out.append(
            f"""[`SIPI GRU:` *`{record["codice_sipi_grugliasco"] if record["codice_sipi_grugliasco"] else "-"}`*],"""
        )
        out.append(")")
        # out.append("")
        # out.append(
        #     f"""`{"DA MOVIMENTARE" if record["da_movimentare"] else "STRUMENTO/BENE DA NON MOVIMENTARE/DISMETTERE"}`"""
        # )
        # out.append("")
        # out.append(
        #     f"""`{"DA DISINVENTARIARE" if record["da_disinventariare"] else ""}`"""
        # )
        # out.append("")

        # out.append(f"`Scollegamento / Ricollegamento in autonomia:` *`{record['collegamento_autonomia']}`*,")
        # out.append("")
        # if record["collegamento_autonomia"] == "No":
        #     out.append(f"`Ditta che si occupa del collegamento nel caso che la ditta che si occupa del trasloco non fosse in grado:` *`{record['ditta_collegamento']}`*,")
        # out.append("")
        
        # out.append("")
        # out.append(f"""`{record["destinazione"]}`""")
        out.append("")
        out.append("],")
        out.append("")
        out.append("[")
        out.append("")
        out.append("#grid( columns: (2.5cm, 2.5cm),")
        out.append("[")
        out.append("#rect(width: 2.3cm,height: 2.3cm,")
        # out.append(f"""  fill: {"green" if record["da_movimentare"] else "red"},""")
        out.append("  stroke: 0.4cm+white,")
        out.append(")")
        out.append("],")
        out.append("[")
        out.append(
            f"""#qr-code("https://penelope.unito.it/chimicatransfer/view_qrcode/{record["id"]}", width: 2.3cm)"""
        )
        out.append("]")
        out.append(")")
        out.append("]")
        out.append("")
        out.append(")")
        out.append("")
        out.append("#line(length: 100%)")
        out.append("")
        out.append("]")

    return "\n".join(out)

@app.route(APP_ROOT + "/exportxlsx", methods=["POST"])
@app.route(APP_ROOT + "/exportxlsx/<int:record_id>", methods=["GET"])
def exportxlsx(record_id: str = ""):
    ids = request.form.getlist("record_ids")
    label_name=''

    if not ids:
        record_list = [record_id]
        label_name = record_list
    else:
        record_list = ids
        if len(ids) == 1:
            label_name = ids[0]
        else:
            label_name = 'multiple_choices'

    #ids = [x[0] for x in records]
    with engine.connect() as conn:
        results = conn.execute(
            text(
                (
        'SELECT id AS "ID", '
        'indirizzo AS "Indirizzo", piano AS "Piano", '
        'nome_strumento AS "Nome Strumentazione", '
        'responsabile_strumento AS "Resp. Strumento", '
        'codice_sipi_torino AS "Codice SIPI Attuale", '
        'codice_sipi_grugliasco AS "Codice SIPI Grugliasco", '
        'categoria AS "Categoria", '
        'peso AS "Peso", '
        'dimensioni AS "Dimensioni", '
        'collegamento_autonomia AS "Scollegamento / Ricollegamento in autonomia?", '
        'ditta_collegamento, '
        'delicatezza AS "Grado di Delicatezza", '
        'difficolta AS "Difficoltà di trasloco", '
        'quale_difficolta AS "Se N = Si, quale difficoltà", '
        "(dimensioni = '' OR dimensioni ~ '^[0-9]+x[0-9]+x[0-9]+$') AS dimensioni_ok "
        "FROM inventario WHERE id IN :ids AND deleted IS NULL "
                )
            ).bindparams(bindparam("ids", expanding=True)),
            {"ids": ids},
        )
        records = results.fetchall()
        keys = results.keys()
    # print('keys', keys)
    # print('records', records)
    df = pd.DataFrame(records, columns=keys)
    #df = df.drop(columns=["peso_non_conforme", "dimensioni_non_conforme"])
    df = df.replace({True: "SI", False: "NO"})
    df = df.rename(columns={"ditta_collegamento":"Se K = NO, ditta che si occupa del collegamento nel caso che la ditta che si occupa del trasloco non fosse in grado"})
    # add volume totale
    #df["volume totale tutti beni (m³)"] = round(volume_totale, 2)
    # add peso totale
    #df["Peso totale tutti beni (Kg)"] = round(peso_totale, 2)

    output = BytesIO()
    spreadsheet_engine: Literal["xlsxwriter"] = (
        "xlsxwriter"
    )
    with pd.ExcelWriter(output, engine=spreadsheet_engine) as writer:
        df.to_excel(writer, index=False, sheet_name="Risultati")
    output.seek(0)

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if spreadsheet_engine == "xlsxwriter"
        else "application/vnd.oasis.opendocument.spreadsheet",
        as_attachment=True,
        download_name=f"risultati_ricerca.{'xlsx' }",
    )

@app.route(APP_ROOT + "/exporttotal", methods=["POST"])
def exporttotal(record_id: str = ""):
    ids = request.form.getlist("record_ids")
    label_name=''

    if not ids:
        record_list = [record_id]
        label_name = record_list
    else:
        record_list = ids
        if len(ids) == 1:
            label_name = ids[0]
        else:
            label_name = 'multiple_choices'

    #ids = [x[0] for x in records]
    with engine.connect() as conn:
        results = conn.execute(
            text(
                (
        'SELECT id AS "ID", '
        'indirizzo AS "Indirizzo", piano AS "Piano", '
        'nome_strumento AS "Nome Strumentazione", '
        'responsabile_strumento AS "Resp. Strumento", '
        'codice_sipi_torino AS "Codice SIPI Attuale", '
        'codice_sipi_grugliasco AS "Codice SIPI Grugliasco", '
        'categoria AS "Categoria", '
        'peso AS "Peso", '
        'dimensioni AS "Dimensioni", '
        'collegamento_autonomia AS "Scollegamento / Ricollegamento in autonomia?", '
        'ditta_collegamento, '
        'delicatezza AS "Grado di Delicatezza", '
        'difficolta AS "Difficoltà di trasloco", '
        'quale_difficolta AS "Se N = Si, quale difficoltà", '
        "(dimensioni = '' OR dimensioni ~ '^[0-9]+x[0-9]+x[0-9]+$') AS dimensioni_ok "
        "FROM inventario WHERE  deleted IS NULL "
                )
            )
        )
        records = results.fetchall()
        keys = results.keys()
    # print('keys', keys)
    # print('records', records)
    df = pd.DataFrame(records, columns=keys)
    #df = df.drop(columns=["peso_non_conforme", "dimensioni_non_conforme"])
    df = df.replace({True: "SI", False: "NO"})
    df = df.rename(columns={"ditta_collegamento":"Se K = NO, ditta che si occupa del collegamento nel caso che la ditta che si occupa del trasloco non fosse in grado"})
    # add volume totale
    #df["volume totale tutti beni (m³)"] = round(volume_totale, 2)
    # add peso totale
    #df["Peso totale tutti beni (Kg)"] = round(peso_totale, 2)

    output = BytesIO()
    spreadsheet_engine: Literal["xlsxwriter"] = (
        "xlsxwriter"
    )
    with pd.ExcelWriter(output, engine=spreadsheet_engine) as writer:
        df.to_excel(writer, index=False, sheet_name="Risultati")
    output.seek(0)

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if spreadsheet_engine == "xlsxwriter"
        else "application/vnd.oasis.opendocument.spreadsheet",
        as_attachment=True,
        download_name=f"dotazioni_totali.{'xlsx' }",
    )


@app.route(APP_ROOT + "/etichetta", methods=["POST"])
@app.route(APP_ROOT + "/etichetta/<int:record_id>", methods=["GET"])
# @check_login
def etichetta(record_id: str = ""):
    """
    Stampa etichetta da incollare sul bene
    require typst (https://github.com/typst/typst)
    """

    record_ids = request.form.getlist("record_ids")
    label_name=''

    if not record_ids:
        record_list = [record_id]
        label_name = record_list
    else:
        record_list = record_ids
        if len(record_ids) == 1:
            label_name = f"[{record_ids[0]}]"
        else:
            label_name = 'multiple_choices'
    # print(label_name)
    typst_content = label(record_list)

    try:
        # Server version
        temp_typst_path = f"/tmp/label_{label_name}.typst"
        temp_pdf_path = f"/tmp/label_{label_name}.pdf"
        with open(temp_typst_path, "w") as f_out:
            f_out.write(typst_content)
        subprocess.run(["/usr/bin/typst", "compile", temp_typst_path, temp_pdf_path])
        
        # # Local version
        # temp_typst_path = f"../typst/source/label_{label_name}.typst"
        # temp_pdf_path = f"../typst/source/label_{label_name}.pdf"
        # with open(temp_typst_path, "w") as f_out:
        #     f_out.write(typst_content)
        # subprocess.run(["../typst/typst", "compile", temp_typst_path, temp_pdf_path])

        # send file to client
        return send_file(
            temp_pdf_path,
            mimetype="application/pdf",
            as_attachment=False,
            download_name=f"etichetta_{label_name}.pdf",
        )

    finally:
        # Delete temp files
        if Path(temp_typst_path).exists():
            Path(temp_typst_path).unlink()
        if Path(temp_pdf_path).exists():
            Path(temp_pdf_path).unlink()


@app.route(APP_ROOT + "/mappe", methods=["GET"])
# @check_login
def mappe():
    return render_template("mappe.html")


@app.route(APP_ROOT + "/version")
def version():
    """
    display version of service
    """

    return f"(c) Olivier Friard 2025<br>v. {__version__} modified by Anna Di Leva"


"""
@app.route(APP_ROOT + "/test")
def test():
    subprocess.run(["/usr/bin/typst", "compile", "/tmp/1.typst"])

    return "test"
"""

@app.route('/favicon.ico') 
def favicon(): 
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == "__main__":
    app.run(debug=True)
