# -*- coding: utf-8 -*-
"""
Módulo de Base de Datos SQLite para el Gestor Bancario Local.
Gestiona la creación de tablas, categorías por defecto y consultas de saldo.
"""

import sqlite3
import os
from pathlib import Path

DATA_DIR = os.environ.get("DATA_DIR")
if DATA_DIR:
    dir_path = Path(DATA_DIR)
    dir_path.mkdir(parents=True, exist_ok=True)
    DB_FILE = dir_path / "cuentas_bancarias.db"
else:
    DB_FILE = Path(__file__).resolve().parent / "cuentas_bancarias.db"


def get_connection():
    """Retorna una conexión a la base de datos con acceso por nombre de columna."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Inicializa la base de datos creando las tablas e insertando datos por defecto."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Tabla de cuentas bancarias
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            bank_name TEXT NOT NULL,
            account_type TEXT NOT NULL DEFAULT 'Corriente',
            initial_balance REAL NOT NULL DEFAULT 0.0,
            currency TEXT NOT NULL DEFAULT 'EUR',
            color TEXT NOT NULL DEFAULT '#2563EB',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Tabla de categorías
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL, -- 'gasto' o 'ingreso'
            icon TEXT NOT NULL DEFAULT 'tag',
            color TEXT NOT NULL DEFAULT '#64748B'
        )
        """)

        # Tabla de transacciones / movimientos
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            to_account_id INTEGER,
            category_id INTEGER,
            type TEXT NOT NULL, -- 'gasto', 'ingreso', 'transferencia'
            amount REAL NOT NULL,
            date TEXT NOT NULL, -- YYYY-MM-DD
            description TEXT,
            payee TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE,
            FOREIGN KEY (to_account_id) REFERENCES accounts (id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL
        )
        """)

        # Insertar categorías por defecto si está vacía
        cursor.execute("SELECT COUNT(*) AS count FROM categories")
        if cursor.fetchone()["count"] == 0:
            default_categories = [
                # Gastos
                ("Alimentación y Supermercado", "gasto", "cart", "#EF4444"),
                ("Vivienda y Alquiler", "gasto", "home", "#F97316"),
                ("Suministros (Luz, Agua, Gas, Internet)", "gasto", "bolt", "#F59E0B"),
                ("Restaurantes y Ocio", "gasto", "coffee", "#EC4899"),
                ("Transporte y Combustible", "gasto", "car", "#8B5CF6"),
                ("Salud y Farmacia", "gasto", "heart", "#10B981"),
                ("Compras y Ropa", "gasto", "shopping-bag", "#6366F1"),
                ("Suscripciones y Tecnología", "gasto", "tv", "#06B6D4"),
                ("Educación y Libros", "gasto", "book", "#14B8A6"),
                ("Otros Gastos", "gasto", "dots", "#64748B"),
                # Ingresos
                ("Nómina / Salario", "ingreso", "briefcase", "#10B981"),
                ("Transferencia / Bizum recibido", "ingreso", "arrow-down-left", "#059669"),
                ("Inversiones y Rendimientos", "ingreso", "trending-up", "#3B82F6"),
                ("Ventas segunda mano", "ingreso", "tag", "#8B5CF6"),
                ("Otros Ingresos", "ingreso", "plus-circle", "#0EA5E9")
            ]
            cursor.executemany(
                "INSERT INTO categories (name, type, icon, color) VALUES (?, ?, ?, ?)",
                default_categories
            )

        # Insertar una cuenta de ejemplo si no existe ninguna
        cursor.execute("SELECT COUNT(*) AS count FROM accounts")
        if cursor.fetchone()["count"] == 0:
            cursor.execute("""
            INSERT INTO accounts (name, bank_name, account_type, initial_balance, currency, color)
            VALUES ('Cuenta Nómina', 'Mi Banco Principal', 'Corriente', 1500.0, 'EUR', '#2563EB')
            """)
            cursor.execute("""
            INSERT INTO accounts (name, bank_name, account_type, initial_balance, currency, color)
            VALUES ('Cuenta de Ahorro', 'Banco Ahorro', 'Ahorro', 5000.0, 'EUR', '#10B981')
            """)

        conn.commit()


def get_accounts_with_balance():
    """Devuelve todas las cuentas calculando dinámicamente su saldo actual real."""
    query = """
    SELECT 
        a.id, 
        a.name, 
        a.bank_name, 
        a.account_type, 
        a.initial_balance, 
        a.currency, 
        a.color,
        ROUND(
            a.initial_balance
            + COALESCE((SELECT SUM(amount) FROM transactions WHERE account_id = a.id AND type = 'ingreso'), 0)
            - COALESCE((SELECT SUM(amount) FROM transactions WHERE account_id = a.id AND type = 'gasto'), 0)
            + COALESCE((SELECT SUM(amount) FROM transactions WHERE to_account_id = a.id AND type = 'transferencia'), 0)
            - COALESCE((SELECT SUM(amount) FROM transactions WHERE account_id = a.id AND type = 'transferencia'), 0)
        , 2) AS current_balance
    FROM accounts a
    ORDER BY a.name ASC;
    """
    with get_connection() as conn:
        rows = conn.execute(query).fetchall()
        return [dict(r) for r in rows]


def get_total_net_worth():
    """Calcula el patrimonio neto total sumando los saldos actuales de todas las cuentas."""
    accounts = get_accounts_with_balance()
    return sum(acc["current_balance"] for acc in accounts)
