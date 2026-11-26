# -*- coding: utf-8 -*-
"""
Aplicación Principal del Gestor Bancario Local (Flask).
Proporciona endpoints REST y renderiza la interfaz web moderna.
"""

import os
import sys
import csv
import io
from datetime import datetime, date
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response, send_file

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import init_db, get_connection, get_accounts_with_balance, get_total_net_worth

app = Flask(__name__, template_folder="templates", static_folder="static")

# Inicializar base de datos
init_db()


# -------------------------------------------------------------
# RUTAS DE INTERFAZ WEB
# -------------------------------------------------------------

@app.route('/')
def index():
    """Página principal del panel de control bancario."""
    return render_template('index.html')


# -------------------------------------------------------------
# API: CUENTAS BANCARIAS
# -------------------------------------------------------------

@app.route('/api/accounts', methods=['GET'])
def list_accounts():
    """Retorna todas las cuentas con su saldo actual calculado."""
    accounts = get_accounts_with_balance()
    return jsonify(accounts), 200


@app.route('/api/accounts', methods=['POST'])
def create_account():
    """Crea una nueva cuenta bancaria."""
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    bank_name = data.get('bank_name', '').strip() or 'Banco'
    account_type = data.get('account_type', 'Corriente')
    initial_balance = float(data.get('initial_balance', 0.0))
    currency = data.get('currency', 'EUR')
    color = data.get('color', '#2563EB')

    if not name:
        return jsonify({'error': 'El nombre de la cuenta es obligatorio'}), 400

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO accounts (name, bank_name, account_type, initial_balance, currency, color)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, bank_name, account_type, initial_balance, currency, color))
        conn.commit()
        new_id = cursor.lastrowid

    return jsonify({'id': new_id, 'message': 'Cuenta creada correctamente'}), 201


@app.route('/api/accounts/<int:account_id>', methods=['DELETE'])
def delete_account(account_id):
    """Elimina una cuenta bancaria y sus movimientos asociados."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM accounts WHERE id = ?", (account_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Cuenta no encontrada'}), 404

        cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        conn.commit()

    return jsonify({'message': 'Cuenta eliminada'}), 200


# -------------------------------------------------------------
# API: CATEGORÍAS
# -------------------------------------------------------------

@app.route('/api/categories', methods=['GET'])
def list_categories():
    """Lista las categorías de ingresos y gastos."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM categories ORDER BY type ASC, name ASC").fetchall()
        return jsonify([dict(r) for r in rows]), 200


@app.route('/api/categories', methods=['POST'])
def create_category():
    """Crea una categoría personalizada."""
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    cat_type = data.get('type', 'gasto')
    color = data.get('color', '#64748B')

    if not name:
        return jsonify({'error': 'El nombre es obligatorio'}), 400

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO categories (name, type, color) VALUES (?, ?, ?)", (name, cat_type, color))
            conn.commit()
            return jsonify({'id': cursor.lastrowid, 'message': 'Categoría creada'}), 201
    except Exception as e:
        return jsonify({'error': f'Categoría ya existe o error: {e}'}), 400


# -------------------------------------------------------------
# API: MOVIMIENTOS / TRANSACCIONES
# -------------------------------------------------------------

@app.route('/api/transactions', methods=['GET'])
def list_transactions():
    """Obtiene el listado de transacciones con filtros opcionales."""
    account_id = request.args.get('account_id')
    category_id = request.args.get('category_id')
    tx_type = request.args.get('type')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search = request.args.get('search')
    limit = int(request.args.get('limit', 100))

    query = """
    SELECT 
        t.id,
        t.account_id,
        a.name AS account_name,
        a.bank_name,
        t.to_account_id,
        a_to.name AS to_account_name,
        t.category_id,
        c.name AS category_name,
        c.color AS category_color,
        t.type,
        t.amount,
        t.date,
        t.description,
        t.payee
    FROM transactions t
    LEFT JOIN accounts a ON t.account_id = a.id
    LEFT JOIN accounts a_to ON t.to_account_id = a_to.id
    LEFT JOIN categories c ON t.category_id = c.id
    WHERE 1=1
    """
    params = []

    if account_id:
        query += " AND (t.account_id = ? OR t.to_account_id = ?)"
        params.extend([account_id, account_id])

    if category_id:
        query += " AND t.category_id = ?"
        params.append(category_id)

    if tx_type:
        query += " AND t.type = ?"
        params.append(tx_type)

    if start_date:
        query += " AND t.date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND t.date <= ?"
        params.append(end_date)

    if search:
        query += " AND (t.description LIKE ? OR t.payee LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY t.date DESC, t.id DESC LIMIT ?"
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return jsonify([dict(r) for r in rows]), 200


@app.route('/api/transactions', methods=['POST'])
def create_transaction():
    """Registra un nuevo movimiento (ingreso, gasto o transferencia)."""
    data = request.get_json() or {}
    account_id = data.get('account_id')
    to_account_id = data.get('to_account_id')
    category_id = data.get('category_id')
    tx_type = data.get('type')  # 'gasto', 'ingreso', 'transferencia'
    amount = float(data.get('amount', 0.0))
    tx_date = data.get('date') or date.today().strftime('%Y-%m-%d')
    description = data.get('description', '').strip()
    payee = data.get('payee', '').strip()

    if not account_id or amount <= 0 or not tx_type:
        return jsonify({'error': 'Parámetros obligatorios incompletos (cuenta, importe y tipo)'}), 400

    if tx_type == 'transferencia':
        if not to_account_id:
            return jsonify({'error': 'La transferencia requiere una cuenta destino'}), 400
        if int(account_id) == int(to_account_id):
            return jsonify({'error': 'La cuenta origen y destino deben ser distintas'}), 400

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions 
            (account_id, to_account_id, category_id, type, amount, date, description, payee)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (account_id, to_account_id, category_id, tx_type, amount, tx_date, description, payee))
        conn.commit()
        new_id = cursor.lastrowid

    return jsonify({'id': new_id, 'message': 'Movimiento registrado con éxito'}), 201


