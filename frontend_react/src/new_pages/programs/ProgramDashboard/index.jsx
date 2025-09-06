import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Container, Row, Col, Card, Button, Tabs, Tab, Breadcrumb, Alert } from 'react-bootstrap';
import { FaArrowLeft, FaChartBar, FaDownload, FaFileCode, FaRedo } from 'react-icons/fa';
import toast from 'react-hot-toast';

import { PlanificacionBaseDashboard } from '../../../new_components/Program/Details/Dashboard/PlanificacionBaseDashboard';
import { ComparadorPlanificacion } from '../../../new_components/Program/Details/Dashboard/ComparadorPlanificacion';
import { cargarJsonBase } from '../../../api/planificacion.api';
import { getProgram } from '../../../api/programs.api';
import LoadingSpinner from '../../../components/UI/LoadingSpinner/LoadingSpinner';

export default function ProgramDashboard() {
    const { programId } = useParams();
    const navigate = useNavigate();

    // Estados
    const [loading, setLoading] = useState(true);
    const [jsonBaseData, setJsonBaseData] = useState(null);
    const [programData, setProgramData] = useState(null);
    const [activeTab, setActiveTab] = useState('base');
    const [error, setError] = useState('');

    // Cargar datos al montar
    useEffect(() => {
        if (programId) {
            cargarDatos();
        }
    }, [programId]);

    const cargarDatos = async () => {
        try {
            setLoading(true);
            setError('');

            // Cargar datos del programa y JSON base en paralelo
            const [programResponse, jsonBaseResponse] = await Promise.allSettled([
                getProgram(programId),
                cargarJsonBase(programId)
            ]);

            // Manejar respuesta del programa
            if (programResponse.status === 'fulfilled') {
                setProgramData(programResponse.value);
            } else {
                console.error('Error cargando programa:', programResponse.reason);
                throw new Error('No se pudo cargar la información del programa');
            }

            // Manejar respuesta del JSON base
            if (jsonBaseResponse.status === 'fulfilled') {
                setJsonBaseData(jsonBaseResponse.value);
            } else {
                console.warn('No hay JSON base disponible:', jsonBaseResponse.reason);
                // No es un error crítico, puede que aún no se haya generado
            }

        } catch (err) {
            console.error('Error cargando datos del dashboard:', err);
            setError(err.message || 'Error cargando datos del dashboard');
            toast.error('Error cargando datos del dashboard');
        } finally {
            setLoading(false);
        }
    };

    const handleVolverAlPrograma = () => {
        navigate(`/programs/${programId}/new`);
    };

    const handleActualizar = () => {
        cargarDatos();
        toast.info('Actualizando datos...');
    };

    const handleExportarDatos = () => {
        // Implementar exportación a Excel/PDF
        toast.info('Función de exportación en desarrollo');
    };

    if (loading) {
        return (
            <Container fluid className="py-4">
                <LoadingSpinner message="Cargando dashboard de planificación..." />
            </Container>
        );
    }

    if (error) {
        return (
            <Container fluid className="py-4">
                <Alert variant="danger">
                    <h5>Error al cargar el dashboard</h5>
                    <p>{error}</p>
                    <div className="d-flex gap-2">
                        <Button variant="outline-danger" onClick={cargarDatos}>
                            <FaRedo className="me-1" />
                            Reintentar
                        </Button>
                        <Button variant="secondary" onClick={handleVolverAlPrograma}>
                            <FaArrowLeft className="me-1" />
                            Volver al Programa
                        </Button>
                    </div>
                </Alert>
            </Container>
        );
    }

    return (
        <Container fluid className="py-4">
            {/* Breadcrumb y navegación */}
            <Row className="mb-4">
                <Col>
                    <Breadcrumb>
                        <Breadcrumb.Item href="/programs">Programas</Breadcrumb.Item>
                        <Breadcrumb.Item onClick={handleVolverAlPrograma} style={{ cursor: 'pointer' }}>
                            {programData?.nombre || `Programa ${programId}`}
                        </Breadcrumb.Item>
                        <Breadcrumb.Item active>Dashboard</Breadcrumb.Item>
                    </Breadcrumb>
                </Col>
            </Row>

            {/* Header del dashboard */}
            <Row className="mb-4">
                <Col>
                    <Card>
                        <Card.Body>
                            <div className="d-flex justify-content-between align-items-center">
                                <div>
                                    <h2 className="mb-1">
                                        <FaChartBar className="me-2 text-primary" />
                                        Dashboard de Planificación
                                    </h2>
                                    <h5 className="text-muted mb-0">
                                        {programData?.nombre || `Programa ${programId}`}
                                    </h5>
                                </div>
                                
                                <div className="d-flex gap-2">
                                    <Button 
                                        variant="outline-secondary" 
                                        onClick={handleActualizar}
                                    >
                                        <FaRedo className="me-1" />
                                        Actualizar
                                    </Button>
                                    
                                    <Button 
                                        variant="outline-info" 
                                        onClick={handleExportarDatos}
                                    >
                                        <FaDownload className="me-1" />
                                        Exportar
                                    </Button>
                                    
                                    <Button 
                                        variant="primary" 
                                        onClick={handleVolverAlPrograma}
                                    >
                                        <FaArrowLeft className="me-1" />
                                        Volver al Programa
                                    </Button>
                                </div>
                            </div>
                        </Card.Body>
                    </Card>
                </Col>
            </Row>

            {/* Contenido principal del dashboard */}
            <Row>
                <Col>
                    {jsonBaseData ? (
                        <Tabs 
                            activeKey={activeTab} 
                            onSelect={setActiveTab} 
                            className="mb-4"
                        >
                            <Tab 
                                eventKey="base" 
                                title={
                                    <span>
                                        <FaFileCode className="me-1" />
                                        Planificación Base
                                    </span>
                                }
                            >
                                <PlanificacionBaseDashboard 
                                    programId={programId}
                                    jsonBaseData={jsonBaseData}
                                />
                            </Tab>
                            
                            <Tab 
                                eventKey="comparacion" 
                                title={
                                    <span>
                                        <FaChartBar className="me-1" />
                                        Comparación vs Actual
                                    </span>
                                }
                            >
                                <ComparadorPlanificacion 
                                    jsonBase={jsonBaseData}
                                    estadoActual={programData}
                                />
                            </Tab>
                            
                            <Tab 
                                eventKey="historico" 
                                title={
                                    <span>
                                        📈 Histórico
                                    </span>
                                }
                            >
                                <Card>
                                    <Card.Body className="text-center py-5">
                                        <h5>📈 Vista Histórica</h5>
                                        <p className="text-muted">
                                            Funcionalidad en desarrollo para mostrar evolución temporal
                                        </p>
                                    </Card.Body>
                                </Card>
                            </Tab>
                        </Tabs>
                    ) : (
                        <Alert variant="warning" className="text-center">
                            <h5>
                                <FaFileCode className="me-2" />
                                No hay JSON base disponible
                            </h5>
                            <p>
                                Para ver el dashboard, primero debe generar la planificación base 
                                desde la página del programa.
                            </p>
                            <Button 
                                variant="primary" 
                                onClick={handleVolverAlPrograma}
                            >
                                <FaArrowLeft className="me-1" />
                                Ir al Programa
                            </Button>
                        </Alert>
                    )}
                </Col>
            </Row>
        </Container>
    );
}