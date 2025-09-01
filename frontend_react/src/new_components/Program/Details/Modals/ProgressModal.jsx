import React, { useState } from 'react';
import { Modal, Form, Button, Alert } from 'react-bootstrap';
import { toast } from 'react-hot-toast';
import { updateItemRutaProgress } from '../../../../api/programs.api';

export const ProgressModal = ({
    show,
    onHide,
    itemRuta,
    otData,
    onProgressUpdate
}) => {
    const [formData, setFormData] = useState({
        cantidad_completada: '',
        observaciones: '',
        fecha_inicio: itemRuta?.fecha_inicio_real ? new Date(itemRuta?.fecha_inicio_real).toISOString().slice(0, 16) : '',
        fecha_fin: itemRuta?.fecha_fin_real ? new Date(itemRuta?.fecha_fin_real).toISOString().slice(0, 16) : '',
        operador: itemRuta?.operador_actual
    });

    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!formData.cantidad_completada) {
            toast.error('Ingrese la cantidad completada');
            return;
        }
        try {
            setLoading(true);
            const response = await updateItemRutaProgress(itemRuta.id, {
                ...formData,
                cantidad_completada: parseFloat(formData.cantidad_completada),
            });

            onProgressUpdate(response);
            toast.success('Progreso actualizado correctamente');
            onHide();
        } catch (error){
            console.error('Error actualizando progreso:', error);
            toast.error('Error al actualizar progreso');
        } finally {
            setLoading(false);
        }
    };

    const cantidadTotal = parseFloat(itemRuta?.cantidad || 0);
    const cantidadCompletada = parseFloat(itemRuta?.cantidad_terminado_proceso || 0);
    const cantidadRestante = Math.max(0, cantidadTotal - cantidadCompletada);

    return ( 
        <Modal
            show={show}
            onHide={onHide}
        >
            <Modal.Header closeButton>
                <Modal.Title>Actualizar Progreso</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Alert variant="info">
                    <strong>OT:</strong> {otData?.orden_trabajo_codigo_ot} <br />
                    <strong>Proceso:</strong> {itemRuta?.proceso?.descripcion} <br />
                    <strong>Cantidad Total:</strong> {cantidadTotal} <br />
                    <strong>Completado:</strong> {cantidadCompletada} <br />
                    <strong>Restante: </strong> {cantidadRestante}
                </Alert>

                <Form onSubmit={handleSubmit}>
                    <Form.Group className="mb-3">
                        <Form.Label>Cantidad Completada</Form.Label>
                        <Form.Control 
                            type="number"
                            value={formData.cantidad_completada}
                            onChange={(e) => setFormData(prev => ({
                                ...prev,
                                cantidad_completada: e.target.value
                            }))}
                            max={cantidadRestante}
                        />
                    </Form.Group>

                    <Form.Group className="mb-3">
                        <Form.Label>Observaciones</Form.Label>
                        <Form.Control 
                            as="textarea"
                            rows={3}
                            value={formData.observaciones}
                            onChange={(e) => setFormData(prev => ({
                                ...prev,
                                observaciones: e.target.value
                            }))}
                        />
                    </Form.Group>

                    <Form.Group className="mb-3">
                        <Form.Label>Fecha Inicio</Form.Label>
                        <Form.Control 
                            type="datetime-local"
                            value={formData.fecha_inicio}
                            onChange={(e) => setFormData(prev => ({
                                ...prev,
                                fecha_inicio: e.target.value
                            }))}
                        />
                    </Form.Group>
                    <Form.Group className="mb-3">
                        <Form.Label>Fecha Fin</Form.Label>
                        <Form.Control 
                            type="datetime-local"
                            value={formData.fecha_fin}
                            onChange={(e) => setFormData(prev => ({
                                ...prev,
                                fecha_fin: e.target.value
                            }))}
                        />
                    </Form.Group>
                </Form>
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={onHide}>
                    Cancelar
                </Button>
                <Button
                    variant="primary"
                    onClick={handleSubmit}
                    disabled={loading}
                >
                    {loading ? 'Guardando...' : 'Guardar Progreso'}
                </Button>
            </Modal.Footer>
        </Modal>
    );
};
