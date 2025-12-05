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
from sqlalchemy import create_engine, text
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
# """SELECT id AS "ID", """
# """responsabile_strumento AS "Responsabile del laboratorio/ufficio", """
# """num_inventario AS "Numero di inventario", num_inventario_ateneo, data_carico,"""
# """codice_sipi_torino AS "Codice SIPI Torino", codice_sipi_grugliasco AS "Codice SIPI Grugliasco", """
# "CASE WHEN microscopia THEN 'SI' ELSE 'NO' END AS microscopia,"
# """CASE WHEN catena_del_freddo THEN 'SI' ELSE 'NO' END AS "Rispettare la catena del freddo","""
# "CASE WHEN alta_specialistica THEN 'SI' ELSE 'NO' END AS alta_specialistica,                    "
# "CASE WHEN da_movimentare THEN 'SI' ELSE 'NO' END AS da_movimentare,"
# "CASE WHEN trasporto_in_autonomia THEN 'SI' ELSE 'NO' END AS trasporto_in_autonomia,"
# "CASE WHEN da_disinventariare THEN 'SI' ELSE 'NO' END AS da_disinventariare,"
# "CASE WHEN rosso_fase_alimentazione_privilegiata THEN 'SI' ELSE 'NO' END AS rosso_fase_alimentazione_privilegiata,"
# "CASE WHEN didattica THEN 'SI' ELSE 'NO' END AS didattica,"
# "valore_convenzionale,"
# "denominazione_fornitore, anno_fabbricazione, numero_seriale,"
# "categoria_inventoriale, catalogazione_materiale_strumentazione, peso, dimensioni,"
# "ditta_costruttrice_fornitrice, note "
# "FROM inventario "
# "WHERE id = :id"

# # Aggiungi record
# @app.route(APP_ROOT + "/aggiungi", methods=["GET", "POST"])
# @app.route(APP_ROOT + "/aggiungi/", methods=["GET", "POST"])
# @app.route(APP_ROOT + "/aggiungi/<query_string>", methods=["GET", "POST"])
# #@check_login
# def aggiungi(query_string: str = ""):
#     """
#     aggiungi bene all'inventario
#     """
#     if request.method == "GET":
#         with engine.connect() as conn:
#             responsabili = conn.execute(
#                 text(
#                     "SELECT DISTINCT responsabile_strumento FROM inventario WHERE deleted IS NULL ORDER BY responsabile_strumento"
#                 )
#             ).fetchall()

#         search_responsabile = "None"
#         if query_string:
#             search_responsabile = query_string.split("=")[1].replace("+", " ")
#             print(f"{search_responsabile=}")

#         return render_template(
#             "aggiungi.html",
#             responsabili=responsabili,
#             boolean_fields=BOOLEAN_FIELDS,
#             query_string=query_string,
#             search_responsabile=search_responsabile,
#         )

#     if request.method == "POST":
#         data = dict(request.form)

#         # modify values for boolean fields
#         for field in BOOLEAN_FIELDS:
#             value = request.form.get(field)
#             data[field] = value == "true"

#         # check for new responsabile
#         if data["responsabile_strumento"] == "altro":
#             data["responsabile_strumento"] = data["nuovo_responsabile_strumento"]

