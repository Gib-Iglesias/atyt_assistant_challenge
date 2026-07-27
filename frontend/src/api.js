// Cliente de la API. Dos responsabilidades: obtener el token de Django y abrir
// el stream de chat contra FastAPI.
//
// El streaming NO usa EventSource: el navegador no permite enviar cabeceras con
// EventSource, y el token JWT tiene que viajar en Authorization. Se usa fetch
// con ReadableStream y se parsea el protocolo SSE a mano.

const TOKEN_KEY = "atyt_token";
const USER_KEY = "atyt_user";

export function guardarSesion(token, user) {
  sessionStorage.setItem(TOKEN_KEY, token);
  sessionStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function leerSesion() {
  const token = sessionStorage.getItem(TOKEN_KEY);
  const user = sessionStorage.getItem(USER_KEY);
  if (!token || !user) return null;
  return { token, user: JSON.parse(user) };
}

export function cerrarSesion() {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
}

export async function iniciarSesion(username, password) {
  const resp = await fetch("/api/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!resp.ok) {
    const cuerpo = await resp.json().catch(() => ({}));
    throw new Error(cuerpo.detail || "No se pudo iniciar sesion.");
  }
  const data = await resp.json();
  guardarSesion(data.access_token, data.user);
  return data.user;
}

// Abre el stream y llama a onEvent(tipo, datos) por cada evento SSE.
// Devuelve una promesa que resuelve al terminar el stream.
export async function enviarMensajeStream(mensaje, token, onEvent, signal) {
  const resp = await fetch("/api/chat/stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message: mensaje }),
    signal,
  });

  if (resp.status === 401) throw new Error("La sesion expiro. Vuelve a entrar.");
  if (!resp.ok) throw new Error(`Error del servidor (${resp.status}).`);

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Los eventos SSE se separan por linea en blanco.
    const trozos = buffer.split("\n\n");
    buffer = trozos.pop() || "";
    for (const trozo of trozos) {
      const evento = parseEvento(trozo);
      if (evento) onEvent(evento.tipo, evento.datos);
    }
  }
}

function parseEvento(trozo) {
  let tipo = "message";
  let data = "";
  for (const linea of trozo.split("\n")) {
    if (linea.startsWith("event: ")) tipo = linea.slice(7).trim();
    else if (linea.startsWith("data: ")) data += linea.slice(6);
  }
  if (!data) return null;
  try {
    return { tipo, datos: JSON.parse(data) };
  } catch {
    return null;
  }
}
