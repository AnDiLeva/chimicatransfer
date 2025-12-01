import pandas as pd
from sqlalchemy import create_engine, text
import sys
import os

# Configurazione database
DB_URL = "postgresql://chem_togru_user:chempassword456@localhost:5432/chimicatransfer"
engine = create_engine(DB_URL)
#TODO da qui modificare 
# Mappatura colonne Excel → DB
excel_to_db_fields = {
    "Indirizzo": "indirizzo",
    "Piano": "piano",
    "Codice Sipi attuale": "codice_sipi_torino",
    "Nome Strumento": "nome_strumento",
    "Resp. Strumento": "responsabile_strumento",
    "Dimensioni": "dimensioni",
    "Peso (Kg)": "peso",
    "Scollegamento / Ricollegamento in autonomia?": "collegamento_autonomia",
    "Se I = NO, quale ditta se ne occuperà?": "ditta_collegamento",
    "Delicatezza": "delicatezza",
    "Difficoltà di trasloco": "difficolta",
    "Se si, quali": "quale_difficolta",
    "Simil-codice SIPI GRU": "codice_sipi_grugliasco",
    "Note L": "note",
}
# excel_to_db_fields = {
#     "Excel_ID": "excel_id",
#     "Indirizzo": "indirizzo",
#     "Piano": "piano",
#     "Codice Sipi attuale": "codice_sipi_torino",
#     "Nome Strumento": "nome_strumento",
#     "Resp. Strumento": "responsabile_strumento",
#     "Dimensioni": "dimensioni",
#     "Peso (Kg)": "peso",
#     "Scollegamento / Ricollegamento in autonomia?": "collegamento_autonomia",
#     "Se I = NO, quale ditta se ne occuperà?": "ditta_collegamento",
#     "Delicatezza": "delicatezza",
#     "Difficoltà di trasloco": "difficolta",
#     "Se si, quali": "quale_difficolta",
#     "Simil-codice SIPI GRU": "codice_sipi_grugliasco",
#     "Note L": "note",
# }


def upload_excel(file_path, user_email="cli_uploader"):
    if not os.path.exists(file_path):
        print(f"❌ File non trovato: {file_path}")
        return

    try:
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        df.fillna("", inplace=True)

        for col in df.columns:
            df[col] = df[col].astype(str)

        # Eventuale rinomina colonna "Peso"
        # for col in df.columns:
        #     if col.startswith("Peso"):
        #         df.rename(columns={col: "Peso"}, inplace=True)
        #         print(df.columns)
        #         break

        df.rename(columns=excel_to_db_fields, inplace=True)

        # Controllo colonne mancanti
        expected_cols = list(excel_to_db_fields.values())
        missing_cols = [c for c in expected_cols if c not in df.columns]
        if missing_cols:
            print(f"❌ Mancano colonne nel file Excel: {missing_cols}")
            return

        # # Record senza responsabile
        # senza_responsabile = df[df["responsabile_laboratorio"] == ""]

        with engine.connect() as conncreate:
            conncreate.execute(
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
                    deleted TIMESTAMP DEFAULT NULL
                )
            """)
            )
            conncreate.commit()

        with engine.connect() as conn:
            conn.execute(
                text("SET LOCAL application_name = :user"),
                {"user": user_email},
            )

            for _, row in df.iterrows():
                # print("row to insert", _, row)
                sql = text("""
                    INSERT INTO inventario (
                        indirizzo, piano, codice_sipi_torino,
                        nome_strumento, responsabile_strumento, dimensioni, peso,
                        collegamento_autonomia, ditta_collegamento, delicatezza,
                        difficolta, quale_difficolta, codice_sipi_grugliasco, note
                    ) VALUES (
                        :indirizzo, :piano, :codice_sipi_torino,
                        :nome_strumento, :responsabile_strumento, :dimensioni, :peso,
                        :collegamento_autonomia, :ditta_collegamento, :delicatezza,
                        :difficolta, :quale_difficolta, :codice_sipi_grugliasco, :note
                    )
                """)
                conn.execute(sql, row.to_dict())

            conn.commit()

        print("✅ File caricato e dati inseriti con successo!")

        # if not senza_responsabile.empty:
        #     print(f"⚠️ {len(senza_responsabile)} beni senza responsabile di laboratorio:")
        #     for _, row in senza_responsabile.iterrows():
        #         print(f"- {row['descrizione_bene']} (inv: {row['num_inventario']})")

    except Exception as e:
        print(f"❌ Errore nel caricamento del file: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python upload_excel_cli.py <file_excel.xlsx>")
    else:
        upload_excel(sys.argv[1])
