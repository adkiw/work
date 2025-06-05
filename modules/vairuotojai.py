# modules/vairuotojai.py
import streamlit as st
import pandas as pd
from datetime import date

# --- Galimų tautybių sąrašas ---
TAUTYBES = [
    ("", ""),
    ("Lietuva", "LT"),
    ("Baltarusija", "BY"),
    ("Ukraina", "UA"),
    ("Uzbekistanas", "UZ"),
    ("Indija", "IN"),
    ("Nigerija", "NG"),
    ("Lenkija", "PL"),
]

# ------------------------------- MAIN ------------------------------- #
def show(conn, c):
    st.title("Vairuotojų valdymas")

    # 1) Užtikrinkite, kad visi stulpeliai būtų lentelėje 'vairuotojai'
    existing = [r[1] for r in c.execute("PRAGMA table_info(vairuotojai)").fetchall()]
    extras = {
        "vardas": "TEXT",
        "pavarde": "TEXT",
        "gimimo_metai": "TEXT",
        "tautybe": "TEXT",
        "kadencijos_pabaiga": "TEXT",
        "atostogu_pabaiga": "TEXT",
    }
    for col, typ in extras.items():
        if col not in existing:
            c.execute(f"ALTER TABLE vairuotojai ADD COLUMN {col} {typ}")
    conn.commit()

    # 2) Sudarome žemėlapį „vardas pavardė → vilkiko numeris“
    driver_to_vilk = {}
    for numeris, drv_str in c.execute("SELECT numeris, vairuotojai FROM vilkikai").fetchall():
        if drv_str:
            for name in drv_str.split(", "):
                driver_to_vilk[name] = numeris

    # 3) Sesijos kintamieji
    if "selected_vair" not in st.session_state:
        st.session_state.selected_vair = None

    def clear_sel():
        st.session_state.selected_vair = None

    def new_vair():
        st.session_state.selected_vair = 0

    def edit_vair(v_id):
        st.session_state.selected_vair = v_id

    sel = st.session_state.selected_vair

    # ---------------------------------------------------------------
    # 4) Naujo vairuotojo forma
    # ---------------------------------------------------------------
    if sel == 0:
        with st.form("new_form", clear_on_submit=True):
            vardas  = st.text_input("Vardas", key="vardas")
            pavarde = st.text_input("Pavardė", key="pavarde")
            gim_data = st.date_input(
                "Gimimo data", value=date(1980, 1, 1), min_value=date(1950, 1, 1), key="gim_data"
            )
            taut_opts = [f"{name} ({code})" for name, code in TAUTYBES]
            tautybe = st.selectbox("Tautybė", taut_opts, key="tautybe")
            atost_pab = st.date_input("Atostogų pabaiga", value=date.today(), key="atost_pab")

            col1, col2 = st.columns(2)
            save = col1.form_submit_button("💾 Išsaugoti vairuotoją")
            back = col2.form_submit_button("🔙 Grįžti į sąrašą", on_click=clear_sel)

        if save:
            if not vardas or not pavarde:
                st.warning("⚠️ Privalomi laukai: vardas ir pavardė.")
            else:
                try:
                    c.execute(
                        """
                        INSERT INTO vairuotojai (
                            vardas, pavarde, gimimo_metai, tautybe,
                            kadencijos_pabaiga, atostogu_pabaiga
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            vardas,
                            pavarde,
                            gim_data.isoformat(),
                            tautybe.split("(")[-1][:-1] if "(" in tautybe else tautybe,
                            "",  # kadencijos_pabaiga – tuščia, nes nepriskirtas
                            atost_pab.isoformat()
                        ),
                    )
                    conn.commit()
                    st.success("✅ Vairuotojas įrašytas.")
                    clear_sel()
                except Exception as e:
                    st.error(f"❌ Klaida: {e}")
        return  # --- baigiam NEW VIEW ---

    # ---------------------------------------------------------------
    # 5) Redagavimo forma (kai pasirenkamas esamas vairuotojas)
    # ---------------------------------------------------------------
    if sel not in (None, 0):
        df_sel = pd.read_sql_query("SELECT * FROM vairuotojai WHERE id = ?", conn, params=(sel,))
        if df_sel.empty:
            st.error("❌ Vairuotojas nerastas.")
            clear_sel()
            return

        row = df_sel.iloc[0]
        full_name  = f"{row['vardas']} {row['pavarde']}"
        is_assigned = full_name in driver_to_vilk

        with st.form("edit_form", clear_on_submit=False):
            vardas = st.text_input("Vardas", value=row['vardas'], key="vardas")
            pavarde = st.text_input("Pavardė", value=row['pavarde'], key="pavarde")
            gim_data = st.date_input(
                "Gimimo data",
                value=date.fromisoformat(row['gimimo_metai']) if row['gimimo_metai'] else date(1980, 1, 1),
                min_value=date(1950, 1, 1),
                key="gim_data"
            )
            taut_opts = [f"{name} ({code})" for name, code in TAUTYBES]
            taut_idx = 0
            if row['tautybe']:
                for i, v in enumerate(taut_opts):
                    if row['tautybe'] in v:
                        taut_idx = i
                        break
            tautybe = st.selectbox("Tautybė", taut_opts, index=taut_idx, key="tautybe")

            # Kadencijos/atostogų laukai priklausomai nuo priskyrimo
            if is_assigned:
                kad_pab = st.date_input(
                    "Kadencijos pabaiga",
                    value=date.fromisoformat(row['kadencijos_pabaiga']) if row['kadencijos_pabaiga'] else date.today(),
                    key="kad_pab"
                )
            else:
                atost_pab = st.date_input(
                    "Atostogų pabaiga",
                    value=date.fromisoformat(row['atostogu_pabaiga']) if row['atostogu_pabaiga'] else date.today(),
                    key="atost_pab"
                )

            col1, col2 = st.columns(2)
            save = col1.form_submit_button("💾 Išsaugoti pakeitimus")
            back = col2.form_submit_button("🔙 Grįžti į sąrašą", on_click=clear_sel)

        if save:
            try:
                kad_str   = kad_pab.isoformat() if is_assigned else ""
                atost_str = atost_pab.isoformat() if not is_assigned else ""
                c.execute(
                    """
                    UPDATE vairuotojai
                    SET vardas=?, pavarde=?, gimimo_metai=?, tautybe=?,
                        kadencijos_pabaiga=?, atostogu_pabaiga=?
                    WHERE id=?
                    """,
                    (
                        vardas, pavarde, gim_data.isoformat(),
                        tautybe.split("(")[-1][:-1] if "(" in tautybe else tautybe,
                        kad_str, atost_str, sel
                    ),
                )
                conn.commit()
                st.success("✅ Pakeitimai išsaugoti.")
                clear_sel()
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
        return  # --- baigiam EDIT VIEW ---

    # ---------------------------------------------------------------
    # 6) Sąrašas (kai sel is None) – mygtukas dabar VIRŠUJE
    # ---------------------------------------------------------------
    st.button("➕ Pridėti vairuotoją", on_click=new_vair, use_container_width=True)

    # 6.1) Užkrauname sąrašą
    df = pd.read_sql_query("SELECT * FROM vairuotojai", conn)
    if df.empty:
        st.info("ℹ️ Kol kas nėra vairuotojų. Paspauskite mygtuką viršuje, kad įvestumėte pirmąjį.")
        return

    # 6.2) Paruošiame lentelę atvaizdavimui
    df = df.fillna("")
    df_disp = df[[
        "id", "vardas", "pavarde", "gimimo_metai", "tautybe",
        "kadencijos_pabaiga", "atostogu_pabaiga"
    ]].copy()
    df_disp.rename(columns={
        "vardas": "Vardas",
        "pavarde": "Pavardė",
        "gimimo_metai": "Gimimo data",
        "tautybe": "Tautybė",
        "kadencijos_pabaiga": "Kadencijos pabaiga",
        "atostogu_pabaiga": "Atostogų pabaiga"
    }, inplace=True)

    # 6.3) Rodyti lentelę su „✏️“ mygtukais
    for _, r in df_disp.iterrows():
        cols = st.columns(len(df_disp.columns) + 1)
        for i, col in enumerate(df_disp.columns):
            cols[i].write(r[col])
        cols[-1].button(
            "✏️", key=f"edit_{r['id']}", on_click=edit_vair, args=(r['id'],)
        )
