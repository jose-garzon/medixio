import { useMutation } from "@tanstack/react-query";
import { deleteAppointment } from "./indexedDBRepository";

export function useDeleteAppointment() {
  return useMutation({
    mutationFn: deleteAppointment,
  });
}
