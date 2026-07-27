// Estado de la conversacion y consumo del stream.
//
// Traduce los eventos SSE tipados (token, citations, escalated, done, error) a
// actualizaciones del mensaje del asistente que se esta construyendo. El
// componente solo pinta; toda la logica de streaming vive aqui.

import { useCallback, useRef, useState } from "react";
import { enviarMensajeStream } from "../api.js";

let contador = 0;
const nuevoId = () => `m${++contador}`;

export function useSSEChat(token, onSesionInvalida) {
  const [mensajes, setMensajes] = useState([]);
  const [enCurso, setEnCurso] = useState(false);
  const abortRef = useRef(null);

  const actualizarUltimo = useCallback((cambios) => {
    setMensajes((prev) => {
      const copia = [...prev];
      const i = copia.length - 1;
      copia[i] = { ...copia[i], ...cambios(copia[i]) };
      return copia;
    });
  }, []);

  const enviar = useCallback(
    async (texto) => {
      if (!texto.trim() || enCurso) return;

      setMensajes((prev) => [
        ...prev,
        { id: nuevoId(), rol: "user", texto },
        { id: nuevoId(), rol: "assistant", texto: "", citas: [], escalado: null, error: null },
      ]);
      setEnCurso(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await enviarMensajeStream(
          texto,
          token,
          (tipo, datos) => {
            if (tipo === "token") {
              actualizarUltimo((m) => ({ texto: m.texto + datos.text }));
            } else if (tipo === "citations") {
              actualizarUltimo(() => ({ citas: datos.citations }));
            } else if (tipo === "escalated") {
              actualizarUltimo(() => ({ escalado: datos.ticket_id }));
            } else if (tipo === "error") {
              actualizarUltimo((m) => ({
                error: datos.detail,
                texto: m.texto || "",
              }));
            }
          },
          controller.signal
        );
      } catch (e) {
        if (e.message.includes("sesion")) {
          onSesionInvalida?.();
          return;
        }
        actualizarUltimo(() => ({ error: e.message }));
      } finally {
        setEnCurso(false);
        abortRef.current = null;
      }
    },
    [token, enCurso, actualizarUltimo, onSesionInvalida]
  );

  const detener = useCallback(() => {
    abortRef.current?.abort();
    setEnCurso(false);
  }, []);

  return { mensajes, enCurso, enviar, detener };
}
