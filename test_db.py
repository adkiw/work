import os
from db import init_db

def test_db_tables():
    db_path = "test_main.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    conn, c = init_db(db_path)
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in c.fetchall()]
    assert "klientai" in tables
    assert "kroviniai" in tables
    assert "vilkikai" in tables
    conn.close()
    os.remove(db_path)

def test_add_client():
    db_path = "test_main.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    conn, c = init_db(db_path)
    c.execute("INSERT INTO klientai (pavadinimas, vat_numeris) VALUES (?, ?)", ("Testas", "LT999999999"))
    conn.commit()
    c.execute("SELECT pavadinimas FROM klientai WHERE vat_numeris=?", ("LT999999999",))
    result = c.fetchone()
    assert result[0] == "Testas"
    conn.close()
    os.remove(db_path)
