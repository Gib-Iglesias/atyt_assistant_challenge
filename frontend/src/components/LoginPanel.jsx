import { useState } from "react";
import { iniciarSesion } from "../api.js";

export default function LoginPanel({ onEntrar }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(false);

  async function entrar() {
    setError(null);
    setCargando(true);
    try {
      const user = await iniciarSesion(username.trim(), password);
      onEntrar(user);
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }

  return (
    <div className="login-wrap">
      <h1>atyt · soporte</h1>
      <p>Consola interna del equipo de soporte.</p>

      <div className="field">
        <label htmlFor="u">Usuario</label>
        <input
          id="u"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && document.getElementById("p").focus()}
          autoFocus
        />
      </div>
      <div className="field">
        <label htmlFor="p">Contrasena</label>
        <input
          id="p"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && entrar()}
        />
      </div>

      <button onClick={entrar} disabled={cargando || !username || !password}>
        {cargando ? "Entrando..." : "Entrar"}
      </button>
      {error && <div className="login-err">{error}</div>}

      <div className="login-hint">
        Demo: agente_acme / demo1234
        <br />
        admin / admin123
      </div>
    </div>
  );
}
