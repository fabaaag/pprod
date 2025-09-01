import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Dropdown, Button, Alert } from 'react-bootstrap';
import CompNavbar from '../../components/Navbar/CompNavbar';
import { Footer } from '../../components/Footer/Footer';
import DashboardEjecutivo from '../../components/Programa/DashboardEjecutivo';
import { getAllPrograms } from '../../api/programs.api';
import { getKpisConsolidados } from '../../api/executive.api';
import './DashboardEjecutivoPage.css';

const DashboardEjecutivoPage = () => {
  const [programas, setProgramas] = useState([]);
  const [programaSeleccionado, setProgramaSeleccionado] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [consolidado, setConsolidado] = useState(null);

  useEffect(() => {
    cargarProgramas();
    cargarConsolidado();
  }, []);

  const cargarProgramas = async () => {
    try {
      const response = await getAllPrograms();
      setProgramas(response.data);
      
      // Seleccionar automáticamente el primer programa activo
      const programaActivo = response.data.find(p => new Date(p.fecha_fin) >= new Date());
      if (programaActivo) {
        setProgramaSeleccionado(programaActivo);
      }
      
      setError(null);
    } catch (err) {
      setError('Error al cargar programas: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const cargarConsolidado = async () => {
    try {
      const data = await getKpisConsolidados();
      setConsolidado(data.consolidado);
    } catch (err) {
      console.error('Error cargando consolidado:', err);
    }
  };

  if (loading) {
    return (
      <div>
        <CompNavbar />
        <Container className="mt-4">
          <div className="text-center">
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">Cargando...</span>
            </div>
            <p className="mt-2">Cargando Dashboard Ejecutivo...</p>
          </div>
        </Container>
        <Footer />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <CompNavbar />
        <Container className="mt-4">
          <Alert variant="danger">
            <h4>Error</h4>
            <p>{error}</p>
            <Button variant="outline-danger" onClick={cargarProgramas}>
              Reintentar
            </Button>
          </Alert>
        </Container>
        <Footer />
      </div>
    );
  }

  return (
    <div className="dashboard-ejecutivo-page">
      <CompNavbar />
      
      <Container fluid className="dashboard-ejecutivo-page-content">
        {/* Header con selección de programa */}
        <Row className="mb-4">
          <Col>
            <Card className="shadow-sm">
              <Card.Body>
                <Row className="align-items-center">
                  <Col md={6}>
                    <h1 className="dashboard-title mb-0">
                      🎯 Dashboard Ejecutivo
                    </h1>
                    <p className="text-muted mb-0">
                      Métricas de alto nivel para toma de decisiones
                    </p>
                  </Col>
                  
                  <Col md={6} className="text-end">
                    <div className="d-flex align-items-center justify-content-end gap-3">
                      <div>
                        <label className="form-label mb-1">Programa:</label>
                        <Dropdown>
                          <Dropdown.Toggle variant="outline-primary" size="lg">
                            {programaSeleccionado ? programaSeleccionado.nombre : 'Seleccionar Programa'}
                          </Dropdown.Toggle>
                          
                          <Dropdown.Menu>
                            {programas.map(programa => (
                              <Dropdown.Item
                                key={programa.id}
                                onClick={() => setProgramaSeleccionado(programa)}
                                active={programaSeleccionado?.id === programa.id}
                              >
                                <div>
                                  <strong>{programa.nombre}</strong>
                                  <br />
                                  <small className="text-muted">
                                    {programa.fecha_inicio} - {programa.fecha_fin}
                                  </small>
                                </div>
                              </Dropdown.Item>
                            ))}
                          </Dropdown.Menu>
                        </Dropdown>
                      </div>
                      
                      <Button 
                        variant="success" 
                        onClick={cargarConsolidado}
                        title="Actualizar datos"
                      >
                        🔄 Actualizar
                      </Button>
                    </div>
                  </Col>
                </Row>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        {/* Resumen consolidado de todos los programas */}
        {consolidado && (
          <Row className="mb-4">
            <Col>
              <Card className="shadow-sm border-primary">
                <Card.Header className="bg-primary text-white">
                  <h5 className="mb-0">📊 Resumen Empresarial</h5>
                </Card.Header>
                <Card.Body>
                  <Row>
                    <Col md={3} className="text-center">
                      <h3 className="text-primary">{consolidado.total_programas_activos}</h3>
                      <p className="text-muted mb-0">Programas Activos</p>
                    </Col>
                    <Col md={3} className="text-center">
                      <h3 className="text-success">{consolidado.kilos_planificados_total.toLocaleString()}</h3>
                      <p className="text-muted mb-0">Kilos Planificados</p>
                    </Col>
                    <Col md={3} className="text-center">
                      <h3 className="text-info">{consolidado.kilos_fabricados_total.toLocaleString()}</h3>
                      <p className="text-muted mb-0">Kilos Fabricados</p>
                    </Col>
                    <Col md={3} className="text-center">
                      <h3 className="text-warning">{consolidado.eficiencia_promedio_empresa.toFixed(1)}%</h3>
                      <p className="text-muted mb-0">Eficiencia Promedio</p>
                    </Col>
                  </Row>
                  
                  <hr />
                  
                  <div className="row">
                    <div className="col">
                      <h6>Programas en Detalle:</h6>
                      <div className="table-responsive">
                        <table className="table table-sm">
                          <thead>
                            <tr>
                              <th>Programa</th>
                              <th>Kg Planificados</th>
                              <th>Kg Fabricados</th>
                              <th>% Completado</th>
                              <th>Eficiencia</th>
                            </tr>
                          </thead>
                          <tbody>
                            {consolidado.programas_detalle.map(programa => (
                              <tr key={programa.id}>
                                <td>
                                  <Button
                                    variant="link"
                                    size="sm"
                                    onClick={() => {
                                      const prog = programas.find(p => p.id === programa.id);
                                      if (prog) setProgramaSeleccionado(prog);
                                    }}
                                  >
                                    {programa.nombre}
                                  </Button>
                                </td>
                                <td>{programa.kilos_planificados.toLocaleString()}</td>
                                <td>{programa.kilos_fabricados.toLocaleString()}</td>
                                <td>
                                  <span className={`badge ${
                                    programa.porcentaje_completado >= 80 ? 'bg-success' :
                                    programa.porcentaje_completado >= 60 ? 'bg-warning' : 'bg-danger'
                                  }`}>
                                    {programa.porcentaje_completado.toFixed(1)}%
                                  </span>
                                </td>
                                <td>
                                  <span className={`badge ${
                                    programa.eficiencia >= 80 ? 'bg-success' :
                                    programa.eficiencia >= 60 ? 'bg-warning' : 'bg-danger'
                                  }`}>
                                    {programa.eficiencia.toFixed(1)}%
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                </Card.Body>
              </Card>
            </Col>
          </Row>
        )}

        {/* Dashboard específico del programa seleccionado */}
        {programaSeleccionado ? (
          <Row>
            <Col>
              <Card className="shadow-sm">
                <Card.Header>
                  <h5 className="mb-0">
                    📋 Dashboard del Programa: {programaSeleccionado.nombre}
                  </h5>
                </Card.Header>
                <Card.Body className="p-0">
                  <DashboardEjecutivo programaId={programaSeleccionado.id} />
                </Card.Body>
              </Card>
            </Col>
          </Row>
        ) : (
          <Row>
            <Col>
              <Alert variant="info" className="text-center">
                <h4>Selecciona un programa</h4>
                <p>Elige un programa desde el dropdown superior para ver las métricas ejecutivas específicas.</p>
              </Alert>
            </Col>
          </Row>
        )}
      </Container>
      
      <Footer />
    </div>
  );
};

export default DashboardEjecutivoPage; 