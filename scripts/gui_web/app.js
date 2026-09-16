/* GUI de pokemon-ldn-trade.
   Sin dependencias: durante el intercambio no hay Internet, asi que nada de
   CDNs. Todo el trabajo de verdad lo hace el servidor (scripts/gui.py), que a
   su vez llama a make_pk3 / read_pk3 / frlgtrade. Aqui solo hay pantalla. */

const $  = (s, raiz = document) => raiz.querySelector(s);
const $$ = (s, raiz = document) => [...raiz.querySelectorAll(s)];

let CAT = null;          // catalogo (especies, movimientos, objetos...)
let ESTADO = null;       // estado del sistema
let CAJA = [];           // .pk3 encontrados
let ELEGIDO = { relleno: null, enviar: null };
let TEMPORIZADOR = null; // sondeo del registro del intercambio

const ESTADISTICAS = ["PS", "Ataque", "Defensa", "Velocidad", "At. Esp.", "Def. Esp."];
const CORTAS = ["PS", "Ata", "Def", "Vel", "AtEsp", "DefEsp"];

/* ---------------------------------------------------------------- red --- */

async function api(ruta, cuerpo) {
  const opciones = cuerpo
    ? { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cuerpo) }
    : {};
  const r = await fetch(ruta, opciones);
  const datos = await r.json();
  if (!r.ok || datos.error) throw new Error(datos.error || ("HTTP " + r.status));
  return datos;
}

function avisar(texto, clase = "") {
  const div = document.createElement("div");
  div.className = "aviso-flotante " + clase;
  div.textContent = texto;
  $("#avisos").append(div);
  setTimeout(() => div.remove(), 6000);
}

/* ------------------------------------------------------------ utiles --- */

const nombreEspecie = (id) => {
  const e = CAT && CAT.especies.find((x) => x.id === id);
  return e ? e.nombre : "#" + id;
};