#         query = text("""
#             INSERT INTO inventario (
#             quantita,
#                  num_inventario, num_inventario_ateneo, data_carico,
#                 descrizione_bene, codice_sipi_torino, codice_sipi_grugliasco, destinazione,
#                 microscopia, catena_del_freddo, alta_specialistica, da_movimentare, trasporto_in_autonomia, da_disinventariare,
#                 rosso_fase_alimentazione_privilegiata, 
#                 didattica, valore_convenzionale, esercizio_bene_migrato,
#                 responsabile_strumento, denominazione_fornitore, anno_fabbricazione, numero_seriale,
#                 categoria_inventoriale, catalogazione_materiale_strumentazione, peso, dimensioni,
#                 ditta_costruttrice_fornitrice, note
#             ) VALUES (
#                 :quantita, :num_inventario, :num_inventario_ateneo, :data_carico,
#                 :descrizione_bene, :codice_sipi_torino, :codice_sipi_grugliasco, :destinazione,
#                 :microscopia, :catena_del_freddo, :alta_specialistica, :da_movimentare, :trasporto_in_autonomia, :da_disinventariare,
#                 :rosso_fase_alimentazione_privilegiata, :didattica, :valore_convenzionale, :esercizio_bene_migrato,
#                 :responsabile_strumento, :denominazione_fornitore, :anno_fabbricazione, :numero_seriale,
#                 :categoria_inventoriale, :catalogazione_materiale_strumentazione, :peso, :dimensioni,
#                 :ditta_costruttrice_fornitrice, :note
#             )
#             RETURNING id
#         """)
#         with engine.connect() as conn:
#             conn.execute(
#                 text("SET LOCAL application_name = :user"), {"user": session["email"]}
#             )
#             new_id = conn.execute(query, data).fetchone()[0]
#             conn.commit()

#             # foto
#             foto = request.files.get("foto")
#             if foto and foto.filename != "":
#                 foto.save(
#                     Path(app.config["UPLOAD_FOLDER"])
#                     / Path(str(new_id) + "_1").with_suffix(Path(foto.filename).suffix)
#                 )

#         if query_string:
#             return redirect(APP_ROOT + f"/search?{query_string}")
#         else:
#             return redirect(url_for("index"))


# # Modifica record - form
# @app.route(APP_ROOT + "/modifica/<int:record_id>")
# @app.route(APP_ROOT + "/modifica/<int:record_id>/")
# @app.route(APP_ROOT + "/modifica/<int:record_id>/<path:query_string>")
# @check_login
# def modifica(record_id, query_string: str = ""):
#     """
#     modifica un bene
#     """
#     with engine.connect() as conn:
#         result = conn.execute(
#             text(
#                 (
#                     "SELECT id, quantita, descrizione_bene, responsabile_strumento, "
#                     "num_inventario, num_inventario_ateneo, data_carico,"
#                     "codice_sipi_torino, codice_sipi_grugliasco, destinazione,"
#                     "CASE WHEN microscopia THEN 'SI' ELSE 'NO' END AS microscopia,"
#                     "CASE WHEN catena_del_freddo THEN 'SI' ELSE 'NO' END AS catena_del_freddo,"
#                     "CASE WHEN alta_specialistica THEN 'SI' ELSE 'NO' END AS alta_specialistica,                    "
#                     "CASE WHEN da_movimentare THEN 'SI' ELSE 'NO' END AS da_movimentare,"
#                     "CASE WHEN trasporto_in_autonomia THEN 'SI' ELSE 'NO' END AS trasporto_in_autonomia,"
#                     "CASE WHEN da_disinventariare THEN 'SI' ELSE 'NO' END AS da_disinventariare,"
#                     "CASE WHEN rosso_fase_alimentazione_privilegiata THEN 'SI' ELSE 'NO' END AS rosso_fase_alimentazione_privilegiata,"
#                     "CASE WHEN didattica THEN 'SI' ELSE 'NO' END AS didattica,"
#                     "valore_convenzionale,"
#                     "denominazione_fornitore, anno_fabbricazione, numero_seriale,"
#                     "categoria_inventoriale, catalogazione_materiale_strumentazione, peso, dimensioni,"
#                     "ditta_costruttrice_fornitrice, note "
#                     "FROM inventario "
#                     "WHERE id = :id"
#                 )
#             ),
#             {"id": record_id},
#         )
#         record = result.fetchone()

#         responsabili = conn.execute(
#             text(
#                 "SELECT DISTINCT responsabile_strumento FROM inventario WHERE deleted IS NULL ORDER BY responsabile_strumento"
#             )
#         ).fetchall()

#         # check for images
#         img_list = [
#             x.name for x in list(Path(app.config["UPLOAD_FOLDER"]).glob("*_*.*"))
#         ]

#     return render_template(
#         "modifica.html",
#         record=record,
#         query_string=query_string,
#         responsabili=responsabili,
#         img_list=img_list,
#         boolean_fields=BOOLEAN_FIELDS,
#     )


