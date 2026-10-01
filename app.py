import hmac
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify

import database as db

app = Flask(__name__)
app.secret_key = os.environ.get("VERTICE_SECRET_KEY", "dev-secret-cambiar-en-produccion")

# La contraseña del panel solo viene de una variable de entorno: el repositorio es
# público, así que nunca va escrita aquí ni en render.yaml. Sin ella el panel no abre.
ADMIN_PASSWORD = os.environ.get("VERTICE_PANEL_PASSWORD", "")


@app.before_request
def _ensure_db():
    if not db.DB_PATH.exists():
        db.init_db()


def clase_a_dict(clase):
    return {
        "id": clase["id"],
        "nombre": clase["nombre"],
        "descripcion": clase["descripcion"],
        "instructor": clase["instructor"],
        "capacidad": clase["capacidad"],
        "dia": db.DIAS_SEMANA[clase["dia_semana"]],
        "hora": clase["hora"],
        "duracion_min": clase["duracion_min"],
    }


@app.route("/")
def inicio():
    clases = [clase_a_dict(c) for c in db.obtener_clases()]
    tipos_clase = []
    nombres_vistos = set()
    for c in clases:
        if c["nombre"] not in nombres_vistos:
            nombres_vistos.add(c["nombre"])
            tipos_clase.append(c)
    return render_template("index.html", clases=clases, tipos_clase=tipos_clase)


@app.route("/reservar")
def reservar():
    clases = [clase_a_dict(c) for c in db.obtener_clases()]
    clase_preseleccionada = request.args.get("clase_id", type=int)
    return render_template("reservar.html", clases=clases, clase_preseleccionada=clase_preseleccionada)


@app.route("/reservar", methods=["POST"])
def crear_reservacion():
    clase_id = request.form.get("clase_id", type=int)
    fecha = request.form.get("fecha", "").strip()
    nombre = request.form.get("nombre", "").strip()
    telefono = request.form.get("telefono", "").strip()
    email = request.form.get("email", "").strip()

    clase = db.obtener_clase(clase_id) if clase_id else None

    if not clase or not fecha or not nombre or not telefono or not email:
        flash("Completa todos los campos para reservar tu lugar.", "error")
        return redirect(url_for("reservar", clase_id=clase_id))

    if db.lugares_disponibles(clase_id, fecha) <= 0:
        flash("Ese horario ya no tiene lugares disponibles. Elige otra fecha.", "error")
        return redirect(url_for("reservar", clase_id=clase_id))

    reservacion_id = db.crear_reservacion(clase_id, nombre, telefono, email, fecha)
    return redirect(url_for("confirmacion", reservacion_id=reservacion_id))


@app.route("/confirmacion/<int:reservacion_id>")
def confirmacion(reservacion_id):
    reservacion = db.obtener_reservacion(reservacion_id)
    if reservacion is None:
        return redirect(url_for("inicio"))
    return render_template(
        "confirmacion.html",
        reservacion=reservacion,
        dia=db.DIAS_SEMANA[reservacion["dia_semana"]],
    )


@app.route("/api/clases/<int:clase_id>/fechas")
def api_fechas_clase(clase_id):
    clase = db.obtener_clase(clase_id)
    if clase is None:
        return jsonify({"error": "clase no encontrada"}), 404

    fechas = []
    for fecha in db.proximas_fechas(clase["dia_semana"], cantidad=4):
        fecha_iso = fecha.isoformat()
        fechas.append(
            {
                "fecha": fecha_iso,
                "lugares_disponibles": db.lugares_disponibles(clase_id, fecha_iso),
            }
        )
    return jsonify({"fechas": fechas})


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if not ADMIN_PASSWORD:
            flash("El panel está desactivado: falta configurar su contraseña en el servidor.", "error")
        elif hmac.compare_digest(password.encode(), ADMIN_PASSWORD.encode()):
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Contraseña incorrecta.", "error")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    reservaciones = db.obtener_reservaciones()
    total = len(reservaciones)
    confirmadas = sum(1 for r in reservaciones if r["estado"] == "confirmada")
    return render_template(
        "admin_dashboard.html",
        reservaciones=reservaciones,
        dias=db.DIAS_SEMANA,
        total=total,
        confirmadas=confirmadas,
    )


@app.route("/admin/reservaciones/<int:reservacion_id>/cancelar", methods=["POST"])
def admin_cancelar(reservacion_id):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    db.cancelar_reservacion(reservacion_id)
    flash("Reservación cancelada.", "ok")
    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    db.init_db()
    app.run(debug=True)
