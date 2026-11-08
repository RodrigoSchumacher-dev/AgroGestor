
import sqlite3
import math
import os
from werkzeug.security import generate_password_hash, check_password_hash


def validar_numero_positivo(valor):
    try:
        numero = float(valor)
        return math.isfinite(numero) and numero > 0
    except (TypeError, ValueError, OverflowError):
        return False


def get_db_connection():
    caminho_banco = os.environ.get("DATABASE_PATH", "agrogestor.db")

    conexao = sqlite3.connect(caminho_banco)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def init_db():
    conexao = get_db_connection()
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            hash TEXT NOT NULL
        )
    """)
    conexao.commit()
    conexao.close()


def init_plantings():
    conexao = get_db_connection()
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS plantings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            crop_name TEXT NOT NULL,
            area REAL NOT NULL,
            planting_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Planejada',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conexao.commit()
    conexao.close()


def init_expenses():
    conexao = get_db_connection()
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            planting_id INTEGER,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            expense_date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (planting_id) REFERENCES plantings(id)
        )
    """)
    conexao.commit()
    conexao.close()


def init_harvests():
    conexao = get_db_connection()
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS harvests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            planting_id INTEGER NOT NULL,
            quantity REAL NOT NULL,
            harvest_date TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (planting_id) REFERENCES plantings(id)
        )
    """)
    conexao.commit()
    conexao.close()


def init_sales():
    conexao = get_db_connection()
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            planting_id INTEGER NOT NULL,
            quantity REAL NOT NULL,
            price_per_unit REAL NOT NULL,
            sale_date TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (planting_id) REFERENCES plantings(id)
        )
    """)
    conexao.commit()
    conexao.close()


def init_all_tables():
    init_db()
    init_plantings()
    init_expenses()
    init_harvests()
    init_sales()


def register_user(username, email, password):
    senha_hash = generate_password_hash(password)
    conexao = get_db_connection()

    try:
        conexao.execute("""
            INSERT INTO users (username, email, hash)
            VALUES (?, ?, ?)
        """, (username, email, senha_hash))
        conexao.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conexao.close()