# # Modifica record - salvataggio
# @app.route(APP_ROOT + "/salva_modifiche/<int:record_id>", methods=["POST"])
# @check_login
# def salva_modifiche(record_id):
#     data = dict(request.form)

#     for field in BOOLEAN_FIELDS:
#         value = request.form.get(field)
#         data[field] = value == "true"

#     # check for new responsabile
#     if data["responsabile_strumento"] == "altro":
#         data["responsabile_strumento"] = data["nuovo_responsabile_strumento"]

#     query = text(
#         (
#             "UPDATE inventario SET "
#             "    quantita = :quantita, "
#             "    descrizione_bene = :descrizione_bene, "
#             "    responsabile_strumento = :responsabile_strumento, "
#             "    num_inventario = :num_inventario, "
#             "    num_inventario_ateneo = :num_inventario_ateneo, "
#             "    data_carico = :data_carico, "
#             "    codice_sipi_torino = :codice_sipi_torino, "
#             "    codice_sipi_grugliasco = :codice_sipi_grugliasco, "
#             "    destinazione = :destinazione, "
#             "    microscopia = :microscopia, "
#             "    catena_del_freddo = :catena_del_freddo, "
#             "    alta_specialistica = :alta_specialistica, "
#             "    da_movimentare = :da_movimentare, "
#             "    trasporto_in_autonomia = :trasporto_in_autonomia, "
#             "    da_disinventariare = :da_disinventariare, "
#             "    rosso_fase_alimentazione_privilegiata = :rosso_fase_alimentazione_privilegiata, "
#             "    didattica = :didattica, "
#             "    valore_convenzionale = :valore_convenzionale, "
#             # "    esercizio_bene_migrato = :esercizio_bene_migrato, "
#             "    denominazione_fornitore = :denominazione_fornitore, "
#             "    anno_fabbricazione = :anno_fabbricazione, "
#             "    numero_seriale = :numero_seriale, "
#             "    categoria_inventoriale = :categoria_inventoriale, "
#             "    catalogazione_materiale_strumentazione = :catalogazione_materiale_strumentazione, "
#             "    peso = :peso, "
#             "    dimensioni = :dimensioni, "
#             "    ditta_costruttrice_fornitrice = :ditta_costruttrice_fornitrice, "
#             "    note = :note "
#             "WHERE id = :id "
#         )
#     )
#     with engine.connect() as conn:
#         conn.execute(
#             text("SET LOCAL application_name = :user"), {"user": session["email"]}
#         )
#         conn.execute(query, {**data, "id": record_id})
#         conn.commit()

#     foto = request.files.get("foto")
#     if foto and foto.filename != "":
#         # filename = secure_filename(foto.filename)
#         img_list = [
#             x.stem
#             for x in list(Path(app.config["UPLOAD_FOLDER"]).glob(f"{record_id}_*.*"))
#         ]
#         if not img_list:
#             foto.save(
#                 Path(app.config["UPLOAD_FOLDER"])
#                 / Path(str(record_id) + "_1").with_suffix(Path(foto.filename).suffix)
#             )
#         else:
#             img_id = max([int(x.split("_")[1]) for x in img_list]) + 1
#             foto.save(
#                 Path(app.config["UPLOAD_FOLDER"])
#                 / Path(str(record_id) + f"_{img_id}").with_suffix(
#                     Path(foto.filename).suffix
#                 )
#             )

#     query_string = request.form.get("query_string", "")
#     if query_string == "tutti":
#         return redirect(APP_ROOT + "/tutti")
#     elif query_string:
#         return redirect(APP_ROOT + f"/search?{query_string}")
#     else:
#         return redirect(url_for("index"))


