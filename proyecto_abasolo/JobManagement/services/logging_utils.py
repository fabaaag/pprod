import logging
import os

# ✅ Variable global para evitar configuración múltiple
_loggers_configured = False

def setup_logging():
    global _loggers_configured
    
    # ✅ Solo configurar una vez
    if _loggers_configured:
        return get_existing_loggers()
    
    # Crear directorio de log si no existe
    log_dir = "logs_jm"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configurar diferentes loggers para diferentes propósitos
    loggers_config = {
        'planificacion': {
            'file': 'planificacion.log',
            'level': logging.INFO,
            'format': '%(asctime)s [%(levelname)s] %(message)s'
        },
        'tareas': {
            'file': 'tareas.log',
            'level': logging.INFO,
            'format': '%(asctime)s [%(levelname)s] %(message)s'
        },
        'timeline': {
            'file': 'timeline.log',
            'level': logging.INFO,
            'format': '%(asctime)s [%(levelname)s] %(message)s'
        },
        'scheduler': {
            'file': 'scheduler.log',
            'level': logging.DEBUG,
            'format': '%(asctime)s [%(levelname)s] %(message)s'
        }
    }
    
    for name, config in loggers_config.items():
        logger = logging.getLogger(name)
        
        # ✅ Limpiar handlers existentes
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        
        logger.setLevel(config['level'])
        
        file_handler = logging.FileHandler(
            os.path.join(log_dir, config['file']),
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(config['format']))
        logger.addHandler(file_handler)

    _loggers_configured = True
    return loggers_config

def get_existing_loggers():
    """Retorna los loggers ya configurados sin crear nuevos handlers"""
    return {
        'planificacion': logging.getLogger('planificacion'),
        'tareas': logging.getLogger('tareas'),
        'timeline': logging.getLogger('timeline'),
        'scheduler': logging.getLogger('scheduler')
    }