(function () {
  const selectClase = document.getElementById("clase_id");
  const selectFecha = document.getElementById("fecha");

  if (!selectClase || !selectFecha) return;

  const formateador = new Intl.DateTimeFormat("es-MX", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });

  function etiquetaFecha(isoFecha, lugares) {
    const [anio, mes, dia] = isoFecha.split("-").map(Number);
    const fecha = new Date(anio, mes - 1, dia);
    const texto = formateador.format(fecha);
    const capitalizada = texto.charAt(0).toUpperCase() + texto.slice(1);
    if (lugares <= 0) return `${capitalizada} — sin lugares`;
    return `${capitalizada} — ${lugares} lugar${lugares === 1 ? "" : "es"} disponible${lugares === 1 ? "" : "s"}`;
  }

  async function cargarFechas(claseId) {
    selectFecha.innerHTML = "<option value=\"\">Cargando fechas...</option>";
    selectFecha.disabled = true;

    if (!claseId) {
      selectFecha.innerHTML = "<option value=\"\">Primero elige una clase</option>";
      return;
    }

    try {
      const respuesta = await fetch(`/api/clases/${claseId}/fechas`);
      const datos = await respuesta.json();

      selectFecha.innerHTML = "";
      const opcionInicial = document.createElement("option");
      opcionInicial.value = "";
      opcionInicial.textContent = "Selecciona una fecha";
      opcionInicial.disabled = true;
      opcionInicial.selected = true;
      selectFecha.appendChild(opcionInicial);

      datos.fechas.forEach((f) => {
        const opcion = document.createElement("option");
        opcion.value = f.fecha;
        opcion.textContent = etiquetaFecha(f.fecha, f.lugares_disponibles);
        opcion.disabled = f.lugares_disponibles <= 0;
        selectFecha.appendChild(opcion);
      });

      selectFecha.disabled = false;
    } catch (error) {
      selectFecha.innerHTML = "<option value=\"\">No se pudieron cargar las fechas</option>";
    }
  }

  selectClase.addEventListener("change", () => cargarFechas(selectClase.value));

  // Si la página llegó con una clase elegida pero sin sus fechas (por ejemplo, un enlace viejo), cargarlas
  if (selectClase.value && selectFecha.disabled) {
    cargarFechas(selectClase.value);
  }
})();

// Menú móvil
(function () {
  const boton = document.querySelector(".nav__toggle");
  const enlaces = document.getElementById("nav-links");
  if (!boton || !enlaces) return;

  boton.addEventListener("click", () => {
    const abierto = enlaces.classList.toggle("is-open");
    boton.setAttribute("aria-expanded", String(abierto));
    boton.setAttribute("aria-label", abierto ? "Cerrar menú" : "Abrir menú");
  });

  enlaces.querySelectorAll("a").forEach((enlace) => {
    enlace.addEventListener("click", () => {
      enlaces.classList.remove("is-open");
      boton.setAttribute("aria-expanded", "false");
      boton.setAttribute("aria-label", "Abrir menú");
    });
  });
})();

// Mensajes flash: cierre manual y auto-dismiss
(function () {
  document.querySelectorAll(".flash").forEach((flash) => {
    const cerrar = () => flash.remove();
    const boton = flash.querySelector(".flash__cerrar");
    if (boton) boton.addEventListener("click", cerrar);
    setTimeout(cerrar, 6000);
  });
})();

// Animación de aparición al hacer scroll (progressive enhancement: sin JS,
// los elementos ya son visibles por la regla base de .reveal en el CSS)
(function () {
  const elementos = document.querySelectorAll(".reveal");
  if (!elementos.length || !("IntersectionObserver" in window)) return;

  elementos.forEach((el) => el.classList.add("reveal--pending"));

  const observador = new IntersectionObserver(
    (entradas) => {
      entradas.forEach((entrada) => {
        if (entrada.isIntersecting) {
          entrada.target.classList.remove("reveal--pending");
          observador.unobserve(entrada.target);
        }
      });
    },
    { threshold: 0.15 }
  );

  elementos.forEach((el) => observador.observe(el));
})();