# # Modifica record - form
# @app.route(APP_ROOT + "/duplica/<int:record_id>", methods=["GET", "POST"])
# @app.route(APP_ROOT + "/duplica/<int:record_id>/", methods=["GET", "POST"])
# @app.route(
#     APP_ROOT + "/duplica/<int:record_id>/<path:query_string>", methods=["GET", "POST"]
# )
# @check_login
# def duplica(record_id, query_string: str = ""):
#     """
#     duplica un bene
#     """
#     if request.method == "GET":
#         with engine.connect() as conn:
#             result = conn.execute(
#                 text(
#                     (
#                         "SELECT id, descrizione_bene, responsabile_strumento FROM inventario WHERE id = :id"
#                     )
#                 ),
#                 {"id": record_id},
#             )
#             record = result.fetchone()

#         return render_template(
#             "duplica_bene.html",
#             record_id=record_id,
#             record=record,
#             query_string=query_string,
#         )

#     if request.method == "POST":
#         copy_number = int(request.form.get("numero_copie"))
#         with engine.connect() as conn:
#             for i in range(1, copy_number + 1):
#                 sql = text(
#                     "INSERT INTO inventario ( "
#                     "  num_inventario, "
#                     "  num_inventario_ateneo, "
#                     "  data_carico, "
#                     "  descrizione_bene, "
#                     "  codice_sipi_torino, "
#                     "  codice_sipi_grugliasco, "
#                     "  destinazione, "
#                     "  rosso_fase_alimentazione_privilegiata, "
#                     "  valore_convenzionale, "
#                     "  esercizio_bene_migrato, "
#                     "  responsabile_strumento, "
#                     "  denominazione_fornitore, "
#                     "  anno_fabbricazione, "
#                     "  numero_seriale, "
#                     "  categoria_inventoriale, "
#                     "  catalogazione_materiale_strumentazione, "
#                     "  peso, "
#                     "  dimensioni, "
#                     "  ditta_costruttrice_fornitrice, "
#                     "  note, "
#                     "  deleted, "
#                     "  microscopia, "
#                     "  catena_del_freddo, "
#                     "  alta_specialistica, "
#                     "  da_movimentare, "
#                     "  trasporto_in_autonomia, "
#                     "  da_disinventariare, "
#                     "  didattica "
#                     ") "
#                     "SELECT "
#                     "  num_inventario, "
#                     "  num_inventario_ateneo, "
#                     "  data_carico, "
#                     f"  CONCAT(descrizione_bene, ' #', {i + 1}) , "
#                     "  codice_sipi_torino, "
#                     "  codice_sipi_grugliasco, "
#                     "  destinazione, "
#                     "  rosso_fase_alimentazione_privilegiata, "
#                     "  valore_convenzionale, "
#                     "  esercizio_bene_migrato, "
#                     "  responsabile_strumento, "
#                     "  denominazione_fornitore, "
#                     "  anno_fabbricazione, "
#                     "  numero_seriale, "
#                     "  categoria_inventoriale, "
#                     "  catalogazione_materiale_strumentazione, "
#                     "  peso, "
#                     "  dimensioni, "
#                     "  ditta_costruttrice_fornitrice, "
#                     "  note, "
#                     "  deleted, "
#                     "  microscopia, "
#                     "  catena_del_freddo, "
#                     "  alta_specialistica, "
#                     "  da_movimentare, "
#                     "  trasporto_in_autonomia, "
#                     "  da_disinventariare, "
#                     "  didattica "
#                     "FROM inventario "
#                     "WHERE id = :record_id "
#                 )
#                 conn.execute(sql, {"record_id": record_id})
#                 conn.commit()

#         flash("Bene duplicato con successo!", "success")

#         return redirect(url_for("search") + "?" + query_string)


# @app.route(APP_ROOT + "/delete_foto/<img_id>")
# @check_login
# def delete_foto(img_id: str):
#     """
#     cancella foto
#     """
#     record_id = img_id.split("_")[0]
#     if (Path(app.config["UPLOAD_FOLDER"]) / img_id).exists():
#         (Path(app.config["UPLOAD_FOLDER"]) / img_id).unlink()
#         # record
#         with engine.connect() as conn:
#             conn.execute(
#                 text(
#                     f"INSERT INTO inventario_audit (operation_type, record_id, executed_by) VALUES ('DELETED FOTO {img_id}', :record_id, :executed_by)"
#                 ),
#                 {"record_id": record_id, "executed_by": session["email"]},
#             )
#             conn.commit()

