// Las citas son el elemento distintivo de esta consola: cada respuesta muestra
// de que documento y pagina salio, con la puntuacion de relevancia. Es lo que
// convierte una respuesta en algo verificable.

export default function CitationList({ citas }) {
  if (!citas || citas.length === 0) return null;
  return (
    <div className="citations">
      <div className="label">Fuentes</div>
      {citas.map((c, i) => (
        <div className="cite" key={`${c.document_id}-${c.page_start}-${i}`}>
          <span className="doc">{c.title}</span>
          <span className="page">
            p.{c.page_start}
            {c.page_end !== c.page_start ? `–${c.page_end}` : ""}
          </span>
          <span className="score">rel {c.score}</span>
        </div>
      ))}
    </div>
  );
}
