import { useMutation } from "@tanstack/react-query";
import { updateAppointment } from "./appointmentsRepository";

export function useUpdateAppointment() {
  return useMutation({
    mutationFn: updateAppointment,
  });
}
