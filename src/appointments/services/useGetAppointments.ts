import { getAppointments } from "@/services/db/store";
import { useQuery } from "@tanstack/react-query";
import { Appointment } from "../types";

interface UseGetAppointmentsParams {
  type: "active" | "past";
}

const useGetAppointments = (params: UseGetAppointmentsParams) => {
  return useQuery<Appointment[]>({
    queryKey: ["appointments"],
    queryFn: () => getAppointments(params.type),
  });
};

export default useGetAppointments;
