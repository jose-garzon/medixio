import { deleteAppointment } from "@/services/db/store";
import { useMutation } from "@tanstack/react-query";

export function useDeleteAppointment() {
  return useMutation({
    mutationFn: deleteAppointment,
  });
}