#     return redirect(f"/chimicatransfer/modifica/{record_id}")


# @app.route(APP_ROOT + "/modifica_multipla", methods=["POST"])
# @check_login
# def modifica_multipla():
#     campo = request.form.get("campo")
#     nuovo_valore = request.form.get("nuovo_valore")
#     record_ids = request.form.getlist("record_ids")
#     query_string = request.form.get("query_string", "")

#     if campo in (
#         "da_movimentare",
#         "trasporto_in_autonomia",
#     ) and nuovo_valore.upper() not in ("SI", "NO"):
#         flash(
#             Markup(
#                 f"Il valore per il campo <b>{campo.replace('_', ' ')}</b> deve essere <b>SI</b> o <b>NO</b>"
#             ),
#             "danger",
#         )
#         return redirect(url_for("search") + "?" + query_string)

#     if (
#         nuovo_valore
#         and record_ids
#         and campo
#         in (
#             "responsabile_strumento",
#             "codice_sipi_torino",
#             "codice_sipi_grugliasco",
#             "da_movimentare",
#             "trasporto_in_autonomia",
#             "catena_del_freddo",
#             "didattica",
#             "destinazione",
#             "note",
#         )
#     ):
#         # set boolean values
#         if campo in (
#             "da_movimentare",
#             "trasporto_in_autonomia",
#             "catena_del_freddo",
#             "didattica",
#         ):
#             nuovo_valore = nuovo_valore.upper() == "SI"

#         with engine.connect() as conn:
#             for rid in record_ids:
#                 query = text(
#                     f"UPDATE inventario SET {campo} = :nuovo_valore WHERE id = :id"
#                 )

#                 conn.execute(
#                     text("SET LOCAL application_name = :user"),
#                     {"user": session["email"]},
#                 )
#                 conn.execute(query, {"id": rid, "nuovo_valore": nuovo_valore})
#                 conn.commit()

#     return redirect(url_for("search") + "?" + query_string)


# @app.route(APP_ROOT + "/upload_excel", methods=["GET", "POST"])
# @check_login
# def upload_excel():
#     if request.method == "POST":
#         file = request.files.get("file")
#         if not file:
#             flash("Nessun file caricato", "danger")
#             return redirect(request.url)

#         try:
#             df = pd.read_excel(file)
#             df.columns = df.columns.str.strip()

#             excel_to_db_fields = {
#                 "Numero inventario": "num_inventario",
#                 "Num inventario Ateneo": "num_inventario_ateneo",
#                 "Data carico": "data_carico",
#                 "Descrizione bene": "descrizione_bene",
#                 "Codice Sipi Torino": "codice_sipi_torino",
#                 "Codice Sipi Grugliasco": "codice_sipi_grugliasco",
#                 "Destinazione (colori legenda)": "destinazione",
#                 "Rosso fase_alimentazione privilegiata": "rosso_fase_alimentazione_privilegiata",
#                 "Valore convenzionale": "valore_convenzionale",
#                 "Esercizio bene migrato": "esercizio_bene_migrato",
#                 "Responsabile di Laboratorio": "responsabile_strumento",
#                 "Denominazione Fornitore": "denominazione_fornitore",
#                 "Anno fabbricazione": "anno_fabbricazione",
#                 "Numero seriale": "numero_seriale",
#                 "Catalogazione del materiale/strumentazione": "catalogazione_materiale_strumentazione",
#                 "Peso": "peso",
#                 "Dimensioni (Altezza e larghezza/lunghezza espressi in cm)": "dimensioni",
#                 "Ditta costruttrice/Fornitrice": "ditta_costruttrice_fornitrice",
#                 "Note": "note",
#             }

#             for col in df.columns:
#                 if col.startswith("Peso"):
#                     df.rename(columns={col: "Peso"}, inplace=True)
#                     break  # Se vuoi rinominare solo la prima colonna che matcha

