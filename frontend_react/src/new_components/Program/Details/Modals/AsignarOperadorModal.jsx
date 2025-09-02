import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Row, Col, Spinner, Alert, Badge } from 'react-bootstrap';
import { assignOperatorToProgram , getOperadoresPorMaquina } from '../../../../api/operator.api';
import { FaUserPlus, FaCalendarAlt, FaUserSlash, FaLightbulb } from 'react-icons/fa';
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
    itemsTimeline = [],
    loading
})  => {
    const [operadores, setOperadores] = useState([]);
    const [selectedOperador, setSelectedOperador] = useState('');
    const [fechaInicio, setFechaInicio] = useState(new Date());
    const [fechaFin, setFechaFin] = useState(new Date());
    const [isLoading, setIsLoading] = useState(false);
    const [asignacionActual, setAsignacionActual] = useState(null);
    const [error, setError] = useState('');
    const [fechasSugeridas, setFechasSugeridas] = useState(null);
    const [usandoFechasSugeridas, setUsandoFechasSugeridas] = useState(false);

    //Función para obtener fechas sugeridas del timeline
    const obtenerFechasSugeridasDelTimeline = () => {
        if (!itemsTimeline || itemsTimeline.length === 0){
            console.log("No hay items de timeline disponibles");
            return null;
        }

        try {
            console.log("Buscando fechas sugeridas para ItemRuta:", itemRuta);
            setIsLoading(loading);
            //Buscar todos los elementos que conicidan con este ItemRuta
            const elementosRelacionados = itemsTimeline.filter(item => {
                //1. buscar por ID del ItemRuta en el ID del item
                const coincideId = String(item.id).includes(`item_${itemRuta.id}_`);

                //2. buscar por proceso_id y ot_id
                const coincideProceso = item.proceso_id === `proc_${itemRuta.proceso_id}` ||
                                        item.proceso_codigo === itemRuta.codigo_proceso;
                const coincideOT = item.ot_id === `ot_${ot.id}` ||
                                    item.ot_codigo === ot.orden_trabajo_codigo_ot;


                return coincideId || (coincideProceso && coincideOT);
            });

            console.log(`Elementos encontrados para ItemRuta ${itemRuta.id}:`, elementosRelacionados);

            if (elementosRelacionados.length === 0){ console.log("no se encontraron elementos relacionados en el timeline"); return null;}

            //Obtener todas las fechas de inicio y fin
            const fechas = elementosRelacionados.map(item  => ({
                inicio: new Date(item.start_time),
                fin: new Date(item.end_time)
            }));

            //Calcular fecha minima de inicio y maxima de fin
            const fechaInicioMin = new Date(Math.min(...fechas.map(f => f.inicio.getTime())));
            const fechaFinMax = new Date(Math.max(...fechas.map(f => f.fin.getTime())));

            return {
                fechaInicio: fechaInicioMin,
                fechaFin: fechaFinMax,
                elementosEncontrados: elementosRelacionados.length,
                detalleElementos: elementosRelacionados.map(el => ({
                    id: el.id,
                    inicio: el.start_time,
                    fin: el.end_time,
                    cantidad: el.cantidad_intervalo
                }))
            };
        } catch (error) {
            console.error("Error al obtener fechas sugeridas del timeline:", error);
            return null;
        } finally {
            setIsLoading(false);
        }
    };

    const aplicarFechasSugeridas = () => {
        if(fechasSugeridas){
            setFechaInicio(fechasSugeridas.fechaInicio);
            setFechaFin(fechasSugeridas.fechaFin);
            setUsandoFechasSugeridas(true);
            toast.success('Fechas sugeridas aplicadas');

        }
    };

    // Función para restablecer fechas por defecto
    const restablecerFechasPorDefecto = () => {
        const ahora = new Date();
        const finPorDefecto = new Date(ahora.getTime() + (8 * 60 * 60 * 1000)); // 8horas despues

        setFechaInicio(ahora);
        setFechaFin(finPorDefecto);
        setUsandoFechasSugeridas(false);
    };


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

    // useEffect principal
    useEffect(() => {
        if (show && itemRuta) {
            loadOperadores();
            
            // Obtener fechas sugeridas del timeline
            const sugerencias = obtenerFechasSugeridasDelTimeline();
            setFechasSugeridas(sugerencias);
            
            if (sugerencias) {
                console.log("Fechas sugeridas encontradas:", sugerencias);
                // Aplicar automáticamente las fechas sugeridas
                setFechaInicio(sugerencias.fechaInicio);
                setFechaFin(sugerencias.fechaFin);
                setUsandoFechasSugeridas(true);
            } else {
                console.log("No se encontraron fechas sugeridas, usando fechas por defecto");
                restablecerFechasPorDefecto();
            }
        }
    }, [show, itemRuta, itemsTimeline]);

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
                item_ruta_id: itemRuta.id,
                operador_id: selectedOperador,
                fecha_inicio: fechaInicio.toISOString(),
                fecha_fin: fechaFin.toISOString()
            };

            const responsebknd = await assignOperatorToProgram(programId, assignmentData);
            console.log('repsonse del backend:',  responsebknd.data);

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

    /*
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
    
    */

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

                         {/* Sugerencias de fechas del timeline */}
                         {fechasSugeridas && (
                            <div className="mb-4 p-3 border border-info rounded bg-info bg-opacity-10">
                                <h6 className="text-info mb-3">
                                    <FaLightbulb className="me-2" />
                                    Fechas Sugeridas del Timeline
                                </h6>
                                <Row>
                                    <Col md={6}>
                                        <small className="text-muted">Fecha Inicio Sugerida:</small>
                                        <div className="fw-bold">
                                            {fechasSugeridas.fechaInicio.toLocaleDateString()} {fechasSugeridas.fechaInicio.toLocaleTimeString()}
                                        </div>
                                    </Col>
                                    <Col md={6}>
                                        <small className="text-muted">Fecha Fin Sugerida:</small>
                                        <div className="fw-bold">
                                            {fechasSugeridas.fechaFin.toLocaleDateString()} {fechasSugeridas.fechaFin.toLocaleTimeString()}
                                        </div>
                                    </Col>
                                </Row>
                                <div className="mt-2">
                                    <Badge bg="info" className="me-2">
                                        {fechasSugeridas.elementosEncontrados} elemento(s) encontrado(s) en timeline
                                    </Badge>
                                    {usandoFechasSugeridas && (
                                        <Badge bg="success">
                                            ✓ Usando fechas sugeridas
                                        </Badge>
                                    )}
                                </div>
                                <div className="mt-3">
                                    <Button 
                                        size="sm" 
                                        variant="outline-info" 
                                        onClick={aplicarFechasSugeridas}
                                        className="me-2"
                                    >
                                        <FaLightbulb className="me-1" />
                                        Aplicar Sugerencias
                                    </Button>
                                    <Button 
                                        size="sm" 
                                        variant="outline-secondary" 
                                        onClick={restablecerFechasPorDefecto}
                                    >
                                        Restablecer por Defecto
                                    </Button>
                                </div>
                            </div>
                        )}

                        {/* Asignación */}
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
                                            {operador.rut} - {operador.nombre}
                                        </option>
                                    ))}
                                </Form.Select>
                            </Form.Group>
                            
                            <Row>
                                <Col md={6}>
                                    <Form.Group className='mb-3'>
                                        <Form.Label>
                                            <FaCalendarAlt className="me-1" /> 
                                            Fecha Inicio <span className="text-danger">*</span>
                                        </Form.Label>
                                        <DatePicker 
                                            selected={fechaInicio}
                                            onChange={date => {
                                                setFechaInicio(date);
                                                setUsandoFechasSugeridas(false);
                                            }}
                                            showTimeSelect
                                            timeFormat="HH:mm"
                                            timeIntervals={15}
                                            dateFormat="dd/MM/yyyy HH:mm"
                                            className='form-control'
                                            required
                                        />
                                    </Form.Group>
                                </Col>
                                <Col md={6}>
                                    <Form.Group className='mb-3'>
                                        <Form.Label>
                                            <FaCalendarAlt className="me-1" /> 
                                            Fecha Fin <span className="text-danger">*</span>
                                        </Form.Label>
                                        <DatePicker 
                                            selected={fechaFin}
                                            onChange={date => {
                                                setFechaFin(date);
                                                setUsandoFechasSugeridas(false);
                                            }}
                                            showTimeSelect
                                            timeFormat="HH:mm"
                                            timeIntervals={15}
                                            dateFormat="dd/MM/yyyy HH:mm"
                                            className='form-control'
                                            required
                                            minDate={fechaInicio}
                                        />
                                    </Form.Group>
                                </Col>
                            </Row>
                        </div>

                        {asignacionActual && (
                            <Alert variant='info'>
                                <strong>Información:</strong> Ya existe una asignación para este proceso.
                                Si continúa, se actualizará con los nuevos datos.
                            </Alert>
                        )}
                    </Form>
                )}
            </Modal.Body>

            <Modal.Footer>
                <Button variant='secondary' onClick={onHide} disabled={isLoading}>
                    Cancelar
                </Button>

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
                    <FaUserPlus className="me-1" /> 
                    {asignacionActual ? 'Actualizar Asignación' : 'Asignar Operador'} 
                </Button>
            </Modal.Footer>
        </Modal>
    );
};
