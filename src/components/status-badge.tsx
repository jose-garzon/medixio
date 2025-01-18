import { AppointmentStatus } from "@/appointments/types";
import { Badge, BadgeProps } from "./ui/badge";

interface StatusBadgeProps {
  status: AppointmentStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const labelMap = {
    draft: "Por agendar",
    active: "Agendada",
    lost: "Perdida",
    done: "Pasada",
  };
  const variantMap: Record<AppointmentStatus, BadgeProps["variant"]> = {
    draft: "secondary",
    active: "default",
    lost: "destructive",
    done: "outline",
  };
  return (
    <Badge variant={variantMap[status] ?? variantMap.draft}>
      {labelMap[status] ?? labelMap.draft}
    </Badge>
  );
}
