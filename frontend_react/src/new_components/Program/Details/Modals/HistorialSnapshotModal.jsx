import React, { useState, useEffect } from 'react';
import { Modal, Button, Table, Badge, Card, Row, Col, Form, Alert, Spinner } from 'react-bootstrap';
import { FaHistory, FaCamera, FaChartLine, FaEye, FaCalendarAlt } from 'react-icons/fa';
import { obtenerHistorialSnapshots, compararSnapshots } from '../../../../api/planificacion.api';
import toast from 'react-hot-toast';

export const HistorialSnapshotsModal = ({ 
    show, 
    onHide, 
    programId, 
    programData 
}) => {
    const [historial, setHistorial] = useState([]);
    const [loading, setLoading] = useState(false);
    const [diasMostrar, setDiasMostrar] = useState(30);
    const [comparacion, setComparacion] = useState(null);
    const [loadingComparacion, setLoadingComparacion] = useState(false);

    useEffect(() => {
        if (show && programId) {
            cargarHistorial();
        }
    }, [show, programId, diasMostrar]);

    const cargarHistorial = async () => {
        try {
            setLoading(true);
            const resultado = await obtenerHistorialSnapshots(programId, diasMostrar);
            setHistorial(resultado.historial || []);
        } catch (error) {
            console.error('Error cargando historial:', error);
            toast.error('Error al cargar el historial de snapshots');
        } finally {
            setLoading(false);
        }
    };

    const handleCompararPeriodo = async () => {
        if (historial.length < 2) {
            toast.warning('Se necesitan al menos 2 snapshots para comparar');
            return;
        }

        try {
            setLoadingComparacion(true);
            const fechaDesde = historial[historial.length - 1].fecha;
            const fechaHasta = historial[0].fecha;
            
            const resultado = await compararSnapshots(programId, fechaDesde, fechaHasta);
            setComparacion(resultado.evolucion);
            toast.success('Comparación generada exitosamente');
        } catch (error) {
            console.error('Error generando comparación:', error);
            toast.error('Error al generar comparación');
        } finally {
            setLoadingComparacion(false);
        }
    };

    const formatearFecha = (fechaISO) => {
        return new Date(fechaISO).toLocaleDateString('es-CL', {
            weekday: 'short',
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    };

    const formatearValor = (valor) => {
        return new Intl.NumberFormat('es-CL').format(valor);
    };

    const renderBadgeEficiencia = (eficiencia) => {
        const variant = eficiencia >= 100 ? 'success' : 
                      eficiencia >= 80 ? 'warning' : 'danger';
        return <Badge bg={variant}>{eficiencia.toFixed(1)}%</Badge>;
    };

    return (
        <Modal show={show} onHide={onHide} size="xl" centered>
            <Modal.Header closeButton>
                <Modal.Title>
                    <FaHistory className="me-2 text-primary" />
                    Historial de Snapshots - {programData?.nombre}
                </Modal.Title>
            </Modal.Header>

            <Modal.Body>
                {/* Controles */}
                <Row className="mb-4">
                    <Col md={4}>
                        <Form.Group>
                            <Form.Label>Días a mostrar:</Form.Label>
                            <Form.Select 
                                value={diasMostrar} 
                                onChange={(e) => setDiasMostrar(parseInt(e.target.value))}
                            >
                                <option value={7}>Últimos 7 días</option>
                                <option value={15}>Últimos 15 días</option>
                                <option value={30}>Últimos 30 días</option>
                                <option value={60}>Últimos 60 días</option>
                            </Form.Select>
                        </Form.Group>
                    </Col>
                    <Col md={4} className="d-flex align-items-end">
                        <Button 
                            variant="outline-primary" 
                            onClick={cargarHistorial}
                            disabled={loading}
                        >
                            {loading ? <Spinner animation="border" size="sm" /> : <FaHistory />}
                            {loading ? ' Cargando...' : ' Actualizar'}
                        </Button>
                    </Col>
                    <Col md={4} className="d-flex align-items-end justify-content-end">
                        <Button 
                            variant="info" 
                            onClick={handleCompararPeriodo}
                            disabled={loadingComparacion || historial.length < 2}
                        >
                            {loadingComparacion ? <Spinner animation="border" size="sm" /> : <FaChartLine />}
                            {loadingComparacion ? ' Comparando...' : ' Comparar Período'}
                        </Button>
                    </Col>
                </Row>

                {/* Comparación del período (si existe) */}
                {comparacion && (
                    <Card className="mb-4">
                        <Card.Header>
                            <h6 className="mb-0">📊 Evolución del Período</h6>
                        </Card.Header>
                        <Card.Body>
                            <Row>
                                <Col md={3}>
                                    <div className="text-center">
                                        <h5 className="text-primary">
                                            {formatearValor(comparacion.diferencias.avance_total)}
                                        </h5>
                                        <small>Avance Total del Período</small>
                                    </div>
                                </Col>
                                <Col md={3}>
                                    <div className="text-center">
                                        <h5 className="text-success">
                                            +{comparacion.diferencias.porcentaje.toFixed(1)}%
                                        </h5>
                                        <small>Incremento de Progreso</small>
                                    </div>
                                </Col>
                                <Col md={3}>
                                    <div className="text-center">
                                        <h5 className="text-info">
                                            ${formatearValor(comparacion.diferencias.valor_producido)}
                                        </h5>
                                        <small>Valor Producido</small>
                                    </div>
                                </Col>
                                <Col md={3}>
                                    <div className="text-center">
                                        <h5 className="text-warning">
                                            {comparacion.diferencias.ots_completadas}
                                        </h5>
                                        <small>OTs Completadas</small>
                                    </div>
                                </Col>
                            </Row>
                        </Card.Body>
                    </Card>
                )}

                {/* Tabla de historial */}
                {loading ? (
                    <div className="text-center py-5">
                        <Spinner animation="border" />
                        <p className="mt-2">Cargando historial de snapshots...</p>
                    </div>
                ) : historial.length > 0 ? (
                    <Table hover responsive>
                        <thead>
                            <tr>
                                <th>Fecha</th>
                                <th>OTs</th>
                                <th>Avance Total</th>
                                <th>% Progreso</th>
                                <th>Valor Producido</th>
                                <th>Kilos</th>
                                <th>Eficiencia</th>
                                <th>Avance Diario</th>
                                <th>Estados</th>
                                <th>Notas</th>
                            </tr>
                        </thead>
                        <tbody>
                            {historial.map((snapshot, index) => (
                                <tr key={snapshot.id}>
                                    <td>
                                        <div>
                                            <strong>{formatearFecha(snapshot.fecha)}</strong>
                                            <br />
                                            <small className="text-muted">
                                                ID: {snapshot.id}
                                            </small>
                                        </div>
                                    </td>
                                    <td>{snapshot.metricas.total_ots}</td>
                                    <td>{formatearValor(snapshot.metricas.avance_total)}</td>
                                    <td>
                                        <div className="d-flex align-items-center">
                                            <div className="progress me-2" style={{ width: '60px', height: '8px' }}>
                                                <div 
                                                    className="progress-bar" 
                                                    style={{ width: `${snapshot.metricas.porcentaje_avance}%` }}
                                                ></div>
                                            </div>
                                            <small>{snapshot.metricas.porcentaje_avance.toFixed(1)}%</small>
                                        </div>
                                    </td>
                                    <td>${formatearValor(snapshot.metricas.valor_producido)}</td>
                                    <td>{formatearValor(snapshot.metricas.kilos_producidos)} kg</td>
                                    <td>{renderBadgeEficiencia(snapshot.metricas.eficiencia)}</td>
                                    <td>
                                        <Badge bg={snapshot.metricas.avance_diario > 0 ? 'success' : 'secondary'}>
                                            {formatearValor(snapshot.metricas.avance_diario)}
                                        </Badge>
                                    </td>
                                    <td>
                                        <small>
                                            <Badge bg="success" className="me-1">{snapshot.estados.completadas}</Badge>
                                            <Badge bg="info" className="me-1">{snapshot.estados.en_proceso}</Badge>
                                            <Badge bg="secondary">{snapshot.estados.pendientes}</Badge>
                                        </small>
                                    </td>
                                    <td>
                                        <div>
                                            {snapshot.metadatos.importacion_realizada && (
                                                <Badge bg="primary" className="me-1">Importado</Badge>
                                            )}
                                            {snapshot.metadatos.notas && (
                                                <FaEye 
                                                    className="text-info" 
                                                    title={snapshot.metadatos.notas}
                                                    style={{ cursor: 'pointer' }}
                                                />
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </Table>
                ) : (
                    <Alert variant="info" className="text-center">
                        <FaCamera className="me-2" />
                        No hay snapshots disponibles para mostrar
                    </Alert>
                )}
            </Modal.Body>

            <Modal.Footer>
                <Button variant="secondary" onClick={onHide}>
                    Cerrar
                </Button>
            </Modal.Footer>
        </Modal>
    );
};