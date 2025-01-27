import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  CalendarIcon,
  ClockIcon,
  AlertCircleIcon,
  TriangleAlertIcon,
} from "lucide-react";
import useGetAppointments from "../services/useGetAppointments";

interface StatCardProps {
  title: string;
  icon: React.ElementType;
  value: number;
}

function StatCard({ title, icon: Icon, value }: StatCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent className="flex items-center gap-4">
        <Icon className="h-5 w-5 text-muted-foreground" />
        <div className="text-2xl font-bold">{value}</div>
      </CardContent>
    </Card>
  );
}

export default function Stats() {
  const { data: appointments } = useGetAppointments();
  const upcoming =
    appointments?.filter((appt) => appt.status === "active").length ?? 0;
  const lost =
    appointments?.filter((appt) => appt.status === "lost").length ?? 0;
  const draft =
    appointments?.filter((appt) => appt.status === "draft").length ?? 0;
  return (
    <div className="grid grid-cols-2 gap-3">
      <StatCard
        title="Total"
        icon={CalendarIcon}
        value={appointments?.length ?? 0}
      />
      <StatCard title="Siguientes" icon={ClockIcon} value={upcoming} />
      <StatCard title="Perdidas" icon={AlertCircleIcon} value={lost} />
      <StatCard title="por agendar" icon={TriangleAlertIcon} value={draft} />
    </div>
  );
}
