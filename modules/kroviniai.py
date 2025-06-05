import streamlit as st
import pandas as pd
from datetime import date, time, timedelta

EU_COUNTRIES = [
    ("", ""), ("Lietuva", "LT"), ("Baltarusija", "BY"), ("Latvija", "LV"), ("Lenkija", "PL"), ("Vokietija", "DE"),
    ("Prancūzija", "FR"), ("Ispanija", "ES"), ("Italija", "IT"), ("Olandija", "NL"), ("Belgija", "BE"),
    ("Austrija", "AT"), ("Švedija", "SE"), ("Suomija", "FI"), ("Čekija", "CZ"), ("Slovakija", "SK"),
    ("Vengrija", "HU"), ("Rumunija", "RO"), ("Bulgarija", "BG"), ("Danija", "DK"), ("Norvegija", "NO"),
    ("Šveicarija", "CH"), ("Kroatija", "HR"), ("Slovėnija", "SI"), ("Portugalija", "PT"), ("Graikija", "GR"),
    ("Airija", "IE"), ("Didžioji Britanija", "GB"),
]

HEADER_LABELS = {
    "id": "ID",
    "busena": "Būsena",
    "pakrovimo_data": "Pakr. data",
    "iskrovimo_data": "Iškr. data",
    "pakrovimo_vieta": "Pakr. vieta",
    "iskrovimo_vieta": "Iškr. vieta",
    "klientas": "Klientas",
    "vilkikas": "Vilkikas",
    "priekaba": "Priekaba",
    "ekspedicijos_vadybininkas": "Eksp. vadyb.",
    "transporto_vadybininkas": "Transp. vadyb.",
    "atsakingas_vadybininkas": "Atsak. vadyb.",
    "uzsakymo_numeris": "Užsak. nr.",
    "kilometrai": "Km",
    "frachtas": "Frachtas",
    "saskaitos_busena": "Sąskaitos būsena"
}

FIELD_ORDER = [
    "id", "busena", "pakrovimo_data", "iskrovimo_data",
    "pakrovimo_vieta", "iskrovimo_vieta",
    "klientas", "vilkikas", "priekaba", "ekspedicijos_vadybininkas",
    "transporto_vadybininkas", "atsakingas_vadybininkas",
    "uzsakymo_numeris", "kilometrai", "frachtas",
    "saskaitos_busena"
]

def get_busena(c, krovinys):
    if not krovinys.get("vilkikas"):
        return "Nesuplanuotas"
    if krovinys.get("vilkikas") == "":
        return "Nesuplanuotas"
    busena = "Suplanuotas"
    r = c.execute("""
        SELECT pakrovimo_statusas, iskrovimo_statusas
        FROM vilkiku_darbo_laikai
        WHERE vilkiko_numeris = ? AND data = ?
        ORDER BY id DESC LIMIT 1
    """, (krovinys['vilkikas'], krovinys['pakrovimo_data'])).fetchone()
    if not r:
        return busena
    pk_status, ik_status = r
    if ik_status == "Iškrauta":
        return "Iškrauta"
    if ik_status == "Atvyko":
        return "Atvyko į iškrovimą"
    if ik_status == "Kita" and pk_status != "Pakrauta":
        return "Kita (iškrovimas)"
    if pk_status == "Pakrauta":
        return "Pakrauta"
    if pk_status == "Atvyko":
        return "Atvyko į pakrovimą"
    if pk_status == "Kita":
        return "Kita (pakrovimas)"
    return busena

def get_vieta(salis, regionas):
    if not salis:
        return ""
    return f"{salis}{regionas or ''}"

