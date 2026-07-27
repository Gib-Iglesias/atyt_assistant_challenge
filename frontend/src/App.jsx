import { useState } from "react";
import { leerSesion, cerrarSesion } from "./api.js";
import LoginPanel from "./components/LoginPanel.jsx";
import Chat from "./components/Chat.jsx";

export default function App() {
  const [sesion, setSesion] = useState(() => leerSesion());

  function entrar(user) {
    setSesion(leerSesion());
  }

  function salir() {
    cerrarSesion();
    setSesion(null);
  }

  if (!sesion) {
    return (
      <div className="app">
        <LoginPanel onEntrar={entrar} />
      </div>
    );
  }

  return <Chat sesion={sesion} onSalir={salir} onSesionInvalida={salir} />;
}
