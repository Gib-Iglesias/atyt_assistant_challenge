import { useEffect, useRef } from "react";
import CitationList from "./CitationList.jsx";

const SUGERENCIAS = [
  "cuanto tardan los reembolsos?",
  "que pasa si el pedido ya fue enviado?",
  "estado del pedido ACME-000001",
];

export default function MessageList({ mensajes, enCurso, onSugerencia }) {
  const finRef = useRef(null);
  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [mensajes]);

  if (mensajes.length === 0) {
    return (
      <div className="thread">
        <div className="empty">
          <h2>En que puedo ayudarte</h2>
          <p>
            Pregunta sobre la documentacion de producto o consulta el estado de un
            pedido por su referencia. Cada respuesta cita su fuente.
          </p>
          <div className="suggestions">
            {SUGERENCIAS.map((s) => (
              <button key={s} onClick={() => onSugerencia(s)}>
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="thread">
      {mensajes.map((m) => (
        <Mensaje key={m.id} m={m} enCurso={enCurso} />
      ))}
      <div ref={finRef} />
    </div>
  );
}

function Mensaje({ m, enCurso }) {
  const esUsuario = m.rol === "user";
  const esUltimoAsistente = !esUsuario;
  const escribiendo = esUltimoAsistente && enCurso && !m.texto && !m.error && !m.escalado;

  return (
    <div className={`msg ${esUsuario ? "user" : "assistant"}`}>
      <span className="role">{esUsuario ? "tu" : "asistente"}</span>

      {(m.texto || escribiendo) && (
        <div className={`bubble ${escribiendo ? "cursor" : ""}`}>{m.texto}</div>
      )}

      {!esUsuario && <CitationList citas={m.citas} />}

      {m.escalado && (
        <div className="banner escalated">
          Caso escalado a un agente humano · ticket <span className="tk">#{m.escalado}</span>
        </div>
      )}

      {m.error && <div className="banner error">{m.error}</div>}
    </div>
  );
}
