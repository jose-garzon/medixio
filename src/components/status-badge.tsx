import { AppointmentStatus } from "@/services/appointments/types";
import { Badge, BadgeProps } from "./ui/badge";

interface StatusBadgeProps {
  status: AppointmentStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const labelMap = {
    Draft: "Por agendar",
    Active: "Agendada",
    Outdated: "Perdida",
    Done: "Pasada",
  };
  const variantMap: Record<AppointmentStatus, BadgeProps["variant"]> = {
    Draft: "secondary",
    Active: "default",
    Outdated: "destructive",
    Done: "outline",
  };
  return (
    <Badge className="mt-2" variant={variantMap[status] ?? variantMap.Draft}>
      {labelMap[status] ?? labelMap.Draft}
    </Badge>
  );
}
