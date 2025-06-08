import streamlit as st
import pandas as pd
from datetime import date

def show(conn, c):
    # 1) Užtikrinti, kad reikalingi stulpeliai egzistuotų
    existing_cols = [r[1] for r in c.execute("PRAGMA table_info(vilkikai)").fetchall()]
    extras = {
        "draudimas": "TEXT",
        "pagaminimo_metai": "INTEGER",
        "marke": "TEXT",
        "tech_apziura": "TEXT",
        "vadybininkas": "TEXT",
        "vairuotojai": "TEXT",
        "priekaba": "TEXT"
    }
    for col, col_type in extras.items():
        if col not in existing_cols:
            c.execute(f"ALTER TABLE vilkikai ADD COLUMN {col} {col_type}")
    conn.commit()

    # 2) Paruošti išskleidžiamuosius sąrašus
    priekabu_list = [r[0] for r in c.execute("SELECT numeris FROM priekabos").fetchall()]
    markiu_list = [r[0] for r in c.execute("SELECT reiksme FROM lookup WHERE kategorija = 'Markė'").fetchall()]
    vairuotoju_list = [f"{r[1]} {r[2]}" for r in c.execute("SELECT id, vardas, pavarde FROM vairuotojai").fetchall()]

    vadybininku_list = [
        f"{r[0]} {r[1]}"
        for r in c.execute(
            "SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe = ?",
            ("Transporto vadybininkas",)
        ).fetchall()
    ]
    vadybininku_dropdown = [""] + vadybininku_list  # pirmasis elementas tuščias

    # 3) Atgaliniai kvietimai sesijos būsenai
    def clear_selection():
        st.session_state.selected_vilk = None
        for key in list(st.session_state.keys()):
            if key.startswith("f_"):
                st.session_state[key] = ""

    def new_vilk():
        st.session_state.selected_vilk = 0

    def edit_vilk(numeris):
        st.session_state.selected_vilk = numeris

    # 4) Antraštė
    st.title("Vilkikų valdymas")

    # 5) Inicializuoti sesijos būseną, jei dar neapibrėžta
    if 'selected_vilk' not in st.session_state:
        st.session_state.selected_vilk = None

    # 6) Jei vilkikas nėra pasirinktas, rodyti sąrašą ir „Priekabų paskirstymo“ formą
    if st.session_state.selected_vilk is None:
        # 6.1) „Bendras priekabų priskirstymas“ forma
        st.markdown("### 🔄 Bendras priekabų priskirstymas")
        with st.form("priekabu_priskirt_forma", clear_on_submit=True):
            vilk_list = [""] + [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]
            pr_opts = [""]

            # Sudaryti priekabų parinktis:
            for num in priekabu_list:
                assigned_row = c.execute(
                    "SELECT numeris FROM vilkikai WHERE priekaba = ?", (num,)
                ).fetchone()

                # Jei priskirta kitam vilkikui, pažymėti raudonai su to vilkiko numeriu
                if assigned_row and assigned_row[0] != "":
                    assigned_truck = assigned_row[0]
                    pr_opts.append(f"🔴 {num} ({assigned_truck})")
                else:
                    # Jei nepriskirta arba paskirta šiam vilkikui – laikyti laisva (žalia)
                    pr_opts.append(f"🟢 {num} (laisva)")

            sel_vilk = st.selectbox("Pasirinkite vilkiką", vilk_list, key="f_sel_vilk")
            sel_priek = st.selectbox("Pasirinkite priekabą", pr_opts, key="f_sel_priek")
            upd = st.form_submit_button("💾 Išsaugoti")

        if upd and sel_vilk:
            # 6.1.a) Išgauti priekabos numerį
            prn = ""
            if sel_priek and (sel_priek.startswith("🟢") or sel_priek.startswith("🔴")):
                parts = sel_priek.split(" ", 1)
                if len(parts) > 1:
                    prn = parts[1].split()[0]

            # 6.1.b) Dabartinė priekaba pasirinktame vilkike
            cur = c.execute(
                "SELECT priekaba FROM vilkikai WHERE numeris = ?", (sel_vilk,)
            ).fetchone()
            cur_trailer = cur[0] if cur and cur[0] else ""

            # 6.1.c) Patikrinti, ar prn jau priskirta kitam vilkikui
            other = c.execute(
                "SELECT numeris FROM vilkikai WHERE priekaba = ?", (prn,)
            ).fetchone()

            # 6.1.d) Jei taip, sukeisti: kitam vilkikui priskirti cur_trailer
            if other and other[0] != sel_vilk:
                other_truck = other[0]
                c.execute(
                    "UPDATE vilkikai SET priekaba = ? WHERE numeris = ?",
                    (cur_trailer or "", other_truck)
                )

            # 6.1.e) Priskirti prn (arba tuščią) sel_vilk
            c.execute(
                "UPDATE vilkikai SET priekaba = ? WHERE numeris = ?",
                (prn or "", sel_vilk)
            )
            conn.commit()
            st.success("✅ Priekabos paskirstymas sėkmingai atnaujintas.")
            clear_selection()

        # 6.2) „Pridėti naują vilkiką“ mygtukas
        st.button("➕ Pridėti naują vilkiką", on_click=new_vilk, use_container_width=True)

        # 6.3) Vilkikų sąrašo atvaizdavimas (rūšiuojant pagal tech_apziura)
        df = pd.read_sql_query("SELECT * FROM vilkikai ORDER BY tech_apziura ASC", conn)
        if df.empty:
            st.info("🔍 Kol kas nėra vilkikų.")
            return

        # 6.4) DataFrame paruošimas rodymui
        df = df.fillna('')
        df_disp = df.copy()
        df_disp.rename(columns={
            'marke': 'Modelis',
            'pagaminimo_metai': 'Pirmos registracijos data',
            'vadybininkas': 'Transporto vadybininkas'
        }, inplace=True)

        # Išskaidyti vairuotojus
        drivers = df_disp.get('vairuotojai', pd.Series(dtype=str)).fillna('')
        drivers_df = drivers.str.split(', ', n=1, expand=True)
        if drivers_df.shape[1] < 2:
            drivers_df[1] = ''
        drivers_df = drivers_df.fillna('')
        df_disp['Vairuotojas 1'] = drivers_df[0]
        df_disp['Vairuotojas 2'] = drivers_df[1]
        df_disp.drop(columns=['vairuotojai'], inplace=True)

        # Dienų skaičius iki techninės apžiūros ir draudimo pabaigos
        df_disp['Liko iki tech apžiūros'] = df_disp['tech_apziura'].apply(
            lambda x: (date.fromisoformat(x) - date.today()).days if x else ''
        )
        df_disp['Liko iki draudimo'] = df_disp['draudimas'].apply(
            lambda x: (date.fromisoformat(x) - date.today()).days if x else ''
        )

        # 6.5) Filtrai (pradžios atitikimas)
        filter_cols = st.columns(len(df_disp.columns) + 1)
        for i, col in enumerate(df_disp.columns):
            filter_cols[i].text_input(label="", placeholder=col, key=f"f_{col}")
        filter_cols[-1].write("")

        df_filt = df_disp.copy()
        for col in df_disp.columns:
            val = st.session_state.get(f"f_{col}", "")
            if val:
                df_filt = df_filt[
                    df_filt[col].astype(str).str.lower().str.startswith(val.lower())
                ]

        # 6.6) Eilutės su redagavimo mygtukais
        for _, row in df_filt.iterrows():
            row_cols = st.columns(len(df_filt.columns) + 1)
            for i, col in enumerate(df_filt.columns):
                row_cols[i].write(row[col])
            row_cols[-1].button(
                "✏️",
                key=f"edit_{row['numeris']}",
                on_click=edit_vilk,
                args=(row['numeris'],)
            )

        # 6.7) CSV eksportas
        csv = df.to_csv(index=False, sep=';').encode('utf-8')
        st.download_button(
            label="💾 Eksportuoti kaip CSV",
            data=csv,
            file_name="vilkikai.csv",
            mime="text/csv"
        )
        return

    # 7) Jei vilkikas pasirinktas (naujas/redagavimas), rodyti detalų formą
    sel = st.session_state.selected_vilk
    is_new = (sel == 0)
    vilk = {}
    if not is_new:
        df_v = pd.read_sql_query("SELECT * FROM vilkikai WHERE numeris = ?", conn, params=(sel,))
        if df_v.empty:
            st.error("❌ Vilkikas nerastas.")
            clear_selection()
            return
        vilk = df_v.iloc[0].to_dict()

    # Sudaryti priskirtų vairuotojų rinkinį (išskyrus esamą, jei redaguojama)
    assigned_set = set()
    for row in c.execute("SELECT numeris, vairuotojai FROM vilkikai").fetchall():
        numeris_row, drv_str = row
        if drv_str:
            for drv in drv_str.split(', '):
                if not (not is_new and numeris_row == sel and drv):
                    assigned_set.add(drv)

    # Sudaryti priskirtų priekabų rinkinį (išskyrus esamą, jei redaguojama)
    assigned_trailers = set()
    for row in c.execute("SELECT numeris, priekaba FROM vilkikai").fetchall():
        numeris_row, pr_str = row
        if pr_str:
            if not (not is_new and numeris_row == sel and pr_str):
                assigned_trailers.add(pr_str)

    with st.form("vilkiku_forma", clear_on_submit=False):
        col1, col2 = st.columns(2)

        # 7.1) Pirmojo stulpelio laukai
        numeris = col1.text_input("Vilkiko numeris", value=("" if is_new else vilk.get('numeris', '')))

        opts_m = [""] + markiu_list
        idx_m = 0
        if (not is_new) and vilk.get('marke') in markiu_list:
            idx_m = opts_m.index(vilk['marke'])
        modelis = col1.selectbox("Modelis", opts_m, index=idx_m)

        pr_initial = date.fromisoformat(vilk['pagaminimo_metai']) if (not is_new and vilk.get('pagaminimo_metai')) else None
        pr_data = col1.date_input("Pirmos registracijos data", value=pr_initial, key="pr_data")

        tech_initial = date.fromisoformat(vilk['tech_apziura']) if (not is_new and vilk.get('tech_apziura')) else None
        tech_date = col1.date_input("Tech. apžiūros pabaiga", value=tech_initial, key="tech_date")

        draud_initial = date.fromisoformat(vilk['draudimas']) if (not is_new and vilk.get('draudimas')) else None
        draud_date = col1.date_input("Draudimo galiojimo pabaiga", value=draud_initial, key="draud_date")

        # 7.2) Antrojo stulpelio laukai
        if not is_new and vilk.get('vadybininkas', "") in vadybininku_list:
            vadyb_idx = vadybininku_dropdown.index(vilk['vadybininkas'])
        else:
            vadyb_idx = 0
        vadyb = col2.selectbox("Transporto vadybininkas", vadybininku_dropdown, index=vadyb_idx)

        transporto_grupe = ""
        if vadyb:
            parts = vadyb.split(" ")
            vard = parts[0]
            pav = parts[1] if len(parts) > 1 else ""
            gr = c.execute(
                "SELECT grupe FROM darbuotojai WHERE vardas = ? AND pavarde = ?",
                (vard, pav)
            ).fetchone()
            transporto_grupe = gr[0] if gr and gr[0] else ""
        col2.text_input("Transporto grupė", value=transporto_grupe, disabled=True)

        # 7.3) Vairuotojų išskleidžiamieji sąrašai
        v1_opts = [""]
        for name in vairuotoju_list:
            if name in assigned_set:
                v1_opts.append(f"🔴 {name}")
            else:
                v1_opts.append(f"🟢 {name}")

        v1_idx = 0
        v2_idx = 0
        if not is_new and vilk['vairuotojai']:
            parts = vilk['vairuotojai'].split(', ')
            if parts:
                for idx, opt in enumerate(v1_opts):
                    if opt.endswith(parts[0]):
                        v1_idx = idx
                        break
                if len(parts) > 1:
                    for idx, opt in enumerate(v1_opts):
                        if opt.endswith(parts[1]):
                            v2_idx = idx
                            break

        v1 = col2.selectbox("Vairuotojas 1", v1_opts, index=v1_idx, key="v1")
        v2 = col2.selectbox("Vairuotojas 2", v1_opts, index=v2_idx, key="v2")

        # 7.4) Priekabų išskleidžiamasis sąrašas su būsenos ikonėlėmis
        pr_opts = [""]
        for num in priekabu_list:
            if num in assigned_trailers:
                assigned_truck = c.execute(
                    "SELECT numeris FROM vilkikai WHERE priekaba = ?", (num,)
                ).fetchone()[0]
                pr_opts.append(f"🔴 {num} ({assigned_truck})")
            else:
                pr_opts.append(f"🟢 {num} (laisva)")

        pr_idx = 0
        if (not is_new) and vilk.get('priekaba'):
            for idx, opt in enumerate(pr_opts):
                if opt.endswith(vilk['priekaba']):
                    pr_idx = idx
                    break
        sel_pr = col2.selectbox("Priekaba", pr_opts, index=pr_idx)

        # 7.5) Formos mygtukai
        back = st.form_submit_button("🔙 Grįžti į sąrašą", on_click=clear_selection)
        submit = st.form_submit_button("📅 Išsaugoti vilkiką")

    # 8) Apdoroti formos pateikimą
    if submit:
        def extract_name(selection):
            if selection and (selection.startswith("🟢") or selection.startswith("🔴")):
                name = selection.split(" ", 1)[1]
                return name.split(" ")[0] if "(" in name and ")" in name else name
            return ""
        drv1_name = extract_name(v1)
        drv2_name = extract_name(v2)

        # 8.1) Neleisti priskirti vairuotojo, kuris jau priskirtas
        if drv1_name and drv1_name in assigned_set:
            st.warning(f"⚠️ Vairuotojas {drv1_name} jau priskirtas kitam vilkikui.")
        # 8.2) Neleisti pasirinkti tą patį vairuotoją du kartus
        elif drv2_name and drv2_name in assigned_set:
            st.warning(f"⚠️ Vairuotojas {drv2_name} jau priskirtas kitam vilkikui.")
        elif drv1_name and drv2_name and drv1_name == drv2_name:
            st.warning("⚠️ Vairuotojas negali būti ir Vairuotojas 1, ir Vairuotojas 2 vienu metu.")
        elif not numeris:
            st.warning("⚠️ Įveskite vilkiko numerį.")
        else:
            # 8.3) Išgauti priekabos numerį
            trailer = ""
            if sel_pr and (sel_pr.startswith("🟢") or sel_pr.startswith("🔴")):
                trailer = sel_pr.split(" ", 1)[1].split()[0]

            # 8.4) Dabartinė šio vilkiko priekaba
            cur = c.execute(
                "SELECT priekaba FROM vilkikai WHERE numeris = ?", (sel,)
            ).fetchone()
            cur_trailer = cur[0] if cur and cur[0] else ""

            # 8.5) Patikrinti, ar priekaba jau priskirta kitam vilkikui
            other = c.execute(
                "SELECT numeris FROM vilkikai WHERE priekaba = ?", (trailer,)
            ).fetchone()

            if other and other[0] != sel:
                other_truck = other[0]
                # Sukeisti: kitam vilkikui priskirti dabartinę priekabą
                c.execute(
                    "UPDATE vilkikai SET priekaba = ? WHERE numeris = ?",
                    (cur_trailer or "", other_truck)
                )

            # 8.6) Priskirti priekabą šiam vilkikui
            c.execute(
                "UPDATE vilkikai SET priekaba = ? WHERE numeris = ?",
                (trailer or "", sel)
            )

            # 8.7) Sukonstruoti vairuotojų tekstą
            vairuotoju_text = ", ".join(filter(None, [drv1_name, drv2_name])) or ''
            try:
                if is_new:
                    c.execute(
                        """INSERT INTO vilkikai 
                           (numeris, marke, pagaminimo_metai, tech_apziura, draudimas, 
                            vadybininkas, vairuotojai, priekaba)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            numeris,
                            modelis or '',
                            pr_data.isoformat() if pr_data else '',
                            tech_date.isoformat() if tech_date else '',
                            draud_date.isoformat() if draud_date else '',
                            vadyb or '',
                            vairuotoju_text,
                            trailer
                        )
                    )
                else:
                    c.execute(
                        """UPDATE vilkikai 
                           SET marke=?, pagaminimo_metai=?, tech_apziura=?, draudimas=?, 
                               vadybininkas=?, vairuotojai=?, priekaba=? 
                           WHERE numeris=?""",
                        (
                            modelis or '',
                            pr_data.isoformat() if pr_data else '',
                            tech_date.isoformat() if tech_date else '',
                            draud_date.isoformat() if draud_date else '',
                            vadyb or '',
                            vairuotoju_text,
                            trailer,
                            sel
                        )
                    )
                conn.commit()
                st.success("✅ Vilkikas išsaugotas sėkmingai.")
                if tech_date:
                    st.info(f"🔧 Dienų iki tech. apžiūros liko: {(tech_date - date.today()).days}")
                if draud_date:
                    st.info(f"🛡️ Dienų iki draudimo pabaigos liko: {(draud_date - date.today()).days}")
                clear_selection()
            except Exception as e:
                st.error(f"❌ Klaida saugant: {e}")
    # 9) show() funkcijos pabaiga
