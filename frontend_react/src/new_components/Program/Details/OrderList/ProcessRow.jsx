import React, {useEffect, useState} from 'react';
import { Form, Button, Badge } from 'react-bootstrap';
import toast from 'react-hot-toast';
import { getMaquinas } from '../../../../api/programs.api';
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
        // Recargar datos del proceso si es necesario
        // Esto depende de cómo manejes la actualización de datos
        toast.success("Operador asignado correctamente");
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
                <Button size ="sm"
                    onClick={() => handleAsignarOperador(proceso.id, programId, ot.id)}
                >
                    Asignar Operador
                </Button>
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
        // Ya no pasamos itemsTimeline={routesData}
    />
    
    
    </>
  );
};