#             """
#             # Trasforma num_inventario in intero dove possibile
#             df["num_inventario"] = (
#                 pd.to_numeric(df["num_inventario"], errors="coerce")
#                 .fillna(0)
#                 .astype(int)
#             )
#             """

#             # Controllo duplicati su num_inventario solo se diverso da NaN e stringa vuota
#             """
#             mask_validi = (df["num_inventario"].notna()) & (df["num_inventario"] != "")
#             duplicati = df.loc[mask_validi, "num_inventario"].duplicated(keep=False)

#             if duplicati.any():
#                 num_duplicati = duplicati.sum()
#                 inv_duplicati = df.loc[
#                     duplicati.index[duplicati], ["num_inventario", "descrizione_bene"]
#                 ]
#                 elenco = "<br>".join(
#                     f"{row['descrizione_bene']} (inv: {row['num_inventario']})"
#                     for _, row in inv_duplicati.iterrows()
#                 )
#                 flash(
#                     Markup(
#                         f"<b>Nessun dato caricato</b> perché sono stati trovati <b>{num_duplicati} beni con numero di inventario duplicato nel file</b>:<br><br>{elenco}"
#                     ),
#                     "danger",
#                 )

#                 return redirect(request.url)
#             """

#             print(df.columns)

#             expected_cols = list(excel_to_db_fields.keys())
#             missing_cols = [c for c in expected_cols if c not in df.columns]
#             if missing_cols:
#                 flash(
#                     Markup(
#                         f"Mancano colonne nel file Excel:<br><b> {'<br>'.join(missing_cols)}</b>"
#                     ),
#                     "danger",
#                 )
#                 return redirect(request.url)

#             # rename columns
#             df.rename(columns=excel_to_db_fields, inplace=True)
#             df.fillna("", inplace=True)

#             # record senza responsabile
#             senza_responsabile = df[df["responsabile_strumento"] == ""]

#             #

#             with engine.connect() as conn:
#                 conn.execute(
#                     text("SET LOCAL application_name = :user"),
#                     {"user": session["email"]},
#                 )
#                 for _, row in df.iterrows():
#                     sql = text("""
#                     INSERT INTO inventario (
#                          num_inventario, num_inventario_ateneo, data_carico,
#                         descrizione_bene, codice_sipi_torino, codice_sipi_grugliasco, destinazione,
#                         rosso_fase_alimentazione_privilegiata, valore_convenzionale, esercizio_bene_migrato,
#                         responsabile_strumento, denominazione_fornitore, anno_fabbricazione, numero_seriale,
#                         catalogazione_materiale_strumentazione, peso, dimensioni,
#                         ditta_costruttrice_fornitrice, note
#                     ) VALUES (
#                          :num_inventario, :num_inventario_ateneo, :data_carico,
#                         :descrizione_bene, :codice_sipi_torino, :codice_sipi_grugliasco, :destinazione,
#                         :rosso_fase_alimentazione_privilegiata, :valore_convenzionale, :esercizio_bene_migrato,
#                         :responsabile_strumento, :denominazione_fornitore, :anno_fabbricazione, :numero_seriale,
#                         :catalogazione_materiale_strumentazione, :peso, :dimensioni,
#                         :ditta_costruttrice_fornitrice, :note
#                     )
#                     """)
#                     conn.execute(sql, row.to_dict())
#                 conn.commit()

#             flash("File caricato e dati inseriti con successo!", "success")

#             # se ci sono record senza responsabile -> flash di report sintetico
#             count_senza_responsabile = len(senza_responsabile)

#             if count_senza_responsabile > 0:
#                 # Prepariamo una lista di stringhe tipo "num_inventario (descrizione_bene)"
#                 dettagli = [
#                     f"{row['descrizione_bene']} (inv: {row['num_inventario']})"
#                     for _, row in senza_responsabile.iterrows()
#                 ]
#                 inventari = "<br>".join(dettagli)
#                 flash(
#                     Markup(
#                         f"<b>{count_senza_responsabile} beni senza responsabile di laboratorio</b>:<br>{inventari}"
#                     ),
#                     "warning",
#                 )

#             return redirect(url_for("index"))