def show(conn, c):
    st.title("Užsakymų valdymas")
    add_clicked = st.button("➕ Pridėti naują krovinį", use_container_width=True)

    # Įsitikiname, kad lentelėje 'kroviniai' yra visi reikiami stulpeliai
    expected = {
        'klientas': 'TEXT',
        'uzsakymo_numeris': 'TEXT',
        'pakrovimo_salis': 'TEXT',
        'pakrovimo_regionas': 'TEXT',
        'pakrovimo_miestas': 'TEXT',
        'pakrovimo_adresas': 'TEXT',
        'pakrovimo_data': 'TEXT',
        'pakrovimo_laikas_nuo': 'TEXT',
        'pakrovimo_laikas_iki': 'TEXT',
        'iskrovimo_salis': 'TEXT',
        'iskrovimo_regionas': 'TEXT',
        'iskrovimo_miestas': 'TEXT',
        'iskrovimo_adresas': 'TEXT',
        'iskrovimo_data': 'TEXT',
        'iskrovimo_laikas_nuo': 'TEXT',
        'iskrovimo_laikas_iki': 'TEXT',
        'vilkikas': 'TEXT',
        'priekaba': 'TEXT',
        'atsakingas_vadybininkas': 'TEXT',
        'ekspedicijos_vadybininkas': 'TEXT',
        'transporto_vadybininkas': 'TEXT',
        'kilometrai': 'INTEGER',
        'frachtas': 'REAL',
        'svoris': 'INTEGER',
        'paleciu_skaicius': 'INTEGER',
        'saskaitos_busena': 'TEXT',
        'busena': 'TEXT'
    }
    c.execute("PRAGMA table_info(kroviniai)")
    existing = {r[1] for r in c.fetchall()}
    for col, typ in expected.items():
        if col not in existing:
            try:
                c.execute(f"ALTER TABLE kroviniai ADD COLUMN {col} {typ}")
            except Exception as e:
                # Jei jau egzistuoja, praleidžiame
                if "duplicate column name" in str(e).lower():
                    pass
                else:
                    raise
    conn.commit()  # :contentReference[oaicite:0]{index=0}

    # Paruošiame dropdown sąrašus ir žemėlapius
    klientai = [r[0] for r in c.execute("SELECT pavadinimas FROM klientai").fetchall()]
    if len(klientai) == 0:
        st.warning("Nėra nė vieno kliento! Pridėkite klientą modulyje **Klientai** ir grįžkite čia.")
        return

    vilkikai = [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]
    eksped_vadybininkai = [
        f"{r[0]} {r[1]}"
        for r in c.execute("SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe = ?", ("Ekspedicijos vadybininkas",)).fetchall()
    ]
    eksped_dropdown = [""] + eksped_vadybininkai
    vilkikai_df = pd.read_sql_query("SELECT numeris, vadybininkas FROM vilkikai", conn)
    vilk_vad_map = {r['numeris']: r['vadybininkas'] for _, r in vilkikai_df.iterrows()}

    # Sudarome žemėlapį: klientas → likes_limitas (dabar esamas)
    df_klientai = pd.read_sql_query("SELECT pavadinimas, likes_limitas FROM klientai", conn)
    klientu_limitai = {row['pavadinimas']: row['likes_limitas'] for _, row in df_klientai.iterrows()}

    if 'selected_cargo' not in st.session_state:
        st.session_state['selected_cargo'] = None
    if add_clicked:
        st.session_state['selected_cargo'] = 0

    def clear_sel():
        st.session_state['selected_cargo'] = None
        for k in list(st.session_state):
            if k.startswith("f_"):
                st.session_state[k] = ""

    def edit_cargo(cid):
        st.session_state['selected_cargo'] = cid

    sel = st.session_state['selected_cargo']

    # 4. Esamų krovinių sąrašas
    if sel is None:
        df = pd.read_sql_query("SELECT * FROM kroviniai", conn)
        if df.empty:
            st.info("Kol kas nėra krovinių.")
        else:
            # Sukuriame sujungtus stulpelius
            df["pakrovimo_vieta"] = df.apply(lambda r: get_vieta(r.get('pakrovimo_salis', ''), r.get('pakrovimo_regionas', '')), axis=1)
            df["iskrovimo_vieta"] = df.apply(lambda r: get_vieta(r.get('iskrovimo_salis', ''), r.get('iskrovimo_regionas', '')), axis=1)
            df["transporto_vadybininkas"] = df["vilkikas"].map(vilk_vad_map).fillna("")
            df["atsakingas_vadybininkas"] = df["vilkikas"].map(vilk_vad_map).fillna("")
            busenos = []
            for _, row in df.iterrows():
                busenos.append(get_busena(c, row))
            df["busena"] = busenos

            df_disp = df[FIELD_ORDER].fillna("")

            # Filtrai viršuje
            filter_cols = st.columns(len(df_disp.columns) + 1)
            for i, col in enumerate(df_disp.columns):
                filter_cols[i].text_input(
                    " ",
                    key=f"f_{col}",
                    label_visibility="collapsed"
                )
            filter_cols[-1].write("")

            df_f = df_disp.copy()
            for col in df_disp.columns:
                v = st.session_state.get(f"f_{col}", "")
                if v:
                    df_f = df_f[df_f[col].astype(str).str.contains(v, case=False, na=False)]

            hdr = st.columns(len(df_disp.columns) + 1)
            for i, col in enumerate(df_disp.columns):
                label = HEADER_LABELS.get(col, col.replace("_", "<br>")[:14])
                hdr[i].markdown(f"<b>{label}</b>", unsafe_allow_html=True)
            hdr[-1].markdown("<b>Veiksmai</b>", unsafe_allow_html=True)

            for _, row in df_f.iterrows():
                row_cols = st.columns(len(df_disp.columns) + 1)
                for i, col in enumerate(df_disp.columns):
                    row_cols[i].write(row[col])
                row_cols[-1].button(
                    "✏️",
                    key=f"edit_{row['id']}",
                    on_click=edit_cargo,
                    args=(row['id'],)
                )

    # 5. Forma krovinio pridėjimui/redagavimui
    if sel is not None:
        is_new = (sel == 0)
        if not is_new:
            df_sel = pd.read_sql_query("SELECT * FROM kroviniai WHERE id = ?", conn, params=(sel,))
            if df_sel.empty:
                st.error("Krovinys nerastas.")
                clear_sel()
                return
            row = df_sel.iloc[0]
        else:
            row = {}

        with st.form("cargo_form", clear_on_submit=False):
            klientas = st.selectbox(
                "Klientas",
                [""] + klientai,
                index=(klientai.index(row['klientas']) + 1 if not is_new and row.get('klientas') in klientai else 0)
            )
            uzsak = st.text_input("Užsakymo numeris", value=row.get('uzsakymo_numeris', ""))

            # Pakrovimo vieta
            col1, col2 = st.columns(2)
            with col1:
                pk_salis = st.selectbox(
                    "Pakrovimo šalis",
                    [c[0] for c in EU_COUNTRIES],
                    index=(next((i for i, t in enumerate(EU_COUNTRIES) if t[0] == row.get('pakrovimo_salis')), 0))
                )
            with col2:
                pk_regionas = st.text_input("Pakrovimo regionas", value=row.get('pakrovimo_regionas', ""))
            pk_mie = st.text_input("Pakrovimo miestas", value=row.get('pakrovimo_miestas', ""))
            pk_adr = st.text_input("Pakrovimo adresas", value=row.get('pakrovimo_adresas', ""))
            pk_data = st.date_input(
                "Pakrovimo data",
                value=date.fromisoformat(row['pakrovimo_data']) if not is_new and row.get('pakrovimo_data') else date.today()
            )
            pk_nuo = st.time_input(
                "Laikas nuo",
                value=time.fromisoformat(row['pakrovimo_laikas_nuo']) if not is_new and row.get('pakrovimo_laikas_nuo') else time(hour=8, minute=0)
            )
            pk_iki = st.time_input(
                "Laikas iki",
                value=time.fromisoformat(row['pakrovimo_laikas_iki']) if not is_new and row.get('pakrovimo_laikas_iki') else time(hour=17, minute=0)
            )

            # Iškrovimo vieta
            col3, col4 = st.columns(2)
            with col3:
                is_salis = st.selectbox(
                    "Iškrovimo šalis",
                    [c[0] for c in EU_COUNTRIES],
                    index=(next((i for i, t in enumerate(EU_COUNTRIES) if t[0] == row.get('iskrovimo_salis')), 0))
                )
            with col4:
                is_regionas = st.text_input("Iškrovimo regionas", value=row.get('iskrovimo_regionas', ""))
            is_mie = st.text_input("Iškrovimo miestas", value=row.get('iskrovimo_miestas', ""))
            is_adr = st.text_input("Iškrovimo adresas", value=row.get('iskrovimo_adresas', ""))
            isk_data = st.date_input(
                "Iškrovimo data",
                value=date.fromisoformat(row['iskrovimo_data']) if not is_new and row.get('iskrovimo_data') else date.today()
            )
            is_nuo = st.time_input(
                "Iškr. laikas nuo",
                value=time.fromisoformat(row['iskrovimo_laikas_nuo']) if not is_new and row.get('iskrovimo_laikas_nuo') else time(hour=8, minute=0)
            )
            is_iki = st.time_input(
                "Iškr. laikas iki",
                value=time.fromisoformat(row['iskrovimo_laikas_iki']) if not is_new and row.get('iskrovimo_laikas_iki') else time(hour=17, minute=0)
            )

            # Transportas ir vadybininkai
            vilk = st.selectbox(
                "Vilkikas",
                [""] + vilkikai,
                index=(vilkikai.index(row['vilkikas']) + 1 if not is_new and row.get('vilkikas') in vilkikai else 0)
            )
            priekaba_value = st.text_input("Priekaba", value=row.get('priekaba', ""))
            eksped_vad = st.selectbox(
                "Ekspedicijos vadybininkas",
                eksped_dropdown,
                index=(eksped_dropdown.index(row['ekspedicijos_vadybininkas']) if not is_new and row.get('ekspedicijos_vadybininkas') in eksped_dropdown else 0)
            )
            transp_vad = st.text_input("Transporto vadybininkas", value=row.get('transporto_vadybininkas', ""))

            # Krovinio duomenys
            km_int = st.number_input("Kilometrai", min_value=0, value=row.get('kilometrai', 0), step=1)
            frachtas_float = st.number_input("Frachtas (€)", min_value=0.0, value=row.get('frachtas', 0.0), step=0.01, format="%.2f")
            sv_int = st.number_input("Svoris (kg)", min_value=0, value=row.get('svoris', 0), step=1)
            pal_int = st.number_input("Palecių skaičius", min_value=0, value=row.get('paleciu_skaicius', 0), step=1)
            sask_busenos = ["", "Išrašyta", "Apmokėta"]
            sask_busena_val = sask_busenos[0] if is_new else row.get('saskaitos_busena', sask_busenos[0])
            sask_busena = st.selectbox(
                "Sąskaitos būsena",
                sask_busenos,
                index=sask_busenos.index(sask_busena_val)
            )

            save = st.form_submit_button("💾 Išsaugoti")

            if save:
                vals = {
                    'klientas': klientas,
                    'uzsakymo_numeris': uzsak,
                    'pakrovimo_salis': pk_salis,
                    'pakrovimo_regionas': pk_regionas,
                    'pakrovimo_miestas': pk_mie,
                    'pakrovimo_adresas': pk_adr,
                    'pakrovimo_data': pk_data.isoformat(),
                    'pakrovimo_laikas_nuo': pk_nuo.isoformat(),
                    'pakrovimo_laikas_iki': pk_iki.isoformat(),
                    'iskrovimo_salis': is_salis,
                    'iskrovimo_regionas': is_regionas,
                    'iskrovimo_miestas': is_mie,
                    'iskrovimo_adresas': is_adr,
                    'iskrovimo_data': isk_data.isoformat(),
                    'iskrovimo_laikas_nuo': is_nuo.isoformat(),
                    'iskrovimo_laikas_iki': is_iki.isoformat(),
                    'vilkikas': vilk,
                    'priekaba': priekaba_value,
                    'atsakingas_vadybininkas': transp_vad,
                    'ekspedicijos_vadybininkas': eksped_vad,
                    'transporto_vadybininkas': transp_vad,
                    'kilometrai': km_int,
                    'frachtas': frachtas_float,
                    'svoris': sv_int,
                    'paleciu_skaicius': pal_int,
                    'saskaitos_busena': sask_busena
                }

                try:
                    if is_new:
                        cols = ",".join(vals.keys())
                        placeholders = ",".join(["?"] * len(vals))
                        q = f"INSERT INTO kroviniai ({cols}) VALUES ({placeholders})"
                        c.execute(q, tuple(vals.values()))
                    else:
                        set_str = ",".join(f"{k}=?" for k in vals)
                        q = f"UPDATE kroviniai SET {set_str} WHERE id=?"
                        c.execute(q, tuple(vals.values()) + (sel,))
                    conn.commit()

                    # Atnaujiname klientų limitus: suskaičiuojame nesumokėtų faktūrų sumą
                    unpaid_total = 0.0
                    try:
                        r2 = c.execute("""
                            SELECT SUM(k.frachtas)
                            FROM kroviniai AS k
                            JOIN klientai AS cl ON k.klientas = cl.pavadinimas
                            WHERE cl.vat_numeris = ?
                              AND k.saskaitos_busena != 'Apmokėta'
                        """, (klientas,)).fetchone()
                        if r2 and r2[0] is not None:
                            unpaid_total = r2[0]
                    except:
                        unpaid_total = 0.0

                    # Naujas limitas: 1/3 musu_limitas – nesumokėtos sumos skirtumas
                    new_musu = klientu_limitai.get(klientas, 0.0) / 3.0
                    new_liks = new_musu - unpaid_total
                    if new_liks < 0:
                        new_liks = 0.0

                    c.execute("""
                        UPDATE klientai
                        SET musu_limitas = ?, likes_limitas = ?
                        WHERE pavadinimas = ?
                    """, (new_musu, new_liks, klientas))
                    conn.commit()

                    st.success("✅ Krovinys išsaugotas ir limitai atnaujinti.")
                    clear_sel()
                except Exception as e:
                    st.error(f"❌ Klaida: {e}")
