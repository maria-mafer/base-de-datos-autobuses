import oracledb
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

USUARIO = "SYSTEM"
CONTRASENA = "Oracle"
HOST = "localhost"
PUERTO = 1521
SID = "xe"


def conectar():
    return oracledb.connect(
        user=USUARIO,
        password=CONTRASENA,
        dsn=f"{HOST}:{PUERTO}/{SID}"
    )


@app.route("/")
def inicio():
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT id_ruta, nombre
        FROM RUTA
        ORDER BY id_ruta
    """)

    rutas = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template("index.html", rutas=rutas)


@app.route("/servicios")
def servicios():
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT id_servicio,
               id_ruta,
               hora_salida,
               hora_llegada,
               dias_programados,
               matricula,
               dni_conductor
        FROM SERVICIO_DIARIO
        ORDER BY id_servicio
    """)

    servicios = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template("servicios.html", servicios=servicios)


@app.route("/pasajeros")
def pasajeros():
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT dni, nombre, telefono
        FROM PASAJERO
        ORDER BY nombre
    """)

    pasajeros = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template("pasajeros.html", pasajeros=pasajeros)


@app.route("/boletos")
def boletos():
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT id_boleto,
               dni_pasajero,
               id_servicio,
               fecha_viaje,
               importe
        FROM BOLETO
        ORDER BY id_boleto
    """)

    boletos = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template("boletos.html", boletos=boletos)


@app.route("/autobuses")
def autobuses():
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT matricula, modelo, fabricante, plazas, caracteristicas
        FROM AUTOBUS
        ORDER BY matricula
    """)

    autobuses = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template("autobuses.html", autobuses=autobuses)


@app.route("/conductores")
def conductores():
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT dni,
               nombre,
               telefono,
               direccion
        FROM CONDUCTOR
        ORDER BY nombre
    """)

    conductores = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template("conductores.html", conductores=conductores)


@app.route("/revisiones")
def revisiones():
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT r.id_revision,
               r.matricula,
               r.fecha_revision,
               r.diagnostico,
               rep.codigo_reparacion,
               rep.tiempo_empleado,
               rep.comentario
        FROM REVISION r
        LEFT JOIN REPARACION rep
            ON r.id_revision = rep.id_revision
        ORDER BY r.fecha_revision DESC
    """)

    revisiones = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template("revisiones.html", revisiones=revisiones)


@app.route("/reportes")
def reportes():
    conexion = conectar()
    cursor = conexion.cursor()

    # Promedio de viajeros por ruta
    cursor.execute("""
        SELECT
            r.id_ruta,
            r.nombre,
            ROUND(AVG(v.total_viajeros), 2)
        FROM RUTA r
        LEFT JOIN (
            SELECT
                s.id_servicio,
                s.id_ruta,
                COUNT(b.id_boleto) AS total_viajeros
            FROM SERVICIO_DIARIO s
            LEFT JOIN BOLETO b
                ON s.id_servicio = b.id_servicio
            GROUP BY s.id_servicio, s.id_ruta
        ) v
        ON r.id_ruta = v.id_ruta
        GROUP BY r.id_ruta, r.nombre
        ORDER BY r.id_ruta
    """)

    promedio_ruta = cursor.fetchall()

    # Viajeros por servicio
    cursor.execute("""
        SELECT
            s.id_servicio,
            r.nombre,
            COUNT(b.id_boleto)
        FROM SERVICIO_DIARIO s
        JOIN RUTA r
            ON s.id_ruta = r.id_ruta
        LEFT JOIN BOLETO b
            ON s.id_servicio = b.id_servicio
        GROUP BY s.id_servicio, r.nombre
        ORDER BY s.id_servicio
    """)

    viajeros_servicio = cursor.fetchall()

    # Kilometros por autobus
    cursor.execute("""
        SELECT
            a.matricula,
            a.modelo,
            ROUND(SUM(r.km), 2)
        FROM AUTOBUS a
        JOIN SERVICIO_DIARIO s
            ON a.matricula = s.matricula
        JOIN RUTA r
            ON s.id_ruta = r.id_ruta
        GROUP BY a.matricula, a.modelo
        ORDER BY a.matricula
    """)

    km_autobus = cursor.fetchall()

    # Kilometros por conductor
    cursor.execute("""
        SELECT
            c.dni,
            c.nombre,
            ROUND(SUM(r.km), 2)
        FROM CONDUCTOR c
        JOIN SERVICIO_DIARIO s
            ON c.dni = s.dni_conductor
        JOIN RUTA r
            ON s.id_ruta = r.id_ruta
        GROUP BY c.dni, c.nombre
        ORDER BY c.nombre
    """)

    km_conductor = cursor.fetchall()

    # Horas de viaje por pasajero
    cursor.execute("""
        SELECT
            p.dni,
            p.nombre,
            ROUND(
                SUM(
                    (
                        TO_DATE(s.hora_llegada, 'HH24:MI')
                        - TO_DATE(s.hora_salida, 'HH24:MI')
                    ) * 24
                ),
                2
            )
        FROM PASAJERO p
        JOIN BOLETO b
            ON p.dni = b.dni_pasajero
        JOIN SERVICIO_DIARIO s
            ON b.id_servicio = s.id_servicio
        GROUP BY p.dni, p.nombre
        ORDER BY p.nombre
    """)

    horas_pasajero = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template(
        "reportes.html",
        promedio_ruta=promedio_ruta,
        viajeros_servicio=viajeros_servicio,
        km_autobus=km_autobus,
        km_conductor=km_conductor,
        horas_pasajero=horas_pasajero
    )


@app.route("/comprar-boleto", methods=["GET", "POST"])
def comprar_boleto():
    conexion = conectar()
    cursor = conexion.cursor()

    if request.method == "POST":
        dni_pasajero = request.form["dni_pasajero"]
        id_servicio = request.form["id_servicio"]
        fecha_viaje = request.form["fecha_viaje"]
        importe = request.form["importe"]

        cursor.execute("""
            INSERT INTO BOLETO (dni_pasajero, id_servicio, fecha_viaje, importe)
            VALUES (:1, :2, TO_DATE(:3, 'YYYY-MM-DD'), :4)
        """, (dni_pasajero, id_servicio, fecha_viaje, importe))

        conexion.commit()

        cursor.close()
        conexion.close()

        return redirect(url_for("boletos"))

    cursor.execute("SELECT dni, nombre FROM PASAJERO ORDER BY nombre")
    pasajeros = cursor.fetchall()

    cursor.execute("SELECT id_servicio, id_ruta FROM SERVICIO_DIARIO ORDER BY id_servicio")
    servicios = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template("comprar_boleto.html", pasajeros=pasajeros, servicios=servicios)


import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)