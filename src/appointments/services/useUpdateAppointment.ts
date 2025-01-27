import { updateAppointment } from "@/services/db/store";
import { useMutation } from "@tanstack/react-query";

export function useUpdateAppointment() {
  return useMutation({
    mutationFn: updateAppointment,
  });
}
