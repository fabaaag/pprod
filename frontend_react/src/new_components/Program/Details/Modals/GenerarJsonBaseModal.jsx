import React, { useState, useEffect } from 'react';
import { Modal, Button, Alert, Form, Spinner, Badge } from 'react-bootstrap';
import { FaFileCode, FaCheckCircle, FaExclamationTriangle, FaTimes } from 'react-icons/fa';
import toast from 'react-hot-toast';
import { generarJsonBase, verificarPlanificacionLista } from '../../../../api/planificacion.api';

export const GenerarJsonBaseModal = ({ 
    show, 
    onHide, 
    programId, 
    programData,
    onJsonGenerado 
}) => {
    const [fechaBase, setFechaBase] = useState(new Date().toISOString().split('T')[0]);
    const [loading, setLoading] = useState(false);
    const [verificandoRequisitos, setVerificandoRequisitos] = useState(false);
    const [requisitos, setRequisitos] = useState(null);
    const [error, setError] = useState('');

    // Verificar requisitos cuando se abre el modal
    useEffect(() => {
        if (show && programId) {
            verificarRequisitos();
        }
    }, [show, programId]);

    const verificarRequisitos = async () => {
        try {
            setVerificandoRequisitos(true);
            const resultado = await verificarPlanificacionLista(programId);
            setRequisitos(resultado);
        } catch (err) {
            console.error('Error verificando requisitos:', err);
            setError('Error al verificar requisitos de planificación');
        } finally {
            setVerificandoRequisitos(false);
        }
    };

    const handleGenerarJson = async () => {
        try {
            setLoading(true);
            setError('');

            const resultado = await generarJsonBase(programId, fechaBase);

            if (resultado.success) {
                toast.success('✅ JSON base generado exitosamente');
                
                if (onJsonGenerado) {
                    onJsonGenerado({
                        archivoGenerado: resultado.archivo_generado,
                        fechaBase: resultado.fecha_base,
                        datosGenerados: resultado.datos_generados
                    });
                }
                
                onHide();
            } else {
                setError(resultado.error || 'Error generando JSON base');
                toast.error('❌ Error al generar JSON base');
            }

        } catch (err) {
            console.error('Error generando JSON:', err);
            setError(err.response?.data?.error || 'Error al generar JSON base');
            toast.error('❌ Error al generar JSON base');
        } finally {
            setLoading(false);
        }
    };

    const renderRequisitoItem = (label, cumplido, detalle = '') => (
        <div className="d-flex align-items-center mb-2">
            {cumplido ? (
                <FaCheckCircle className="text-success me-2" />
            ) : (
                <FaTimes className="text-danger me-2" />
            )}
            <span className={cumplido ? 'text-success' : 'text-danger'}>
                {label}
            </span>
            {detalle && <small className="text-muted ms-2">({detalle})</small>}
        </div>
    );

    return (
        <Modal show={show} onHide={onHide} size="lg" centered backdrop="static">
            <Modal.Header closeButton>
                <Modal.Title>
                    <FaFileCode className="me-2 text-primary" />
                    Generar JSON Base de Planificación
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
                        Este proceso generará un archivo JSON con la planificación base actual.
                        Este archivo será usado como referencia para futuras comparativas.
                    </small>
                </Alert>

                {/* Verificación de requisitos */}
                <div className="mb-4">
                    <h6 className="mb-3">🔍 Verificación de Requisitos</h6>
                    
                    {verificandoRequisitos ? (
                        <div className="text-center py-3">
                            <Spinner animation="border" size="sm" className="me-2" />
                            Verificando requisitos...
                        </div>
                    ) : requisitos ? (
                        <div className="border rounded p-3">
                            {renderRequisitoItem(
                                'Programa tiene órdenes de trabajo',
                                requisitos.requisitos.tiene_ots,
                                `${requisitos.total_ots} OTs`
                            )}
                            {renderRequisitoItem(
                                'Órdenes con rutas definidas',
                                requisitos.requisitos.ots_con_rutas === requisitos.total_ots,
                                `${requisitos.requisitos.ots_con_rutas}/${requisitos.total_ots}`
                            )}
                            {renderRequisitoItem(
                                'Procesos con máquinas asignadas',
                                requisitos.requisitos.procesos_con_maquinas === requisitos.requisitos.total_procesos,
                                `${requisitos.requisitos.procesos_con_maquinas}/${requisitos.requisitos.total_procesos}`
                            )}
                            {renderRequisitoItem(
                                'Estándares definidos',
                                requisitos.requisitos.estandares_definidos === requisitos.requisitos.total_procesos,
                                `${requisitos.requisitos.estandares_definidos}/${requisitos.requisitos.total_procesos}`
                            )}
                            
                            <hr className="my-3" />
                            
                            <div className="text-center">
                                {requisitos.planificacion_lista ? (
                                    <Badge bg="success" className="p-2">
                                        ✅ Planificación Lista para Generar JSON
                                    </Badge>
                                ) : (
                                    <Badge bg="warning" className="p-2">
                                        ⚠️ Completar Requisitos Antes de Generar JSON
                                    </Badge>
                                )}
                            </div>
                        </div>
                    ) : (
                        <Alert variant="secondary">
                            No se pudieron verificar los requisitos
                        </Alert>
                    )}
                </div>

                {/* Formulario de fecha */}
                {requisitos?.planificacion_lista && (
                    <Form className="mb-4">
                        <Form.Group>
                            <Form.Label>Fecha Base de la Planificación</Form.Label>
                            <Form.Control
                                type="date"
                                value={fechaBase}
                                onChange={(e) => setFechaBase(e.target.value)}
                                disabled={loading}
                            />
                            <Form.Text className="text-muted">
                                Esta fecha se usará como referencia en el archivo JSON
                            </Form.Text>
                        </Form.Group>
                    </Form>
                )}

                {/* Información sobre el proceso */}
                <Alert variant="secondary" className="mb-0">
                    <h6>📄 Contenido del JSON Base:</h6>
                    <ul className="mb-0">
                        <li>📊 Estado completo de todas las órdenes de trabajo</li>
                        <li>🔧 Procesos con máquinas y estándares asignados</li>
                        <li>👷 Asignaciones de operadores actuales</li>
                        <li>📈 Métricas de planificación (kilos, valor)</li>
                        <li>📅 Fechas y metadata de la planificación</li>
                    </ul>
                </Alert>
            </Modal.Body>

            <Modal.Footer>
                <Button variant="secondary" onClick={onHide} disabled={loading}>
                    Cancelar
                </Button>
                
                <Button 
                    variant="primary" 
                    onClick={handleGenerarJson}
                    disabled={loading || !requisitos?.planificacion_lista}
                >
                    {loading ? (
                        <>
                            <Spinner animation="border" size="sm" className="me-2" />
                            Generando JSON...
                        </>
                    ) : (
                        <>
                            <FaFileCode className="me-2" />
                            Generar JSON Base
                        </>
                    )}
                </Button>
            </Modal.Footer>
        </Modal>
    );
};