import { createAppointment } from "@/services/db/store";
import { useMutation } from "@tanstack/react-query";

export function useCreateNewAppointment() {
  return useMutation({
    mutationFn: createAppointment,
  });
}
