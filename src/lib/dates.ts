import { format } from "date-fns";
import { es } from "date-fns/locale";

export function formatDate(date: Date) {
  return format(date, "eeee dd MMMM", { locale: es });
}

export function convertTo24Hour(hour: string, minute: string, period: string) {
  let h = parseInt(hour);
  if (period === "PM" && h !== 12) h += 12;
  if (period === "AM" && h === 12) h = 0;
  return `${h.toString().padStart(2, "0")}:${minute}`;
}

export function convertTo12Hour(value: string) {
  if (!value) return { hour: "12", minute: "00", period: "AM" };

  const [h, m] = value?.split(":") || ["12", "00"];
  let hour = parseInt(h);
  let period = "AM";

  if (hour >= 12) {
    period = "PM";
    if (hour > 12) hour -= 12;
  }
  if (hour === 0) hour = 12;

  return {
    hour: hour.toString().padStart(2, "0"),
    minute: m,
    period,
  };
}

export function convertTo12HourFormat(time24: string): string {
  const [hour, minute] = time24.split(":").map(Number);
  const period = hour >= 12 ? "PM" : "AM";
  const hour12 = hour % 12 || 12;
  return `${hour12}:${minute.toString().padStart(2, "0")} ${period}`;
}
