import React, { useState, useEffect } from 'react';
import axiosInstance from '../../api/axiosConfig';
import { AnalisisAvancesModal } from './AnalisisAvancesModal';
import './css/InconsistenciasModal.css';

const InconsistenciasModal = ({ programaId, isOpen, onClose }) => {
    const [inconsistencias, setInconsistencias] = useState([]);
    const [loading, setLoading] = useState(false);
    const [selectedOT, setSelectedOT] = useState(null);

    useEffect(() => {
        if (isOpen && programaId) {
            cargarInconsistencias();
        }
    }, [isOpen, programaId]);

    const cargarInconsistencias = async () => {
        setLoading(true);
        try {
            const response = await axiosInstance.get(`/gestion/api/v1/programas/${programaId}/ots-inconsistencias/`);
            setInconsistencias(response.data.ots || []);
        } catch (error) {
            console.error('Error cargando inconsistencias:', error);
            setInconsistencias([]);
        } finally {
            setLoading(false);
        }
    };

    const abrirDetalleOT = (ot) => {
        setSelectedOT(ot);
    };

    if (!isOpen) return null;

    return (
        <div className="inconsistencias-modal-overlay">
            <div className="inconsistencias-modal">
                <div className="modal-header">
                    <h2>🔍 Análisis de Inconsistencias</h2>
                    <button onClick={onClose} className="btn-close">×</button>
                </div>

                {loading ? (
                    <div className="loading">Cargando...</div>
                ) : (
                    <div className="modal-content">
                        {inconsistencias.length === 0 ? (
                            <div className="no-inconsistencias">
                                ✅ No se encontraron inconsistencias
                            </div>
                        ) : (
                            <div className="ots-lista">
                                {inconsistencias.map(ot => (
                                    <div key={ot.ot_id} className="ot-card">
                                        <div className="ot-header">
                                            <h3>OT {ot.codigo_ot}</h3>
                                            <span className={`diferencia ${ot.diferencia !== 0 ? 'warning' : 'ok'}`}>
                                                Diferencia: {ot.diferencia}
                                            </span>
                                        </div>
                                        
                                        <div className="ot-stats">
                                            <div>Avance OT: {ot.avance_ot}</div>
                                            <div>Avance Procesos: {ot.avance_procesos}</div>
                                        </div>

                                        <div className="inconsistencias-tags">
                                            {ot.inconsistencias.map(inc => (
                                                <span key={inc} className="tag-inconsistencia">
                                                    {inc}
                                                </span>
                                            ))}
                                        </div>

                                        <button 
                                            onClick={() => abrirDetalleOT(ot)}
                                            className="btn-analizar"
                                        >
                                            🔧 Analizar y Corregir
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {selectedOT && (
                    <AnalisisAvancesModal 
                        show={true}
                        onHide={() => setSelectedOT(null)}
                        programId={programaId}
                        otId={selectedOT.ot_id}
                        otData={selectedOT}
                        onAvancesActualizados={cargarInconsistencias}
                    />
                )}
            </div>
        </div>
    );
};

export default InconsistenciasModal;