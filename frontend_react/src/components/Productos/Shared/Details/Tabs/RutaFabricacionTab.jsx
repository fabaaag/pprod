import React, { useState, useEffect } from 'react';
import { Alert, Badge, Button, Form, Row, Col, Modal } from 'react-bootstrap';
import { FaExclamationTriangle, FaClock, FaIndustry, FaTools, FaEdit, FaSave } from 'react-icons/fa';
import { LoadingSpinner } from '../../../../UI/LoadingSpinner/LoadingSpinner';

import toast from 'react-hot-toast';
import '../css/RutaFabricacion.css';
import { getMaquinasCompatibles, actualizarEstandar, getEstandaresProceso } from '../../../../../api/productos.api';

export const RutaFabricacionTab = ({
    rutas,
    tipo = 'producto', // 'producto' o 'pieza'
    objetoId, // ID del producto o pieza
    loadingRutas = false,
    onRutaUpdated = null  // Callback para notificar al componente padre que se actualizó una ruta
}) => {
    // Estados para el selector de máquinas
    const [maquinasCompatibles, setMaquinasCompatibles] = useState({});
    const [loadingMaquinas, setLoadingMaquinas] = useState({});
    const [showModal, setShowModal] = useState(false);
    const [selectedRuta, setSelectedRuta] = useState(null);
    const [selectedMaquinaId, setSelectedMaquinaId] = useState(null);
    const [nuevoEstandar, setNuevoEstandar] = useState(0);
    const [savingEstandar, setSavingEstandar] = useState(false);
    const [expandedProcesos, setExpandedProcesos] = useState({});
    const [hoveredProcess, setHoveredProcess] = useState(null);
    const [rutaId, setRutaId] = useState(null);

    if (!rutas || rutas.length === 0) {
        return (
            <Alert variant="warning">
                <FaExclamationTriangle className="me-2" />
                {`Este ${tipo} no tiene rutas de fabricación definidas.`}
            </Alert>
        );
    }

    if (loadingRutas) {
        return (
            <div className="text-center py-4">
                <LoadingSpinner message="Cargando rutas de fabricación..." size="small" />
            </div>
        );
    }

    // Ordenar rutas por número de etapa
    const rutasOrdenadas = [...rutas].sort((a, b) => a.nro_etapa - b.nro_etapa);

    // Función para cargar máquinas compatibles con un proceso
    const cargarMaquinasCompatibles = async (procesoId, forzarRecarga = false) => {
        if (maquinasCompatibles[procesoId] && !forzarRecarga) {
            return maquinasCompatibles[procesoId];
        }
        
        setLoadingMaquinas(prev => ({ ...prev, [procesoId]: true }));
        
        try {
            const maquinas = await getMaquinasCompatibles(procesoId, tipo, objetoId);
            const estandares = await getEstandaresProceso(procesoId, tipo, objetoId);

            console.log('Estándares recibidos:', estandares);
            console.log('Máquinas recibidas:', maquinas);

            //Combinar la información de máquinas con sus estándares
            const maquinasConEstandares = maquinas.map(maquina => {
                const estandarEncontrado = estandares.find(e => {
                    const maquinaIdEstandar = e.maquina?.id || e.maquina;
                    return parseInt(maquinaIdEstandar) === parseInt(maquina.id);
                });

                console.log(`Máquina ${maquina.id} ${maquina.descripcion}:`, {
                    estandarEncontrado,
                    estandar: estandarEncontrado?.estandar || 0,
                    es_principal: estandarEncontrado?.es_principal || false,
                });
                
                return {
                    ...maquina,
                    estandar: estandarEncontrado?.estandar || 0,
                    es_principal: estandarEncontrado?.es_principal || false
                }
            })

            console.log('Máquinas con estándares:', maquinasConEstandares);
            
            setMaquinasCompatibles(prev => ({
                ...prev,
                [procesoId]: maquinasConEstandares
            }));

            return maquinasConEstandares;

        } catch (error) {
            console.error('Error cargando máquinas compatibles:', error);
            toast.error('Error al cargar máquinas compatibles');
            return [];
        } finally {
            setLoadingMaquinas(prev => ({ ...prev, [procesoId]: false }));
        }
    };

    // Función para abrir modal de selección de máquina
    const abrirSelectorMaquina = (ruta) => {
        console.log('Ruta recibida:', ruta);
        console.log('Ruta ID:', ruta?.id);
        
        // Verificar que la ruta tenga un ID
        if (!ruta || !ruta.id) {
            console.error('Error: La ruta no tiene ID', ruta);
            toast.error('Error: No se pudo identificar la ruta');
            return;
        }
        
        // Guardar el ID en una variable de estado separada como respaldo
        setRutaId(ruta.id);
        
        setSelectedRuta(ruta);
        setSelectedMaquinaId(ruta.maquina?.id);
        setNuevoEstandar(ruta.estandar || 0);
        
        if (ruta.proceso?.id) {
            cargarMaquinasCompatibles(ruta.proceso.id);
        } else {
            console.error('Error: La ruta no tiene un proceso asociado', ruta);
            toast.error('Error: La ruta no tiene un proceso asociado');
        }
        
        setShowModal(true);
    };

    // Función para guardar el estándar actualizado
    const guardarEstandar = async () => {
        // Usar rutaId como respaldo si selectedRuta.id es undefined
        const idRuta = selectedRuta?.id || rutaId;
        
        if (!idRuta) {
            console.error('Error: No se pudo identificar la ruta', { selectedRuta, rutaId });
            toast.error('Error: No se pudo identificar la ruta');
            return;
        }
        
        if (!selectedMaquinaId) {
            toast.error('Por favor seleccione una máquina');
            return;
        }
        
        setSavingEstandar(true);
        
        try {
            //Determinar si es la máquina principal (la que estaba originalmente)
            const esPrincipal = selectedMaquinaId === selectedRuta.maquina.id;

            console.log('Enviando datos al backend:', {
                rutaId: idRuta,
                maquinaId: selectedMaquinaId,
                estandar: nuevoEstandar,
                es_principal: esPrincipal
            });
            
            const response = await actualizarEstandar(idRuta, selectedMaquinaId, parseInt(nuevoEstandar), esPrincipal);
            
            console.log('Respuesta del backend:', response);
            toast.success('Estándar actualizado correctamente');
            
            // Actualizar la lista de máquinas compatibles para reflejar el cambio
            if (selectedRuta?.proceso?.id) {
                
                cargarMaquinasCompatibles(selectedRuta.proceso.id, true);
            }
            
            setShowModal(false);
            
            // Notificar al componente padre que se actualizó una ruta
            if (onRutaUpdated) {
                onRutaUpdated();
            }
        } catch (error) {
            console.error('Error guardando estándar:', error);
            const errorMsg = error.response?.data?.error || error.message || 'Error desconocido';
            toast.error(`Error al guardar estándar: ${errorMsg}`);
        } finally {
            setSavingEstandar(false);
        }
    };

    // Cuando se selecciona una máquina, actualizar el estándar
    const handleMaquinaChange = async (e) => {
        const maquinaId = parseInt(e.target.value);
        setSelectedMaquinaId(maquinaId);

        console.log("Maquina seleccionada ID:", maquinaId);
        
        // Buscar el estándar correspondiente a esta máquina
        if (maquinaId && selectedRuta?.proceso?.id){
            let maquinasDisponibles = maquinasCompatibles[selectedRuta.proceso.id] || [];
            let maquinaSeleccionada = maquinasDisponibles.find(m => m.id === maquinaId);

            if (maquinaSeleccionada){
                console.log("Máquina seleccionada con estandar:", maquinaSeleccionada);
                setNuevoEstandar(maquinaSeleccionada.estandar || 0);
            } else {
                // si no encontramos la maquina en la caché forzamos una recarga
                console.log("Máquina no encontrada en caché, recargando datos...");
                const maquinasActualizadas = await cargarMaquinasCompatibles(selectedRuta.proceso.id, true);
                const maquinaActualizada = maquinasActualizadas.find(m => m.id === maquinaId);
                if (maquinaActualizada){
                    console.log("Máquina actualizada con estándar:", maquinaActualizada);
                    setNuevoEstandar(maquinaActualizada.estandar || 0);
                } else {
                    setNuevoEstandar(0);
                }
            }
        }
    };

    // Esta función agrupa por proceso REAL (no por nro_etapa) y mantiene orden lógico
    const agruparRutasPorProcesoReal = (rutas) => {
        // Primero, encontrar todos los procesos únicos
        const procesosUnicos = [];
        const procesosIds = new Set();
        
        // Ordenar primero por nro_etapa para mantener secuencia lógica
        // Si hay duplicados en nro_etapa, ordenar por ID para consistencia
        const rutasOrdenadas = [...rutas].sort((a, b) => {
            if (a.nro_etapa !== b.nro_etapa) {
                return a.nro_etapa - b.nro_etapa;
            }
            return a.id - b.id;
        });
        
        // Extraer los procesos únicos manteniendo el orden lógico
        rutasOrdenadas.forEach(ruta => {
            const procesoId = ruta.proceso?.id;
            if (!procesosIds.has(procesoId)) {
                procesosIds.add(procesoId);
                procesosUnicos.push({
                    id: procesoId,
                    proceso: ruta.proceso,
                    nro_etapa: ruta.nro_etapa,
                    rutas: []
                });
            }
        });
        
        // Ahora asignar todas las rutas a su proceso correspondiente
        rutasOrdenadas.forEach(ruta => {
            const procesoId = ruta.proceso?.id;
            const procesoGrupo = procesosUnicos.find(p => p.id === procesoId);
            if (procesoGrupo) {
                procesoGrupo.rutas.push(ruta);
            }
        });
        
        return procesosUnicos;
    };

    // Añadimos esta función para controlar la expansión de un proceso
    const toggleProcesoExpansion = (procesoId) => {
        setExpandedProcesos(prev => ({
            ...prev,
            [procesoId]: !prev[procesoId]
        }));
        
        // Si no se han cargado las máquinas compatibles para este proceso, cargarlas
        if (!maquinasCompatibles[procesoId]) {
            cargarMaquinasCompatibles(procesoId);
        }
    };

    return (
        <div className="ruta-fabricacion-container">
            {/* Resumen de la ruta */}
            <div className="route-summary mb-4">
                <div className="summary-item">
                    <h5><FaClock className="icon" /> Tiempo Total</h5>
                    <div className="summary-value">
                        {rutasOrdenadas.reduce((total, ruta) => total + (ruta.estandar || 0), 0)} unidades/hora
                    </div>
                </div>
                <div className="summary-item">
                    <h5><FaIndustry className="icon" /> Máquinas</h5>
                    <div className="summary-value">
                        {new Set(rutasOrdenadas.map(ruta => ruta.maquina?.id)).size}
                    </div>
                </div>
                <div className="summary-item">
                    <h5><FaTools className="icon" /> Etapas</h5>
                    <div className="summary-value">
                        {rutasOrdenadas.length}
                    </div>
                </div>
            </div>

            {/* Ruta de Procesos */}
            <h5 className="section-title">Secuencia de Fabricación</h5>
            <div className="process-timeline">
                {agruparRutasPorProcesoReal(rutas).map(grupo => (
                    <div 
                        key={`proceso-${grupo.id}`} 
                        className={`process-group ${expandedProcesos[grupo.id] ? 'expanded' : ''}`}
                        onMouseEnter={() => setHoveredProcess(grupo.id)}
                        onMouseLeave={() => setHoveredProcess(null)}
                    >
                        {/* Cabecera del proceso (clickeable para expandir) */}
                        <div 
                            className="process-header"
                            onClick={() => toggleProcesoExpansion(grupo.id)}
                        >
                            <div className="process-number">
                                {grupo.nro_etapa}
                            </div>
                            <div className="process-content">
                                <h6 className="d-flex justify-content-between align-items-center">
                                    {grupo.proceso?.descripcion || 'Proceso'}
                                    <div>
                                        {(hoveredProcess === grupo.id || expandedProcesos[grupo.id]) && (
                                            <Button 
                                                variant="outline-secondary" 
                                                size="sm"
                                                className="me-2"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    toggleProcesoExpansion(grupo.id);
                                                }}
                                                title={expandedProcesos[grupo.id] ? "Ocultar máquinas alternativas" : "Ver máquinas alternativas"}
                                            >
                                                {expandedProcesos[grupo.id] ? "▲" : "▼"}
                                            </Button>
                                        )}
                                        <Button 
                                            variant="outline-primary" 
                                            size="sm"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                //Asegurarnos de encontrar la ruta original con su ID
                                                if (grupo.rutas && grupo.rutas.length > 0) {
                                                    const rutaOriginal = rutas.find(r => 
                                                        // Buscar la ruta original completa con su ID
                                                        r.proceso?.id === grupo.proceso?.id &&
                                                        r.nro_etapa === grupo.nro_etapa
                                                    );
                                                    if (rutaOriginal && rutaOriginal.id) {
                                                        console.log("No se encontró la ruta original con ID", rutaOriginal.id);
                                                        abrirSelectorMaquina(rutaOriginal);
                                                    } else {
                                                        console.error("No se encontró la ruta original con ID");
                                                        toast.error("Error: no se pudo identificar la ruta");
                                                    }
                                                } else {
                                                    console.error("No hay rutas para este proceso");
                                                    toast.error("Error: no hay rutas para este proceso");
                                                }
                                            }}
                                            title="Editar máquina y estándar"
                                        >
                                            <FaEdit />
                                        </Button>
                                    </div>
                                </h6>
                                <div className="process-detail">
                                    <span className="machine">
                                        <FaIndustry className="icon" />
                                        {grupo.rutas[0].maquina?.descripcion || 'Máquina'}
                                    </span>
                                    <span className="standard">
                                        <FaClock className="icon" />
                                        {grupo.rutas[0].estandar || 0} und/hr
                                    </span>
                                </div>
                            </div>
                        </div>
                        
                        {/* Panel de máquinas alternativas (expandible) */}
                        {expandedProcesos[grupo.id] && (
                            <div className="maquinas-alternativas-panel">
                                {loadingMaquinas[grupo.id] ? (
                                    <div className="text-center py-3">
                                        <LoadingSpinner message="Cargando máquinas compatibles..." size="sm" />
                                    </div>
                                ) : (
                                    <div className="maquinas-list">
                                        {maquinasCompatibles[grupo.id]?.map(maquina => (
                                            <div 
                                                key={maquina.id} 
                                                className={`maquina-item ${maquina.id === grupo.rutas[0].maquina?.id ? 'active' : ''}`}
                                                onClick={() => {
                                                    //Buscar la ruta original completa con su ID
                                                    const rutaOriginal = rutas.find( r => 
                                                        r.proceso?.id === grupo.proceso?.id &&
                                                        r.nro_etapa === grupo.nro_etapa
                                                    );

                                                    if (rutaOriginal && rutaOriginal.id) {
                                                        // Crear una copia de la ruta original con la máquina seleccionada
                                                        const rutaModificada = {
                                                            ...rutaOriginal,
                                                            maquina: {
                                                                id: maquina.id,
                                                                codigo_maquina: maquina.codigo,
                                                                descripcion: maquina.descripcion,
                                                            }
                                                        };
                                                        console.log("Ruta modificada con ID:", rutaModificada.id);
                                                        abrirSelectorMaquina(rutaModificada);
                                                    } else {
                                                        console.error("No se encontró la ruta original con ID");
                                                        toast.error("Error: No se pudo identificar la ruta");
                                                    }
                                                }}
                                            >
                                                <div className="maquina-info">
                                                    <Badge bg={maquina.id === grupo.rutas[0].maquina?.id ? "primary" : "secondary"}>
                                                        {maquina.codigo}
                                                    </Badge>
                                                    <span className="maquina-descripcion">{maquina.descripcion}</span>
                                                </div>
                                                <div className="estandar-value">
                                                    {maquina.estandar} und/hr
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {/* Modal para selección de máquina */}
            <Modal 
                show={showModal} 
                onHide={() => setShowModal(false)}
                backdrop="static"
                centered
            >
                <Modal.Header closeButton>
                    <Modal.Title>
                        <FaIndustry className="me-2" />
                        Seleccionar Máquina Alternativa
                    </Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    {loadingMaquinas[selectedRuta?.proceso?.id] ? (
                        <div className="text-center py-3">
                            <LoadingSpinner message="Cargando máquinas compatibles..." size="sm" />
                        </div>
                    ) : (
                        <>
                            <p className="mb-3">
                                Proceso: <strong>{selectedRuta?.proceso?.descripcion}</strong>
                            </p>
                            
                            <Form.Group className="mb-3">
                                <Form.Label>Máquina:</Form.Label>
                                <Form.Select
                                    value={selectedMaquinaId || ''}
                                    onChange={handleMaquinaChange}
                                >
                                    <option value="">Seleccione una máquina</option>
                                    {maquinasCompatibles[selectedRuta?.proceso?.id]?.map(maquina => (
                                        <option key={maquina.id} value={maquina.id}>
                                            {maquina.codigo} - {maquina.descripcion} ({maquina.estandar} und/hr)
                                        </option>
                                    ))}
                                </Form.Select>
                            </Form.Group>
                            
                            <Form.Group className="mb-3">
                                <Form.Label>Estándar de producción (und/hr):</Form.Label>
                                <Form.Control
                                    type="number"
                                    min="0"
                                    value={nuevoEstandar}
                                    onChange={(e) => setNuevoEstandar(e.target.value)}
                                />
                                <Form.Text className="text-muted">
                                    Cantidad de unidades que se pueden producir por hora.
                                </Form.Text>
                            </Form.Group>
                            
                            {/* Tabla de estándares por máquina */}
                            {maquinasCompatibles[selectedRuta?.proceso?.id]?.length > 0 && (
                                <div className="mt-4">
                                    <h6>Estándares actuales por máquina:</h6>
                                    <div className="estandares-por-maquina">
                                        {maquinasCompatibles[selectedRuta?.proceso?.id].map(maquina => (
                                            <div 
                                                key={maquina.id} 
                                                className={`estandar-maquina-item ${maquina.id === selectedMaquinaId ? 'selected' : ''}`}
                                            >
                                                <div className="maquina-info">
                                                    <Badge bg={maquina.id === selectedMaquinaId ? "primary" : "secondary"}>
                                                        {maquina.codigo}
                                                    </Badge>
                                                    <span className="maquina-descripcion">{maquina.descripcion}</span>
                                                </div>
                                                <div className="estandar-value">
                                                    {maquina.estandar} und/hr
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={() => setShowModal(false)}>
                        Cancelar
                    </Button>
                    <Button 
                        variant="primary" 
                        onClick={guardarEstandar}
                        disabled={savingEstandar || !selectedMaquinaId}
                    >
                        {savingEstandar ? (
                            <>
                                <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                                Guardando...
                            </>
                        ) : (
                            <>
                                <FaSave className="me-2" />
                                Guardar
                            </>
                        )}
                    </Button>
                </Modal.Footer>
            </Modal>
        </div>
    );
};