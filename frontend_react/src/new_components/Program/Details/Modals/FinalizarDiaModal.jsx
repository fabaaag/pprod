import React, { useState, useEffect } from 'react';
import { Modal, Button, Alert, Form, Row, Col, Spinner, Badge } from 'react-bootstrap';
import { FaCalendarCheck, FaDownload, FaUpload, FaExclamationTriangle } from 'react-icons/fa';
import toast from 'react-hot-toast';
import { finalizarDia } from '../../../../api/planificacion.api';

export const FinalizarDiaModal = ({ 
    show, 
    onHide, 
    programId, 
    programData,
    onDiaFinalizado 
}) => {
    const [fechaFinalizacion, setFechaFinalizacion] = useState(new Date().toISOString().split('T')[0]);
    const [importarAvances, setImportarAvances] = useState(false);
    const [loading, setLoading] = useState(false);
    const [previewCambios, setPreviewCambios] = useState(null);
    const [error, setError] = useState('');

    // Reset form when modal opens
    useEffect(() => {
        if (show) {
            setFechaFinalizacion(new Date().toISOString().split('T')[0]);
            setImportarAvances(false);
            setPreviewCambios(null);
            setError('');
        }
    }, [show]);

    const handleFinalizarDia = async () => {
        try {
            setLoading(true);
            setError('');

            const resultado = await finalizarDia(programId, fechaFinalizacion, importarAvances);

            if (resultado.success) {
                toast.success(`✅ Día ${fechaFinalizacion} finalizado exitosamente`);
                
                // Llamar callback con los resultados
                if (onDiaFinalizado) {
                    onDiaFinalizado({
                        fechaFinalizada: resultado.fecha_finalizada,
                        nuevaFechaInicio: resultado.nueva_fecha_inicio,
                        cambiosImportados: resultado.cambios_importados,
                        comparativa: resultado.comparativa
                    });
                }
                
                onHide();
            } else {
                setError(resultado.error || 'Error finalizando día');
                toast.error('❌ Error al finalizar el día');
            }

        } catch (err) {
            console.error('Error finalizando día:', err);
            setError(err.response?.data?.error || 'Error al finalizar el día');
            toast.error('❌ Error al finalizar el día');
        } finally {
            setLoading(false);
        }
    };

    const previsualizarCambios = async () => {
        // Esta función se puede implementar más tarde para mostrar preview
        toast.info('🔍 Función de previsualización en desarrollo');
    };

    return (
        <Modal show={show} onHide={onHide} size="lg" centered backdrop="static">
            <Modal.Header closeButton>
                <Modal.Title>
                    <FaCalendarCheck className="me-2 text-primary" />
                    Finalizar Día de Producción
                </Modal.Title>
            </Modal.Header>

            <Modal.Body>
                {error && (
                    <Alert variant="danger" className="mb-3">
                        <FaExclamationTriangle className="me-2" />
                        {error}
                    </Alert>
                )}

                {/* Información del programa */}
                <Alert variant="info" className="mb-4">
                    <h6 className="mb-2">📋 Programa: {programData?.nombre || 'Cargando...'}</h6>
                    <small>
                        Este proceso finalizará el día seleccionado y actualizará la fecha de inicio 
                        del programa para continuar con la planificación.
                    </small>
                </Alert>

                <Form>
                    <Row className="mb-3">
                        <Col md={6}>
                            <Form.Group>
                                <Form.Label>Fecha a Finalizar</Form.Label>
                                <Form.Control
                                    type="date"
                                    value={fechaFinalizacion}
                                    onChange={(e) => setFechaFinalizacion(e.target.value)}
                                    disabled={loading}
                                />
                            </Form.Group>
                        </Col>
                        <Col md={6} className="d-flex align-items-end">
                            <Form.Group className="w-100">
                                <Form.Check
                                    type="checkbox"
                                    id="importar-avances"
                                    label="Importar avances del sistema externo"
                                    checked={importarAvances}
                                    onChange={(e) => setImportarAvances(e.target.checked)}
                                    disabled={loading}
                                />
                                <Form.Text className="text-muted">
                                    Actualiza las cantidades producidas desde el sistema AVSA
                                </Form.Text>
                            </Form.Group>
                        </Col>
                    </Row>

                    {importarAvances && (
                        <Alert variant="warning" className="mb-3">
                            <h6>⚠️ Importación de Avances</h6>
                            <p className="mb-2">Se importarán los avances desde los archivos del sistema externo:</p>
                            <ul className="mb-0">
                                <li>📄 Archivo de OTs (ot.txt)</li>
                                <li>📄 Archivo de Rutas (ruta_ot.txt)</li>
                            </ul>
                        </Alert>
                    )}

                    {/* Preview de cambios (futuro) */}
                    {previewCambios && (
                        <Alert variant="success" className="mb-3">
                            <h6>🔍 Vista Previa de Cambios</h6>
                            <p>Se detectaron {previewCambios.length} cambios para aplicar.</p>
                            <Button size="sm" variant="outline-success" onClick={previsualizarCambios}>
                                Ver Detalles
                            </Button>
                        </Alert>
                    )}
                </Form>

                {/* Proceso que se ejecutará */}
                <Alert variant="secondary" className="mb-0">
                    <h6>🔄 Proceso que se ejecutará:</h6>
                    <ol className="mb-0">
                        <li>📸 Capturar estado actual de la planificación</li>
                        {importarAvances && <li>📊 Importar avances del sistema externo</li>}
                        <li>🔍 Generar comparativa de cambios</li>
                        <li>📅 Actualizar fecha de inicio del programa</li>
                        <li>💾 Guardar registro del día finalizado</li>
                    </ol>
                </Alert>
            </Modal.Body>

            <Modal.Footer>
                <Button variant="secondary" onClick={onHide} disabled={loading}>
                    Cancelar
                </Button>
                
                <Button 
                    variant="primary" 
                    onClick={handleFinalizarDia}
                    disabled={loading}
                >
                    {loading ? (
                        <>
                            <Spinner animation="border" size="sm" className="me-2" />
                            Finalizando...
                        </>
                    ) : (
                        <>
                            <FaCalendarCheck className="me-2" />
                            Finalizar Día
                        </>
                    )}
                </Button>
            </Modal.Footer>
        </Modal>
    );
};