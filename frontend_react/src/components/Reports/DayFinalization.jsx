import React, { useState } from 'react';
import { Modal, Button, Alert, Spinner } from 'react-bootstrap';
import { FaExclamationTriangle, FaCheckCircle, FaClock } from 'react-icons/fa';
//import { finalizarDia } from '../../api/supervisorReport.api';
import './css/DayFinalization.css'

export const DayFinalization = ({ show, onHide, date, tasks, programId, onFinalized }) => {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    
    const pendingTasks = tasks.filter(t => 
        t.estado !== 'COMPLETADO' && 
        t.estado !== 'CONTINUADO' && 
        t.porcentaje_cumplimiento < 100
    );
    const hasUnfinishedTasks = pendingTasks.length > 0;

    const handleFinalize = async () => {
        try {
            setIsLoading(true);
            setError(null);
            
            const formattedDate = date.toISOString().split('T')[0];
            const response = await finalizarDia(programId, formattedDate);
            
            if (response.data) {
                onFinalized && onFinalized(response.data);
                onHide();
            }
        } catch (err) {
            setError(err.response?.data?.error || 'Error al finalizar el día');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Modal show={show} onHide={onHide} centered className="day-finalization-modal">
            <Modal.Header closeButton>
                <Modal.Title>
                    <FaClock className="me-2" />
                    Finalizar Día
                </Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <div className="date-summary">
                    <h6>Fecha: {date?.toLocaleDateString('es-ES', {
                        weekday: 'long',
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                    })}</h6>
                </div>

                {error && (
                    <Alert variant="danger" className="mt-3">
                        <FaExclamationTriangle className="me-2" />
                        {error}
                    </Alert>
                )}

                {hasUnfinishedTasks ? (
                    <Alert variant="warning" className="mt-3">
                        <FaExclamationTriangle className="me-2" />
                        <strong>Atención:</strong> Hay tareas sin completar
                    </Alert>
                ) : (
                    <Alert variant="success" className="mt-3">
                        <FaCheckCircle className="me-2" />
                        Todas las tareas están completadas
                    </Alert>
                )}

                {hasUnfinishedTasks && (
                    <div className="pending-tasks mt-3">
                        <h6>Tareas pendientes:</h6>
                        <ul className="task-list">
                            {pendingTasks.map(task => (
                                <li key={task.id} className="task-item">
                                    <span className="ot-code">{task.orden_trabajo.codigo}</span>
                                    <span className="process">{task.proceso.descripcion}</span>
                                    <span className={`status ${task.estado.toLowerCase()}`}>
                                        {task.estado} ({task.porcentaje_cumplimiento?.toFixed(1)}%)
                                    </span>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={onHide} disabled={isLoading}>
                    Cancelar
                </Button>
                <Button 
                    variant="primary" 
                    onClick={handleFinalize}
                    className={hasUnfinishedTasks ? 'btn-warning' : 'btn-success'}
                    disabled={isLoading}
                >
                    {isLoading ? (
                        <>
                            <Spinner
                                as="span"
                                animation="border"
                                size="sm"
                                role="status"
                                aria-hidden="true"
                                className="me-2"
                            />
                            Finalizando...
                        </>
                    ) : (
                        hasUnfinishedTasks ? 'Finalizar con Pendientes' : 'Finalizar Día'
                    )}
                </Button>
            </Modal.Footer>
        </Modal>
    );
};