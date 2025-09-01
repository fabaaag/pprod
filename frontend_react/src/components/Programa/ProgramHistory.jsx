import React, { useState, useEffect } from 'react';
import { Card, Collapse, Table, Badge, Button, Modal, Row, Col } from 'react-bootstrap';
import { FaHistory, FaCalendarAlt, FaExchangeAlt, FaPlus, FaMinus, FaEdit, FaTrash } from 'react-icons/fa';
import { getProgramHistory, deleteProgramHistory } from '../../api/programs.api';
import { toast } from 'react-hot-toast';
import moment from 'moment';
import { LoadingSpinner } from '../UI/LoadingSpinner/LoadingSpinner';
import './css/ProgramHistory.css';
import Timeline from 'react-calendar-timeline';
import "react-calendar-timeline/dist/Timeline.scss";
import DatePicker from 'react-datepicker';
import axios from 'axios';
//import { supervisorReportAPI } from '../../api/supervisorReport.api';

const TareaCambio = ({ cambio }) => {
    if (!cambio) return null;

    const renderIcon = () => {
        switch (cambio.tipo) {
            case 'COMPLETADO':
                return <FaEdit className="me-2 text-success" />;
            case 'CONTINUACION':
                return <FaExchangeAlt className="me-2 text-warning" />;
            default:
                return null;
        }
    };

    const renderCambioDetalle = () => {
        const { estado_original, estado_nuevo } = cambio;
        
        if (!estado_original || !estado_nuevo) return null;
        
                return (
                    <>
                        <div className="d-flex align-items-center">
                            <span className="me-2">Estado:</span>
                    <Badge bg="secondary">{estado_original.estado || 'No definido'}</Badge>
                            <FaExchangeAlt className="mx-2" />
                    <Badge bg={cambio.tipo === 'COMPLETADO' ? 'success' : 'warning'}>
                        {estado_nuevo.estado || cambio.tipo}
                    </Badge>
                        </div>
                            <div className="mt-1">
                                <small>
                        Cantidad completada: {estado_original.cantidad_completada || 0} → {estado_nuevo.cantidad_completada || estado_original.cantidad_completada || 0}
                                </small>
                            </div>
                {cambio.tipo === 'CONTINUACION' && (
                            <div className="mt-1">
                                <small>
                            Continuación para: {estado_nuevo.fecha_continuacion || 'No definida'}<br/>
                            Cantidad pendiente: {estado_nuevo.cantidad_pendiente || 0}
                                </small>
                            </div>
                        )}
                    </>
                );
    };

    return (
        <tr className="cambio-row">
            <td className="align-middle" width="40">{renderIcon()}</td>
            <td>
                <div className="cambio-detalle">
                    {renderCambioDetalle()}
                </div>
            </td>
        </tr>
    );
};

const ResumenDia = ({ resumen }) => (
    <div className="resumen-dia mb-3">
        <div className="d-flex justify-content-between flex-wrap gap-2">
            <Badge bg="primary" className="me-2">
                Total: {resumen?.tareas_totales || 0}
            </Badge>
            <Badge bg="success" className="me-2">
                Completadas: {resumen?.tareas_completadas || 0}
            </Badge>
            <Badge bg="warning">
                Continuadas: {resumen?.tareas_continuadas || 0}
            </Badge>
        </div>
        {resumen?.fecha_cierre && (
            <div className="mt-2">
                <small>Cerrado el: {moment(resumen.fecha_cierre).format('DD/MM/YYYY HH:mm')}</small>
            </div>
        )}
    </div>
);

const ResumenFabricacion = ({ timelineData, resumenData }) => {
    console.log('Datos del resumen recibidos:', resumenData);

    // Si no tenemos datos del resumen, mostramos mensaje
    if (!resumenData) {
        return (
            <div className="resumen-fabricacion p-3 border-top border-bottom bg-light">
                <h6 className="mb-3">Resumen de Fabricación</h6>
                <div className="text-center text-muted">
                    <p>No hay datos de fabricación disponibles para esta fecha</p>
                </div>
            </div>
        );
        }

    return (
        <div className="resumen-fabricacion p-3 border-top border-bottom bg-light">
            <h6 className="mb-3">Resumen de Fabricación</h6>
            <Row>
                <Col md={4}>
                    <div className="stat-item">
                        <div className="stat-label">Kilos Totales</div>
                        <div className="stat-value">
                            {(resumenData.kilos_totales || 0).toLocaleString()} kg
                        </div>
                    </div>
                </Col>
                <Col md={4}>
                    <div className="stat-item">
                        <div className="stat-label">Kilos Fabricados</div>
                        <div className="stat-value">
                            {(resumenData.kilos_fabricados || 0).toLocaleString()} kg
                        </div>
                    </div>
                </Col>
                <Col md={4}>
                    <div className="stat-item">
                        <div className="stat-label">Progreso</div>
                        <div className="progress" style={{ height: '20px' }}>
                            <div 
                                className="progress-bar" 
                                role="progressbar" 
                                style={{ width: `${resumenData.porcentaje_progreso || 0}%` }}
                                aria-valuenow={resumenData.porcentaje_progreso || 0} 
                                aria-valuemin="0" 
                                aria-valuemax="100"
                            >
                                {((resumenData.porcentaje_progreso || 0).toFixed(1))}%
                            </div>
                        </div>
                    </div>
                </Col>
            </Row>
        </div>
    );
};

