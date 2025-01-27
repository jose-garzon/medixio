import { getAppointments } from "@/services/db/store";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Appointment, GetAppointmentVariables } from "../types";

export interface UseGetAppointmentsParams {
  filter: GetAppointmentVariables;
}
function createGetAppointmentsKey(params?: UseGetAppointmentsParams) {
  return ["appointments", params];
}
function useGetAppointments(params?: UseGetAppointmentsParams) {
  return useQuery<Appointment[]>({
    queryKey: createGetAppointmentsKey(params),
    queryFn: () => getAppointments(params?.filter),
  });
}

export function useOperateOverAppointments(params?: UseGetAppointmentsParams) {
  const client = useQueryClient();
  function refetchAppointments() {
    client.invalidateQueries({ queryKey: createGetAppointmentsKey(params) });
    client.invalidateQueries({
      queryKey: createGetAppointmentsKey({ filter: { status: "draft" } }),
    });
  }
  return { refetchAppointments };
}

export default useGetAppointments;
