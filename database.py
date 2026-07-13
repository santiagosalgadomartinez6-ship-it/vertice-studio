import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).parent / "vertice.db"

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS clases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            instructor TEXT NOT NULL,
            capacidad INTEGER NOT NULL,
            dia_semana INTEGER NOT NULL,
            hora TEXT NOT NULL,
            duracion_min INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reservaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clase_id INTEGER NOT NULL REFERENCES clases(id),
            nombre_cliente TEXT NOT NULL,
            telefono TEXT NOT NULL,
            email TEXT NOT NULL,
            fecha TEXT NOT NULL,
            creado_en TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'confirmada'
        );
        """
    )
    conn.commit()

    if conn.execute("SELECT COUNT(*) FROM clases").fetchone()[0] == 0:
        clases_semilla = [
            ("Funcional HIIT", "Entrenamiento funcional de alta intensidad por estaciones.", "Coach Iván", 12, 0, "07:00", 45),
            ("Funcional HIIT", "Entrenamiento funcional de alta intensidad por estaciones.", "Coach Iván", 12, 2, "07:00", 45),
            ("Yoga Flow", "Secuencias dinámicas para movilidad, fuerza y respiración.", "Renata", 15, 1, "08:00", 60),
            ("Yoga Flow", "Secuencias dinámicas para movilidad, fuerza y respiración.", "Renata", 15, 3, "08:00", 60),
            ("Spinning", "Cardio en bici estática al ritmo de la música.", "Coach Iván", 20, 4, "18:00", 45),
            ("Box Fit", "Boxeo y acondicionamiento físico combinados.", "Coach Dana", 14, 1, "19:00", 50),
            ("Pilates Reformer", "Fuerza, postura y control con máquina reformer.", "Renata", 8, 5, "09:00", 50),
        ]
        conn.executemany(
            """INSERT INTO clases
               (nombre, descripcion, instructor, capacidad, dia_semana, hora, duracion_min)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            clases_semilla,
        )
        conn.commit()
    conn.close()


def obtener_clases():
    conn = get_db()
    clases = conn.execute("SELECT * FROM clases ORDER BY dia_semana, hora").fetchall()
    conn.close()
    return clases


def obtener_clase(clase_id):
    conn = get_db()
    clase = conn.execute("SELECT * FROM clases WHERE id = ?", (clase_id,)).fetchone()
    conn.close()
    return clase


def proximas_fechas(dia_semana, cantidad=4):
    hoy = datetime.now().date()
    dias_hasta = (dia_semana - hoy.weekday()) % 7
    primera = hoy + timedelta(days=dias_hasta)
    return [primera + timedelta(weeks=i) for i in range(cantidad)]


def lugares_disponibles(clase_id, fecha_iso):
    conn = get_db()
    clase = conn.execute("SELECT capacidad FROM clases WHERE id = ?", (clase_id,)).fetchone()
    ocupados = conn.execute(
        """SELECT COUNT(*) FROM reservaciones
           WHERE clase_id = ? AND fecha = ? AND estado = 'confirmada'""",
        (clase_id, fecha_iso),
    ).fetchone()[0]
    conn.close()
    if clase is None:
        return 0
    return max(clase["capacidad"] - ocupados, 0)


def crear_reservacion(clase_id, nombre, telefono, email, fecha_iso):
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO reservaciones
           (clase_id, nombre_cliente, telefono, email, fecha, creado_en)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (clase_id, nombre, telefono, email, fecha_iso, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    nueva_id = cursor.lastrowid
    conn.close()
    return nueva_id


def obtener_reservacion(reservacion_id):
    conn = get_db()
    fila = conn.execute(
        """SELECT r.*, c.nombre AS clase_nombre, c.hora, c.dia_semana, c.instructor
           FROM reservaciones r JOIN clases c ON c.id = r.clase_id
           WHERE r.id = ?""",
        (reservacion_id,),
    ).fetchone()
    conn.close()
    return fila


def obtener_reservaciones():
    conn = get_db()
    filas = conn.execute(
        """SELECT r.*, c.nombre AS clase_nombre, c.hora, c.instructor
           FROM reservaciones r JOIN clases c ON c.id = r.clase_id
           ORDER BY r.creado_en DESC"""
    ).fetchall()
    conn.close()
    return filas


def cancelar_reservacion(reservacion_id):
    conn = get_db()
    conn.execute("UPDATE reservaciones SET estado = 'cancelada' WHERE id = ?", (reservacion_id,))
    conn.commit()
    conn.close()
