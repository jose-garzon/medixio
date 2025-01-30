import { useMutation } from "@tanstack/react-query";
import { updateAppointment } from "./indexedDBRepository";

export function useUpdateAppointment() {
  return useMutation({
    mutationFn: updateAppointment,
  });
}
