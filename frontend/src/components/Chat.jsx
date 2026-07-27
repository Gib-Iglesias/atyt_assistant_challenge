import { useSSEChat } from "../hooks/useSSEChat.js";
import MessageList from "./MessageList.jsx";
import Composer from "./Composer.jsx";

export default function Chat({ sesion, onSalir, onSesionInvalida }) {
  const { mensajes, enCurso, enviar, detener } = useSSEChat(
    sesion.token,
    onSesionInvalida
  );
  const { user } = sesion;

  return (
    <div className="app">
      <header className="top">
        <div className="brand">
          <span className="mark">atyt · soporte</span>
          <span className="sub">consola interna</span>
        </div>
        <div className="whoami">
          <span className="who">{user.username}</span>
          {user.tenant_slug && <span className="tenant-chip">{user.tenant_slug}</span>}
          <button className="linkbtn" onClick={onSalir}>
            salir
          </button>
        </div>
      </header>

      <MessageList mensajes={mensajes} enCurso={enCurso} onSugerencia={enviar} />
      <Composer onEnviar={enviar} enCurso={enCurso} onDetener={detener} />
    </div>
  );
}
