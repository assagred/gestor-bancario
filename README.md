# Gestor Bancario Local (Windows PC)

Una aplicación web local moderna, privada y rápida para llevar el control de tus cuentas bancarias y finanzas personales directamente en tu ordenador Windows, sin depender de servicios externos ni subir tus datos financieros a la nube.

---

## 🚀 Cómo iniciar la aplicación

Tienes dos opciones muy sencillas:

### Opción 1: Doble clic (Recomendada)
Haz doble clic en el archivo:
```
iniciar_gestor.bat
```
Se abrirá automáticamente la consola de Python y tu navegador web por defecto en `http://localhost:5050`.

### Opción 2: Desde la terminal
```bash
cd gestor_bancario
python app.py
```
Y abre tu navegador en [http://localhost:5050](http://localhost:5050).

---

## 🛠️ Características Principales

1. **Gestión Multicuenta:**
   * Crea y administra cuentas corrientes, de ahorro, tarjetas de crédito, efectivo o inversión.
   * Asigna colores distintivos a cada entidad bancaria (BBVA, Santander, Revolut, etc.).
   * Cálculo dinámico del saldo real exacto en cada momento.

2. **Registro de Movimientos:**
   * **Gastos:** Asocia compras a categorías (Supermercado, Alquiler, Suministros, Restaurantes, etc.).
   * **Ingresos:** Registra nóminas, bizums recibidos, rendimientos y ventas.
   * **Transferencias entre cuentas:** Mueve dinero entre tus propias cuentas (origen y destino) actualizando ambos saldos en una sola operación.

3. **Panel de Control y Gráficos Interactivos:**
   * Indicadores KPI: Patrimonio Neto Total, Ingresos del Mes, Gastos del Mes y Tasa de Ahorro.
   * **Gráfico Donut:** Distribución del gasto por categorías del mes en curso.
   * **Gráfico de Barras:** Evolución y comparación de Ingresos vs. Gastos en los últimos 6 meses.

4. **Filtros y Búsqueda en Tiempo Real:**
   * Filtra tus movimientos por cuenta, por tipo (gasto, ingreso, transferencia) o busca por concepto/destinatario.

5. **Privacidad y Exportación:**
   * Todos los datos se guardan de forma 100% local en una base de datos SQLite (`cuentas_bancarias.db`).
   * Botón **Exportar CSV** para descargar todos tus movimientos y abrirlos en Excel o Calc.
