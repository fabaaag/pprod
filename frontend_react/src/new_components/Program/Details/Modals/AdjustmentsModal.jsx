import React from 'react';
import { Modal, Form, Button, Alert, ListGroup } from 'react-bootstrap';
import moment from 'moment';

export const AdjustmentsModal = ({
    show,
    onHide,
    adjustments,
    onApplyAdjustments,
    loading
}) => {
    if (!adjustments) return null;

    return (
        <Modal show={show} onHide={onHide} size="lg">
            <Modal.Header closeButton>
                <Modal.Title>Ajustes Necesarios</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Alert variant="warning">
                    <strong>Fecha actual de fin:</strong> {moment(adjustments.fecha_actual).format('DD/MM/YYYY HH:mm')} <br />
                    <strong>Nueva fecha de fin propuesta:</strong> {moment(adjustments.nueva.fecha_fin).format('DD/MM/YYYY HH:mm')}
                </Alert>

                <div className="mb-3">
                    <strong>Total de ajustes necesarios: </strong>
                    {adjustments.ajustes_sugeridos.length}
                </div>

                <ListGroup>
                    {adjustments.ajustes_sugeridos.map((ajuste, index) => (
                        <ListGroup.Item key={index}>
                            <div className="d-flex justify-content-between align-items-start">
                                <div>
                                    <h6>OT: {ajuste.orden_trabajo}</h6>
                                    <p className="mb-1">
                                        Proceso: {ajuste.proceso.descripcion}
                                    </p>
                                    <small>
                                        Máquina: {ajuste.maquina || 'N/A'}
                                    </small>
                                </div>
                                <div className="text-end">
                                    <Badge bg="warning">
                                        Retraso: {ajuste.tiempo_retraso} hrs
                                    </Badge>
                                    <div className="mt-1">
                                        <small>
                                            Nueva fecha: {moment(ajuste.nueva_ficha).format('DD/MM/YYYY HH:mm')}
                                        </small>
                                    </div>
                                </div>
                            </div>
                        </ListGroup.Item>
                    ))}
                </ListGroup>
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={onHide}>
                    Cancelar
                </Button>
                <Button
                    variant="primary"
                    onClick={onApplyAdjustments}
                    disabled={loading}
                >
                    {loading ? 'Aplicando ajustes...' : 'Aplicar Ajustes'}
                </Button>
            </Modal.Footer>
        </Modal>
    );
};
