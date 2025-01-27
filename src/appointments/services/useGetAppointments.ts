import { getAppointments } from "@/services/db/store";
import { useQuery } from "@tanstack/react-query";
import { Appointment, GetAppointmentVariables } from "../types";

interface UseGetAppointmentsParams {
  filter: GetAppointmentVariables;
}

const useGetAppointments = (params?: UseGetAppointmentsParams) => {
  return useQuery<Appointment[]>({
    queryKey: ["appointments", params],
    queryFn: () => getAppointments(params?.filter),
  });
};

export default useGetAppointments;
