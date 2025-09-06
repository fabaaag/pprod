import React from 'react';
import { Modal, Button, Alert, Table, Badge, Row, Col, Card } from 'react-bootstrap';
import { FaChartLine, FaArrowUp, FaArrowDown, FaMinus, FaCheckCircle } from 'react-icons/fa';

export const ComparativaAvancesModal = ({ 
    show, 
    onHide, 
    comparativa,
    fechaFinalizada 
}) => {
    if (!comparativa) return null;

    const renderCambioIcon = (diferencia) => {
        if (diferencia > 0) return <FaArrowUp className="text-success me-1" />;
        if (diferencia < 0) return <FaArrowDown className="text-danger me-1" />;
        return <FaMinus className="text-muted me-1" />;
    };

    const renderEstadoBadge = (estadoAntes, estadoDespues) => {
        if (estadoAntes === estadoDespues) {
            return <Badge bg="secondary">{estadoDespues}</Badge>;
        }
        
        const isProgress = (estadoAntes === 'PENDIENTE' && estadoDespues === 'EN_PROCESO') ||
                          (estadoAntes === 'EN_PROCESO' && estadoDespues === 'COMPLETADO') ||
                          (estadoAntes === 'PENDIENTE' && estadoDespues === 'COMPLETADO');
        
        return (
            <div>
                <Badge bg="light" text="dark" className="me-1">{estadoAntes}</Badge>
                <span className="me-1">→</span>
                <Badge bg={isProgress ? "success" : "warning"}>{estadoDespues}</Badge>
            </div>
        );
    };

    return (
        <Modal show={show} onHide={onHide} size="xl" centered>
            <Modal.Header closeButton>
                <Modal.Title>
                    <FaChartLine className="me-2 text-primary" />
                    Comparativa de Avances - {fechaFinalizada}
                </Modal.Title>
            </Modal.Header>

            <Modal.Body>
                {/* Resumen general */}
                <Row className="mb-4">
                    <Col md={3}>
                        <Card className="text-center h-100">
                            <Card.Body>
                                <h3 className="text-primary">{comparativa.resumen.ots_modificadas}</h3>
                                <small className="text-muted">OTs Modificadas</small>
                            </Card.Body>
                        </Card>
                    </Col>
                    <Col md={3}>
                        <Card className="text-center h-100">
                            <Card.Body>
                                <h3 className="text-info">{comparativa.resumen.procesos_avanzados}</h3>
                                <small className="text-muted">Procesos Avanzados</small>
                            </Card.Body>
                        </Card>
                    </Col>
                    <Col md={3}>
                        <Card className="text-center h-100">
                            <Card.Body>
                                <h3 className="text-success">{comparativa.resumen.procesos_completados}</h3>
                                <small className="text-muted">Procesos Completados</small>
                            </Card.Body>
                        </Card>
                    </Col>
                    <Col md={3}>
                        <Card className="text-center h-100">
                            <Card.Body>
                                <h3 className="text-warning">
                                    {comparativa.resumen.cantidad_total_avanzada.toFixed(1)}
                                </h3>
                                <small className="text-muted">Cantidad Total Avanzada</small>
                            </Card.Body>
                        </Card>
                    </Col>
                </Row>

                {/* Cambios por OT */}
                {comparativa.cambios_por_ot && comparativa.cambios_por_ot.length > 0 ? (
                    <div>
                        <h6 className="mb-3">📋 Cambios por Orden de Trabajo</h6>
                        
                        {comparativa.cambios_por_ot.map((cambioOT, index) => (
                            <Card key={index} className="mb-3">
                                <Card.Header>
                                    <div className="d-flex justify-content-between align-items-center">
                                        <h6 className="mb-0">
                                            OT {cambioOT.codigo_ot} - {cambioOT.descripcion}
                                        </h6>
                                        <Badge bg="primary">
                                            {renderCambioIcon(cambioOT.diferencia_avance)}
                                            {cambioOT.diferencia_avance.toFixed(1)} unidades
                                        </Badge>
                                    </div>
                                </Card.Header>
                                
                                {cambioOT.procesos_modificados && cambioOT.procesos_modificados.length > 0 && (
                                    <Card.Body>
                                        <Table size="sm" className="mb-0">
                                            <thead>
                                                <tr>
                                                    <th>Proceso</th>
                                                    <th className="text-center">Cantidad Anterior</th>
                                                    <th className="text-center">Cantidad Nueva</th>
                                                    <th className="text-center">Diferencia</th>
                                                    <th className="text-center">Estado</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {cambioOT.procesos_modificados.map((proceso, procIndex) => (
                                                    <tr key={procIndex}>
                                                        <td>
                                                            <strong>{proceso.codigo_proceso}</strong>
                                                            <br />
                                                            <small className="text-muted">{proceso.descripcion}</small>
                                                        </td>
                                                        <td className="text-center">
                                                            {proceso.cantidad_terminado_antes?.toFixed(1) || '0.0'}
                                                        </td>
                                                        <td className="text-center">
                                                            {proceso.cantidad_terminado_despues?.toFixed(1) || '0.0'}
                                                        </td>
                                                        <td className="text-center">
                                                            <span className={
                                                                proceso.diferencia_terminado > 0 ? 'text-success' :
                                                                proceso.diferencia_terminado < 0 ? 'text-danger' : 'text-muted'
                                                            }>
                                                                {renderCambioIcon(proceso.diferencia_terminado)}
                                                                {proceso.diferencia_terminado?.toFixed(1) || '0.0'}
                                                            </span>
                                                        </td>
                                                        <td className="text-center">
                                                            {renderEstadoBadge(proceso.estado_antes, proceso.estado_despues)}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </Table>
                                    </Card.Body>
                                )}
                            </Card>
                        ))}
                    </div>
                ) : (
                    <Alert variant="info" className="text-center">
                        <FaCheckCircle className="me-2" />
                        No se detectaron cambios en las órdenes de trabajo
                    </Alert>
                )}

                {/* Cambios importados */}
                {comparativa.cambios_importados && comparativa.cambios_importados.length > 0 && (
                    <Alert variant="success" className="mt-4">
                        <h6>📊 Cambios Importados del Sistema Externo</h6>
                        <p>Se procesaron {comparativa.cambios_importados.length} cambios desde el sistema ERP.</p>
                    </Alert>
                )}
            </Modal.Body>

            <Modal.Footer>
                <Button variant="primary" onClick={onHide}>
                    Cerrar
                </Button>
            </Modal.Footer>
        </Modal>
    );
};