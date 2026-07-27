import { useRef, useState } from "react";

export default function Composer({ onEnviar, enCurso, onDetener }) {
  const [texto, setTexto] = useState("");
  const ref = useRef(null);

  function enviar() {
    const t = texto.trim();
    if (!t || enCurso) return;
    onEnviar(t);
    setTexto("");
    if (ref.current) ref.current.style.height = "auto";
  }

  function alTeclear(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      enviar();
    }
  }

  function autoAlto(e) {
    setTexto(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 140)}px`;
  }

  return (
    <div className="composer">
      <textarea
        ref={ref}
        rows={1}
        value={texto}
        placeholder="Escribe tu consulta..."
        onChange={autoAlto}
        onKeyDown={alTeclear}
      />
      {enCurso ? (
        <button className="stop" onClick={onDetener}>
          Detener
        </button>
      ) : (
        <button onClick={enviar} disabled={!texto.trim()}>
          Enviar
        </button>
      )}
    </div>
  );
}
