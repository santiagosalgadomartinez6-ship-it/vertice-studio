import hmac
import logging
import os
import re
import secrets
import time
from collections import defaultdict

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort, Response

import database as db

app = Flask(__name__)
app.secret_key = os.environ.get("VERTICE_SECRET_KEY", "dev-secret-cambiar-en-produccion")

EN_PRODUCCION = os.environ.get("FLASK_ENV") == "production"
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=EN_PRODUCCION,
    MAX_CONTENT_LENGTH=64 * 1024,   # ningún formulario del sitio necesita más
)

# La contraseña del panel solo viene de una variable de entorno: el repositorio es
# público, así que nunca va escrita aquí ni en render.yaml. Sin ella el panel no abre.
ADMIN_PASSWORD = os.environ.get("VERTICE_PANEL_PASSWORD", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("vertice")

# En memoria por proceso: suficiente para un solo worker (ver render.yaml).
# Si se escala a varios workers de gunicorn, mover a Redis o similar.
intentos_login = defaultdict(list)
LOGIN_MAX_INTENTOS = 8
LOGIN_VENTANA_SEGUNDOS = 10 * 60


_indices_verificados = False


@app.before_request
def _ensure_db():
    global _indices_verificados
    if not db.DB_PATH.exists():
        db.init_db()
    if not _indices_verificados:
        # CREATE INDEX IF NOT EXISTS es idempotente; se llama siempre desde
        # aquí (y no solo cuando la base de datos se crea desde cero) para
        # que una vertice.db ya existente también reciba el índice nuevo al
        # reiniciar el proceso. La bandera evita abrir una conexión extra en
        # cada request una vez confirmado en este proceso.
        db.crear_indices()
        _indices_verificados = True


@app.after_request
def _cabeceras_seguridad(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "script-src 'self'"
    )
    if EN_PRODUCCION:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def _csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(24)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = _csrf_token
app.jinja_env.globals["url_actual"] = lambda: request.url_root.rstrip("/") + request.path


@app.before_request
def _verificar_csrf():
    if request.method == "POST":
        token = request.form.get("csrf_token", "")
        # En bytes: compare_digest con texto truena si el token trae ñ o acentos
        if not token or not hmac.compare_digest(token.encode(), session.get("csrf_token", "").encode()):
            abort(403)


def contrasena_valida(recibida, esperada):
    # En bytes: compare_digest con texto truena si trae ñ o acentos
    if not esperada:
        return False
    return hmac.compare_digest(str(recibida or "").encode(), esperada.encode())


def _demasiados_intentos(clave):
    ahora = time.time()
    intentos_login[clave] = [t for t in intentos_login[clave] if ahora - t < LOGIN_VENTANA_SEGUNDOS]
    return len(intentos_login[clave]) >= LOGIN_MAX_INTENTOS


def _anotar_intento_fallido(clave):
    intentos_login[clave].append(time.time())


MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _etiqueta_fecha(fecha, lugares):
    dia_semana = db.DIAS_SEMANA[fecha.weekday()]
    texto = f"{dia_semana} {fecha.day} de {MESES[fecha.month - 1]}"
    if lugares <= 0:
        return f"{texto} — sin lugares"
    if lugares == 1:
        return f"{texto} — 1 lugar disponible"
    return f"{texto} — {lugares} lugares disponibles"


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


@app.route("/robots.txt")
def robots():
    contenido = (
        "User-agent: *\n"
        "Disallow: /admin\n"
        "Disallow: /confirmacion\n"
        f"Sitemap: {request.host_url.rstrip('/')}/sitemap.xml\n"
    )
    return Response(contenido, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap():
    base = request.host_url.rstrip("/")
    urls = [f"{base}/", f"{base}/reservar"]
    cuerpo = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{cuerpo}</urlset>"
    )
    return Response(xml, mimetype="application/xml")


@app.route("/reservar")
def reservar():
    clases = [clase_a_dict(c) for c in db.obtener_clases()]
    clase_preseleccionada = request.args.get("clase_id", type=int)

    fechas_preseleccionadas = []
    clase_original = db.obtener_clase(clase_preseleccionada) if clase_preseleccionada else None
    if clase_original:
        for fecha in db.proximas_fechas(clase_original["dia_semana"], cantidad=4):
            fecha_iso = fecha.isoformat()
            lugares = db.lugares_disponibles(clase_preseleccionada, fecha_iso)
            fechas_preseleccionadas.append(
                {"fecha": fecha_iso, "lugares_disponibles": lugares, "etiqueta": _etiqueta_fecha(fecha, lugares)}
            )

    return render_template(
        "reservar.html",
        clases=clases,
        clase_preseleccionada=clase_preseleccionada,
        fechas_preseleccionadas=fechas_preseleccionadas,
    )


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

    if len(nombre) > 100 or len(telefono) > 20:
        flash("Revisa tus datos: el nombre o el teléfono son demasiado largos.", "error")
        return redirect(url_for("reservar", clase_id=clase_id))

    # El largo se revisa antes del patrón: con textos enormes un patrón así se vuelve muy lento
    if len(email) > 254 or not re.match(r"^[^\s@]+@[^\s@.]+(\.[^\s@.]+)+$", email):
        flash("Ingresa un correo electrónico válido.", "error")
        return redirect(url_for("reservar", clase_id=clase_id))

    if fecha not in {f.isoformat() for f in db.proximas_fechas(clase["dia_semana"], cantidad=4)}:
        flash("Elige una de las fechas disponibles.", "error")
        return redirect(url_for("reservar", clase_id=clase_id))

    if db.lugares_disponibles(clase_id, fecha) <= 0:
        flash("Ese horario ya no tiene lugares disponibles. Elige otra fecha.", "error")
        return redirect(url_for("reservar", clase_id=clase_id))

    reservacion_id = db.crear_reservacion(clase_id, nombre, telefono, email, fecha)
    # Los folios son consecutivos: la confirmación solo la ve quien hizo la reservación
    session["mis_reservaciones"] = session.get("mis_reservaciones", [])[-19:] + [reservacion_id]
    return redirect(url_for("confirmacion", reservacion_id=reservacion_id))


@app.route("/confirmacion/<int:reservacion_id>")
def confirmacion(reservacion_id):
    reservacion = db.obtener_reservacion(reservacion_id)
    if reservacion is None or reservacion_id not in session.get("mis_reservaciones", []):
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
        # Solo cuentan los intentos fallidos: entrar bien no gasta intentos
        cliente = request.remote_addr or "desconocido"
        if _demasiados_intentos(cliente):
            flash("Demasiados intentos. Espera unos minutos e inténtalo de nuevo.", "error")
            return render_template("admin_login.html"), 429
        password = request.form.get("password", "")
        if not ADMIN_PASSWORD:
            flash("El panel está desactivado: falta configurar su contraseña en el servidor.", "error")
        elif contrasena_valida(password, ADMIN_PASSWORD):
            session.clear()
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            _anotar_intento_fallido(cliente)
            flash("Contraseña incorrecta.", "error")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    pagina = max(request.args.get("pagina", 1, type=int) or 1, 1)
    por_pagina = 20
    total, confirmadas = db.contar_reservaciones()
    total_paginas = max(-(-total // por_pagina), 1)
    pagina = min(pagina, total_paginas)
    reservaciones = db.obtener_reservaciones(pagina, por_pagina)
    return render_template(
        "admin_dashboard.html",
        reservaciones=reservaciones,
        dias=db.DIAS_SEMANA,
        total=total,
        confirmadas=confirmadas,
        pagina=pagina,
        total_paginas=total_paginas,
    )


@app.route("/admin/reservaciones/<int:reservacion_id>/cancelar", methods=["POST"])
def admin_cancelar(reservacion_id):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    db.cancelar_reservacion(reservacion_id)
    flash("Reservación cancelada.", "ok")
    return redirect(url_for("admin_dashboard"))


@app.errorhandler(403)
def error_403(_error):
    return render_template("error.html", codigo=403, mensaje="Tu sesión expiró o la solicitud no es válida. Vuelve a intentarlo."), 403


@app.errorhandler(404)
def error_404(_error):
    return render_template("error.html", codigo=404, mensaje="No encontramos lo que buscabas. Vuelve al inicio."), 404


@app.errorhandler(413)
def error_413(_error):
    return render_template("error.html", codigo=413, mensaje="Lo que enviaste es demasiado grande. Revisa tus datos e inténtalo de nuevo."), 413


@app.errorhandler(500)
def error_500(error):
    logger.exception(error)
    return render_template("error.html", codigo=500, mensaje="Algo salió mal de nuestro lado. Inténtalo de nuevo en un momento."), 500


if __name__ == "__main__":
    db.init_db()
    db.crear_indices()
    app.run(debug=True)
