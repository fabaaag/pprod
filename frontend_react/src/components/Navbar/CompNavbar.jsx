import { Link, NavLink, useNavigate } from 'react-router-dom'
import './Navbar.css'
import logavsa from './img/logavsa.png'
import { Nav, Navbar, NavDropdown, Container } from 'react-bootstrap';
import React from 'react';
import { logout } from '../../api/auth.api';
import { toast } from 'react-hot-toast';
import { FaIndustry, FaTools, FaUsers, FaCogs, FaUserCircle } from 'react-icons/fa';
import { motion } from 'framer-motion';

const CompNavbar = () => {
    const navigate = useNavigate();
    const user = JSON.parse(localStorage.getItem('user'));

    const handleLogout = () => {
        logout();
        toast.success('Sesión cerrada correctamente');
        navigate('/login');
    };

    return (
        <Navbar variant='dark' bg='dark' expand='lg' className="navbar-custom sticky-top">
            <Container>
                <motion.div
                    whileHover={{ scale: 1.05 }}
                    transition={{ type: "spring", stiffness: 400, damping: 10 }}
                >
                    <Navbar.Brand href="/" className="brand-container">
                        <img 
                            src={logavsa} 
                            alt="logo" 
                            className="brand-logo"
                        />
                        <span className='brand-text'>Abasolo Vallejo</span>
                    </Navbar.Brand>
                </motion.div>

                <Navbar.Toggle aria-controls="navbar-dark-example"/>
                <Navbar.Collapse id="navbar-dark">
                    <Nav className="me-auto nav-links">
                        <NavDropdown
                            title={
                                <span className="nav-dropdown-title">
                                    <FaIndustry className="nav-icon" />
                                    <span>Maestro Materiales</span>
                                </span>
                            }
                            menuVariant='dark'
                            className="custom-dropdown"
                        >
                            <NavDropdown.Item href="/productos">Productos</NavDropdown.Item>
                            <NavDropdown.Divider />
                            <NavDropdown.Item href="/piezas">Piezas</NavDropdown.Item>
                        </NavDropdown>

                        <NavDropdown
                            title={
                                <span className="nav-dropdown-title">
                                    <FaTools className="nav-icon" />
                                    <span>Planificación Producción</span>
                                </span>
                            }
                            menuVariant='dark'
                            className="custom-dropdown"
                        >
                            <NavDropdown.Item href="/orders">Órdenes de Trabajo</NavDropdown.Item>
                            <NavDropdown.Divider />
                            <NavDropdown.Item href="/programs">
                                📋 Programas de Producción
                            </NavDropdown.Item>
                            <NavDropdown.Divider />
                            <NavDropdown.Item href="/operators">Gestión de Operarios</NavDropdown.Item>
                            
                            {user?.rol === 'ADMIN' && (
                                <>  
                                    <NavDropdown.Divider /> 
                                    <NavDropdown.Item href="/dashboard-ejecutivo">📊 Dashboard Ejecutivo</NavDropdown.Item>
                                    <NavDropdown.Divider /> 
                                    <NavDropdown.Item href="/produccion-form">📈 Formulario de Producción</NavDropdown.Item>
                                </>)}
                        </NavDropdown>

                        {/* Menú experimental eliminado */}
                        {user?.rol === 'ADMIN' && (
                            <>
                                <NavDropdown
                                    title={
                                        <span className="nav-dropdown-title">
                                            <FaCogs className="nav-icon" />
                                            <span>Gestión de Máquinas</span>
                                        </span>
                                    }
                                    menuVariant='dark'
                                    className="custom-dropdown"
                                >
                                    <NavDropdown.Item href="/machines">Listado de Máquinas</NavDropdown.Item>
                                    <NavDropdown.Divider />
                                    <NavDropdown.Item href="">Evento Mantención</NavDropdown.Item> 
                                </NavDropdown>
                            </>
                        )}
                        
                    </Nav>

                    <Nav>
                        <NavDropdown
                            title={
                                <span className="nav-dropdown-title user-dropdown">
                                    <FaUserCircle className="nav-icon" />
                                    <span>{user ? `${user.first_name || user.username}` : 'Usuario'}</span>
                                </span>
                            }
                            id='user-dropdown'
                            align='end'
                            menuVariant='dark'
                            className="custom-dropdown"
                        >
                            <NavDropdown.Item onClick={() => navigate('/profile')}>Mi Perfil</NavDropdown.Item>
                            <NavDropdown.Divider />
                            <NavDropdown.Item onClick={handleLogout}>Cerrar Sesión</NavDropdown.Item>
                            {user?.rol === 'ADMIN' && (
                                <>
                                    <NavDropdown.Divider />
                                    <NavDropdown.Item onClick={() => navigate('/users/manage')}>
                                        Gestión de Usuarios
                                    </NavDropdown.Item>
                                </>
                            )}
                            <NavDropdown.Divider />
                            <NavDropdown.Item onClick={() => navigate('/clients')}>Clientes</NavDropdown.Item>
                        </NavDropdown>
                    </Nav>
                </Navbar.Collapse>
            </Container>
        </Navbar>
    );
};

export default CompNavbar;
