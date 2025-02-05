import { useMutation } from "@tanstack/react-query";
import { createAppointment } from "./appointmentsRepository";

export function useCreateNewAppointment() {
  return useMutation({
    mutationFn: createAppointment,
  });
}
