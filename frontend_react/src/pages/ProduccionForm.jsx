import React, { useState, useEffect } from 'react';
import {
  getOperadores,
  getDashboardOperador,
  getFormularioIngreso,
  procesarIngreso,
  getFallasDisponibles,
  getHistorialProduccion,
  getEstadisticasOperador
} from '../api/produccion.api';
import './ProduccionForm.css';

export const ProduccionForm = () => {
  const [step, setStep] = useState('seleccionar');
  const [operadores, setOperadores] = useState([]);
  const [operadorSeleccionado, setOperadorSeleccionado] = useState(null);
  const [dashboardData, setDashboardData] = useState(null);
  const [asignaciones, setAsignaciones] = useState([]);
  const [fallas, setFallas] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Estados del formulario de ingreso
  const [formData, setFormData] = useState({
    asignacion_id: '',
    cantidad: '',
    falla_id: '',
    observaciones: '',
    tipo_ingreso: 'INCREMENTAL'
  });

  // Cargar operadores al iniciar
  useEffect(() => {
    cargarOperadores();
  }, []);

  // Cargar lista de operadores
  const cargarOperadores = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await getOperadores();
      
      if (response.data.success) {
        setOperadores(response.data.operadores);
        setError('');
      } else {
        setError(response.data.error || 'Error al cargar operadores');
        setOperadores([]);
      }
    } catch (err) {
      setError('Error de conexión al cargar operadores');
      setOperadores([]);
      console.error('Error cargando operadores:', err);
    } finally {
      setLoading(false);
    }
  };

  // Seleccionar operador y cargar dashboard
  const seleccionarOperador = async (operador) => {
    setOperadorSeleccionado(operador);
    await cargarDashboard(operador.id);
  };

  // Cargar dashboard del operador
  const cargarDashboard = async (operadorId) => {
    setLoading(true);
    setError('');

    try {
      const response = await getDashboardOperador(operadorId);
      
      if (response.data.success) {
        setDashboardData(response.data);
        setStep('dashboard');
      } else {
        setError(response.data.error || 'Error al cargar dashboard');
      }
    } catch (err) {
      setError('Error de conexión al cargar dashboard');
      console.error('Error cargando dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  // Cargar formulario de ingreso
  const cargarFormularioIngreso = async () => {
    setLoading(true);
    setError('');

    try {
      const [asignacionesResponse, fallasResponse] = await Promise.all([
        getFormularioIngreso(operadorSeleccionado.id),
        getFallasDisponibles()
      ]);

      if (asignacionesResponse.data.success && fallasResponse.data.success) {
        setAsignaciones(asignacionesResponse.data.asignaciones_disponibles);
        setFallas(fallasResponse.data.fallas);
        setStep('ingresar');
      } else {
        setError('Error al cargar datos del formulario');
      }
    } catch (err) {
      setError('Error de conexión al cargar formulario');
      console.error('Error cargando formulario:', err);
    } finally {
      setLoading(false);
    }
  };

  // Procesar ingreso de producción
  const procesarIngresoProduccion = async (e) => {
    e.preventDefault();
    
    if (!formData.asignacion_id || !formData.cantidad) {
      setError('Debe seleccionar una asignación e ingresar cantidad');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await procesarIngreso(operadorSeleccionado.id, formData);

      if (response.data.success) {
        setSuccess(`¡Producción registrada exitosamente! ${response.data.message}`);
        
        // Resetear formulario
        setFormData({
          asignacion_id: '',
          cantidad: '',
          falla_id: '',
          observaciones: '',
          tipo_ingreso: 'INCREMENTAL'
        });
        
        // Recargar dashboard después de 2 segundos
        setTimeout(() => {
          cargarDashboard(operadorSeleccionado.id);
        }, 2000);
      } else {
        setError(response.data.error || 'Error al procesar ingreso');
      }
    } catch (err) {
      if (err.response?.data?.error) {
        setError(err.response.data.error);
      } else if (err.response?.data?.errores) {
        setError(err.response.data.errores.join(', '));
      } else {
        setError('Error de conexión al procesar ingreso');
      }
      console.error('Error procesando ingreso:', err);
    } finally {
      setLoading(false);
    }
  };

  // Renderizar selector de operadores
  const renderSelectorOperadores = () => (
    <div className="selector-container">
      <h2>👥 Seleccionar Operador</h2>
      
      <div className="selector-header">
        <button onClick={cargarOperadores} className="btn-secondary" disabled={loading}>
          🔄 Recargar Operadores
        </button>
        <span className="info-badge">
          {operadores.length} operadores disponibles
        </span>
      </div>

      {error && <div className="error-message">{error}</div>}

      {operadores.length > 0 ? (
        <div className="operadores-grid">
          {operadores.map((operador) => (
            <div
              key={operador.id}
              className={`operador-card ${operador.tiene_trabajo_activo ? 'con-trabajo' : 'sin-trabajo'}`}
              onClick={() => seleccionarOperador(operador)}
            >
              <div className="operador-avatar">
                {operador.nombre.split(' ').map(n => n[0]).join('').slice(0, 2)}
              </div>
              
              <div className="operador-info">
                <h4>{operador.nombre}</h4>
                <p className="rut">RUT: {operador.rut}</p>
                <p className="empresa">{operador.empresa.nombre}</p>
                
                <div className="operador-stats">
                  <span className={`stat-item ${operador.asignaciones_hoy > 0 ? 'active' : ''}`}>
                    📋 {operador.asignaciones_hoy} asignaciones
                  </span>
                  <span className={`stat-item ${operador.ingresos_hoy > 0 ? 'active' : ''}`}>
                    📊 {operador.ingresos_hoy} ingresos hoy
                  </span>
                </div>
              </div>
              
              {operador.tiene_trabajo_activo && (
                <div className="trabajo-activo-badge">
                  ✅ Con trabajo activo
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="no-operadores">
          {loading ? (
            <p>Cargando operadores...</p>
          ) : (
            <p>No hay operadores disponibles</p>
          )}
        </div>
      )}
    </div>
  );

  // Renderizar dashboard
  const renderDashboard = () => (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h2>👤 {operadorSeleccionado.nombre}</h2>
        <button onClick={() => setStep('seleccionar')} className="btn-secondary">
          ← Cambiar Operador
        </button>
      </div>

      {/* Estadísticas */}
      <div className="stats-grid">
        <div className="stat-card">
          <h3>{dashboardData.estadisticas_hoy.total_asignaciones}</h3>
          <p>Asignaciones Hoy</p>
        </div>
        <div className="stat-card">
          <h3>{dashboardData.estadisticas_hoy.total_producido}</h3>
          <p>Unidades Producidas</p>
        </div>
        <div className="stat-card">
          <h3>{dashboardData.estadisticas_hoy.total_ingresos}</h3>
          <p>Registros Hoy</p>
        </div>
      </div>

      {/* Asignaciones */}
      <div className="asignaciones-section">
        <div className="section-header">
          <h3>📋 Mis Asignaciones de Hoy</h3>
          <button onClick={cargarFormularioIngreso} className="btn-primary">
            ➕ Ingresar Producción
          </button>
        </div>

        {dashboardData.asignaciones.length > 0 ? (
          <div className="asignaciones-grid">
            {dashboardData.asignaciones.map((asignacion) => (
              <div key={asignacion.id} className="asignacion-card">
                <h4>OT: {asignacion.orden_trabajo.codigo_ot}</h4>
                <p><strong>Proceso:</strong> {asignacion.item_ruta.proceso.descripcion}</p>
                <p><strong>Máquina:</strong> {asignacion.item_ruta.maquina?.descripcion || 'Sin máquina'}</p>
                
                <div className="progress-info">
                  <div className="progress-bar">
                    <div 
                      className="progress-fill" 
                      style={{ width: `${asignacion.item_ruta.porcentaje_completado}%` }}
                    ></div>
                  </div>
                  <span>{asignacion.item_ruta.porcentaje_completado.toFixed(1)}%</span>
                </div>
                
                <div className="cantidad-info">
                  {asignacion.item_ruta.cantidad_terminada} / {asignacion.item_ruta.cantidad_pedido} unidades
                </div>
                
                <span className={`estado-badge estado-${asignacion.item_ruta.estado_proceso.toLowerCase()}`}>
                  {asignacion.item_ruta.estado_proceso}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="no-data">No hay asignaciones para hoy</div>
        )}
      </div>

      {/* Últimos ingresos */}
      {dashboardData.ultimos_ingresos.length > 0 && (
        <div className="ingresos-section">
          <h3>📈 Últimos Ingresos</h3>
          <div className="ingresos-list">
            {dashboardData.ultimos_ingresos.map((ingreso) => (
              <div key={ingreso.id} className="ingreso-item">
                <span className="hora">{new Date(ingreso.fecha_ingreso).toLocaleTimeString()}</span>
                <span className="ot">{ingreso.orden_trabajo || 'N/A'}</span>
                <span className="proceso">{ingreso.proceso || 'N/A'}</span>
                <span className="cantidad">{ingreso.cantidad} unidades</span>
                {ingreso.falla && <span className="falla">⚠️ {ingreso.falla.descripcion}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  // Renderizar formulario de ingreso
  const renderFormularioIngreso = () => (
    <div className="ingreso-container">
      <div className="ingreso-header">
        <h2>📊 Ingresar Producción - {operadorSeleccionado.nombre}</h2>
        <button onClick={() => setStep('dashboard')} className="btn-secondary">
          ← Volver al Dashboard
        </button>
      </div>

      <form onSubmit={procesarIngresoProduccion} className="ingreso-form">
        <div className="form-group">
          <label>Seleccionar Trabajo:</label>
          <select
            value={formData.asignacion_id}
            onChange={(e) => setFormData({...formData, asignacion_id: e.target.value})}
            required
          >
            <option value="">-- Seleccione una asignación --</option>
            {asignaciones.map((asignacion) => (
              <option key={asignacion.id} value={asignacion.id}>
                OT: {asignacion.orden_trabajo.codigo_ot} - {asignacion.proceso.descripcion}
                ({asignacion.cantidades.pendiente} pendientes)
              </option>
            ))}
          </select>
        </div>

        {/* Mostrar detalles de la asignación seleccionada */}
        {formData.asignacion_id && (
          <div className="asignacion-detalle">
            {(() => {
              const asignacion = asignaciones.find(a => a.id == formData.asignacion_id);
              return asignacion ? (
                <div className="detalle-card">
                  <h4>Detalles del Trabajo:</h4>
                  <p><strong>OT:</strong> {asignacion.orden_trabajo.codigo_ot}</p>
                  <p><strong>Proceso:</strong> {asignacion.proceso.descripcion}</p>
                  <p><strong>Máquina:</strong> {asignacion.maquina?.descripcion || 'Sin máquina'}</p>
                  <p><strong>Pendiente:</strong> {asignacion.cantidades.pendiente} unidades</p>
                  <p><strong>Progreso:</strong> {asignacion.cantidades.porcentaje.toFixed(1)}%</p>
                </div>
              ) : null;
            })()}
          </div>
        )}

        <div className="form-group">
          <label>Cantidad Producida:</label>
          <input
            type="number"
            step="0.01"
            min="0.01"
            value={formData.cantidad}
            onChange={(e) => setFormData({...formData, cantidad: e.target.value})}
            placeholder="Ingrese cantidad..."
            required
          />
        </div>

        <div className="form-group">
          <label>Tipo de Ingreso:</label>
          <select
            value={formData.tipo_ingreso}
            onChange={(e) => setFormData({...formData, tipo_ingreso: e.target.value})}
          >
            <option value="INCREMENTAL">Incremental (se suma a lo anterior)</option>
            <option value="TOTAL">Total (reemplaza el total)</option>
          </select>
        </div>

        <div className="form-group">
          <label>Reportar Falla (opcional):</label>
          <select
            value={formData.falla_id}
            onChange={(e) => setFormData({...formData, falla_id: e.target.value})}
          >
            <option value="">-- Sin fallas --</option>
            {fallas.map((falla) => (
              <option key={falla.id} value={falla.id}>
                {falla.descripcion}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Observaciones (opcional):</label>
          <textarea
            value={formData.observaciones}
            onChange={(e) => setFormData({...formData, observaciones: e.target.value})}
            placeholder="Escriba observaciones adicionales..."
            rows="3"
          />
        </div>

        <div className="form-actions">
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? 'Procesando...' : '✅ Registrar Producción'}
          </button>
        </div>
      </form>

      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">{success}</div>}
    </div>
  );

  return (
    <div className="produccion-app">
      {loading && <div className="loading-overlay">Cargando...</div>}
      
      {step === 'seleccionar' && renderSelectorOperadores()}
      {step === 'dashboard' && renderDashboard()}
      {step === 'ingresar' && renderFormularioIngreso()}
    </div>
  );
};
