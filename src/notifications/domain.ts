import { addHours, subDays, subMinutes } from "date-fns";

interface SchduleNotificationsParams {
  id: string;
  date: string;
}
export interface NotificationsAPI {
  scheduleNotifications: (params: SchduleNotificationsParams) => Promise<void>;
}

export function getNotificationsSetup(date: Date) {
  return [
    {
      time: subDays(date, 1),
      message: "📅 Tu cita es mañana",
    },
    {
      time: subMinutes(date, 30),
      message: "⌛ Tu cita es en 30 minutos",
    },
    {
      time: addHours(date, 1),
      message: "⭐ ¿Cómo te fue en la cita?",
    },
  ];
}