#         except Exception as e:
#             raise
#             flash(f"Errore nel caricamento del file: {e}", "danger")
#             return redirect(request.url)

#     return render_template("upload_excel.html")


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

    # Se viene richiesta esportazione Excel e ci sono risultati
    if request.args.get("export", "").lower() == "xlsx" and records:
        df = pd.DataFrame(records, columns=keys)
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Risultati")
        output.seek(0)

        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="risultati_ricerca.xlsx",
        )

    return render_template(
        "search.html",
        records=records,
        request_args=request.args,
        fields=fields,
        query_string=query_string,
        boolean_fields=BOOLEAN_FIELDS,
        columns=keys,
    )

# @app.route(APP_ROOT + "/otherlocation", methods=["GET"])
# def searchotherlocation():
#     fields = [
#         "responsabile_strumento",
#         "codice_sipi_torino",
#         "codice_sipi_grugliasco",
#         "collegamento_autonomia",
#         "ditta_collegamento",
#         "delicatezza",
#         "difficolta",
#         "indirizzo",
#         "piano",
#         "nome_strumento",
#         "categoria",
#     ]
#     query_string = request.query_string.decode("utf-8")
#     query = (
#         'SELECT id AS "ID", indirizzo AS "Indirizzo", piano AS "Piano",'
#         ' nome_strumento AS "Nome Strumentazione", responsabile_strumento AS "Responsabile",'
#         ' codice_sipi_torino AS "Codice SIPI Torino", codice_sipi_grugliasco AS "Codice SIPI Grugliasco",'
#         'categoria AS "Categoria", '
#         "(peso = '' OR peso ~ '^-?[0-9]+(\.[0-9]+)?$')  AS peso_numeric, "
#         "(dimensioni = '' OR dimensioni ~ '^[0-9]+x[0-9]+x[0-9]+$') AS dimensioni_ok " 
#         "FROM inventario WHERE deleted IS NULL " 
#         "AND indirizzo ILIKE '%ungheria%' or indirizzo ilike '%fisica%'"
#         )
#     query += " ORDER BY id ASC"
#     sql = text(query)
#     with engine.connect() as conn:
#         result = conn.execute(sql)
#         records = result.fetchall()
#         keys = result.keys()
#     return render_template(
#         "search.html",
#         records=records,
#         request_args=request.args,
#         fields=fields,
#         query_string=query_string,
#         boolean_fields=BOOLEAN_FIELDS,
#         columns=keys,
#     )


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
        sql = text(("SELECT * FROM inventario WHERE id = :id "))
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
            '#import "@preview/cades:0.3.0": qr-code\n'
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

        out.append(
            f"""#text(size: 12pt)[*`{record["nome_strumento"].replace("`", "'") if record["nome_strumento"] else " "}`*]"""
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
        out.append(
            f"""`{"Scollegamento / Ricollegamento in autonomia" if record["collegamento_autonomia"] else ""}`"""
        )
        out.append(
            f"""`{"Ditta che si occupa del collegamento" if record["ditta_collegamento"] else ""}`"""
        )
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


@app.route(APP_ROOT + "/etichetta", methods=["POST"])
@app.route(APP_ROOT + "/etichetta/<int:record_id>", methods=["GET"])
# @check_login
def etichetta(record_id: str = ""):
    """
    Stampa etichetta da incollare sul bene
    require typst (https://github.com/typst/typst)
    """

    record_ids = request.form.getlist("record_ids")

    if not record_ids:
        record_list = [record_id]
    else:
        record_list = record_ids

    typst_content = label(record_list)

    try:
        temp_typst_path = f"/tmp/label_{record_id}.typst"
        with open(temp_typst_path, "w") as f_out:
            f_out.write(typst_content)

        temp_pdf_path = f"/tmp/label_{record_id}.pdf"

        subprocess.run(["/usr/bin/typst", "compile", temp_typst_path, temp_pdf_path])
        

        # send file to client
        return send_file(
            temp_pdf_path,
            mimetype="application/pdf",
            as_attachment=False,
            download_name=f"etichetta_{record_id}.pdf",
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