export const ProgramHistory = ({ programId, isAdmin }) => {
    useEffect(() => {
        console.log('isAdmin value:', isAdmin);
    }, [isAdmin]);

    const [show, setShow] = useState(false);
    const [historial, setHistorial] = useState([]);
    const [selectedDate, setSelectedDate] = useState(null);
    const [timelineState, setTimelineState] = useState({
        data: null,
        error: null,
        loading: false
    });
    const [resumenData, setResumenData] = useState(null);

    const handleClose = () => setShow(false);
    const handleShow = () => {
        setShow(true);
        cargarHistorial();
    };

    const cargarHistorial = async () => {
        if (!programId) return;
        
        setTimelineState(prev => ({ ...prev, loading: true }));
        try {
            const data = await getProgramHistory(programId);
            setHistorial(data);
        } catch (error) {
            console.error('Error al cargar historial:', error);
            toast.error('Error al cargar el historial');
        } finally {
            setTimelineState(prev => ({ ...prev, loading: false }));
        }
    };

    const cargarTimelineHistorica = async (fecha) => {
        setTimelineState(prev => ({ ...prev, loading: true }));
        try {
            const [timelineResponse, resumenResponse] = await Promise.all([
                getProgramHistory(programId, fecha),
                //supervisorReportAPI.getDailySummary(programId, fecha)
            ]);

            setTimelineState({
                data: timelineResponse,
                error: null,
                loading: false
            });
            setResumenData(resumenResponse);
            setSelectedDate(fecha);
        } catch (error) {
            setTimelineState(prev => ({ ...prev, error: error.message, loading: false }));
            toast.error('Error al cargar los datos del historial');
        }
    };

    const handleDeleteHistorial = async (historialId, event) => {
        event.stopPropagation(); // Evitar que se active el onClick del padre
        
        if (!window.confirm('¿Está seguro de eliminar este registro histórico? Esta acción no se puede deshacer.')) {
            return;
        }

        try {
            await deleteProgramHistory(programId, historialId);
            toast.success('Registro histórico eliminado correctamente');
            cargarHistorial(); // Recargar la lista
            
            // Si el registro eliminado era el seleccionado, limpiar la vista
            if (selectedDate === registro.fecha_referencia) {
                setTimelineState(prev => ({ ...prev, data: null, error: null }));
                setSelectedDate(null);
            }
        } catch (error) {
            if (error.response?.status === 403) {
                toast.error('No tiene permisos para realizar esta acción');
            } else {
                toast.error('Error al eliminar el registro histórico');
            }
        }
    };

    const renderTimeline = (timelineData) => {
        if (!timelineData?.timeline_data) return null;

        const { grupos = [], items = [] } = timelineData.timeline_data;

        // Validación mejorada de datos
        if (!Array.isArray(grupos) || !Array.isArray(items)) {
            console.error('Formato de datos inválido:', timelineData);
            return (
                <div className="alert alert-warning">
                    Error en el formato de datos del historial
                </div>
            );
        }

        // Convertir grupos al formato esperado por react-calendar-timeline
        const groups = grupos.map(grupo => ({
            id: grupo.id || `ot_${grupo.orden_trabajo}`,
            title: `${grupo.orden_trabajo_codigo_ot} - ${grupo.descripcion}`,
            stackItems: true,
            height: 70
        }));

        // Convertir items al formato esperado por react-calendar-timeline
        const timelineItems = items.map(item => {
            // Determinar el estado para el color
            const estado = item.estado?.toLowerCase() || 'pendiente';
            let backgroundColor;
            switch (estado) {
                case 'completado':
                    backgroundColor = '#4CAF50'; // Verde
                    break;
                case 'continuado':
                    backgroundColor = '#FFA726'; // Naranja
                    break;
                case 'en_proceso':
                    backgroundColor = '#2196F3'; // Azul
                    break;
                default:
                    backgroundColor = '#9E9E9E'; // Gris para pendiente
            }
            
            return {
                id: item.id,
                group: item.grupo_id || item.ot_id,
                title: item.nombre || item.name,
                start_time: moment(item.inicio || item.start_time),
                end_time: moment(item.fin || item.end_time),
                className: `timeline-item ${estado}`,
                        itemProps: {
                            style: {
                        backgroundColor,
                                color: 'white',
                                borderRadius: '4px',
                        padding: '2px 6px',
                        fontSize: '12px'
                    },
                    'data-tip': `
                        ${item.nombre || item.name}
                        Cantidad: ${item.cantidad_intervalo || 0} de ${item.cantidad_total || 0}
                        Estado: ${item.estado || 'Pendiente'}
                        Inicio: ${moment(item.inicio || item.start_time).format('DD/MM/YYYY HH:mm')}
                        Fin: ${moment(item.fin || item.end_time).format('DD/MM/YYYY HH:mm')}
                    `
                }
            };
        });

        // Resto del código...
        return (
            <div className="timeline-container">
                <Timeline
                    groups={groups}
                    items={timelineItems}
                    defaultTimeStart={moment(timelineData.metadata?.fecha_referencia).startOf('day')}
                    defaultTimeEnd={moment(timelineData.metadata?.fecha_siguiente).add(2, 'days').endOf('day')}
                    canMove={false}
                    canResize={false}
                    stackItems
                    sidebarWidth={250}
                    lineHeight={40}
                    itemHeightRatio={0.7}
                    traditionalZoom
                    timeSteps={{
                        second: 1,
                        minute: 30,
                        hour: 1,
                        day: 1,
                        month: 1,
                        year: 1
                    }}
                />
                
                <ResumenFabricacion 
                    timelineData={timelineData} 
                    resumenData={resumenData}
                />
                
                <div className="cambios-container mt-3">
                    <h5 className="mb-3">Cambios Realizados ({(timelineData.cambios || []).length})</h5>
                    <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                        <Table hover responsive size="sm" className="cambios-table">
                            <tbody>
                                {(timelineData.cambios || []).length > 0 ? 
                                    (timelineData.cambios || []).map((cambio, index) => (
                                        <TareaCambio 
                                            key={`cambio-${cambio.tarea_id}-${index}`} 
                                            cambio={cambio} 
                                        />
                                    )) : 
                                    <tr>
                                        <td colSpan="2" className="text-center py-3 text-muted">
                                            No hay cambios registrados para este período
                                        </td>
                                    </tr>
                                }
                            </tbody>
                        </Table>
                    </div>
                </div>
            </div>
        );
    };

    const renderHistorialItem = (registro) => (
        <div 
            key={registro.id}
            className={`historial-item ${selectedDate === registro.fecha_referencia ? 'active' : ''}`}
            onClick={() => cargarTimelineHistorica(registro.fecha_referencia)}
        >
            <div className="d-flex align-items-center justify-content-between">
                <div className="d-flex align-items-center gap-2">
                    <Badge bg="info">{registro.tipo_reajuste}</Badge>
                    <Button 
                        variant="link" 
                        className="text-danger p-0" 
                        onClick={(e) => handleDeleteHistorial(registro.id, e)}
                        title="Eliminar registro"
                    >
                        <FaTrash size={14} />
                    </Button>
                </div>
                <small className="text-muted">
                    {moment(registro.fecha_reajuste).format('DD/MM/YYYY HH:mm')}
                </small>
            </div>
            {registro.resumen && <ResumenDia resumen={registro.resumen} />}
        </div>
    );

    return (
        <>
            <Button 
                variant="primary" 
                size="sm" 
                onClick={handleShow}
                className="d-flex align-items-center gap-2"
                style={{ marginLeft: '10px' }}
            >
                <FaHistory /> Ver Historial
            </Button>

            <Modal 
                show={show} 
                onHide={handleClose} 
                size="xl"
                className="program-history-modal"
                dialogClassName="modal-90w"
                contentClassName="modal-tall"
            >
                <Modal.Header closeButton>
                    <Modal.Title>
                        <FaHistory className="me-2" />
                        Historial del Programa
                        {isAdmin && (
                            <Badge bg="danger" className="ms-2" style={{ fontSize: '0.7em' }}>
                                Modo Administrador
                            </Badge>
                        )}
                    </Modal.Title>
                </Modal.Header>
                <Modal.Body className="p-0">
                    {timelineState.loading ? (
                        <LoadingSpinner />
                    ) : timelineState.error ? (
                        <div className="alert alert-danger m-3">
                            {timelineState.error}
                        </div>
                    ) : (
                        <Row className="g-0">
                            <Col md={3} className="border-end">
                                <div className="p-3">
                                    <h6 className="mb-3">Registros Históricos</h6>
                                    <div className="historial-list" style={{ maxHeight: '75vh', overflowY: 'auto' }}>
                                        {historial.map(registro => renderHistorialItem(registro))}
                                    </div>
                                </div>
                            </Col>
                            <Col md={9} className="timeline-view-container">
                                {timelineState.data ? (
                                    renderTimeline(timelineState.data)
                                ) : (
                                    <div className="text-center text-muted p-5">
                                        <FaCalendarAlt size={40} className="mb-3 text-light" />
                                        <p>Seleccione un registro para ver los detalles</p>
                                    </div>
                                )}
                            </Col>
                        </Row>
                    )}
                </Modal.Body>
            </Modal>
        </>
    );
};
