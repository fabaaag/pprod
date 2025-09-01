import React, { useState, useEffect, useRef } from 'react';
import { Line, Bar, Doughnut, Radar } from 'react-chartjs-2';
import { getDashboardEjecutivo, testDashboardBase, testApiConnectivity } from '../../api/executive.api';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  RadialLinearScale,
} from 'chart.js';
import './css/DashboardEjecutivo.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  RadialLinearScale
);
  

const DashboardEjecutivo = ({ programaId }) => {
  const [metricas, setMetricas] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tabActiva, setTabActiva] = useState('resumen');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [alertasVisibles, setAlertasVisibles] = useState(true);
  const intervalRef = useRef(null);

  const cargarMetricas = async () => {
    try {
      // PASO 1: Probar conectividad básica
      console.log('🔄 Probando conectividad API...');
      await testApiConnectivity();
      console.log('✅ Conectividad OK');
      
      // PASO 2: Usar dashboard de prueba
      console.log('🔄 Cargando dashboard de prueba...');
      const data = await getDashboardEjecutivo(programaId);
      console.log('✅ Dashboard de prueba cargado:', data);
      
      setMetricas(data.metricas);
      setError(null);
      
      // TODO: Cambiar a getDashboardEjecutivo(programaId) cuando esté funcionando
    } catch (err) {
      console.error('❌ Error cargando dashboard:', err);
      setError('Error al cargar dashboard ejecutivo: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarMetricas();
    
    if (autoRefresh) {
      intervalRef.current = setInterval(cargarMetricas, 60000); // Cada minuto
    }
    
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [programaId, autoRefresh]);

  const toggleAutoRefresh = () => {
    setAutoRefresh(!autoRefresh);
    if (!autoRefresh && intervalRef.current) {
      clearInterval(intervalRef.current);
    }
  };

  if (loading) {
    return (
      <div className="dashboard-ejecutivo-loading">
        <div className="loading-spinner"></div>
        <p>Cargando Dashboard Ejecutivo...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-ejecutivo-error">
        <h3>Error</h3>
        <p>{error}</p>
        <button onClick={cargarMetricas}>Reintentar</button>
      </div>
    );
  }

  const ResumenGeneral = () => {
    const produccion = metricas?.produccion_fisica?.resumen_general || {};
    const alertas = metricas?.alertas_ejecutivas || [];
    const proyecciones = metricas?.proyecciones || {};

    return (
      <div className="resumen-general">
        {/* KPIs Principales */}
        <div className="kpis-principales">
          <div className="kpi-card kilos-planificados">
            <div className="kpi-icono">📊</div>
            <div className="kpi-contenido">
              <h3>Kilos Planificados</h3>
              <div className="kpi-valor">{(produccion.kilos_planificados || 0).toLocaleString()}</div>
              <div className="kpi-unidad">kg</div>
            </div>
          </div>

          <div className="kpi-card kilos-fabricados">
            <div className="kpi-icono">🏭</div>
            <div className="kpi-contenido">
              <h3>Kilos Fabricados</h3>
              <div className="kpi-valor">{(produccion.kilos_fabricados || 0).toLocaleString()}</div>
              <div className="kpi-unidad">kg</div>
            </div>
          </div>

          <div className="kpi-card porcentaje-completado">
            <div className="kpi-icono">📈</div>
            <div className="kpi-contenido">
              <h3>% Completado</h3>
              <div className="kpi-valor">{(produccion.porcentaje_completado_kilos || 0).toFixed(1)}</div>
              <div className="kpi-unidad">%</div>
            </div>
          </div>

          <div className="kpi-card kilos-pendientes">
            <div className="kpi-icono">⏳</div>
            <div className="kpi-contenido">
              <h3>Kilos Pendientes</h3>
              <div className="kpi-valor">{(produccion.kilos_pendientes || 0).toLocaleString()}</div>
              <div className="kpi-unidad">kg</div>
            </div>
          </div>

          {/* Preparado para precios */}
          <div className="kpi-card precio-estimado">
            <div className="kpi-icono">💰</div>
            <div className="kpi-contenido">
              <h3>Valor Estimado</h3>
              <div className="kpi-valor">$0</div>
              <div className="kpi-nota">Configurar precios</div>
            </div>
          </div>

          <div className="kpi-card eficiencia">
            <div className="kpi-icono">⚡</div>
            <div className="kpi-contenido">
              <h3>Eficiencia</h3>
              <div className="kpi-valor">{(metricas?.eficiencia_operacional?.resumen_eficiencia?.eficiencia_promedio_programa || 0).toFixed(1)}</div>
              <div className="kpi-unidad">%</div>
            </div>
          </div>
        </div>

        {/* Gráfico Principal - Progreso */}
        <div className="grafico-principal">
          <h3>Progreso de Producción</h3>
          <div className="grafico-progreso-container">
            <Doughnut
              data={{
                labels: ['Fabricado', 'Pendiente'],
                datasets: [{
                  data: [
                    produccion.kilos_fabricados || 0,
                    produccion.kilos_pendientes || 0
                  ],
                  backgroundColor: ['#28a745', '#dc3545'],
                  borderWidth: 0
                }]
              }}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    position: 'bottom'
                  }
                }
              }}
            />
          </div>
        </div>

        {/* Alertas Ejecutivas */}
        {alertas.length > 0 && alertasVisibles && (
          <div className="alertas-ejecutivas">
            <div className="alertas-header">
              <h3>🚨 Alertas Ejecutivas</h3>
              <button onClick={() => setAlertasVisibles(false)}>×</button>
            </div>
            {alertas.map((alerta, index) => (
              <div key={index} className={`alerta alerta-${alerta.prioridad.toLowerCase()}`}>
                <div className="alerta-titulo">{alerta.titulo}</div>
                <div className="alerta-descripcion">{alerta.descripcion}</div>
                <div className="alerta-impacto">{alerta.impacto_ejecutivo}</div>
                <div className="alerta-accion">{alerta.accion_recomendada}</div>
              </div>
            ))}
          </div>
        )}

        {/* Proyecciones */}
        {proyecciones.finalizacion && (
          <div className="proyecciones">
            <h3>📅 Proyecciones</h3>
            <div className="proyeccion-item">
              <strong>Fecha Proyectada de Finalización:</strong> {proyecciones.finalizacion.fecha_proyectada || 'Sin calcular'}
            </div>
            <div className="proyeccion-item">
              <strong>Retraso Estimado:</strong> {proyecciones.finalizacion.retraso_dias || 0} días
            </div>
            <div className="proyeccion-item">
              <strong>Probabilidad de Cumplimiento:</strong> {proyecciones.finalizacion.probabilidad_cumplimiento || 0}%
            </div>
          </div>
        )}
      </div>
    );
  };

  const ProduccionDetallada = () => {
    const produccion = metricas?.produccion_fisica || {};
    const detalleProductos = produccion.detalle_por_producto || [];
    const produccionDiaria = produccion.produccion_diaria || [];

    return (
      <div className="produccion-detallada">
        {/* Gráfico de Producción Diaria */}
        <div className="grafico-produccion-diaria">
          <h3>Producción Diaria</h3>
          <Line
            data={{
              labels: produccionDiaria.map(d => d.fecha),
              datasets: [
                {
                  label: 'Kilos Planificados',
                  data: produccionDiaria.map(d => d.kilos_planificados),
                  borderColor: '#007bff',
                  backgroundColor: 'rgba(0, 123, 255, 0.1)',
                  fill: true
                },
                {
                  label: 'Kilos Fabricados',
                  data: produccionDiaria.map(d => d.kilos_fabricados),
                  borderColor: '#28a745',
                  backgroundColor: 'rgba(40, 167, 69, 0.1)',
                  fill: true
                }
              ]
            }}
            options={{
              responsive: true,
              scales: {
                y: {
                  beginAtZero: true,
                  title: {
                    display: true,
                    text: 'Kilogramos'
                  }
                }
              }
            }}
          />
        </div>

        {/* Tabla Detalle por Producto */}
        <div className="tabla-productos">
          <h3>Detalle por Producto</h3>
          <div className="tabla-container">
            <table>
              <thead>
                <tr>
                  <th>OT</th>
                  <th>Producto</th>
                  <th>Cliente</th>
                  <th>Kg Planificados</th>
                  <th>Kg Fabricados</th>
                  <th>% Avance</th>
                  <th>Valor Estimado</th>
                </tr>
              </thead>
              <tbody>
                {detalleProductos.map((producto, index) => (
                  <tr key={index}>
                    <td>{producto.orden_codigo}</td>
                    <td>
                      <div className="producto-info">
                        <strong>{producto.producto_codigo}</strong>
                        <small>{producto.descripcion}</small>
                      </div>
                    </td>
                    <td>{producto.cliente}</td>
                    <td>{producto.kilos_planificados.toLocaleString()}</td>
                    <td>{producto.kilos_fabricados.toLocaleString()}</td>
                    <td>
                      <div className="progress-bar">
                        <div 
                          className="progress-fill" 
                          style={{ width: `${producto.porcentaje_avance}%` }}
                        ></div>
                        <span>{producto.porcentaje_avance.toFixed(1)}%</span>
                      </div>
                    </td>
                    <td>
                      <span className="valor-pendiente">$0</span>
                      <small>Configurar precio</small>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  const EficienciaOperacional = () => {
    const eficiencia = metricas?.eficiencia_operacional || {};
    const eficienciaMaquinas = eficiencia.eficiencia_por_maquina || [];
    const eficienciaOperadores = eficiencia.eficiencia_por_operador || [];

    return (
      <div className="eficiencia-operacional">
        {/* Gráfico Eficiencia por Máquina */}
        <div className="grafico-eficiencia-maquinas">
          <h3>Eficiencia por Máquina</h3>
          <Bar
            data={{
              labels: eficienciaMaquinas.map(m => m.maquina_codigo),
              datasets: [{
                label: 'Eficiencia (%)',
                data: eficienciaMaquinas.map(m => m.eficiencia_promedio),
                backgroundColor: eficienciaMaquinas.map(m => 
                  m.eficiencia_promedio >= 80 ? '#28a745' : 
                  m.eficiencia_promedio >= 60 ? '#ffc107' : '#dc3545'
                )
              }]
            }}
            options={{
              responsive: true,
              scales: {
                y: {
                  beginAtZero: true,
                  max: 100
                }
              }
            }}
          />
        </div>

        {/* Tabla Eficiencia Operadores */}
        <div className="tabla-operadores">
          <h3>Eficiencia por Operador</h3>
          <div className="tabla-container">
            <table>
              <thead>
                <tr>
                  <th>Operador</th>
                  <th>Tareas Asignadas</th>
                  <th>Tareas Completadas</th>
                  <th>Eficiencia Tareas</th>
                  <th>Eficiencia Cantidad</th>
                </tr>
              </thead>
              <tbody>
                {eficienciaOperadores.map((operador, index) => (
                  <tr key={index}>
                    <td>{operador.operador_nombre}</td>
                    <td>{operador.tareas_asignadas}</td>
                    <td>{operador.tareas_completadas}</td>
                    <td>
                      <span className={`eficiencia-badge ${
                        operador.eficiencia_tareas >= 80 ? 'alta' :
                        operador.eficiencia_tareas >= 60 ? 'media' : 'baja'
                      }`}>
                        {operador.eficiencia_tareas.toFixed(1)}%
                      </span>
                    </td>
                    <td>
                      <span className={`eficiencia-badge ${
                        operador.eficiencia_cantidad >= 80 ? 'alta' :
                        operador.eficiencia_cantidad >= 60 ? 'media' : 'baja'
                      }`}>
                        {operador.eficiencia_cantidad.toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  const CumplimientoEntregas = () => {
    const cumplimiento = metricas?.cumplimiento_entregas || {};
    const cumplimientoClientes = Object.entries(cumplimiento.cumplimiento_por_cliente || {});

    return (
      <div className="cumplimiento-entregas">
        <h3>Cumplimiento de Entregas por Cliente</h3>
        
        <div className="clientes-grid">
          {cumplimientoClientes.map(([cliente, datos], index) => (
            <div key={index} className="cliente-card">
              <h4>{cliente}</h4>
              <div className="cliente-metricas">
                <div className="metrica">
                  <span className="metrica-label">Órdenes Totales:</span>
                  <span className="metrica-valor">{datos.ordenes_total}</span>
                </div>
                <div className="metrica">
                  <span className="metrica-label">A Tiempo:</span>
                  <span className="metrica-valor">{datos.ordenes_a_tiempo}</span>
                </div>
                <div className="metrica">
                  <span className="metrica-label">Retrasadas:</span>
                  <span className="metrica-valor">{datos.ordenes_retrasadas}</span>
                </div>
                <div className="metrica">
                  <span className="metrica-label">Kilos Entregados:</span>
                  <span className="metrica-valor">{datos.kilos_entregados.toLocaleString()} kg</span>
                </div>
                <div className="cumplimiento-porcentaje">
                  <div className="progress-bar">
                    <div 
                      className="progress-fill" 
                      style={{ 
                        width: `${datos.porcentaje_cumplimiento || 0}%`,
                        backgroundColor: datos.porcentaje_cumplimiento >= 80 ? '#28a745' : 
                                       datos.porcentaje_cumplimiento >= 60 ? '#ffc107' : '#dc3545'
                      }}
                    ></div>
                    <span>{(datos.porcentaje_cumplimiento || 0).toFixed(1)}%</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const CostosEstimados = () => {
    const costos = metricas?.costos_estimados || {};

    return (
      <div className="costos-estimados">
        <div className="costos-header">
          <h3>💰 Estructura de Costos</h3>
          <div className="config-notice">
            ⚠️ Configurar precios y costos para cálculos precisos
          </div>
        </div>

        <div className="costos-grid">
          <div className="costo-categoria">
            <h4>Costos de Materiales</h4>
            <div className="costo-item">
              <span>Planificado:</span>
              <span>$0 {costos.costos_materiales?.nota}</span>
            </div>
          </div>

          <div className="costo-categoria">
            <h4>Costos de Mano de Obra</h4>
            <div className="costo-item">
              <span>Horas Planificadas:</span>
              <span>{costos.costos_mano_obra?.horas_planificadas || 0} hrs</span>
            </div>
            <div className="costo-item">
              <span>Horas Reales:</span>
              <span>{costos.costos_mano_obra?.horas_reales || 0} hrs</span>
            </div>
            <div className="config-note">{costos.costos_mano_obra?.nota}</div>
          </div>

          <div className="costo-categoria">
            <h4>Costos de Máquina</h4>
            <div className="costo-item">
              <span>Horas Máquina:</span>
              <span>{costos.costos_maquina?.horas_maquina_planificadas || 0} hrs</span>
            </div>
            <div className="config-note">{costos.costos_maquina?.nota}</div>
          </div>

          <div className="costo-categoria">
            <h4>Indicadores Preparados</h4>
            <div className="indicadores-futuros">
              <div>• Costo por Kilo</div>
              <div>• Costo por Unidad</div>
              <div>• Margen Estimado</div>
              <div>• ROI del Programa</div>
            </div>
          </div>
        </div>

        <div className="configuracion-costos">
          <button className="btn-configurar">
            ⚙️ Configurar Precios y Costos
          </button>
        </div>
      </div>
    );
  };

  const renderTabContent = () => {
    switch (tabActiva) {
      case 'resumen': return <ResumenGeneral />;
      case 'produccion': return <ProduccionDetallada />;
      case 'eficiencia': return <EficienciaOperacional />;
      case 'entregas': return <CumplimientoEntregas />;
      case 'costos': return <CostosEstimados />;
      default: return <ResumenGeneral />;
    }
  };

  return (
    <div className="dashboard-ejecutivo">
      {/* Header */}
      <div className="dashboard-header">
        <div className="header-title">
          <h1>🎯 Dashboard Ejecutivo</h1>
          <div className="header-subtitle">
            Métricas y KPIs de alto nivel para toma de decisiones
          </div>
        </div>
        
        <div className="header-controls">
          <div className="auto-refresh">
            <label>
              <input 
                type="checkbox" 
                checked={autoRefresh} 
                onChange={toggleAutoRefresh}
              />
              Auto-refresh
            </label>
          </div>
          
          <button className="btn-export">
            📊 Exportar Reporte
          </button>
          
          <div className="last-update">
            Última actualización: {new Date().toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* Navegación por pestañas */}
      <div className="dashboard-tabs">
        <button 
          className={`tab ${tabActiva === 'resumen' ? 'activa' : ''}`}
          onClick={() => setTabActiva('resumen')}
        >
          📊 Resumen Ejecutivo
        </button>
        <button 
          className={`tab ${tabActiva === 'produccion' ? 'activa' : ''}`}
          onClick={() => setTabActiva('produccion')}
        >
          🏭 Producción
        </button>
        <button 
          className={`tab ${tabActiva === 'eficiencia' ? 'activa' : ''}`}
          onClick={() => setTabActiva('eficiencia')}
        >
          ⚡ Eficiencia
        </button>
        <button 
          className={`tab ${tabActiva === 'entregas' ? 'activa' : ''}`}
          onClick={() => setTabActiva('entregas')}
        >
          📅 Entregas
        </button>
        <button 
          className={`tab ${tabActiva === 'costos' ? 'activa' : ''}`}
          onClick={() => setTabActiva('costos')}
        >
          💰 Costos
        </button>
      </div>

      {/* Contenido */}
      <div className="dashboard-content">
        {renderTabContent()}
      </div>
    </div>
  );
};

export default DashboardEjecutivo; 