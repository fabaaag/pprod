import React, { useState, useEffect } from 'react';
import { Card, Table, Badge, Row, Col, Alert, Button, Tabs, Tab } from 'react-bootstrap';
import { FaFileCode, FaChartPie, FaTable, FaDownload } from 'react-icons/fa';

export const PlanificacionBaseDashboard = ({ programId, jsonBaseData }) => {
    if (!jsonBaseData) return null;

    const { metadata, resumen, ordenes_trabajo } = jsonBaseData;

    //console.log("ordenes: ", ordenes_trabajo);
    //console.log("resumen: ", resumen);

    // Calcular estadísticas de la planificación base
    const estadisticas = {
        procesosCompletos: ordenes_trabajo.reduce((acc, ot) => 
            acc + ot.procesos.filter(p => p.estado_proceso === 'COMPLETADO').length, 0),
        procesosEnProceso: ordenes_trabajo.reduce((acc, ot) => 
            acc + ot.procesos.filter(p => p.estado_proceso === 'EN PROCESO').length, 0),
        procesosPendientes: ordenes_trabajo.reduce((acc, ot) => 
            acc + ot.procesos.filter(p => p.estado_proceso === 'PENDIENTE').length, 0),
        valorProducido: ordenes_trabajo.reduce((acc, ot) => 
            acc + (ot.cantidad_avance * ot.valor_unitario), 0),
        kilosProducidos: ordenes_trabajo.reduce((acc, ot) => 
            acc + (ot.cantidad_avance * ot.peso_unitario), 0)
    };

    const renderResumenCard = () => (
        <Card className="mb-4">
            <Card.Header>
                <h5 className="mb-0">
                    <FaChartPie className="me-2" />
                    Resumen de Planificación Base
                </h5>
                <small className="text-muted">
                    Generado: {new Date(metadata.fecha_generacion).toLocaleString()}
                </small>
            </Card.Header>
            <Card.Body>
                <Row>
                    <Col md={3}>
                        <div className="text-center">
                            <h3 className="text-primary">{resumen.total_ots}</h3>
                            <small>Órdenes de Trabajo</small>
                        </div>
                    </Col>
                    <Col md={3}>
                        <div className="text-center">
                            <h3 className="text-info">{resumen.total_procesos}</h3>
                            <small>Procesos Totales</small>
                        </div>
                    </Col>
                    <Col md={3}>
                        <div className="text-center">
                            <h3 className="text-success">${resumen.valor_planificado.toLocaleString()}</h3>
                            <small>Valor Planificado</small>
                        </div>
                    </Col>
                    <Col md={3}>
                        <div className="text-center">
                            <h3 className="text-warning">{resumen.kilos_planificados.toFixed(1)} kg</h3>
                            <small>Kilos Planificados</small>
                        </div>
                    </Col>
                </Row>

                <hr />

                <Row>
                    <Col md={4}>
                        <div className="text-center">
                            <h4 className="text-success">{estadisticas.procesosCompletos}</h4>
                            <small>Procesos Completados</small>
                        </div>
                    </Col>
                    <Col md={4}>
                        <div className="text-center">
                            <h4 className="text-info">{estadisticas.procesosEnProceso}</h4>
                            <small>Procesos En Curso</small>
                        </div>
                    </Col>
                    <Col md={4}>
                        <div className="text-center">
                            <h4 className="text-secondary">{estadisticas.procesosPendientes}</h4>
                            <small>Procesos Pendientes</small>
                        </div>
                    </Col>
                </Row>
            </Card.Body>
        </Card>
    );

    const renderTablaOT = () => (
        <Card>
            <Card.Header>
                <h6 className="mb-0">
                    <FaTable className="me-2" />
                    Detalle por Orden de Trabajo
                </h6>
            </Card.Header>
            <Card.Body>
                <Table striped hover size="sm">
                    <thead>
                        <tr>
                            <th>Código OT</th>
                            <th>Descripción</th>
                            <th>Prioridad</th>
                            <th>Cantidad Total</th>
                            <th>Avance Actual</th>
                            <th>% Avance</th>
                            <th>Procesos</th>
                            <th>Estado General</th>
                        </tr>
                    </thead>
                    <tbody>
                        {ordenes_trabajo.map(ot => {
                            const procesosCompletos = ot.procesos.filter(p => p.estado_proceso === 'COMPLETADO').length;
                            const totalProcesos = ot.procesos.length;
                            const estadoGeneral = procesosCompletos === totalProcesos ? 'COMPLETADO' :
                                                 ot.cantidad_avance > 0 ? 'EN_PROCESO' : 'PENDIENTE';
                            
                            return (
                                <tr key={ot.id}>
                                    <td><strong>{ot.codigo_ot}</strong></td>
                                    <td>{ot.descripcion}</td>
                                    <td>
                                        <Badge bg={ot.prioridad <= 3 ? 'danger' : ot.prioridad <= 6 ? 'warning' : 'secondary'}>
                                            {ot.prioridad}
                                        </Badge>
                                    </td>
                                    <td>{ot.cantidad_total.toLocaleString()}</td>
                                    <td>{ot.cantidad_avance.toLocaleString()}</td>
                                    <td>
                                        <div className="d-flex align-items-center">
                                            <div className="progress me-2" style={{ width: '60px', height: '6px' }}>
                                                <div 
                                                    className="progress-bar" 
                                                    style={{ width: `${ot.porcentaje_avance}%` }}
                                                ></div>
                                            </div>
                                            <small>{ot.porcentaje_avance.toFixed(1)}%</small>
                                        </div>
                                    </td>
                                    <td>
                                        <small>{procesosCompletos}/{totalProcesos}</small>
                                    </td>
                                    <td>
                                        <Badge bg={
                                            estadoGeneral === 'COMPLETADO' ? 'success' :
                                            estadoGeneral === 'EN_PROCESO' ? 'info' : 'secondary'
                                        }>
                                            {estadoGeneral}
                                        </Badge>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </Table>
            </Card.Body>
        </Card>
    );

    return (
        <div>
            <Alert variant="info" className="mb-4">
                <h6>📄 Planificación Base - {jsonBaseData.programa_nombre}</h6>
                <p className="mb-0">
                    Fecha base: <strong>{jsonBaseData.fecha_base}</strong> | 
                    Fecha inicio programa: <strong>{jsonBaseData.fecha_inicio_programa}</strong>
                </p>
            </Alert>

            {renderResumenCard()}
            {renderTablaOT()}
        </div>
    );
};