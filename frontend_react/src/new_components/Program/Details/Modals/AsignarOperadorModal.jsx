import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Row, Col, Spinner, Alert } from 'react-bootstrap';
import { assignOperatorToProgram , getOperadoresPorMaquina } from '../../../../api/operator.api';
import { FaUserPlus, FaCalendarAlt, FaUserSlash } from 'react-icons/fa';
import DatePicker from 'react-datepicker';
import "react-datepicker/dist/react-datepicker.css";
import toast from 'react-hot-toast';
import { set } from 'react-hook-form';

export const AsignarOperadorModal = ({
    show,
    onHide,
    programId,
    itemRuta,
    ot,
    onOperadorAsignado,
    itemsTimeline = []
})  => {
    const [operadores, setOperadores] = useState([]);
    const [selectedOperador, setSelectedOperador] = useState('');
    const [fechaInicio, setFechaInicio] = useState(new Date());
    const [fechaFin, setFechaFin] = useState(new Date());
    const [isLoading, setIsLoading] = useState(false);
    const [asignacionActual, setAsignacionActual] = useState(null);
    const [error, setError] = useState('');
    const [fechasConfiguradas, setFechasConfiguradas] = useState(false);

    //Cargar operadores disponibles y que puedan utilizar la maquina asignada a la tarea.
    useEffect(() => {
        if (show) {
            loadOperadores();
            //checkExistingAssignment();
           const fechas = getFechaHoraFromItem(itemRuta.id);
           if (fechas){
            console.log('fechasss', fechas);
            setFechaInicio(fechas.start);
            setFechaFin(fechas.end);
           } else {
            console.log("No se encontraron fechas en el timeline para el item:", itemRuta.id);
           }
        }
    }, [show, itemRuta, itemsTimeline]);

    const loadOperadores = async () => {
        try{
            setIsLoading(true);
            console.log(itemRuta, programId, ot);
            const data = await getOperadoresPorMaquina(itemRuta.maquina_id);
            setOperadores(data);
        } catch (err) {
            console.error('Error al cargar operadores:', err);
            setError('Error al cargar la lista de operadores');
            toast.error('Error al cargar operadores');
        } finally {
            setIsLoading(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!selectedOperador) {
            setError('Debe seleccionar un operador');
            return;
        }

        if (fechaInicio >= fechaFin){
            setError('La fecha de inicio debe ser anterior a la fecha de fin');
            return;
        }

        setIsLoading(true);
        setError('');

        try {
            const assignmentData = {
                programa_id: programId,
                item_ruta_id: itemRuta,
                operador_id: selectedOperador,
                fecha_inicio: fechaInicio.toISOString(),
                fecha_fin: fechaFin.toISOString()
            };

            await assignOperatorToProgram(programId, assignmentData);

            toast.success('Operador asignado correctamente');
            if (onOperadorAsignado) onOperadorAsignado();
            onHide();
        } catch (err) {
            console.error('Error al asignar operador:', err);
            setError('Error al asignar operador. Por favor, intente nuevamente.');
            toast.error('Error al asignar operador');
        } finally {
            setIsLoading(false);
        }
    };

    const handleRemoveAssignment = async () => {
        if (!window.confirm('¿EStá seguro que desea eliminar esta asignación?')) return;

        setIsLoading(true);
        try{
            const removeData = {
                programa_id: programId,
                item_ruta_id: itemRuta,
                is_removing: true
            };
            
            await assignOperatorToProgram(programId, removeData);

            toast.success('Asignación eliminada correctamente');
            if (onOperadorAsignado) onOperadorAsignado();
            onHide();
        } catch (err) {
            console.error('Error al eliminar asignación:', err);
            setError('Error al eliminar la asignación. Por favor, intente nuevamente.');
            toast.error('Error al eliminar la asignación');
        } finally {
            setIsLoading(false);
        }
    };

    const getFechaHoraFromItem = (itemRutaId) => {
        if (!itemsTimeline || itemsTimeline.length === 0){
            console.log("No hay items de timeline disponibles");
            return null;
        }

        const matchingItem = itemsTimeline.find(item =>
            String(item.id).includes(`item_${itemRutaId}_`)
        );

        if (matchingItem) {
            console.log("Item encontrado:", matchingItem.id);
            return {
                start: matchingItem.start,
                end: matchingItem.end
            };
        }
        console.log("No se encontró ningún item que coincida en el timeline");
        return null;
    }

    return (
        <Modal show={show} onHide={onHide} centered backdrop='static' size='lg'>
            <Modal.Header closeButton>
                <Modal.Title>{asignacionActual ? 'Modificar Asignación de Operador': 'Asignar Operador a Proceso'}</Modal.Title>
            </Modal.Header>

            <Modal.Body>
                {isLoading && ( 
                    <div className="text-center-my-3">
                        <Spinner animation='border' variant='primary'/>
                        <p className="mt-2">Cargando información</p>
                    </div>
                )}

                {!isLoading && (
                    <Form onSubmit={handleSubmit}>
                        {error && <Alert variant="danger">{error}</Alert>}
                        <div className="mb-4 p-3 bg-light rounded">
                            <h5 className="mb-3">Información del Proceso</h5>
                            <Row>
                                <Col md={6}>
                                    <Form.Group className='mb-3'>
                                        <Form.Label>Orden de Trabajo</Form.Label>
                                        <Form.Control type="text" value={ot.orden_trabajo_codigo_ot +' - '+ ot.orden_trabajo_descripcion_producto_ot || 'N/A'} disabled/>
                                    </Form.Group>
                                </Col>
                                <Col md={6}>
                                    <Form.Group className="mb-3">
                                        <Form.Label>Proceso</Form.Label>
                                        <Form.Control type="text" value={itemRuta.codigo_proceso + ' - ' + itemRuta.descripcion || 'N/A'} disabled />
                                    </Form.Group>
                                </Col>
                            </Row>
                        </div>

                        <div className="mb-4 p-3 bg-light rounded">
                            <h5 className="mb-3">Asignación</h5>
                            <Form.Group className='mb-3'>
                                <Form.Label>Operador <span className='text-danger'>*</span></Form.Label>
                                <Form.Select
                                    value={selectedOperador}
                                    onChange={(e) => setSelectedOperador(e.target.value)}
                                    required
                                >
                                    <option value="">Seleccione un operador</option>
                                    {operadores.map(operador => (
                                        <option value={operador.id} key={operador.id}>
                                            {operador.rut} {operador.nombre}
                                        </option>
                                    ))}
                                </Form.Select>
                            </Form.Group>
                            <Row>
                                <Col md={6}>
                                    <Form.Group className='mb-3'>
                                        <Form.Label>
                                            <FaCalendarAlt className="me-1" /> Fecha Inicio <span className="text-danger">*</span>
                                        </Form.Label>
                                        <DatePicker 
                                            selected={fechaInicio}
                                            //onChange={date => setFechaInicio(date)}
                                            showTimeSelect
                                            timeFormat="HH:mm"
                                            timeIntervals={15}
                                            dateFormat="dd/MM/yyyy HH:mm"
                                            className='form-control'
                                            required
                                            disabled
                                        />
                                    </Form.Group>
                                </Col>
                                <Col md={6}>
                                    <Form.Group className='mb-3'>
                                        <Form.Label>
                                            <FaCalendarAlt className="me-1" /> Fecha Fin <span className="text-danger">*</span>
                                        </Form.Label>
                                        <DatePicker 
                                            selected={fechaFin}
                                            //onChange={date => setFechaFin(date)}
                                            showTimeSelect
                                            timeFormat="HH:mm"
                                            timeIntervals={15}
                                            dateFormat="dd/MM/yyyy HH:mm"
                                            className='form-control'
                                            required
                                            minDate={fechaInicio}
                                            disabled
                                        />
                                    </Form.Group>
                                </Col>
                            </Row>
                        </div>

                        {asignacionActual && (
                            <Alert variant='info'>
                                <strong>Información</strong> Ya existe una asignación para este proceso.
                                Si continúa, se actualizará con los nuevos datos.
                            </Alert>
                        )}
                    </Form>
                )}
            </Modal.Body>

            <Modal.Footer>
                <Button variant='secondary' onClick={onHide} disabled={isLoading}>Cancelar</Button>

                {asignacionActual && (
                    <Button
                        variant='danger'
                        onClick={handleRemoveAssignment}
                        disabled={isLoading}
                    >
                        <FaUserSlash className="me-1" /> Eliminar Asignación
                    </Button>
                )}
                <Button
                    variant='primary'
                    onClick={handleSubmit}
                    disabled={isLoading}
                >
                    <FaUserPlus className="me-1" /> {asignacionActual ? 'Actualizar Asignación' : 'Asignar Operador'} 
                </Button>
            </Modal.Footer>
        </Modal>
    );
};
