import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Progress, Alert, Button, DatePicker, Select, Spin, Tabs } from 'antd';
import { 
  TrendingUpOutlined, 
  TrendingDownOutlined, 
  WarningOutlined, 
  CheckCircleOutlined,
  ExportOutlined,
  ReloadOutlined,
  BarChartOutlined,
  LineChartOutlined,
  DashboardOutlined
} from '@ant-design/icons';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import './css/DashboardAvanzado.css';

const { TabPane } = Tabs;
const { Option } = Select;
const { RangePicker } = DatePicker;

const DashboardAvanzado = ({ programaId, onExportar }) => {
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState(null);
  const [alertas, setAlertas] = useState([]);
  const [tendencias, setTendencias] = useState(null);
  const [selectedPeriod, setSelectedPeriod] = useState('7');
  const [refreshInterval, setRefreshInterval] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    if (programaId) {
      fetchDashboardData();
      fetchAlertas();
      
      // Auto-refresh cada 5 minutos
      const interval = setInterval(() => {
        fetchDashboardData();
        fetchAlertas();
      }, 300000);
      
      setRefreshInterval(interval);
      
      return () => {
        if (interval) clearInterval(interval);
      };
    }
  }, [programaId]);

  useEffect(() => {
    if (programaId && selectedPeriod) {
      fetchTendencias();
    }
  }, [programaId, selectedPeriod]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/programas/${programaId}/dashboard/`);
      
      if (response.ok) {
        const data = await response.json();
        setDashboardData(data.dashboard);
        setLastUpdate(new Date());
      } else {
        console.error('Error fetching dashboard data');
      }
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAlertas = async () => {
    try {
      const response = await fetch(`/api/programas/${programaId}/alertas/`);
      
      if (response.ok) {
        const data = await response.json();
        setAlertas(data.alertas || []);
      }
    } catch (error) {
      console.error('Error fetching alertas:', error);
    }
  };

  const fetchTendencias = async () => {
    try {
      const response = await fetch(`/api/programas/${programaId}/tendencias/?days=${selectedPeriod}`);
      
      if (response.ok) {
        const data = await response.json();
        setTendencias(data.analisis_tendencias);
      }
    } catch (error) {
      console.error('Error fetching tendencias:', error);
    }
  };

  const handleExportar = async (formato) => {
    try {
      const response = await fetch(`/api/programas/${programaId}/exportar-metricas/?formato=${formato}`);
      
      if (response.ok) {
        const data = await response.json();
        if (onExportar) {
          onExportar(data, formato);
        }
      }
    } catch (error) {
      console.error('Error exportando:', error);
    }
  };

  const renderKPICard = (title, value, trend, description, color = "blue") => {
    const trendIcon = trend === 'mejorando' ? 
      <TrendingUpOutlined style={{ color: '#52c41a' }} /> : 
      trend === 'deteriorando' ? 
      <TrendingDownOutlined style={{ color: '#ff4d4f' }} /> : 
      null;

    return (
      <Card className="kpi-card" hoverable>
        <Statistic
          title={title}
          value={value}
          precision={2}
          suffix={trendIcon}
          valueStyle={{ color: color === 'success' ? '#3f8600' : color === 'warning' ? '#cf1322' : '#1890ff' }}
        />
        <div className="kpi-description">{description}</div>
      </Card>
    );
  };

  const renderAlertasBanner = () => {
    if (!alertas || alertas.length === 0) return null;

    const alertasCriticas = alertas.filter(a => a.prioridad === 'CRITICA');
    const alertasAltas = alertas.filter(a => a.prioridad === 'ALTA');

    return (
      <div className="alertas-banner">
        {alertasCriticas.map(alerta => (
          <Alert
            key={alerta.id}
            message={alerta.titulo}
            description={alerta.descripcion}
            type="error"
            icon={<WarningOutlined />}
            showIcon
            closable
            style={{ marginBottom: 8 }}
          />
        ))}
        {alertasAltas.map(alerta => (
          <Alert
            key={alerta.id}
            message={alerta.titulo}
            description={alerta.descripcion}
            type="warning"
            showIcon
            closable
            style={{ marginBottom: 8 }}
          />
        ))}
      </div>
    );
  };

  const renderProgressChart = (data, title) => {
    if (!data || !data.metricas_diarias) return null;

    const chartData = data.metricas_diarias.map(metrica => ({
      fecha: metrica.fecha,
      produccion: metrica.resumen.produccion_total,
      eficiencia: metrica.eficiencia_dia,
      completadas: metrica.resumen.tareas_completadas,
      programadas: metrica.resumen.tareas_programadas
    }));

    return (
      <Card title={title} className="chart-card">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="fecha" />
            <YAxis yAxisId="left" />
            <YAxis yAxisId="right" orientation="right" />
            <Tooltip />
            <Legend />
            <Line 
              yAxisId="left" 
              type="monotone" 
              dataKey="produccion" 
              stroke="#8884d8" 
              strokeWidth={2}
              name="Producción"
            />
            <Line 
              yAxisId="right" 
              type="monotone" 
              dataKey="eficiencia" 
              stroke="#82ca9d" 
              strokeWidth={2}
              name="Eficiencia %"
            />
          </LineChart>
        </ResponsiveContainer>
      </Card>
    );
  };

  const renderUtilizacionChart = (utilizacionData) => {
    if (!utilizacionData || !utilizacionData.maquinas) return null;

    const maquinasData = utilizacionData.maquinas.detalle_por_maquina.slice(0, 5).map(maquina => ({
      nombre: maquina.codigo,
      utilizacion: maquina.utilizacion_porcentaje,
      horas: maquina.horas_utilizadas
    }));

    const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

    return (
      <Card title="Utilización de Máquinas" className="chart-card">
        <Row gutter={16}>
          <Col span={12}>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={maquinasData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="nombre" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="utilizacion" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </Col>
          <Col span={12}>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={maquinasData}
                  dataKey="horas"
                  nameKey="nombre"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label
                >
                  {maquinasData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </Col>
        </Row>
      </Card>
    );
  };

  const renderResumenEjecutivo = (resumen) => {
    if (!resumen) return null;

    return (
      <Card title="Resumen Ejecutivo" className="resumen-ejecutivo">
        <Row gutter={16}>
          <Col span={8}>
            <div className="estado-general">
              <h4>Estado General</h4>
              <div className={`estado-badge estado-${resumen.estado_general.toLowerCase()}`}>
                {resumen.estado_general}
              </div>
            </div>
          </Col>
          <Col span={8}>
            <div className="destacados">
              <h4>Destacados</h4>
              {resumen.destacados.map((destacado, index) => (
                <div key={index} className="destacado-item">
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                  {destacado.mensaje}
                </div>
              ))}
            </div>
          </Col>
          <Col span={8}>
            <div className="recomendaciones">
              <h4>Recomendaciones</h4>
              {resumen.recomendaciones_principales.map((rec, index) => (
                <div key={index} className="recomendacion-item">
                  • {rec}
                </div>
              ))}
            </div>
          </Col>
        </Row>
      </Card>
    );
  };

  if (loading && !dashboardData) {
    return (
      <div className="dashboard-loading">
        <Spin size="large" />
        <p>Cargando dashboard...</p>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="dashboard-error">
        <Alert
          message="Error"
          description="No se pudieron cargar los datos del dashboard"
          type="error"
          showIcon
        />
      </div>
    );
  }

  return (
    <div className="dashboard-avanzado">
      {/* Header con controles */}
      <div className="dashboard-header">
        <div className="dashboard-title">
          <h2>
            <DashboardOutlined /> Dashboard de Producción
          </h2>
          {lastUpdate && (
            <span className="last-update">
              Última actualización: {lastUpdate.toLocaleTimeString()}
            </span>
          )}
        </div>
        <div className="dashboard-controls">
          <Select 
            value={selectedPeriod} 
            onChange={setSelectedPeriod}
            style={{ width: 120, marginRight: 8 }}
          >
            <Option value="3">3 días</Option>
            <Option value="7">7 días</Option>
            <Option value="14">14 días</Option>
            <Option value="30">30 días</Option>
          </Select>
          <Button 
            icon={<ReloadOutlined />} 
            onClick={fetchDashboardData}
            style={{ marginRight: 8 }}
          >
            Actualizar
          </Button>
          <Button 
            icon={<ExportOutlined />} 
            onClick={() => handleExportar('json')}
          >
            Exportar
          </Button>
        </div>
      </div>

      {/* Alertas */}
      {renderAlertasBanner()}

      {/* Tabs principales */}
      <Tabs defaultActiveKey="overview" className="dashboard-tabs">
        <TabPane tab={<span><BarChartOutlined />Resumen</span>} key="overview">
          {/* KPIs principales */}
          <Row gutter={16} className="kpis-row">
            <Col span={6}>
              {renderKPICard(
                "Eficiencia General",
                dashboardData.kpis_principales.eficiencia_general.porcentaje,
                dashboardData.kpis_principales.eficiencia_general.tendencia,
                "Eficiencia del programa",
                dashboardData.kpis_principales.eficiencia_general.porcentaje > 80 ? 'success' : 
                dashboardData.kpis_principales.eficiencia_general.porcentaje < 60 ? 'warning' : 'blue'
              )}
            </Col>
            <Col span={6}>
              {renderKPICard(
                "Cumplimiento Plazos",
                dashboardData.kpis_principales.cumplimiento_plazos.porcentaje,
                'estable',
                `${dashboardData.kpis_principales.cumplimiento_plazos.ordenes_a_tiempo} de ${dashboardData.kpis_principales.cumplimiento_plazos.ordenes_analizadas} órdenes`,
                dashboardData.kpis_principales.cumplimiento_plazos.porcentaje > 85 ? 'success' : 
                dashboardData.kpis_principales.cumplimiento_plazos.porcentaje < 70 ? 'warning' : 'blue'
              )}
            </Col>
            <Col span={6}>
              {renderKPICard(
                "Utilización Recursos",
                dashboardData.kpis_principales.utilizacion_recursos.general,
                'mejorando',
                "Máquinas y operadores",
                dashboardData.kpis_principales.utilizacion_recursos.general > 75 ? 'success' : 'blue'
              )}
            </Col>
            <Col span={6}>
              {renderKPICard(
                "Calidad Planificación",
                dashboardData.kpis_principales.calidad_planificacion.score_general,
                'estable',
                dashboardData.kpis_principales.calidad_planificacion.nivel,
                dashboardData.kpis_principales.calidad_planificacion.score_general > 80 ? 'success' : 'blue'
              )}
            </Col>
          </Row>

          {/* Resumen ejecutivo */}
          {renderResumenEjecutivo(dashboardData.resumen_ejecutivo)}

          {/* Métricas del día */}
          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col span={12}>
              <Card title="Producción Hoy" className="metricas-hoy">
                <Row gutter={16}>
                  <Col span={12}>
                    <Statistic
                      title="Tareas Completadas"
                      value={dashboardData.metricas_hoy.resumen.tareas_completadas}
                      suffix={`/ ${dashboardData.metricas_hoy.resumen.tareas_programadas}`}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="Producción Total"
                      value={dashboardData.metricas_hoy.resumen.produccion_total}
                      precision={2}
                    />
                  </Col>
                </Row>
                <div style={{ marginTop: 16 }}>
                  <Progress
                    percent={Math.round((dashboardData.metricas_hoy.resumen.tareas_completadas / dashboardData.metricas_hoy.resumen.tareas_programadas) * 100)}
                    status={dashboardData.metricas_hoy.resumen.tareas_completadas === dashboardData.metricas_hoy.resumen.tareas_programadas ? 'success' : 'active'}
                  />
                </div>
              </Card>
            </Col>
            <Col span={12}>
              <Card title="Eficiencia Hoy">
                <Statistic
                  title="Eficiencia del Día"
                  value={dashboardData.metricas_hoy.eficiencia_dia}
                  precision={2}
                  suffix="%"
                  valueStyle={{ 
                    color: dashboardData.metricas_hoy.eficiencia_dia > 80 ? '#3f8600' : 
                           dashboardData.metricas_hoy.eficiencia_dia < 60 ? '#cf1322' : '#1890ff' 
                  }}
                />
                <div className="utilizacion-recursos-hoy">
                  <p>Máquinas: {dashboardData.metricas_hoy.utilizacion_recursos.maquinas}%</p>
                  <p>Operadores: {dashboardData.metricas_hoy.utilizacion_recursos.operadores}%</p>
                </div>
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane tab={<span><LineChartOutlined />Tendencias</span>} key="tendencias">
          {tendencias && renderProgressChart(tendencias, "Tendencias de Producción")}
          {dashboardData.kpis_principales.utilizacion_recursos && 
           renderUtilizacionChart(dashboardData.kpis_principales.utilizacion_recursos)}
        </TabPane>

        <TabPane tab={<span><WarningOutlined />Alertas y Análisis</span>} key="alertas">
          <div className="alertas-detalle">
            {alertas.length > 0 ? (
              alertas.map(alerta => (
                <Card key={alerta.id} style={{ marginBottom: 16 }}>
                  <Alert
                    message={alerta.titulo}
                    description={
                      <div>
                        <p>{alerta.descripcion}</p>
                        {alerta.valor_actual && (
                          <p>
                            <strong>Valor actual:</strong> {alerta.valor_actual}
                            {alerta.umbral && ` (Umbral: ${alerta.umbral})`}
                          </p>
                        )}
                        <p><strong>Detectado:</strong> {new Date(alerta.fecha_deteccion).toLocaleString()}</p>
                      </div>
                    }
                    type={
                      alerta.prioridad === 'CRITICA' ? 'error' :
                      alerta.prioridad === 'ALTA' ? 'warning' : 'info'
                    }
                    showIcon
                  />
                </Card>
              ))
            ) : (
              <div className="no-alertas">
                <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a' }} />
                <h3>No hay alertas activas</h3>
                <p>El programa está funcionando dentro de los parámetros normales</p>
              </div>
            )}
          </div>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default DashboardAvanzado; 