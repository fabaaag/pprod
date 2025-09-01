import React from 'react';
import { Modal, Button, Badge, Row, Col } from 'react-bootstrap';
import moment from 'moment';
import { FaCalendarAlt, FaClock, FaIndustry, FaUser, FaClipboardList } from 'react-icons/fa';

export const EventDetailsModal = ({
    show,
    onHide,
    event,
}) => {
    if (!event) return null;
    console.log('evento seleccionado:', event)

    const getStatusColor = (estado) => {
        switch (estado?.toUpperCase()) {
            case 'COMPLETADO': return 'success';
            case 'EN_PROCESO': return 'primary';
            case 'DETENIDO': return 'danger';
            case 'PAUSADO': return 'warning';
            default: return 'secondary';
        }
    };

    const getStatusIcon = (estado) => {
        switch (estado?.toUpperCase()) {
            case 'COMPLETADO': return '✅';
            case 'EN_PROCESO': return '🔄';
            case 'DETENIDO': return '⏹️';
            case 'PAUSADO': return '⏸️';
            default: return '⏳';
        }
    };

    const formatDuration = (start, end) => {
        const duration = moment.duration(moment(end).diff(moment(start)));
        const hours = Math.floor(duration.asHours());
        const minutes = duration.minutes();
        return `${hours}h ${minutes}m`;
    };



    const getEstandar = (event) => {
        // Intentar obtener el estándar de diferentes fuentes
        return event.resource?.estandar || 
               event.resource?.cantidad_intervalo / moment.duration(moment(event.end).diff(moment(event.start))).asHours() || 
               0;
    };

    return (
        <Modal show={show} onHide={onHide} size="lg">
            <Modal.Header closeButton>
                <Modal.Title>
                    <FaClipboardList className="me-2" />
                    Detalles del Evento
                </Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Row>
                    <Col md={8}>
                        <h5 className="text-primary mb-3">{event.title}</h5>
                        
                        
                        <div className="mb-3">
                            <h6>Información General</h6>
                            <Row>
                                <Col md={6}>
                                    <div className="mb-2">
                                        <strong>OT:</strong> 
                                        <span className={event.ot_codigo && event.ot !== 'N/A' ? 'text-primary' : 'text-muted'}>
                                            &nbsp;{event.ot_codigo || 'N/A'}
                                        </span>
                                    </div>
                                    <div className="mb-2">
                                        <strong>Producto:</strong> 
                                        <span className={event.producto && event.ot !== 'N/A' ? 'text-primary' : 'text-muted'}>
                                            &nbsp;{event.producto || 'N/A'}
                                        </span>
                                    </div>
                                    <div className="mb-2">
                                        <strong>Proceso:</strong> 
                                        <span className={event.proceso_codigo ? 'text-primary' : 'text-muted'}>
                                            &nbsp;{event.proceso_codigo || ''} - {event.proceso_descripcion || 'N/A'}
                                        </span>
                                    </div>
                                    <div className="mb-2">
                                        <strong>Estado:</strong>
                                        <Badge 
                                            bg={getStatusColor(event.estado)} 
                                            className="ms-2"
                                        >
                                            {getStatusIcon(event.estado)} {event.estado || 'PENDIENTE'}
                                        </Badge>
                                    </div>
                                    {event.porcentaje_avance > 0 && (
                                        <div className="mb-2">
                                            <strong>Avance:</strong>
                                            <Badge bg="success" className="ms-2">
                                                {event.porcentaje_avance.toFixed(1)}%
                                            </Badge>
                                        </div>
                                    )}
                                </Col>
                                <Col md={6}>
                                    <div className="mb-2">
                                        <strong>Cantidad:</strong> 
                                        <span className="text-primary">
                                            {event.cantidad_completado || 0} de {event.cantidad_total || 0}
                                        </span>
                                    </div>
                                    <div className="mb-2">
                                        <strong>Completado:</strong> 
                                        <span className="text-success">
                                            {event.cantidad_terminado || 0}
                                        </span>
                                    </div>
                                    <div className="mb-2">
                                        <strong>Máquina:</strong> 
                                        <span className={event.maquina && event.maquina !== 'Sin máquina' ? 'text-primary' : 'text-muted'}>
                                            {event.maquina || 'Sin asignar'}
                                        </span>
                                        {event.maquina_descripcion && event.maquina_descripcion !== 'Sin máquina' && (
                                            <small className="d-block text-muted">
                                                {event.codigo_maquina + '-' + event.maquina_descripcion}
                                            </small>
                                        )}
                                    </div>
                                    <div className="mb-2">
                                        <strong>Operador:</strong> 
                                        <span className={event.resource?.operador && event.resource.operador !== 'Sin operador' ? 'text-primary' : 'text-muted'}>
                                            {event.resource?.operador || 'Sin asignar'}
                                        </span>
                                    </div>
                                    {event.resource?.ot_fecha_termino && event.resource.ot_fecha_termino !== 'N/A' && (
                                        <div className="mb-2">
                                            <strong>Fecha Término OT:</strong> 
                                            <span className="text-info">
                                                {event.resource.ot_fecha_termino}
                                            </span>
                                        </div>
                                    )}
                                </Col>
                            </Row>
                        </div>

                        <div className="mb-3">
                            <h6>Horarios</h6>
                            <Row>
                                <Col md={6}>
                                    <div className="mb-2">
                                        <FaCalendarAlt className="me-2 text-primary" />
                                        <strong>Inicio Planificado:</strong> {moment(event.start).format('DD/MM/YYYY HH:mm')}
                                    </div>
                                    {event.resource?.fecha_inicio_real && (
                                        <div className="mb-2">
                                            <FaClock className="me-2 text-success" />
                                            <strong>Inicio Real:</strong> {moment(event.resource.fecha_inicio_real).format('DD/MM/YYYY HH:mm')}
                                        </div>
                                    )}
                                </Col>
                                <Col md={6}>
                                    <div className="mb-2">
                                        <FaClock className="me-2 text-success" />
                                        <strong>Fin Planificado:</strong> {moment(event.end).format('DD/MM/YYYY HH:mm')}
                                    </div>
                                    {event.resource?.fecha_fin_real && (
                                        <div className="mb-2">
                                            <FaClock className="me-2 text-danger" />
                                            <strong>Fin Real:</strong> {moment(event.resource.fecha_fin_real).format('DD/MM/YYYY HH:mm')}
                                        </div>
                                    )}
                                </Col>
                            </Row>
                            <div className="mb-2">
                                <FaIndustry className="me-2 text-info" />
                                <strong>Duración Planificada:</strong> {formatDuration(event.start, event.end)}
                            </div>
                            {event.resource?.fecha_inicio_real && event.resource?.fecha_fin_real && (
                                <div className="mb-2">
                                    <FaIndustry className="me-2 text-warning" />
                                    <strong>Duración Real:</strong> {formatDuration(event.resource.fecha_inicio_real, event.resource.fecha_fin_real)}
                                </div>
                            )}
                        </div>

                        {event.resource?.observaciones && (
                            <div className="mb-3">
                                <h6>Observaciones</h6>
                                <div className="p-2 bg-light rounded">
                                    {event.resource.observaciones}
                                </div>
                            </div>
                        )}

                        {/* ✅ NUEVA SECCIÓN: INFORMACIÓN DEL BLOQUE */}
                        {event.resource?.es_bloque_unificado && (
                            <div className="mb-3">
                                <h6>Información del Bloque</h6>
                                <div className="p-2 bg-info bg-opacity-10 rounded">
                                    <div className="mb-2">
                                        <strong>Tipo:</strong> Bloque Unificado
                                    </div>
                                    <div className="mb-2">
                                        <strong>Período:</strong> {event.resource?.periodo || 'N/A'}
                                    </div>
                                    <div className="mb-2">
                                        <strong>Descripción:</strong> Este evento representa múltiples intervalos agrupados para mejor visualización
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* ✅ SECCIÓN DE PROGRESO MEJORADA */}
                        {(event.resource?.estado === 'EN_PROCESO' || event.resource?.porcentaje_avance > 0) && (
                            <div className="mb-3">
                                <h6>Progreso</h6>
                                <div className="progress mb-2" style={{ height: '20px' }}>
                                    <div 
                                        className="progress-bar bg-success" 
                                        style={{ 
                                            width: `${Math.min((event.resource.cantidad_terminado / event.resource.total) * 100, 100)}%` 
                                        }}
                                    >
                                        {((event.resource.cantidad_terminado / event.resource.total) * 100).toFixed(1)}%
                                    </div>
                                </div>
                                <Row>
                                    <Col md={6}>
                                        <small className="text-muted">
                                            <strong>Completado:</strong> {event.resource.cantidad_terminado.toLocaleString()} unidades
                                        </small>
                                    </Col>
                                    <Col md={6}>
                                        <small className="text-muted">
                                            <strong>Restante:</strong> {(event.resource.total - event.resource.cantidad_terminado).toLocaleString()} unidades
                                        </small>
                                    </Col>
                                </Row>
                            </div>
                        )}

                        {/* ✅ NUEVA SECCIÓN: INFORMACIÓN TÉCNICA */}
                        <div className="mb-3">
                            <h6>Información Técnica</h6>
                            <Row>
                                <Col md={6}>
                                    <div className="mb-2">
                                        <strong>Estándar:</strong> 
                                        <span className="text-info">
                                            {getEstandar(event)} u/hr
                                        </span>
                                    </div>
                                    <div className="mb-2">
                                        <strong>Duración Estimada:</strong> 
                                        <span className="text-secondary">
                                            {formatDuration(event.start, event.end)}
                                        </span>
                                    </div>
                                    {event.resource?.es_bloque_unificado && (
                                        <div className="mb-2">
                                            <strong>Tipo de Bloque:</strong> 
                                            <Badge bg="info" className="ms-2">
                                                {event.resource.periodo || 'Unificado'}
                                            </Badge>
                                        </div>
                                    )}
                                </Col>
                                <Col md={6}>
                                    <div className="mb-2">
                                        <strong>Restante:</strong> 
                                        <span className="text-warning">
                                            {(event.resource?.total || 0) - (event.resource?.cantidad_terminado || 0)} unidades
                                        </span>
                                    </div>
                                    <div className="mb-2">
                                        <strong>Eficiencia:</strong> 
                                        <span className={event.resource?.porcentaje_avance >= 100 ? 'text-success' : 'text-warning'}>
                                            {event.resource?.porcentaje_avance ? `${event.resource.porcentaje_avance.toFixed(1)}%` : 'N/A'}
                                        </span>
                                    </div>
                                    {event.resource?.observaciones && (
                                        <div className="mb-2">
                                            <strong>Observaciones:</strong> 
                                            <small className="d-block text-muted mt-1">
                                                {event.resource.observaciones}
                                            </small>
                                        </div>
                                    )}
                                </Col>
                            </Row>
                        </div>
                    </Col>
                    
                    <Col md={4}>
                        <div className="border-start ps-3">
                            <h6>Resumen</h6>
                            <div className="mb-2">
                                <small className="text-muted">ID del Evento:</small><br/>
                                <code className="text-primary">{event.id}</code>
                            </div>
                            <div className="mb-2">
                                <small className="text-muted">Tipo:</small><br/>
                                <Badge bg="info">
                                    {event.resource?.es_bloque_unificado ? 'Bloque Unificado' : 'Tarea Programada'}
                                </Badge>
                            </div>
                            <div className="mb-2">
                                <small className="text-muted">Prioridad:</small><br/>
                                <Badge bg="warning">Normal</Badge>
                            </div>
                            
                            <hr/>
                            
                            <div className="mb-2">
                                <small className="text-muted">Creado:</small><br/>
                                <span className="text-secondary">{moment(event.start).format('DD/MM/YYYY')}</span>
                            </div>
                            <div className="mb-2">
                                <small className="text-muted">Última actualización:</small><br/>
                                <span className="text-secondary">{moment().format('DD/MM/YYYY HH:mm')}</span>
                            </div>
                            
                            {/* ✅ NUEVA INFORMACIÓN ADICIONAL */}
                            {event.resource?.es_bloque_unificado && (
                                <>
                                    <hr/>
                                    <div className="mb-2">
                                        <small className="text-muted">Duración del Bloque:</small><br/>
                                        <strong className="text-info">{formatDuration(event.start, event.end)}</strong>
                                    </div>
                                    <div className="mb-2">
                                        <small className="text-muted">Cantidad Total:</small><br/>
                                        <strong className="text-primary">{event.resource?.cantidad || 0} unidades</strong>
                                    </div>
                                </>
                            )}
                            
                            {/* ✅ INFORMACIÓN DE PROGRESO */}
                            {event.resource?.porcentaje_avance > 0 && (
                                <>
                                    <hr/>
                                    <div className="mb-2">
                                        <small className="text-muted">Progreso Actual:</small><br/>
                                        <div className="progress mt-1" style={{ height: '8px' }}>
                                            <div 
                                                className="progress-bar bg-success" 
                                                style={{ width: `${Math.min(event.resource.porcentaje_avance, 100)}%` }}
                                            ></div>
                                        </div>
                                        <small className="text-success">
                                            {event.resource.porcentaje_avance.toFixed(1)}% completado
                                        </small>
                                    </div>
                                </>
                            )}
                            
                            {/* ✅ ESTADO DEL PROCESO */}
                            <hr/>
                            <div className="mb-2">
                                <small className="text-muted">Estado del Proceso:</small><br/>
                                <Badge 
                                    bg={getStatusColor(event.resource?.estado)} 
                                    className="mt-1"
                                >
                                    {getStatusIcon(event.resource?.estado)} {event.resource?.estado || 'PENDIENTE'}
                                </Badge>
                            </div>
                        </div>
                    </Col>
                </Row>
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={onHide}>
                    Cerrar
                </Button>
                <Button variant="primary">
                    <FaUser className="me-2" />
                    Ver Operador
                </Button>
                <Button variant="info">
                    <FaIndustry className="me-2" />
                    Ver Máquina
                </Button>
            </Modal.Footer>
        </Modal>
    );
}; 