import { useEffect, useState } from 'react'
import { supabase } from './supabase'
import './App.css'

function App() {
  const [referencias, setReferencias] = useState([])
  const [loading, setLoading] = useState(false)

  const [filtros, setFiltros] = useState({
    proveedor: '',
    dali: '',
    sap: '',
    referencia: '',
  })

  const cargarReferencias = async () => {
    setLoading(true)

    const { data, error } = await supabase
      .from('referencias')
      .select('id, proveedor, codigo_proveedor, codigo_general, dali, sap, referencia, ficha_pdf, tiene_ficha')
      .order('proveedor', { ascending: true })
      .limit(200)

    if (error) {
      console.error(error)
      alert(`Error cargando referencias: ${error.message}`)
      setReferencias([])
    } else {
      setReferencias(data || [])
    }

    setLoading(false)
  }

  const buscar = async () => {
    setLoading(true)

    let query = supabase
      .from('referencias')
      .select('id, proveedor, codigo_proveedor, codigo_general, dali, sap, referencia, ficha_pdf, tiene_ficha')
      .order('proveedor', { ascending: true })
      .limit(500)

    if (filtros.proveedor.trim()) {
      query = query.ilike('proveedor', `%${filtros.proveedor.trim()}%`)
    }

    if (filtros.dali.trim()) {
      query = query.ilike('dali', `%${filtros.dali.trim()}%`)
    }

    if (filtros.sap.trim()) {
      query = query.ilike('sap', `%${filtros.sap.trim()}%`)
    }

    if (filtros.referencia.trim()) {
      query = query.ilike('referencia', `%${filtros.referencia.trim()}%`)
    }

    const { data, error } = await query

    if (error) {
      console.error(error)
      alert(`Error buscando referencias: ${error.message}`)
      setReferencias([])
    } else {
      setReferencias(data || [])
    }

    setLoading(false)
  }

  const verSinFicha = async () => {
    setLoading(true)

    const { data, error } = await supabase
      .from('referencias')
      .select('id, proveedor, codigo_proveedor, codigo_general, dali, sap, referencia, ficha_pdf, tiene_ficha')
      .or('tiene_ficha.is.false,ficha_pdf.is.null')
      .order('proveedor', { ascending: true })
      .limit(500)

    if (error) {
      console.error(error)
      alert(`Error cargando referencias sin ficha: ${error.message}`)
      setReferencias([])
    } else {
      setReferencias(data || [])
    }

    setLoading(false)
  }

  useEffect(() => {
    cargarReferencias()
  }, [])

  return (
    <div className="container">
      <div className="hero">
        <img src="/logo.jpg" alt="Princess Hotels" className="hero-logo" />

        <div className="hero-text">
          <h1>DEPARTAMENTO DE COMPRAS</h1>
          <h2>FICHAS TÉCNICAS</h2>
        </div>
      </div>

      <div className="card">
        <h3>Filtros</h3>

        <div className="grid">
          <input
            placeholder="Proveedor"
            value={filtros.proveedor}
            onChange={(e) => setFiltros({ ...filtros, proveedor: e.target.value })}
          />
          <input
            placeholder="DALI"
            value={filtros.dali}
            onChange={(e) => setFiltros({ ...filtros, dali: e.target.value })}
          />
          <input
            placeholder="SAP"
            value={filtros.sap}
            onChange={(e) => setFiltros({ ...filtros, sap: e.target.value })}
          />
          <input
            placeholder="Nombre del artículo"
            value={filtros.referencia}
            onChange={(e) => setFiltros({ ...filtros, referencia: e.target.value })}
          />
        </div>

        <div className="actions">
          <button onClick={buscar}>Buscar</button>
          <button onClick={cargarReferencias}>Ver todos</button>
          <button onClick={verSinFicha}>Sin ficha</button>
        </div>
      </div>

      <div className="card">
        <h3>Resultados</h3>

        {loading ? (
          <p>Cargando...</p>
        ) : referencias.length === 0 ? (
          <p>No hay resultados</p>
        ) : (
          referencias.map((r) => (
            <div key={r.id} className="item">
              <div className="item-title">{r.referencia || r.codigo_general || '(sin nombre)'}</div>
              <div><strong>Proveedor:</strong> {r.proveedor || '-'}</div>
              <div><strong>Código proveedor:</strong> {r.codigo_proveedor || '-'}</div>
              <div><strong>Código general:</strong> {r.codigo_general || '-'}</div>
              <div><strong>DALI:</strong> {r.dali || '-'}</div>
              <div><strong>SAP:</strong> {r.sap || '-'}</div>

              <div className="item-actions">
                {r.ficha_pdf ? (
                  <a href={r.ficha_pdf} target="_blank" rel="noreferrer">
                    Ver ficha PDF
                  </a>
                ) : (
                  <span className="sin-ficha">Sin ficha</span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default App