@app.route('/api/transactions/<int:tx_id>', methods=['DELETE'])
def delete_transaction(tx_id):
    """Elimina un movimiento por su ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM transactions WHERE id = ?", (tx_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Movimiento no encontrado'}), 404
        cursor.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
        conn.commit()
    return jsonify({'message': 'Movimiento eliminado'}), 200


# -------------------------------------------------------------
# API: ESTADÍSTICAS Y GRÁFICOS
# -------------------------------------------------------------

@app.route('/api/stats/summary', methods=['GET'])
def get_stats_summary():
    """Resumen de patrimonio neto, ingresos y gastos del mes en curso."""
    current_month_str = date.today().strftime('%Y-%m')
    total_net_worth = get_total_net_worth()

    with get_connection() as conn:
        # Ingresos del mes
        row_inc = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total 
            FROM transactions 
            WHERE type = 'ingreso' AND strftime('%Y-%m', date) = ?
        """, (current_month_str,)).fetchone()
        monthly_income = row_inc['total']

        # Gastos del mes
        row_exp = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total 
            FROM transactions 
            WHERE type = 'gasto' AND strftime('%Y-%m', date) = ?
        """, (current_month_str,)).fetchone()
        monthly_expense = row_exp['total']

    savings = monthly_income - monthly_expense
    savings_rate = round((savings / monthly_income * 100), 1) if monthly_income > 0 else 0.0

    return jsonify({
        'total_net_worth': round(total_net_worth, 2),
        'monthly_income': round(monthly_income, 2),
        'monthly_expense': round(monthly_expense, 2),
        'monthly_savings': round(savings, 2),
        'savings_rate': savings_rate,
        'current_month': current_month_str
    }), 200


@app.route('/api/stats/category-breakdown', methods=['GET'])
def category_breakdown():
    """Distribución de gastos por categoría (para gráfico circular / donut)."""
    month = request.args.get('month') or date.today().strftime('%Y-%m')

    query = """
    SELECT 
        COALESCE(c.name, 'Sin categoría') AS category,
        COALESCE(c.color, '#94A3B8') AS color,
        ROUND(SUM(t.amount), 2) AS total
    FROM transactions t
    LEFT JOIN categories c ON t.category_id = c.id
    WHERE t.type = 'gasto' AND strftime('%Y-%m', t.date) = ?
    GROUP BY c.name
    ORDER BY total DESC;
    """
    with get_connection() as conn:
        rows = conn.execute(query, (month,)).fetchall()
        return jsonify([dict(r) for r in rows]), 200


@app.route('/api/stats/monthly-history', methods=['GET'])
def monthly_history():
    """Histórico de los últimos 6 meses de ingresos vs gastos (para gráfico de barras/líneas)."""
    query = """
    SELECT 
        strftime('%Y-%m', date) AS month,
        ROUND(SUM(CASE WHEN type = 'ingreso' THEN amount ELSE 0 END), 2) AS income,
        ROUND(SUM(CASE WHEN type = 'gasto' THEN amount ELSE 0 END), 2) AS expense
    FROM transactions
    WHERE date >= date('now', '-5 months', 'start of month')
    GROUP BY strftime('%Y-%m', date)
    ORDER BY month ASC;
    """
    with get_connection() as conn:
        rows = conn.execute(query).fetchall()
        return jsonify([dict(r) for r in rows]), 200


# -------------------------------------------------------------
# EXPORTACIÓN E IMPORTACIÓN CSV
# -------------------------------------------------------------

@app.route('/export-csv')
def export_csv():
    """Exporta todos los movimientos a un archivo CSV descargable."""
    with get_connection() as conn:
        query = """
        SELECT 
            t.id, t.date, t.type, t.amount,
            a.name AS account, 
            COALESCE(a_to.name, '') AS to_account,
            COALESCE(c.name, 'Sin categoría') AS category,
            COALESCE(t.payee, '') AS payee,
            COALESCE(t.description, '') AS description
        FROM transactions t
        LEFT JOIN accounts a ON t.account_id = a.id
        LEFT JOIN accounts a_to ON t.to_account_id = a_to.id
        LEFT JOIN categories c ON t.category_id = c.id
        ORDER BY t.date DESC
        """
        rows = conn.execute(query).fetchall()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['ID', 'Fecha', 'Tipo', 'Importe (EUR)', 'Cuenta Origen', 'Cuenta Destino', 'Categoría', 'Destinatario/Pagador', 'Descripción'])
    for r in rows:
        writer.writerow([r['id'], r['date'], r['type'], r['amount'], r['account'], r['to_account'], r['category'], r['payee'], r['description']])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-disposition": f"attachment; filename=movimientos_bancarios_{date.today().strftime('%Y%m%d')}.csv"}
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    host = '0.0.0.0' if os.environ.get('RENDER') else 'localhost'
    print(f"Iniciando Gestor Bancario en http://{host}:{port}")
    app.run(host=host, port=port, debug=False)
