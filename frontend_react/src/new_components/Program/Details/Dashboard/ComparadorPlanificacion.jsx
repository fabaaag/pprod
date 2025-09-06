import React from 'react';
import { Card, Table, Badge, Row, Col } from 'react-bootstrap';
import { FaArrowUp, FaArrowDown, FaMinus } from 'react-icons/fa';

export const ComparadorPlanificacion = ({ jsonBase, estadoActual }) => {
    if (!jsonBase || !estadoActual) return null;

    const calcularComparacion = () => {
        const otBase = jsonBase.ordenes_trabajo;
        const otActual = estadoActual.ordenes_trabajo || [];

        return otBase.map(otBase => {
            const otActualData = otActual.find(ot => ot.codigo_ot === otBase.codigo_ot);
            
            if (!otActualData) return { ...otBase, cambios: { noEncontrada: true } };

            const cambios = {
                cantidad_avance: {
                    anterior: otBase.cantidad_avance,
                    actual: otActualData.cantidad_avance,
                    diferencia: otActualData.cantidad_avance - otBase.cantidad_avance
                },
                porcentaje_avance: {
                    anterior: otBase.porcentaje_avance,
                    actual: otActualData.porcentaje_avance,
                    diferencia: otActualData.porcentaje_avance - otBase.porcentaje_avance
                },
                procesos: otBase.procesos.map(procesoBase => {
                    const procesoActual = otActualData.procesos?.find(p => 
                        p.codigo_proceso === procesoBase.codigo_proceso && p.item === procesoBase.item
                    );

                    return {
                        ...procesoBase,
                        actual: procesoActual,
                        cambios: procesoActual ? {
                            cantidad_terminado: procesoActual.cantidad_terminado - procesoBase.cantidad_terminado,
                            estado_cambio: procesoBase.estado_proceso !== procesoActual.estado_proceso,
                            estado_anterior: procesoBase.estado_proceso,
                            estado_actual: procesoActual.estado_proceso
                        } : { noEncontrado: true }
                    };
                })
            };

            return { ...otBase, actual: otActualData, cambios };
        });
    };

    const comparacion = calcularComparacion();

    const renderIconoCambio = (diferencia) => {
        if (diferencia > 0) return <FaArrowUp className="text-success me-1" />;
        if (diferencia < 0) return <FaArrowDown className="text-danger me-1" />;
        return <FaMinus className="text-muted me-1" />;
    };

    return (
        <Card>
            <Card.Header>
                <h5 className="mb-0">📊 Comparación: Planificación Base vs Estado Actual</h5>
            </Card.Header>
            <Card.Body>
                <Table hover size="sm">
                    <thead>
                        <tr>
                            <th>Código OT</th>
                            <th>Avance Base</th>
                            <th>Avance Actual</th>
                            <th>Diferencia</th>
                            <th>% Base</th>
                            <th>% Actual</th>
                            <th>Procesos Modificados</th>
                        </tr>
                    </thead>
                    <tbody>
                        {comparacion.map(ot => (
                            <tr key={ot.id}>
                                <td><strong>{ot.codigo_ot}</strong></td>
                                <td>{ot.cantidad_avance.toLocaleString()}</td>
                                <td>{ot.actual?.cantidad_avance?.toLocaleString() || 'N/A'}</td>
                                <td>
                                    {ot.cambios.cantidad_avance && (
                                        <span className={
                                            ot.cambios.cantidad_avance.diferencia > 0 ? 'text-success' :
                                            ot.cambios.cantidad_avance.diferencia < 0 ? 'text-danger' : 'text-muted'
                                        }>
                                            {renderIconoCambio(ot.cambios.cantidad_avance.diferencia)}
                                            {Math.abs(ot.cambios.cantidad_avance.diferencia).toLocaleString()}
                                        </span>
                                    )}
                                </td>
                                <td>{ot.porcentaje_avance.toFixed(1)}%</td>
                                <td>
                                    {ot.actual?.porcentaje_avance?.toFixed(1) || '0.0'}%
                                    {ot.cambios.porcentaje_avance && ot.cambios.porcentaje_avance.diferencia !== 0 && (
                                        <span className="ms-1">
                                            ({ot.cambios.porcentaje_avance.diferencia > 0 ? '+' : ''}
                                            {ot.cambios.porcentaje_avance.diferencia.toFixed(1)}%)
                                        </span>
                                    )}
                                </td>
                                <td>
                                    {ot.cambios.procesos?.filter(p => 
                                        p.cambios?.cantidad_terminado !== 0 || p.cambios?.estado_cambio
                                    ).length || 0}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </Table>
            </Card.Body>
        </Card>
    );
};