def verify_password(username, password):
    conexao = get_db_connection()
    usuario = conexao.execute(
        "SELECT hash FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    conexao.close()

    if usuario is None:
        return False

    return check_password_hash(usuario["hash"], password)


def get_user_id(username):
    conexao = get_db_connection()
    usuario = conexao.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    conexao.close()

    if usuario is None:
        return None

    return usuario["id"]


def register_planting(user_id, crop_name, area, planting_date, status="Planejada"):
    conexao = get_db_connection()

    try:
        if not validar_numero_positivo(area):
            return False

        if status not in ["Planejada", "Em andamento", "Concluída"]:
            return False

        conexao.execute("""
            INSERT INTO plantings (
                user_id, crop_name, area, planting_date, status
            )
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, crop_name, area, planting_date, status))

        conexao.commit()
        return True

    except sqlite3.Error:
        return False
    finally:
        conexao.close()


def get_plantings(user_id):
    conexao = get_db_connection()

    try:
        return conexao.execute("""
            SELECT id, crop_name, area, planting_date, status
            FROM plantings
            WHERE user_id = ?
            ORDER BY id DESC
        """, (user_id,)).fetchall()
    finally:
        conexao.close()


def update_planting(user_id, planting_id, crop_name, area, planting_date, status):
    conexao = get_db_connection()

    try:
        if not validar_numero_positivo(area):
            return False

        resultado = conexao.execute("""
            UPDATE plantings
            SET crop_name = ?,
                area = ?,
                planting_date = ?,
                status = ?
            WHERE id = ? AND user_id = ?
        """, (crop_name, area, planting_date, status, planting_id, user_id))

        conexao.commit()
        return resultado.rowcount > 0

    except sqlite3.Error:
        return False
    finally:
        conexao.close()


def delete_planting(user_id, planting_id):
    conexao = get_db_connection()

    try:
        resultado = conexao.execute("""
            DELETE FROM plantings
            WHERE id = ? AND user_id = ?
        """, (planting_id, user_id))

        conexao.commit()
        return resultado.rowcount > 0

    except sqlite3.Error:
        return False
    finally:
        conexao.close()


def register_expense(user_id, description, category, amount, expense_date, planting_id=None):
    conexao = get_db_connection()

    try:
        if not validar_numero_positivo(amount):
            return False

        if planting_id is not None:
            plantacao = conexao.execute("""
                SELECT id FROM plantings
                WHERE id = ? AND user_id = ?
            """, (planting_id, user_id)).fetchone()

            if plantacao is None:
                return False

        conexao.execute("""
            INSERT INTO expenses (
                user_id, planting_id, description, category, amount, expense_date
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, planting_id, description, category, amount, expense_date))

        conexao.commit()
        return True

    except sqlite3.Error:
        return False
    finally:
        conexao.close()


def get_expenses(user_id):
    conexao = get_db_connection()

    try:
        return conexao.execute("""
            SELECT
                expenses.id,
                expenses.description,
                expenses.category,
                expenses.amount,
                expenses.expense_date,
                expenses.planting_id,
                plantings.crop_name
            FROM expenses
            LEFT JOIN plantings
                ON expenses.planting_id = plantings.id
                AND expenses.user_id = plantings.user_id
            WHERE expenses.user_id = ?
            ORDER BY expenses.expense_date DESC, expenses.id DESC
        """, (user_id,)).fetchall()
    finally:
        conexao.close()


def delete_expense(user_id, expense_id):
    conexao = get_db_connection()

    try:
        resultado = conexao.execute("""
            DELETE FROM expenses
            WHERE id = ? AND user_id = ?
        """, (expense_id, user_id))

        conexao.commit()
        return resultado.rowcount > 0

    except sqlite3.Error:
        return False
    finally:
        conexao.close()


def register_harvest(user_id, planting_id, quantity, harvest_date, notes=None):
    conexao = get_db_connection()

    try:
        if not validar_numero_positivo(quantity):
            return False

        plantacao = conexao.execute("""
            SELECT id FROM plantings
            WHERE id = ? AND user_id = ?
        """, (planting_id, user_id)).fetchone()

        if plantacao is None:
            return False

        conexao.execute("""
            INSERT INTO harvests (
                user_id, planting_id, quantity, harvest_date, notes
            )
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, planting_id, quantity, harvest_date, notes))

        conexao.commit()
        return True

    except sqlite3.Error:
        return False
    finally:
        conexao.close()


def get_harvests(user_id):
    conexao = get_db_connection()

    try:
        return conexao.execute("""
            SELECT
                harvests.id,
                harvests.planting_id,
                harvests.quantity,
                harvests.harvest_date,
                harvests.notes,
                plantings.crop_name,
                plantings.area
            FROM harvests
            INNER JOIN plantings
                ON harvests.planting_id = plantings.id
                AND harvests.user_id = plantings.user_id
            WHERE harvests.user_id = ?
            ORDER BY harvests.harvest_date DESC, harvests.id DESC
        """, (user_id,)).fetchall()
    finally:
        conexao.close()


def delete_harvest(user_id, harvest_id):
    conexao = get_db_connection()

    try:
        colheita = conexao.execute("""
            SELECT planting_id
            FROM harvests
            WHERE id = ? AND user_id = ?
        """, (harvest_id, user_id)).fetchone()

        if colheita is None:
            return False

        planting_id = colheita["planting_id"]

        producao_restante = conexao.execute("""
            SELECT COALESCE(SUM(quantity), 0) AS total
            FROM harvests
            WHERE planting_id = ?
                AND user_id = ?
                AND id != ?
        """, (planting_id, user_id, harvest_id)).fetchone()

        total_vendido = conexao.execute("""
            SELECT COALESCE(SUM(quantity), 0) AS total
            FROM sales
            WHERE planting_id = ? AND user_id = ?
        """, (planting_id, user_id)).fetchone()

        if producao_restante["total"] < total_vendido["total"]:
            return False

        resultado = conexao.execute("""
            DELETE FROM harvests
            WHERE id = ? AND user_id = ?
        """, (harvest_id, user_id))

        conexao.commit()
        return resultado.rowcount > 0

    except sqlite3.Error:
        return False
    finally:
        conexao.close()


def get_harvest_summary(user_id):
    conexao = get_db_connection()

    try:
        return conexao.execute("""
            SELECT
                plantings.id AS planting_id,
                plantings.crop_name,
                plantings.area,
                SUM(harvests.quantity) AS total_quantity,
                SUM(harvests.quantity) / plantings.area AS productivity
            FROM harvests
            INNER JOIN plantings
                ON harvests.planting_id = plantings.id
                AND harvests.user_id = plantings.user_id
            WHERE harvests.user_id = ?
            GROUP BY plantings.id, plantings.crop_name, plantings.area
            ORDER BY plantings.crop_name
        """, (user_id,)).fetchall()
    finally:
        conexao.close()


def get_stock_by_planting(user_id):
    conexao = get_db_connection()

    try:
        resultados = conexao.execute("""
            SELECT
                plantings.id AS planting_id,
                COALESCE((
                    SELECT SUM(harvests.quantity)
                    FROM harvests
                    WHERE harvests.planting_id = plantings.id
                        AND harvests.user_id = plantings.user_id
                ), 0)
                -
                COALESCE((
                    SELECT SUM(sales.quantity)
                    FROM sales
                    WHERE sales.planting_id = plantings.id
                        AND sales.user_id = plantings.user_id
                ), 0) AS available_stock
            FROM plantings
            WHERE plantings.user_id = ?
        """, (user_id,)).fetchall()

        return {
            item["planting_id"]: max(0, item["available_stock"])
            for item in resultados
        }

    finally:
        conexao.close()


def register_sale(user_id, planting_id, quantity, price_per_unit, sale_date, notes=None):
    conexao = get_db_connection()

    try:
        if not validar_numero_positivo(quantity):
            return False

        if not validar_numero_positivo(price_per_unit):
            return False

        plantacao = conexao.execute("""
            SELECT id FROM plantings
            WHERE id = ? AND user_id = ?
        """, (planting_id, user_id)).fetchone()

        if plantacao is None:
            return False

        disponibilidade = conexao.execute("""
            SELECT
                COALESCE((
                    SELECT SUM(quantity) FROM harvests
                    WHERE planting_id = ? AND user_id = ?
                ), 0)
                -
                COALESCE((
                    SELECT SUM(quantity) FROM sales
                    WHERE planting_id = ? AND user_id = ?
                ), 0) AS quantidade_disponivel
        """, (planting_id, user_id, planting_id, user_id)).fetchone()

        if quantity > disponibilidade["quantidade_disponivel"]:
            return False

        conexao.execute("""
            INSERT INTO sales (
                user_id, planting_id, quantity, price_per_unit, sale_date, notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, planting_id, quantity, price_per_unit, sale_date, notes))

        conexao.commit()
        return True

    except sqlite3.Error:
        return False
    finally:
        conexao.close()


def get_sales(user_id):
    conexao = get_db_connection()

    try:
        return conexao.execute("""
            SELECT
                sales.id,
                sales.quantity,
                sales.price_per_unit,
                sales.quantity * sales.price_per_unit AS total_value,
                sales.sale_date,
                sales.notes,
                plantings.crop_name
            FROM sales
            INNER JOIN plantings
                ON sales.planting_id = plantings.id
                AND sales.user_id = plantings.user_id
            WHERE sales.user_id = ?
            ORDER BY sales.sale_date DESC, sales.id DESC
        """, (user_id,)).fetchall()
    finally:
        conexao.close()


def delete_sale(user_id, sale_id):
    conexao = get_db_connection()

    try:
        resultado = conexao.execute("""
            DELETE FROM sales
            WHERE id = ? AND user_id = ?
        """, (sale_id, user_id))

        conexao.commit()
        return resultado.rowcount > 0

    except sqlite3.Error:
        return False
    finally:
        conexao.close()


def get_financial_summary(user_id):
    conexao = get_db_connection()

    try:
        despesas = conexao.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM expenses WHERE user_id = ?
        """, (user_id,)).fetchone()

        receitas = conexao.execute("""
            SELECT COALESCE(SUM(quantity * price_per_unit), 0) AS total
            FROM sales WHERE user_id = ?
        """, (user_id,)).fetchone()

        total_despesas = despesas["total"]
        total_receitas = receitas["total"]

        return {
            "total_despesas": total_despesas,
            "total_receitas": total_receitas,
            "saldo": total_receitas - total_despesas
        }
    finally:
        conexao.close()


# ==================================================
# RELATORIOS GERENCIAIS
# ==================================================

def get_expenses_by_category(user_id, start_date=None, end_date=None):
    conexao = get_db_connection()

    try:
        return conexao.execute("""
            SELECT category, SUM(amount) AS total
            FROM expenses
            WHERE user_id = ?
                AND (? IS NULL OR expense_date >= ?)
                AND (? IS NULL OR expense_date <= ?)
            GROUP BY category
            ORDER BY total DESC
        """, (user_id, start_date, start_date, end_date, end_date)).fetchall()
    finally:
        conexao.close()


def get_revenue_by_planting(user_id, start_date=None, end_date=None):
    conexao = get_db_connection()

    try:
        return conexao.execute("""
            SELECT
                plantings.id AS planting_id,
                plantings.crop_name,
                COALESCE(SUM(sales.quantity * sales.price_per_unit), 0)
                    AS total_revenue,
                COALESCE(SUM(sales.quantity), 0) AS quantity_sold
            FROM plantings
            LEFT JOIN sales
                ON sales.planting_id = plantings.id
                AND sales.user_id = plantings.user_id
                AND (? IS NULL OR sales.sale_date >= ?)
                AND (? IS NULL OR sales.sale_date <= ?)
            WHERE plantings.user_id = ?
            GROUP BY plantings.id, plantings.crop_name
            ORDER BY total_revenue DESC
        """, (start_date, start_date, end_date, end_date, user_id)).fetchall()
    finally:
        conexao.close()


def get_production_sales_by_period(user_id, start_date=None, end_date=None):
    conexao = get_db_connection()

    try:
        return conexao.execute("""
            SELECT
                plantings.id AS planting_id,
                plantings.crop_name,
                COALESCE((
                    SELECT SUM(harvests.quantity)
                    FROM harvests
                    WHERE harvests.planting_id = plantings.id
                        AND harvests.user_id = plantings.user_id
                        AND (? IS NULL OR harvests.harvest_date >= ?)
                        AND (? IS NULL OR harvests.harvest_date <= ?)
                ), 0) AS total_harvested,
                COALESCE((
                    SELECT SUM(sales.quantity)
                    FROM sales
                    WHERE sales.planting_id = plantings.id
                        AND sales.user_id = plantings.user_id
                        AND (? IS NULL OR sales.sale_date >= ?)
                        AND (? IS NULL OR sales.sale_date <= ?)
                ), 0) AS total_sold
            FROM plantings
            WHERE plantings.user_id = ?
            ORDER BY plantings.crop_name
        """, (
            start_date, start_date, end_date, end_date,
            start_date, start_date, end_date, end_date, user_id
        )).fetchall()
    finally:
        conexao.close()


def get_financial_by_planting(user_id, start_date=None, end_date=None):
    conexao = get_db_connection()

    try:
        resultados = conexao.execute("""
            SELECT
                plantings.id AS planting_id,
                plantings.crop_name,
                COALESCE((
                    SELECT SUM(sales.quantity * sales.price_per_unit)
                    FROM sales
                    WHERE sales.planting_id = plantings.id
                        AND sales.user_id = plantings.user_id
                        AND (? IS NULL OR sales.sale_date >= ?)
                        AND (? IS NULL OR sales.sale_date <= ?)
                ), 0) AS total_revenue,
                COALESCE((
                    SELECT SUM(expenses.amount)
                    FROM expenses
                    WHERE expenses.planting_id = plantings.id
                        AND expenses.user_id = plantings.user_id
                        AND (? IS NULL OR expenses.expense_date >= ?)
                        AND (? IS NULL OR expenses.expense_date <= ?)
                ), 0) AS total_expenses
            FROM plantings
            WHERE plantings.user_id = ?
            ORDER BY plantings.crop_name
        """, (
            start_date, start_date, end_date, end_date,
            start_date, start_date, end_date, end_date, user_id
        )).fetchall()

        relatorio = []

        for item in resultados:
            total_receitas = item["total_revenue"]
            total_despesas = item["total_expenses"]

            relatorio.append({
                "planting_id": item["planting_id"],
                "crop_name": item["crop_name"],
                "total_revenue": total_receitas,
                "total_expenses": total_despesas,
                "balance": total_receitas - total_despesas
            })

        return relatorio
    finally:
        conexao.close()
