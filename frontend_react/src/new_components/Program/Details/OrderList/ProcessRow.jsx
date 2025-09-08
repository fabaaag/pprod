import React, {useEffect, useState} from 'react';
import { Form, Button, Badge, Spinner } from 'react-bootstrap';
import { FaUser, FaEdit, FaUserPlus } from 'react-icons/fa';
import toast from 'react-hot-toast';
import { getMaquinas, getProgram } from '../../../../api/programs.api';
import { getAsignacionPorItemRuta } from '../../../../api/operator.api';
import { AsignarOperadorModal } from '../Modals/AsignarOperadorModal';

export const ProcessRow = ({
    proceso,
    ot,
    onProcessChange,
    onProcessClick,
    onResetProgress,
    tieneInconsistencias,
    incluyeEnPlanificacion,
    tieneAvance,
    programId,
    routesData
}) => {
    const [showAsignarOperadorModal, setShowAsignarOperadorModal] = useState(false);
    const cantidadTotal = parseFloat(proceso.cantidad || 0);
    const cantidadTerminada = parseFloat(proceso.cantidad_terminada || 0);
    const cantidadRestante = parseFloat(proceso.cantidad_restante || 0);
    const porcentajeCompletado = cantidadTotal > 0 ? (cantidadTerminada / cantidadTotal) * 100 : 0;
    const [maquinasPorProceso, setMaquinasPorProceso] = useState({});
    const [maquinas, setMaquinas] = useState([]);
    const [timelineItems, setTimelineItems] = useState([]);
    const [isLoading, setIsLoading] = useState(false);

    const [asignacionExistente, setAsignacionExistente] = useState(null);
    const [loadingAsignacion, setLoadingAsignacion] = useState(false);

    const cargarItems = async () => {
        if (!programId) { return; }
        if (routesData?.items) {
            setTimelineItems(routesData.items);
            return;
        }

        try {
            console.log(`cargando items para el proposito inicial`);
            setIsLoading(true);
            const program = await getProgram(programId);
            const items = program.routes_data?.items || [];
            setTimelineItems(items);
            console.log(`items cargados: ${items.length} elementos`);
        } catch (error) {
            console.error("error al cargar elementos", error)
            setTimelineItems([]);
        } finally {
            setIsLoading(false);
        }
    };

    const verificarAsignacionExistente = async () => {
        if (!programId || !proceso.id) return;

        try{
            setLoadingAsignacion(true);
            const asignaciones = await getAsignacionPorItemRuta(programId, proceso.id);
            if (asignaciones && asignaciones.length > 0){
                setAsignacionExistente(asignaciones[0]);
            } else {
                setAsignacionExistente(null);
            }
        } catch (error) {
            console.error("Error al verificar asignación existente:", error);
            setAsignacionExistente(null);
        } finally {
            setLoadingAsignacion(false);
        }
    };

    useEffect(() => {
        cargarItems();
    }, [programId, routesData]);

    useEffect(() => {
        verificarAsignacionExistente();
    }, [programId, proceso.id]);

    const cargarMaquinasPorProceso = async (itemRuta) => {
        try {
            //console.log("[Frontend] itemruta completo: ", itemRuta);

            if(!itemRuta || !itemRuta.codigo_proceso){
                return [];
            }
            const codigoProceso = itemRuta.codigo_proceso;

            if(!codigoProceso){
                return [];
            }
            const maquinasData = await getMaquinas(programId, codigoProceso);
            setMaquinasPorProceso(prev => ({
                ...prev,
                [itemRuta.id]: maquinasData
            }));
            return maquinasData;
        } catch (error) {
            console.error("Error al cargar máquinas para el proceso:", error);
            toast.error("Error al cargar  máquinas disponibles");
            return [];
        }
    };

    const fetchMachineData = async () => {
        if(!programId){
            console.error("No hay programId disponible");
            return;
        }
        try{
            const maquinasData = await getMaquinas(programId);
            setMaquinas(maquinasData);
        } catch (error){
            console.error("Error al cargar máquinas:", error);
            toast.error("¡Error al cargar las máquinas!")
        }
    };
    
    useEffect(() => {
        fetchMachineData();
        if(proceso.codigo_proceso){
            cargarMaquinasPorProceso(proceso);
        }
    }, [proceso.id]);

    const handleAsignarOperador = () => {
        setShowAsignarOperadorModal(true);
    };
    const handleOperadorAsignado = () => {
        setShowAsignarOperadorModal(false);
        verificarAsignacionExistente();
        // Recargar datos del proceso si es necesario
        // Esto depende de cómo manejes la actualización de datos
        toast.success("Operador asignado correctamente");
    };

    const renderAsignacionOperador = () => {
        if (loadingAsignacion) {
            return (
                <div className="d-flex align-items-center justify-content-center">
                    <Spinner className="me-2" size="sm" animation="border">
                        <small className="text-muted">Verificando...</small>
                    </Spinner>
                </div>
            );
        }

        if (asignacionExistente){
            return (
                <div className="d-flex flex-column gap-1">
                    <div className="p-2 bg-light rounded border text-center">
                        <div className="fw-bold text-success small">
                            <FaUser className="me-1" />
                            {asignacionExistente.operador?.nombre || 'Operador asignado'}
                        </div>
                        <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                        {asignacionExistente.operador?.rut}
                        </div>
                        <div className="text-muted" style={{ fontSize: '0.7rem' }}>
                            {new Date(asignacionExistente.fecha_inicio).toLocaleDateString()} -
                            {new Date(asignacionExistente.fecha_fin).toLocaleDateString()}
                        </div>
                    </div>
                    <Button
                        variant="outline-primary"
                        size="sm"
                        onClick={handleAsignarOperador}
                        style={{ fontSize: '0.75rem' }}
                    >
                        <FaEdit className="me-1" />
                        Editar
                    </Button>
                </div>
            );
        } else {
            // Mostrar botón para asignar
            return (
                <Button
                    variant="outline-success"
                    size="sm"
                    onClick={handleAsignarOperador}
                    style={{ fontSize: '0.75rem' }}
                >
                    <FaUserPlus className="me-1" />
                    Asignar Operador
                </Button>
            );
        }
    };

  return (
    <>
        <tr>
        <td>{proceso.descripcion}</td>
        <td className='text-center'>
            <Form.Control 
                size='sm'
                type='number'
                style={{ width: '80px', margin: '0 auto' }}
                value={proceso.estandar || 0}
                onChange={(e) => {
                    onProcessChange(
                        ot.orden_trabajo, 
                        proceso.id, 
                        'estandar', 
                        parseFloat(e.target.value)
                    );
                }}
                className={!proceso.estandar || parseFloat(proceso.estandar) === 0 ? "border-danger" : ""}
            />
        </td>
        <td className="text-center">
            <select 
                className="form-select form-select-sm"
                value={proceso.maquina_id || ''}
                onChange={(e) => onProcessChange(
                    ot.orden_trabajo,
                    proceso.id,
                    "maquina_id",
                    e.target.value
                )}
                //disabled={!proceso.maquina_id}
                onFocus={(e) => {
                    if(!maquinasPorProceso[proceso.id]){
                        cargarMaquinasPorProceso(proceso);
                    }
                }}
            >
                <option value="">Seleccionar máquina</option>
                {(maquinasPorProceso[proceso.id] || maquinas).map(maquina => (
                    <option value={maquina.id} key={maquina.id}>
                        {maquina.codigo_maquina} - {maquina.descripcion || 'Sin descripción'} 
                    </option>
                ))}
            </select>
        </td>
        <td className="text-center">
            <div className="d-flex flex-column align-items center">
                <strong className="fs-6">{cantidadTotal.toLocaleString()}</strong>
                <small className="text-muted">Total</small>
            </div>
        </td>
        <td className="text-center">
            <div className="d-flex flex-column align-items-center">
                <strong className={`fs-6 cantidadTerminada > 0 ? 'text-success': 'text-muted'`}>
                    {cantidadTerminada.toLocaleString()}
                </strong>
                <small className="text-muted">Completado</small>
                {cantidadTerminada > 0 && (
                    <Badge className="mt-1" bg="success">
                        {porcentajeCompletado.toFixed(1)}%
                    </Badge>
                )}
            </div>
        </td>
        <td className="text-center">
            <div className="d-flex flex-column align-items-center">
                <strong className={`fs-6 cantidadRestante > 0 ? 'text-info' : 'text-success'`}>
                    {cantidadRestante.toLocaleString()}
                </strong>
                <Badge 
                    bg={incluyeEnPlanificacion ? 'primary' : 'secondary'}
                    className="mt-1"
                    style={{ fontSize: '0.7rem' }}
                >
                    {incluyeEnPlanificacion ? '📋 Planificar':
                    tieneInconsistencias ? '⚠️ Revisar':
                    '✅ Completo'}
                </Badge>
            </div>
        </td>
        <td className="text-center">
            <Form.Select
                size="sm"
                value={
                    cantidadTerminada === 0 ? 'PENDIENTE':
                    cantidadTerminada >= cantidadTotal ?  'COMPLETADO': 
                    'EN_PROCESO'
                }
                disabled
                //onChange={(e) => onProcessChange(ot.orden_trabajo, proceso.id, 'estado_proceso', e.target.value)}
            >
                <option value="EN_PROCESO">🔵 En Proceso</option>
                <option value="COMPLETADO">🟢 Completado</option>
                <option value="PENDIENTE">🟠 Pendiente</option>
            </Form.Select>
        </td>
        <td className="text-center">
            <div className="d-flex flex-column gap-1 align-items-center">
                {renderAsignacionOperador()}
                {/*<Button
                    variant={tieneInconsistencias ? "warning" : incluyeEnPlanificacion ? "primary" : "secondary"}
                    size="sm"
                    onClick={() => onProcessClick(proceso, ot)}
                    title={
                        tieneInconsistencias ? "Resolver inconsistencias" : 
                        incluyeEnPlanificacion ? "Actualizar progreso" : 
                        "Proceso completado"
                    }
                >
                    {tieneInconsistencias ? '⚠️ Revisar' : 
                    incluyeEnPlanificacion ? '📊 Progreso' : 
                    '✅ OK'} 
                </Button>
                {/*tieneAvance && !tieneInconsistencias && (
                    <Button
                        variant="outline-warning"
                        size="sm"
                        onClick={() => onResetProgress(proceso.id)}
                        title="Resetear avance a 0"
                        style={{ fontSize: '0.7rem', padding: '0.2rem 0.4rem'}}
                    >
                        🔄
                    </Button>
                )*/}
            </div>
        </td>

    </tr>

    {/* Modal de asignación de operador */}
    <AsignarOperadorModal
        show={showAsignarOperadorModal}
        onHide={() => setShowAsignarOperadorModal(false)}
        programId={programId}
        itemRuta={proceso}
        ot={ot || {}}
        onOperadorAsignado={handleOperadorAsignado}
        itemsTimeline={timelineItems}
        isLoading={isLoading}
    />
    
    
    </>
  );
};