function opciones(grupos, vacio) {
  // El value de cada opción es el id interno de Gen III: es lo que entiende
  // make_pk3 sin ambigüedad, y de paso queda a la vista en el desplegable.
  const cabeza = vacio ? `<option value="">${escapar(vacio)}</option>` : "";
  return cabeza + grupos.map((g) => `
    <optgroup label="${escapar(g.grupo)}">
      ${g.opciones.map((o) =>
        `<option value="${o.id}">${escapar(o.es)} · #${o.id}</option>`).join("")}
    </optgroup>`).join("");
}

function crearElemento(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

const escapar = (s) => String(s).replace(/[&<>"]/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/* ---------------------------------------------------------- pestanas --- */

$$("nav button").forEach((b) => b.addEventListener("click", () => {
  $$("nav button").forEach((o) => o.classList.toggle("activa", o === b));
  $$("main > section").forEach((s) => (s.hidden = s.id !== b.dataset.pestana));
  if (b.dataset.pestana === "caja") cargarCaja();
  if (b.dataset.pestana === "intercambio") { cargarEstado(); sondearIntercambio(); }
  if (b.dataset.pestana === "sistema") cargarEstado();
}));

/* -------------------------------------------------------- formulario --- */

function construirSeis(contenedor, prefijo, valor, max) {
  contenedor.innerHTML = CORTAS.map((c, i) => `
    <div>
      <label for="${prefijo}${i}">${c}</label>
      <input id="${prefijo}${i}" type="number" min="0" max="${max}" value="${valor}">
    </div>`).join("");
}

function leerSeis(prefijo) {
  return [0, 1, 2, 3, 4, 5].map((i) => Number($(`#${prefijo}${i}`).value) || 0);
}

function formulario() {
  return {
    especie: $("#especie").value,
    mote: $("#mote").value,
    ot: $("#ot").value,
    otid: $("#otid").value,
    nivel: $("#nivel").value,
    naturaleza: $("#naturaleza").value,
    habilidad: $("#habilidad").value,
    amistad: $("#amistad").value,
    shiny: $("#shiny").checked,
    objeto: $("#objeto").value,
    movimientos: [1, 2, 3, 4].map((i) => $("#mov" + i).value),
    ivs: leerSeis("iv"),
    evs: leerSeis("ev"),
    fateful: $("#fateful").value,
    semilla: $("#semilla").value,
  };
}

function rellenarFormulario(d) {          // desde un .pk3 ya existente
  $("#especie").value = d.especie;
  $("#mote").value = d.mote;
  $("#ot").value = d.ot;
  $("#otid").value = "0x" + d.otid.toString(16);
  $("#nivel").value = d.nivel;
  $("#naturaleza").value = CAT.naturalezas[d.naturaleza].en;   // el <select> va por nombre EN
  $("#shiny").checked = d.shiny;
  $("#objeto").value = d.objeto || "";
  [1, 2, 3, 4].forEach((i) => {
    const mv = d.movimientos[i - 1];
    $("#mov" + i).value = mv ? mv.id : "";
  });
  d.ivs.forEach((v, i) => ($("#iv" + i).value = v));
  d.evs.forEach((v, i) => ($("#ev" + i).value = v));
  $("#fateful").value = d.fateful ? "si" : "auto";
  $("#semilla").value = "";
  $("#fichero").value = "";
  previsualizar();
}

function nuevaSemilla() {
  $("#semilla").value = Math.floor(Math.random() * 4294967296);
}

/* ------------------------------------------------------ vista previa --- */

let esperaPrevia = null;
function previsualizar() {
  clearTimeout(esperaPrevia);
  esperaPrevia = setTimeout(async () => {
    const datos = formulario();
    $("#suma-evs").textContent = `suma ${datos.evs.reduce((a, b) => a + b, 0)} / 510`;
    try {
      const info = await api("/api/vista_previa", datos);
      if (!$("#semilla").value) $("#semilla").value = info.semilla;
      pintarPrevia(info);
      const sugerido = (datos.mote || nombreEspecie(Number(datos.especie)))
        .toLowerCase().replace(/[^a-z0-9._-]/g, "") + ".pk3";
      $("#fichero").placeholder = sugerido;
    } catch (e) {
      $("#previa").innerHTML = `<div class="mensaje fallo">${escapar(e.message)}</div>`;
    }
  }, 220);
}

function pintarPrevia(info) {
  $("#previa").innerHTML = fichaDetallada(info, { titulo: true });
}

function fichaDetallada(info, opciones = {}) {
  const d = info.datos;
  if (!d) return `<div class="mensaje fallo">${escapar(info.fallos.join("; "))}</div>`;
  const stats = d.stats || {};
  const tope = Math.max(...ESTADISTICAS.map((k) => stats[k] || 0), 1);
  const barras = ESTADISTICAS.map((k) => `
    <div class="barra">
      <span>${k}</span><b>${stats[k] ?? "—"}</b>
      <i><em style="width:${((stats[k] || 0) / tope) * 100}%"></em></i>
    </div>`).join("");

  const movs = d.movimientos.length
    ? d.movimientos.map((m) => escapar(m.nombre)).join(", ") : "ninguno";

  return `
    ${opciones.titulo ? `
    <div class="cabecera-previa">
      <span class="mote">${escapar(d.mote)}</span>
      <span class="etiqueta">${escapar(nombreEspecie(d.especie))} · Nv ${d.nivel}</span>
      ${d.shiny ? '<span class="etiqueta brillo">✨ SHINY</span>' : ""}
      ${d.fateful ? '<span class="etiqueta fateful">fateful</span>' : ""}
    </div>` : ""}
    <div class="barras">${barras}</div>
    <dl class="datos">
      <dt>Naturaleza</dt><dd>${escapar(d.naturaleza_nombre)}</dd>
      <dt>IVs</dt><dd>${d.ivs.join(" / ")}</dd>
      <dt>EVs</dt><dd>${d.evs.join(" / ")} <span class="ayuda">(${d.suma_evs})</span></dd>
      <dt>Movimientos</dt><dd>${movs}</dd>
      <dt>Objeto</dt><dd>${escapar(d.objeto_nombre)}</dd>
      <dt>OT</dt><dd>${escapar(d.ot)} · ID ${d.otid_visible}</dd>
      <dt>PID</dt><dd>${d.pid.toString(16).padStart(8, "0")}</dd>
    </dl>
    ${info.fallos.map((f) => `<div class="mensaje fallo">${escapar(f)}</div>`).join("")}
    ${info.avisos.map((a) => `<div class="mensaje aviso">${escapar(a)}</div>`).join("")}
    ${info.ok && !info.avisos.length
      ? '<div class="mensaje bien">Válido: checksum correcto y frlgsim lo lee.</div>' : ""}
  `;
}

/* -------------------------------------------------------------- caja --- */

async function cargarCaja() {
  try {
    CAJA = (await api("/api/pokemon")).pokemon;
  } catch (e) { avisar(e.message, "fallo"); return; }
  pintarCaja();
  rellenarSelectores();
  pintarChecklist();
}

function pintarCaja() {
  const filtro = $("#filtro").value.toLowerCase();
  const rejilla = $("#rejilla-caja");
  rejilla.innerHTML = "";
  let mostrados = 0;

  CAJA.forEach((info) => {
    const d = info.datos;
    const texto = [info.relativa, d && d.mote, d && nombreEspecie(d.especie)]
      .filter(Boolean).join(" ").toLowerCase();
    if (filtro && !texto.includes(filtro)) return;
    mostrados++;

    const clases = ["ficha"];
    if (!info.ok) clases.push("invalido");
    if (ELEGIDO.enviar === info.relativa) clases.push("elegido-enviar");
    if (ELEGIDO.relleno === info.relativa) clases.push("elegido-relleno");

    const cuerpo = d ? `
      <h3>${escapar(d.mote)}
        ${d.shiny ? '<span class="etiqueta brillo">✨</span>' : ""}
        ${!info.ok ? '<span class="etiqueta" style="color:var(--rojo-claro)">no válido</span>' : ""}
      </h3>
      <div class="ruta">${escapar(info.relativa)}</div>
      <ul>
        <li><b>${escapar(nombreEspecie(d.especie))}</b> · Nv ${d.nivel} · ${escapar(d.naturaleza_nombre)}</li>
        <li>IV ${d.ivs.join("/")} — EV ${d.suma_evs}</li>
        <li>${d.movimientos.map((m) => escapar(m.nombre)).join(", ") || "sin movimientos"}</li>
        <li>OT ${escapar(d.ot)} · ${escapar(d.objeto_nombre)}</li>
      </ul>`
      : `<h3>${escapar(info.nombre)}</h3>
         <div class="ruta">${escapar(info.relativa)}</div>
         <div class="mensaje fallo">${escapar(info.fallos.join("; "))}</div>`;

    const ficha = crearElemento(`<div class="${clases.join(" ")}">${cuerpo}
      <div class="fila-botones">
        <button class="accion pequena" data-acc="enviar">Entregar este</button>
        <button class="accion pequena" data-acc="relleno">Relleno</button>
        ${d ? '<button class="accion pequena" data-acc="editar">Copiar al editor</button>' : ""}
        <button class="accion pequena peligro" data-acc="borrar">Borrar</button>
      </div></div>`);

    ficha.addEventListener("click", async (ev) => {
      const acc = ev.target.dataset && ev.target.dataset.acc;
      if (!acc) return;
      if (acc === "enviar" || acc === "relleno") {
        ELEGIDO[acc] = info.relativa;
        pintarCaja(); rellenarSelectores();
        avisar(`${info.nombre} → ${acc === "enviar" ? "se entrega" : "relleno"}`, "bien");
      } else if (acc === "editar") {
        rellenarFormulario(info.datos);
        $$("nav button")[0].click();
      } else if (acc === "borrar") {
        if (!confirm(`¿Borrar ${info.relativa}? No se puede deshacer.`)) return;
        try {
          await api("/api/borrar", { ruta: info.relativa });
          avisar("Borrado " + info.relativa, "bien");
          cargarCaja();
        } catch (e) { avisar(e.message, "fallo"); }
      }
    });
    rejilla.append(ficha);
  });

  $("#resumen-caja").textContent =
    `${mostrados} de ${CAJA.length} ficheros · ${CAJA.filter((x) => !x.ok).length} con problemas`;
}

/* ------------------------------------------------------ intercambio --- */

function rellenarSelectores() {
  const validos = CAJA.filter((x) => x.ok);
  // Por defecto, el relleno y el que se entrega NO son el mismo fichero: el
  // hueco 1 nunca se ofrece, y elegir dos veces lo mismo confunde mas que ayuda.
  // Por defecto se propone lo ultimo que has CREADO, no lo ultimo que hay: lo
  // mas reciente de la caja suele ser un Pokemon recibido de la Switch, y ese
  // no es lo que quieres volver a entregar.
  const propios = validos.filter((x) => !x.relativa.startsWith("pk3/recibido"));
  const preferidos = propios.length ? propios : validos;
  [["#sel-relleno", "relleno", 1], ["#sel-enviar", "enviar", 0]].forEach(([sel, clave, porDefecto]) => {
    const s = $(sel);
    const previo = ELEGIDO[clave] || s.value;
    s.innerHTML = validos.map((x) => {
      const d = x.datos;
      return `<option value="${escapar(x.relativa)}">${escapar(x.relativa)} — ${escapar(d.mote)} Nv${d.nivel}</option>`;
    }).join("");
    if (previo && validos.some((x) => x.relativa === previo)) s.value = previo;
    else if (preferidos.length > porDefecto) s.value = preferidos[porDefecto].relativa;
    else if (validos.length) s.value = validos[0].relativa;
    ELEGIDO[clave] = s.value || null;
  });
}

function pintarChecklist() {
  const e = ESTADO;
  if (!e) return;
  const libre = e.wifi.some((w) => w.libre) || e.servicios.NetworkManager !== "active";
  const puntos = [
    [e.frlgsim && e.venv, "frlg-ldn-trade preparado (vendor/ + venv)",
     "falta: bash scripts/setup_ubuntu.sh"],
    [e.claves.existe, `prod.keys con ${e.claves.n} claves`,
     "no está " + e.claves.ruta],
    [e.root || e.sudo_sin_contrasena, "sudo disponible sin contraseña",
     "sudo pedirá contraseña: lanza la GUI con sudo"],
    [libre, "la radio está suelta", "NetworkManager sigue gestionando la Wi-Fi (pestaña Sistema)"],
    [ELEGIDO.relleno && ELEGIDO.enviar, "hay relleno y Pokémon a entregar", "elige los dos"],
    [ELEGIDO.relleno !== ELEGIDO.enviar, "son dos ficheros distintos",
     "el relleno y el que entregas son el mismo fichero"],
  ];
  $("#checklist").innerHTML = puntos.map(([ok, si, no]) => `
    <li><span class="marca ${ok ? "si" : "no"}">${ok ? "✔" : "✖"}</span>
        <span>${escapar(ok ? si : no)}</span></li>`).join("");
}

function claseLinea(l) {
  if (/ESTABLISHED|checksum=OK|received|wrote |trade (ok|done)|joined/i.test(l)) return "l-ok";
  if (/fail|error|traceback|refus|denied|timeout/i.test(l)) return "l-mal";
  if (/^\s*\[\s*[\d.]+s\]\s*\[sim\]/.test(l)) return "l-sim";
  return "";
}

let recibidasHasta = 0;
async function sondearIntercambio() {
  let s;
  try { s = await api("/api/intercambio?desde=" + recibidasHasta); }
  catch { return; }

  const consola = $("#consola");
  if (s.total < recibidasHasta) { consola.innerHTML = ""; recibidasHasta = 0; }
  if (recibidasHasta === 0 && s.lineas.length) consola.innerHTML = "";
  if (s.lineas.length) {
    const trozo = document.createDocumentFragment();
    s.lineas.forEach((l) => {
      const div = document.createElement("div");
      div.className = claseLinea(l);
      div.textContent = l;
      trozo.append(div);
    });
    consola.append(trozo);
    recibidasHasta = s.desde + s.lineas.length;
    if ($("#autoscroll").checked) consola.scrollTop = consola.scrollHeight;
  }

  $("#ruta-log").textContent = s.log ? "— " + s.log : "";
  $("#btn-lanzar").disabled = s.activo;
  $("#btn-parar").disabled = !s.activo;
  $("#estado-intercambio").textContent = s.activo
    ? "en marcha…"
    : (s.rc === null ? "" : (s.rc === 0 ? "terminado correctamente" : "terminó con código " + s.rc));

  if (s.recibido) {
    $("#tarjeta-recibido").hidden = false;
    $("#recibido").innerHTML = fichaDetallada(s.recibido, { titulo: true }) +
      `<p class="ayuda">Guardado en <code>${escapar(s.recibido.relativa)}</code></p>`;
  }

  clearTimeout(TEMPORIZADOR);
  if (s.activo) TEMPORIZADOR = setTimeout(sondearIntercambio, 700);
  else if (!$("#intercambio").hidden) TEMPORIZADOR = setTimeout(sondearIntercambio, 3000);
}

/* ---------------------------------------------------------- sistema --- */

async function cargarEstado() {
  try { ESTADO = await api("/api/estado"); }
  catch (e) { avisar(e.message, "fallo"); return; }
  const e = ESTADO;

  const pastilla = (ok, texto, aviso) =>
    `<span class="pastilla ${ok ? "ok" : (aviso ? "aviso" : "mal")}">${escapar(texto)}</span>`;
  const wifi = e.wifi.map((w) => pastilla(w.libre, `${w.nombre}: ${w.libre ? "libre" : w.estado}`, !w.libre)).join("");
  $("#pastillas").innerHTML =
    pastilla(e.claves.existe, `prod.keys ${e.claves.existe ? e.claves.n + " claves" : "ausente"}`) +
    pastilla(e.frlgsim && e.venv, e.frlgsim && e.venv ? "frlg-ldn-trade listo" : "falta el vendor") +
    pastilla(e.root || e.sudo_sin_contrasena, e.root ? "root" : (e.sudo_sin_contrasena ? "sudo ok" : "sudo pide contraseña")) +
    wifi +
    pastilla(e.servicios.NetworkManager !== "active", "NetworkManager: " + e.servicios.NetworkManager,
             e.servicios.NetworkManager === "active");

  $("#datos-sistema").innerHTML = `
    <dt>Proyecto</dt><dd><code>${escapar(e.raiz)}</code></dd>
    <dt>Usuario</dt><dd>${escapar(e.usuario)}${e.root ? " (la GUI corre como root)" : ""}</dd>
    <dt>prod.keys</dt><dd>${escapar(e.claves.ruta)} — ${e.claves.existe ? e.claves.n + " claves" : "NO existe"}</dd>
    <dt>frlgsim</dt><dd>${e.frlgsim ? "presente" : "falta"} · venv ${e.venv ? "presente" : "falta"}</dd>
    <dt>Servicios</dt><dd>${Object.entries(e.servicios).map(([k, v]) => `${k}: ${v}`).join(" · ")}</dd>
    <dt>Radios</dt><dd>${e.phys.join(", ") || "ninguna"}</dd>
    <dt>Wi-Fi</dt><dd>${e.wifi.map((w) => `${w.nombre} (${w.estado})`).join(", ") || "ninguna"}</dd>`;

  $("#sel-wifi").innerHTML = e.wifi.map((w) => `<option>${escapar(w.nombre)}</option>`).join("");
  const phyPrevio = $("#sel-phy").value;
  $("#sel-phy").innerHTML = e.phys.map((p) => `<option>${escapar(p)}</option>`).join("");
  if (phyPrevio) $("#sel-phy").value = phyPrevio;
  pintarChecklist();
}

/* -------------------------------------------------------- arranque --- */

async function arrancar() {
  CAT = await api("/api/catalogo");

  $("#especie").innerHTML = CAT.especies
    .map((e) => `<option value="${e.id}">#${String(e.id).padStart(3, "0")} ${escapar(e.nombre)}</option>`).join("");
  $("#especie").value = 1;
  $("#objeto").innerHTML = opciones(CAT.objetos, "— ninguno —");
  [1, 2, 3, 4].forEach((i) => {
    $("#mov" + i).innerHTML = opciones(CAT.movimientos, "— vacío —");
  });
  $("#mov1").value = 33;                       // Placaje, como en la línea de órdenes
  $("#naturaleza").innerHTML = CAT.naturalezas
    .map((n) => `<option value="${n.en}">${escapar(n.es)} — ${escapar(n.efecto)}</option>`).join("");
  $("#naturaleza").value = "hardy";

  construirSeis($("#ivs"), "iv", 31, 31);
  construirSeis($("#evs"), "ev", 0, 255);
  nuevaSemilla();

  // Cualquier cambio en el formulario redibuja la vista previa.
  document.addEventListener("change", (ev) => {
    if (ev.target.closest("#crear") && !["fichero", "sobrescribir"].includes(ev.target.id)) {
      previsualizar();
    }
  });
  document.addEventListener("input", (ev) => {
    if (ev.target.closest("#crear")) {
      if (ev.target.id === "semilla" || ev.target.closest("#previa")) previsualizar();
      else if (!["fichero", "sobrescribir"].includes(ev.target.id)) previsualizar();
    }
    if (ev.target.id === "filtro") pintarCaja();
  });

  $("#btn-semilla").addEventListener("click", () => { nuevaSemilla(); previsualizar(); });
  $$("[data-ivs]").forEach((b) => b.addEventListener("click", () => {
    [0, 1, 2, 3, 4, 5].forEach((i) => {
      $("#iv" + i).value = b.dataset.ivs === "azar"
        ? Math.floor(Math.random() * 32) : Number(b.dataset.ivs);
    });
    previsualizar();
  }));
  $$("[data-evs]").forEach((b) => b.addEventListener("click", () => {
    [0, 1, 2, 3, 4, 5].forEach((i) => ($("#ev" + i).value = 0));
    previsualizar();
  }));

  $("#btn-crear").addEventListener("click", async () => {
    try {
      const info = await api("/api/crear", {
        ...formulario(),
        fichero: $("#fichero").value || $("#fichero").placeholder,
        sobrescribir: $("#sobrescribir").checked,
      });
      avisar("Creado " + info.relativa, "bien");
      ELEGIDO.enviar = info.relativa;
      await cargarCaja();
    } catch (e) { avisar(e.message, "fallo"); }
  });

  $("#btn-recargar-caja").addEventListener("click", cargarCaja);
  $("#btn-recargar-estado").addEventListener("click", cargarEstado);

  [["#sel-relleno", "relleno"], ["#sel-enviar", "enviar"]].forEach(([sel, clave]) =>
    $(sel).addEventListener("change", () => {
      ELEGIDO[clave] = $(sel).value; pintarCaja(); pintarChecklist();
    }));

  $("#btn-lanzar").addEventListener("click", async () => {
    try {
      recibidasHasta = 0;
      $("#consola").innerHTML = "Lanzando…";
      $("#tarjeta-recibido").hidden = true;
      await api("/api/intercambio/lanzar", {
        relleno: $("#sel-relleno").value,
        enviar: $("#sel-enviar").value,
        salida: $("#sel-salida").value,
        version: $("#sel-version").value,
        ot: $("#sel-ot").value,
        phy: $("#sel-phy").value,
        trades: $("#sel-trades").value,
      });
      avisar("Intercambio lanzado: ve a la Switch", "bien");
      sondearIntercambio();
    } catch (e) {
      $("#consola").textContent = "";
      avisar(e.message, "fallo");
    }
  });

  $("#btn-parar").addEventListener("click", async () => {
    try { await api("/api/intercambio/parar", {}); avisar("Señal enviada"); }
    catch (e) { avisar(e.message, "fallo"); }
  });

  $$("[data-radio]").forEach((b) => b.addEventListener("click", async () => {
    try {
      const r = await api("/api/radio",
        { accion: b.dataset.radio, dispositivo: $("#sel-wifi").value });
      ESTADO = r.estado;
      avisar(r.rc === 0 ? "Hecho: " + b.textContent : "Falló: " + r.salida,
             r.rc === 0 ? "bien" : "fallo");
      cargarEstado();
    } catch (e) { avisar(e.message, "fallo"); }
  }));

  $$("[data-sistema]").forEach((b) => b.addEventListener("click", async () => {
    const acc = b.dataset.sistema;
    if (acc !== "sync" && !confirm(`¿Seguro que quieres ${acc} el equipo?`)) return;
    try {
      const r = await api("/api/sistema", { accion: acc });
      avisar(r.salida, "bien");
    } catch (e) { avisar(e.message, "fallo"); }
  }));

  await cargarEstado();
  await cargarCaja();
  previsualizar();
  sondearIntercambio();
}

arrancar().catch((e) => {
  document.body.insertAdjacentHTML("afterbegin",
    `<div class="mensaje fallo" style="margin:20px">No arranca: ${escapar(e.message)}</div>`);
});
