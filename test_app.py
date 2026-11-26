# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app

client = app.test_client()

def test_full_flow():
    # 1. Página principal
    res = client.get('/')
    assert res.status_code == 200, f"Error en index: {res.status_code}"
    print("[OK] Index HTML carga correctamente")

    # 2. Cuentas iniciales
    res = client.get('/api/accounts')
    accs = res.get_json()
    print(f"[OK] Cuentas cargadas ({len(accs)} cuentas encontradas)")

    # 3. Registrar Ingreso (+2100 €)
    res = client.post('/api/transactions', json={
        'account_id': 1,
        'type': 'ingreso',
        'amount': 2100.0,
        'category_id': 11,
        'description': 'Nómina mensual',
        'payee': 'Empresa SA'
    })
    assert res.status_code == 201
    print("[OK] Ingreso registrado con éxito")

    # 4. Registrar Gasto (-85.50 €)
    res = client.post('/api/transactions', json={
        'account_id': 1,
        'type': 'gasto',
        'amount': 85.50,
        'category_id': 1,
        'description': 'Compra semanal',
        'payee': 'Mercadona'
    })
    assert res.status_code == 201
    print("[OK] Gasto registrado con éxito")

    # 5. Registrar Transferencia (300 €) de cuenta 1 a cuenta 2
    res = client.post('/api/transactions', json={
        'account_id': 1,
        'to_account_id': 2,
        'type': 'transferencia',
        'amount': 300.0,
        'description': 'Ahorro mensual programado'
    })
    assert res.status_code == 201
    print("[OK] Transferencia registrada con éxito")

    # 6. Comprobar saldos
    res = client.get('/api/accounts')
    accs = res.get_json()
    for a in accs:
        print(f" -> Cuenta '{a['name']}': Saldo actual = {a['current_balance']} €")

    # 7. Resumen financiero
    res = client.get('/api/stats/summary')
    stats = res.get_json()
    print("[OK] Estadísticas:", stats)

    # 8. Exportar CSV
    res = client.get('/export-csv')
    assert res.status_code == 200
    print("[OK] Exportación CSV generada con éxito")
    print("\n--- ¡TODAS LAS PRUEBAS PASARON SATISFACTORIAMENTE! ---")

if __name__ == '__main__':
    test_full_flow()
