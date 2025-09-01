import { useEffect, useState, useCallback, useMemo } from "react";
import { getAllClients } from '../../api/clients.api';
import CompNavbar from '../Navbar/CompNavbar.jsx';
import { Footer } from "../Footer/Footer.jsx";
import { Table, Card, InputGroup, Form } from "react-bootstrap";
import { FaSearch, FaCheck, FaTimes } from "react-icons/fa";
import { LoadingSpinner } from "../UI/LoadingSpinner/LoadingSpinner.jsx";
import { debounce } from 'lodash';

export function ClientList() {
    const [clients, setClients] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState("");
    const [filterVip, setFilterVip] = useState(false);

    useEffect(() => {
    const fetchClients = async () => {
            try {
            setLoading(true);
            const response = await getAllClients();
                setClients(response.data || []);
        } catch (error) {
                console.error("Error al cargar clientes:", error);
        } finally {
            setLoading(false);
        }
    };

        fetchClients();
    }, []);

    const debouncedSearch = useCallback(
        debounce((value) => {
            setSearchTerm(value);
        }, 300),
        []
    );

    const handleSearchChange = useCallback((e) => {
        const { value } = e.target;
        e.target.value = value;
        debouncedSearch(value);
    }, [debouncedSearch]);

    const filteredClients = useMemo(() => {
        if (!searchTerm && !filterVip) return clients;
        
        const searchLower = searchTerm.toLowerCase();
        return clients.filter(client => {
            const matchesSearch = searchTerm ? (
                (client.codigo_cliente?.toString() || "").toLowerCase().includes(searchLower) || 
                (client.nombre || "").toLowerCase().includes(searchLower) ||
                (client.apodo || "").toLowerCase().includes(searchLower)
            ) : true;

            const matchesVip = filterVip ? client.vip : true;
            return matchesSearch && matchesVip;
        });
    }, [clients, searchTerm, filterVip]);

    if (loading) {
        return (
            <div>
                <CompNavbar />
                <div className="container d-flex justify-content-center align-items-center" style={{ minHeight: "50vh" }}>
                    <LoadingSpinner message="Cargando clientes..." />
                </div>
                <Footer />
            </div>
        );
    }

    return (
        <div>
            <CompNavbar />
            <div className="container">
                <h2 className="text-start my-4">Clientes</h2>
                
                    <Card className="mb-4 shadow-sm">
                    <Card.Body>
                        <div className="row g-3">
                            <div className="col-md-6">
                                <InputGroup>
                                    <InputGroup.Text>
                                        <FaSearch />
                                    </InputGroup.Text>
                                    <Form.Control
                                        placeholder="Buscar cliente..."
                                        onChange={handleSearchChange}
                                        defaultValue={searchTerm}
                                    />
                                </InputGroup>
                            </div>
                            <div className="col-md-6">
                                <Form.Check
                                    type="checkbox"
                                    label="Solo clientes VIP"
                                    checked={filterVip}
                                    onChange={(e) => setFilterVip(e.target.checked)}
                                />
                            </div>
                        </div>
                    </Card.Body>
                    </Card>
                
                {filteredClients.length > 0 ? (
                    <div className="table-responsive">
                    <Table striped bordered hover>
                            <thead>
                                <tr>
                            <th>Código Cliente</th>
                            <th>Nombre</th>
                                    <th className="text-center">¿VIP?</th>
                            <th>Apodo</th>
                                </tr>
                        </thead>
                            <tbody>
                                {filteredClients.map((client) => (
                                    <tr key={client.id || client.codigo_cliente}>
                                    <td>{client.codigo_cliente}</td>
                                    <td>{client.nombre}</td>
                                        <td className="text-center">
                                            {client.vip ? <FaCheck className="text-success" /> : <FaTimes className="text-danger" />}
                                        </td>
                                    <td>{client.apodo}</td>
                                </tr>
                            ))}
                        </tbody>
                    </Table>
                </div>
                ) : (
                    <div className="alert alert-info">
                        No se encontraron clientes que coincidan con tu búsqueda.
                    </div>
                )}
            </div>
            <Footer />
        </div>
    );
}