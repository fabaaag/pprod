import React from 'react';
import { Button, ButtonGroup } from 'react-bootstrap';
import { FaPlus, FaFilePdf, FaHistory, FaExclamationTriangle, FaSave } from 'react-icons/fa';

export const OrderControls = ({
    onAddOrder, 
    onGeneratePDF,
    onShowHistory,
    onCheckAdjustments,
    onShowTimelineReal,
    hasInconsistencies,
    isAdmin,
    onSaveAllProcessChanges,
    savingChanges,
    pendingChangesCount
}) => {
  return (
    <div className="action-buttons d-flex gap-2 align-items-center">
        <Button variant='outline-primary' onClick={onAddOrder}>
            <FaPlus className="me-2" />
            Agregar OT
        </Button>
        
        <Button variant='outline-secondary' onClick={onGeneratePDF}>
            <FaFilePdf className="me-2" />
            Generar PDF
        </Button>

        <Button
          variant="success"
          size="sm"
          onClick={onSaveAllProcessChanges}
          disabled={savingChanges || pendingChangesCount === 0}
          className="me-2"
        >
          <FaSave className="me-1" />
          {savingChanges ? "Guardando..." : `Guardar Cambios (${pendingChangesCount})`}
        </Button>

        
    </div>
  );
};

