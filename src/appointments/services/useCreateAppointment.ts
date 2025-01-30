import { useMutation } from "@tanstack/react-query";
import { createAppointment } from "./indexedDBRepository";

export function useCreateNewAppointment() {
  return useMutation({
    mutationFn: createAppointment,
  });
}
