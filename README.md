# Disponento sistema logistikai

## Aprašymas
DISPO – sistema, skirta logistikos įmonėms centralizuotai ir realiu laiku valdyti krovinius, transporto priemones, darbuotojus, klientus ir užsakymus.

## Pagrindinės funkcijos
- Krovinių, vilkikų, priekabų ir darbuotojų valdymas vienoje sistemoje.
- Klientų kreditų limitų tikrinimas.
- Vilkikų ir priekabų priskyrimo, keitimo galimybės.
- Regionų administravimas ekspedicijos grupėms.
- Patogus Streamlit naudotojo sąsajos dizainas.

## Ekrano nuotraukos
*(Pridėk pagrindinių programos langų ekrano nuotraukas čia)*

## Reikalavimai
- Python >=3.9
- streamlit
- pandas
- pytest

## Diegimas ir paleidimas
1. Atsisiųskite projekto failus.
2. Instaliuokite priklausomybes:
    ```
    pip install -r requirements.txt
    ```
3. Paleiskite programą:
    ```
    streamlit run main.py
    ```
4. Testų paleidimas:
    ```
    python -m pytest
    ```

## Testavimas
Testavimui naudojamas pytest. Testai tikrina ar duomenų bazėje sukuriamos reikalingos lentelės bei ar galima pridėti klientą ir vilkiką.

## Struktūra
- `main.py` – pagrindinis failas, kuris paleidžia programą
- `db.py` – duomenų bazės inicializacija
- `test_db.py` – testų failas
- `requirements.txt` – priklausomybės
- `modules/` – visi programos moduliai (darbuotojai, vilkikai, priekabos ir t.t.)

## Kontaktai
Projektas pateiktas per GitHub arba archyvuotas kaip `.zip` failas.
