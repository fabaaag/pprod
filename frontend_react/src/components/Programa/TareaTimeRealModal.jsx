import React, { useState } from 'react';
import { Modal, Button, Form } from 'react-bootstrap';
import { toast } from 'react-hot-toast';

export function TareaTimeRealModal({ show, onHide, tarea, onTareaUpdated }) {
  return (
    <Modal show={show} onHide={onHide}>
      <Modal.Body>
        <p>Este modal está deshabilitado temporalmente</p>
      </Modal.Body>
    </Modal>
  );
}