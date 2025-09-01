import moment from 'moment';

export const timelineHelpers = {
    // Configuración de horario laboral
    HORARIO_TRABAJO: {
        inicio: { hora: 7, minuto: 45 }, // 7:45AM
        fin: { hora: 17, minuto: 45 }
    },

    // Obtener rango de tiempo visible por defecto
    getDefaultTimeRange: () => {
        const now = moment();
        return {
            start: now.clone().startOf('day').add(timelineHelpers.HORARIO_TRABAJO.inicio.hora, 'hours').add(timelineHelpers.HORARIO_TRABAJO.inicio.minuto, 'minutes'),
            end: now.clone().endOf('day').add(timelineHelpers.HORARIO_TRABAJO.fin.hora).hours(timelineHelpers.HORARIO_TRABAJO.fin.hora).minutes(timelineHelpers.HORARIO_TRABAJO.fin.minuto)
        };
    },

    // Ajustar fecha a horario laboral
    ajustarAHorarioLaboral: (fecha) => {
        const fechaAjustada = moment(fecha);
        const hora = fechaAjustada.hours();
        const minuto = fechaAjustada.minutes();

        if (hora < timelineHelpers.HORARIO_TRABAJO.inicio.hora || (hora===timelineHelpers.HORARIO_TRABAJO.inicio.hora && 
            minuto < timelineHelpers.HORARIO_TRABAJO.inicio.minuto)) {
                fechaAjustada.hours(timelineHelpers.HORARIO_TRABAJO.inicio.hora).
                    minutes(timelineHelpers.HORARIO_TRABAJO.inicio.minuto);
        } else if (hora > timelineHelpers.HORARIO_TRABAJO.fin.hora || (hora ===timelineHelpers.HORARIO_TRABAJO.fin.hora && 
            minuto > timelineHelpers.HORARIO_TRABAJO.fin.minuto)){
                fechaAjustada.hours(timelineHelpers.HORARIO_TRABAJO.fin.hora).
                minutes(timelineHelpers.HORARIO_TRABAJO.fin.minuto);
        }

        return fechaAjustada;
    },

    // Expandir items que cruzan múltiples días
    expandMultiDayItems: (items) => {
        return items.flatMap(item => {
            const startTime = moment(item.start_time);
            const endTime = moment(item.end_time);
            const daysDiff = endTime.diff(startTime, 'days');

            if (daysDiff < 1) return [item];

            const expandedItems = [];
            for (let i = 0; i <= daysDiff; i++){
                const currentStart = i === 0 ? startTime :
                    moment(startTime).add(i, 'days').
                        hours(timelineHelpers.HORARIO_TRABAJO.inicio.hora).
                        minutes(timelineHelpers.HORARIO_TRABAJO.inicio.minuto);

                const currentEnd = i === daysDiff ? endTime :
                    moment(startTime).add(i, 'days').
                        hours(timelineHelpers.HORARIO_TRABAJO.fin.hora).
                        minutes(timelineHelpers.HORARIO_TRABAJO.fin.minuto);

                expandedItems.push({
                    ...item,
                    id: `${item.id}-${i}`,
                    start_time: currentStart,
                    end_time: currentEnd,
                    itemProps: {
                        ...item.itemProps,
                        style: {
                            ...item.itemProps?.style,
                            borderStyle: i === 0 ? 'solid' : 'dashed'
                        }
                    }
                });
            }
            return expandedItems;
        });
    },

    // Calcular duración en horas laborales
    calcularHorasLaborales: (start, end) => {
        const startTime = moment(inicio);
        const endTime = moment(fin);
        let horasTotales = 0;

        while (startTime.isBefore(endTime)){
            if (startTime.hours() >= timelineHelpers.HORARIO_TRABAJO.inicio.hora && 
                startTime.hours() < timelineHelpers.HORARIO_TRABAJO.fin.hora){
                    horasTotales++;
            }
            startTime.add(1, 'hour');
        }
        return horasTotales;
    }
};

export default timelineHelpers;