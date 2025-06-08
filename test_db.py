import os
from db import init_db

def test_sukuria_lenteles():
    # Testuojam, ar sukuriamos svarbiausios lentelės
    db_failas = "testas.db"
    if os.path.exists(db_failas):
        os.remove(db_failas)
    conn, c = init_db(db_failas)
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    lenteles = [t[0] for t in c.fetchall()]
    assert "klientai" in lenteles
    assert "vilkikai" in lenteles
    assert "kroviniai" in lenteles
    conn.close()
    os.remove(db_failas)

def test_prideda_klienta():
    # Pridedam klientą ir tikrinam ar įrašė
    db_failas = "testas.db"
    if os.path.exists(db_failas):
        os.remove(db_failas)
    conn, c = init_db(db_failas)
    c.execute("INSERT INTO klientai (pavadinimas, vat_numeris) VALUES (?, ?)", ("UAB Testas", "LT123456789"))
    conn.commit()
    c.execute("SELECT pavadinimas FROM klientai WHERE vat_numeris = ?", ("LT123456789",))
    rezultatas = c.fetchone()
    assert rezultatas[0] == "UAB Testas"
    conn.close()
    os.remove(db_failas)

def test_prideda_vilkika():
    # Pridedam vilkiką ir tikrinam ar įrašė
    db_failas = "testas.db"
    if os.path.exists(db_failas):
        os.remove(db_failas)
    conn, c = init_db(db_failas)
    c.execute("INSERT INTO vilkikai (numeris, marke) VALUES (?, ?)", ("AAA111", "MAN"))
    conn.commit()
    c.execute("SELECT marke FROM vilkikai WHERE numeris = ?", ("AAA111",))
    rezultatas = c.fetchone()
    assert rezultatas[0] == "MAN"
    conn.close()
    os.remove(db_failas)
