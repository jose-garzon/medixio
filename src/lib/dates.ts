import { format } from "date-fns";
import { es } from "date-fns/locale";

export function formatDate(date: Date) {
  return format(date, "eeee dd MMMM", { locale: es });
}
