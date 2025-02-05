import { useMutation } from "@tanstack/react-query";
import { deleteAppointment } from "./appointmentsRepository";

export function useDeleteAppointment() {
  return useMutation({
    mutationFn: deleteAppointment,
  });
}
