import { Modal, Button, Badge, Accordion, ProgressBar } from 'react-bootstrap';
import { FaClock, FaIndustry, FaTools, FaCheckCircle, FaFilePdf, FaCalendarAlt, FaCodeBranch, FaWeight, FaCogs, FaUser, FaList } from 'react-icons/fa';
import './css/OrderDetailModal.css';
import { jsPDF } from 'jspdf';
import html2canvas from 'html2canvas';

export function OrderDetailModal({ show, onHide, orderData }) {
    if (!orderData) return null;

    const exportToPDF = async () => {
        try {
            const content = document.getElementById('modal-content');
            if (!content) {
                console.error('No se encontró el contenido para exportar');
                return;
            }

            // Añadir indicador de carga
            const loadingButton = document.getElementById('export-button');
            if (loadingButton) {
                loadingButton.disabled = true;
                loadingButton.innerHTML = 'Generando PDF...';
            }

            const canvas = await html2canvas(content, {
                scale: 2, // Mejor calidad
                useCORS: true, // Para imágenes de otros dominios
                logging: false // Evitar logs innecesarios
            });

            const imgData = canvas.toDataURL('image/png');
            const pdf = new jsPDF('p', 'mm', 'a4');
            const pdfWidth = pdf.internal.pageSize.getWidth();
            const pdfHeight = (canvas.height * pdfWidth) / canvas.width;

            pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
            pdf.save(`OT-${orderData.codigo_ot}.pdf`);
        } catch (error) {
            console.error('Error al generar PDF:', error);
            alert('Hubo un error al generar el PDF');
        } finally {
            // Restaurar el botón
            const loadingButton = document.getElementById('export-button');
            if (loadingButton) {
                loadingButton.disabled = false;
                loadingButton.innerHTML = '<i class="fas fa-file-pdf me-2"></i>Exportar PDF';
            }
        }
    };

    //Función para calcular el porcentaje de avance de un proceso
    const calcularPorcentajeAvance = (cantidadTerminada, cantidadPedido) => {
        if (!cantidadPedido || cantidadPedido === 0) return 0;
        return Math.round((cantidadTerminada / cantidadPedido) * 100);
    };

    //Función para obtener el programa asignado (si está disponible en los datos)
    const getProgramaAsignado = () => {
        // Buscar en los datos si viene información del programa
        if (orderData.programa) {
            return orderData.programa;
        }
        // Si no viene en los datos, podriamos hacer una consulta adicional o mostrar "No asignado"
        return null;
    }

    return (
        <Modal 
            show={show} 
            onHide={onHide} 
            size="lg" 
            className="order-detail-modal"
            animation={true}
            transition={true}
            backdropTransition={true}
        >
            <div id="modal-content">
                <Modal.Header closeButton className="border-bottom-0">
                    <Modal.Title className="d-flex align-items-center">
                        <span className="order-number">OT #{orderData.codigo_ot}</span>
                        <Badge bg={orderData.situacion_ot?.codigo_situacion_ot === 'P' ? 'warning' : 'info'} className="ms-3">
                            {orderData.situacion_ot?.descripcion}
                        </Badge>
                    </Modal.Title>
                </Modal.Header>
                
                <Modal.Body className="px-4">
                    {/* Información General Expandida*/}
                    <div className="info-section mb-4">
                        <h5 className="section-title">
                            <FaList className="me-2" />
                            Información General
                        </h5>
                        <div className="info-grid-expanded">
                            <div className="info-item">
                                <label>Descripción</label>
                                <p>{orderData.descripcion_producto_ot}</p>
                            </div>
                            <div className="info-item">
                                <label>Cliente</label>
                                <p>{orderData.cliente?.nombre || 'No especificado'}</p>
                            </div>
                            <div className="info-item">
                                <label>Nota Venta</label>
                                <p>{orderData.nro_nota_venta_ot} - Item: {orderData.item_nota_venta}</p>
                            </div>
                            <div className="info-item">
                                <label>
                                    <FaCodeBranch className="me-1" />
                                    Código Producto Inicial
                                </label>
                                <p>{orderData.codigo_producto_inicial || 'No especificado'}</p>
                            </div>
                            <div className="info-item">
                                <label>
                                    <FaCogs className="me-1" />
                                    Código Producto Salida
                                </label>
                                <p>{orderData.codigo_producto_salida || 'No especificado'}</p>
                            </div>
                            <div className="info-item">
                                <label>
                                    <FaTools className="me-1" />
                                    Materia Prima
                                </label>
                                <p>{orderData.materia_prima?.codigo + '-' + orderData.materia_prima?.nombre || 'No especificado'}</p>
                            </div>
                        </div>
                    </div>

                    <div className="dates-program-section mb-4">
                        <h5 className="section-title">
                            <FaCalendarAlt className="me-2" />
                            Fechas y Asignación
                        </h5>
                        <div className="dates-grid">
                            <div className="date-item">
                                <label>Fecha Emisión</label>
                                <p>{orderData.fecha_emision_formated || 'No definida'}</p>
                            </div>
                            <div className="date-item">
                                <label>Fecha Proceso</label>
                                <p>{orderData.fecha_proc_formated || 'No definida'}</p>
                            </div>
                            <div className="date-item">
                                <label>Fecha Término</label>
                                <p>{orderData.fecha_termino_formated || 'No definida'}</p>
                            </div>
                            <div className="date-item">
                                <label>
                                    <FaUser className="me-1" />
                                    Programa Asignado
                                </label>
                                <p>
                                    {getProgramaAsignado() ?
                                        <Badge bg="success">{getProgramaAsignado().nombre}</Badge> :
                                        <Badge bg="secondary">No Asignado</Badge>
                                    }
                                </p>
                            </div>
                        </div>
                    </div>


                    {/* Progreso y Cantidades */}
                    <div className="progress-section mb-4">
                        <h5 className="section-title">
                            <FaCheckCircle className="me-2" />
                            Progreso de Producción
                        </h5>
                        <div className="progress custom-progress mb-3">
                            <div 
                                className="progress-bar" 
                                style={{ width: `${(orderData.cantidad_avance / orderData.cantidad) * 100}%` }}
                            >
                                {Math.round((orderData.cantidad_avance / orderData.cantidad) * 100)}%
                            </div>
                        </div>
                        <div className="quantities-grid">
                            <div className="quantity-item">
                                <span className="quantity-label">Cantidad Total</span>
                                <span className="quantity-value">{orderData.cantidad}</span>
                            </div>
                            <div className="quantity-item">
                                <span className="quantity-label">Avance</span>
                                <span className="quantity-value">{orderData.cantidad_avance}</span>
                            </div>
                            <div className="quantity-item">
                                <span className="quantity-label">
                                    <FaWeight className="me-1" />
                                    Peso Unitario
                                </span>
                                <span className="quantity-value">{orderData.peso_unitario} kg</span>
                            </div>
                            <div className="quantity-item">
                                <span className="quantity-label">Cantidad M. Prima</span>
                                <span className="quantity-value">{orderData.cantidad_mprima || 0}</span>
                            </div>
                        </div>
                    </div>

                    {/* Ruta de Procesos */}
                    <div className="route-section">
                        <h5 className="section-title">
                            <FaCogs className="me-2" />
                            Ruta de Procesos
                        </h5>
                        <div className="process-timeline-improved">
                            {orderData.ruta_ot?.items.map((item, index) => {
                                const porcentajeAvance = calcularPorcentajeAvance(
                                    item.cantidad_terminado_proceso,
                                    item.cantidad_pedido
                                );
                                return (
                                
                                    <div key={item.item} className="process-item">
                                        <div className="process-number">{item.item}</div>
                                        <div className="process-content-improved">
                                            <div className="process-header">
                                                <h6>{item.proceso.descripcion}</h6>
                                                <Badge
                                                    bg={porcentajeAvance === 100 ? 'success' : 
                                                        porcentajeAvance > 0 ? 'warning' : 'secondary'}
                                                    className='process-status'
                                                >{porcentajeAvance}%</Badge>
                                            </div>
                                            <div className="mini-progress mb-2">
                                                <ProgressBar 
                                                    now={porcentajeAvance}
                                                    variant={porcentajeAvance === 100 ? 'success':
                                                        porcentajeAvance > 0 ? 'warning' : 'secondary'
                                                    }
                                                    size="sm"
                                                />
                                            </div>
                                            <div className="process-details-improved">
                                                <div className="detail-row">
                                                    <span className="machine">
                                                        <FaIndustry className="icon" />
                                                        {item.maquina.descripcion}
                                                    </span>
                                                    <span className="standard">
                                                        <FaClock className="icon" />
                                                        {item.estandar} u/hr
                                                    </span>
                                                </div>
                                                <div className="detail-row">
                                                    <span className="progress-detail">
                                                        <FaCheckCircle className="icon" />
                                                        {item.cantidad_terminado_proceso}/{item.cantidad_pedido}
                                                    </span>
                                                    {item.cantidad_perdida_proceso > 0 && (
                                                        <span className="loss">
                                                            <span className="icon">⚠️</span>
                                                            Perdida: {item.cantidad_perdida_proceso}
                                                        </span>
                                                    )}
    
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </Modal.Body>
            </div>

            <Modal.Footer className="border-top-0">
                <Button 
                    id="export-button"
                    variant="primary" 
                    onClick={exportToPDF}
                >
                    <FaFilePdf className="me-2" />
                    Exportar PDF
                </Button>
                <Button variant="secondary" onClick={onHide}>
                    Cerrar
                </Button>
            </Modal.Footer>
        </Modal>
    );
}