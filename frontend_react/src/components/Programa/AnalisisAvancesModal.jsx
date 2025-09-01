import React, { useState, useEffect } from 'react';
import { Modal, Button, Table, Alert, Badge, Card, Tabs, Tab, Form } from 'react-bootstrap';
import { toast } from 'react-hot-toast';
import axios from '../../api/axiosConfig';

export function AnalisisAvancesModal({ show, onHide, programId, otId, otData, onAvancesActualizados }) {
    const [loading, setLoading] = useState(false);
    const [analisisData, setAnalisisData] = useState(null);
    const [activeTab, setActiveTab] = useState('analisis');
    const [ajustesManual, setAjustesManual] = useState({});

    useEffect(() => {
        if (show && otId) {
            cargarAnalisis();
        }
    }, [show, otId]);

    const cargarAnalisis = async () => {
        try {
            setLoading(true);
            const response = await axios.get(`/gestion/api/v1/programas/${programId}/analizar-avances/${otId}/`);
            setAnalisisData(response.data);
            
            // Inicializar ajustes manuales
            const ajustesIniciales = {};
            response.data.procesos.forEach(proceso => {
                ajustesIniciales[proceso.item_ruta_id] = proceso.cantidad_terminada;
            });
            setAjustesManual(ajustesIniciales);
        } catch (error) {
            toast.error('Error al cargar análisis de avances');
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    const aplicarReconciliacion = async (tipoAplicacion, datos = {}) => {
        try {
            setLoading(true);
            
            let payload = {
                tipo_aplicacion: tipoAplicacion,
                ...datos
            };

            const response = await axios.post(
                `/gestion/api/v1/programas/${programId}/aplicar-reconciliacion/${otId}/`,
                payload
            );

            toast.success('Reconciliación aplicada correctamente');
            onAvancesActualizados();
            onHide();
        } catch (error) {
            toast.error('Error al aplicar reconciliación');
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    const aplicarAjustesManual = () => {
        const ajustes = Object.entries(ajustesManual).map(([itemRutaId, nuevaCantidad]) => ({
            item_ruta_id: parseInt(itemRutaId),
            nueva_cantidad: parseFloat(nuevaCantidad) || 0
        }));

        aplicarReconciliacion('MANUAL', { ajustes });
    };

    const getInconsistenciaColor = (tipo) => {
        switch (tipo) {
            case 'DESBALANCE_ULTIMO_PROCESO': return 'warning';
            case 'FLUJO_ILLOGICO': return 'danger';
            case 'ESTADO_INCORRECTO': return 'info';
            default: return 'secondary';
        }
    };

    const getInconsistenciaIcon = (tipo) => {
        switch (tipo) {
            case 'DESBALANCE_ULTIMO_PROCESO': return '⚖️';
            case 'FLUJO_ILLOGICO': return '🔄';
            case 'ESTADO_INCORRECTO': return '🔍';
            default: return '❓';
        }
    };

    if (!analisisData) return null;

    return (
        <Modal show={show} onHide={onHide} size="xl">
            <Modal.Header closeButton>
                <Modal.Title>
                    📊 Análisis de Avances - OT #{analisisData.ot.codigo}
                </Modal.Title>
            </Modal.Header>

            <Modal.Body>
                {/* ✅ RESUMEN CORREGIDO */}
                <Card className="mb-3">
                    <Card.Body>
                        <div className="row">
                            <div className="col-md-3">
                                <strong>Avance OT:</strong><br/>
                                <span className="h5">{analisisData.ot.cantidad_avance} / {analisisData.ot.cantidad_total}</span>
                                <br/>
                                <Badge bg="info">{analisisData.ot.porcentaje_avance_ot.toFixed(1)}%</Badge>
                            </div>
                            <div className="col-md-3">
                                <strong>Último Proceso:</strong><br/>
                                <span className="h5">{analisisData.resumen.avance_ultimo_proceso}</span>
                                <br/>
                                <small className="text-muted">{analisisData.resumen.ultimo_proceso}</small>
                            </div>
                            <div className="col-md-3">
                                <strong>Diferencia:</strong><br/>
                                <Badge bg={Math.abs(analisisData.resumen.diferencia_avance) < 0.01 ? 'success' : 'warning'}>
                                    {analisisData.resumen.diferencia_avance > 0 ? '+' : ''}{analisisData.resumen.diferencia_avance.toFixed(2)}
                                </Badge>
                                <br/>
                                <small className="text-muted">OT vs Último Proceso</small>
                            </div>
                            <div className="col-md-3">
                                <strong>Estado:</strong><br/>
                                <Badge bg={analisisData.resumen.hay_inconsistencias ? 'danger' : 'success'}>
                                    {analisisData.resumen.hay_inconsistencias ? '❌ Inconsistencias' : '✅ Consistente'}
                                </Badge>
                                <br/>
                                <small className="text-muted">
                                    {analisisData.resumen.procesos_iniciados} / {analisisData.resumen.total_procesos} iniciados
                                </small>
                            </div>
                        </div>
                    </Card.Body>
                </Card>

                {/* ✅ INCONSISTENCIAS CORREGIDAS */}
                {analisisData.inconsistencias.length > 0 && (
                    <Alert variant="warning" className="mb-3">
                        <h6>🚨 Inconsistencias Detectadas:</h6>
                        {analisisData.inconsistencias.map((inc, idx) => (
                            <div key={idx} className="mb-2">
                                <Badge bg={getInconsistenciaColor(inc.tipo)} className="me-2">
                                    {getInconsistenciaIcon(inc.tipo)} {inc.tipo}
                                </Badge>
                                {inc.descripcion}
                                {inc.proceso_afectado && (
                                    <small className="text-muted ms-2">
                                        (Proceso: {inc.proceso_afectado})
                                    </small>
                                )}
                            </div>
                        ))}
                    </Alert>
                )}

                <Tabs activeKey={activeTab} onSelect={setActiveTab}>
                    {/* Tab 1: Análisis Detallado */}
                    <Tab eventKey="analisis" title="📋 Análisis Detallado">
                        <div className="mt-3">
                            <Alert variant="info">
                                <strong>💡 Lógica de Avance:</strong> El avance de la OT se determina por el último proceso completado. 
                                Los procesos anteriores pueden tener más unidades procesadas (flujo normal de producción).
                            </Alert>
                            
                            <Table striped bordered hover>
                                <thead>
                                    <tr>
                                        <th>#</th>
                                        <th>Proceso</th>
                                        <th>Total</th>
                                        <th>Terminado</th>
                                        <th>Pendiente</th>
                                        <th>% Completado</th>
                                        <th>Estado</th>
                                        <th>Rol</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {analisisData.procesos.map(proceso => (
                                        <tr key={proceso.item_ruta_id} 
                                            className={proceso.es_ultimo_proceso ? 'table-warning' : ''}>
                                            <td>{proceso.item}</td>
                                            <td>
                                                <strong>{proceso.proceso.codigo}</strong><br/>
                                                <small>{proceso.proceso.descripcion}</small>
                                            </td>
                                            <td>{proceso.cantidad_total}</td>
                                            <td>
                                                <span className={proceso.cantidad_terminada > 0 ? 'text-success fw-bold' : 'text-muted'}>
                                                    {proceso.cantidad_terminada}
                                                </span>
                                            </td>
                                            <td>{proceso.cantidad_pendiente}</td>
                                            <td>
                                                <Badge bg={
                                                    proceso.porcentaje_completado >= 100 ? 'success' : 
                                                    proceso.porcentaje_completado > 0 ? 'warning' : 'secondary'
                                                }>
                                                    {proceso.porcentaje_completado}%
                                                </Badge>
                                            </td>
                                            <td>
                                                <Badge bg="info">{proceso.estado_proceso}</Badge>
                                            </td>
                                            <td>
                                                {proceso.es_ultimo_proceso && (
                                                    <Badge bg="warning">
                                                        🏁 DETERMINA AVANCE OT
                                                    </Badge>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </Table>
                        </div>
                    </Tab>

                    {/* Tab 2: Ajuste Manual */}
                    <Tab eventKey="manual" title="✏️ Ajuste Manual">
                        <div className="mt-3">
                            <Alert variant="warning">
                                <strong>⚠️ Ajuste Manual:</strong> Modifique las cantidades según la realidad de producción. 
                                Recuerde que el <strong>último proceso determina el avance de la OT</strong>.
                            </Alert>
                            
                            <Table striped bordered>
                                <thead>
                                    <tr>
                                        <th>Proceso</th>
                                        <th>Cantidad Actual</th>
                                        <th>Nueva Cantidad</th>
                                        <th>Diferencia</th>
                                        <th>Impacto en OT</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {analisisData.procesos.map(proceso => (
                                        <tr key={proceso.item_ruta_id}
                                            className={proceso.es_ultimo_proceso ? 'table-warning' : ''}>
                                            <td>
                                                <strong>{proceso.proceso.codigo}</strong><br/>
                                                <small>{proceso.proceso.descripcion}</small>
                                                {proceso.es_ultimo_proceso && (
                                                    <Badge bg="warning" className="ms-2">🏁</Badge>
                                                )}
                                            </td>
                                            <td>{proceso.cantidad_terminada}</td>
                                            <td>
                                                <Form.Control
                                                    type="number"
                                                    min="0"
                                                    max={proceso.cantidad_total}
                                                    step="0.01"
                                                    value={ajustesManual[proceso.item_ruta_id] || 0}
                                                    onChange={(e) => setAjustesManual(prev => ({
                                                        ...prev,
                                                        [proceso.item_ruta_id]: e.target.value
                                                    }))}
                                                />
                                            </td>
                                            <td>
                                                <span className={
                                                    ((ajustesManual[proceso.item_ruta_id] || 0) - proceso.cantidad_terminada) > 0 
                                                        ? 'text-success' : 'text-danger'
                                                }>
                                                    {((ajustesManual[proceso.item_ruta_id] || 0) - proceso.cantidad_terminada).toFixed(2)}
                                                </span>
                                            </td>
                                            <td>
                                                {proceso.es_ultimo_proceso ? (
                                                    <Badge bg="warning">
                                                        Cambiará avance OT a {ajustesManual[proceso.item_ruta_id] || 0}
                                                    </Badge>
                                                ) : (
                                                    <small className="text-muted">Sin impacto directo</small>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </Table>
                            
                            <Button 
                                variant="primary" 
                                onClick={aplicarAjustesManual}
                                disabled={loading}
                            >
                                💾 Aplicar Ajustes Manuales
                            </Button>
                        </div>
                    </Tab>

                    {/* Tab 3: Sugerencias Automáticas */}
                    <Tab eventKey="sugerencias" title="🤖 Sugerencias">
                        <div className="mt-3">
                            <Alert variant="info">
                                <strong>💡 Sugerencias Inteligentes:</strong> Basadas en la lógica correcta donde el último proceso determina el avance de la OT.
                            </Alert>
                            
                            {analisisData.sugerencias_correccion && analisisData.sugerencias_correccion.length > 0 ? (
                                analisisData.sugerencias_correccion.map((sugerencia, idx) => (
                                    <Card key={idx} className="mb-3">
                                        <Card.Body>
                                            <h6>
                                                {sugerencia.tipo === 'ACTUALIZAR_ULTIMO_PROCESO' && '🎯 Actualizar Último Proceso'}
                                                {sugerencia.tipo === 'ACTUALIZAR_AVANCE_OT' && '📊 Actualizar Avance OT'}
                                                {sugerencia.tipo === 'CASCADA_HACIA_ATRAS' && '🔄 Cascada hacia Atrás'}
                                            </h6>
                                            <p>{sugerencia.descripcion}</p>
                                            
                                            {sugerencia.distribucion && (
                                                <div>
                                                    <h6>Distribución Propuesta:</h6>
                                                    <Table size="sm">
                                                        <thead>
                                                            <tr>
                                                                <th>#</th>
                                                                <th>Proceso</th>
                                                                <th>Actual</th>
                                                                <th>Sugerida</th>
                                                                <th>Incremento</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            {sugerencia.distribucion.map(dist => (
                                                                <tr key={dist.item_ruta_id}>
                                                                    <td>{dist.item}</td>
                                                                    <td>{dist.proceso}</td>
                                                                    <td>{dist.cantidad_actual}</td>
                                                                    <td className="fw-bold">{dist.cantidad_sugerida}</td>
                                                                    <td className={dist.incremento >= 0 ? "text-success" : "text-danger"}>
                                                                        {dist.incremento >= 0 ? '+' : ''}{dist.incremento}
                                                                    </td>
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </Table>
                                                </div>
                                            )}
                                            
                                            <Button 
                                                variant="outline-primary" 
                                                size="sm"
                                                onClick={() => {
                                                    if (sugerencia.tipo === 'CASCADA_HACIA_ATRAS') {
                                                        aplicarReconciliacion('CASCADA_HACIA_ATRAS', { 
                                                            distribucion: sugerencia.distribucion 
                                                        });
                                                    } else if (sugerencia.tipo === 'ACTUALIZAR_ULTIMO_PROCESO') {
                                                        aplicarReconciliacion('MANUAL', { 
                                                            ajustes: [{
                                                                item_ruta_id: sugerencia.item_ruta_id,
                                                                nueva_cantidad: sugerencia.cantidad_sugerida
                                                            }]
                                                        });
                                                    } else if (sugerencia.tipo === 'ACTUALIZAR_AVANCE_OT') {
                                                        aplicarReconciliacion('ACTUALIZAR_AVANCE_OT', {
                                                            nuevo_avance: sugerencia.avance_sugerido
                                                        });
                                                    }
                                                }}
                                                disabled={loading}
                                            >
                                                ✅ Aplicar Esta Sugerencia
                                            </Button>
                                        </Card.Body>
                                    </Card>
                                ))
                            ) : (
                                <Alert variant="success">
                                    ✅ No hay sugerencias. Los avances están consistentes.
                                </Alert>
                            )}
                        </div>
                    </Tab>
                </Tabs>
            </Modal.Body>

            <Modal.Footer>
                <Button 
                    variant="outline-danger" 
                    onClick={() => aplicarReconciliacion('RESETEAR_AVANCES', { resetear_ot_tambien: true })}
                >
                    🔄 Resetear Todo a 0
                </Button>
                <Button variant="secondary" onClick={onHide}>
                    Cerrar
                </Button>
            </Modal.Footer>
        </Modal>
    );
}