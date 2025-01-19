import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CalendarPlus } from "lucide-react";
import { NoDraftAppointments } from "./no-appointments";
import useGetAppointments from "../services/useGetAppointments";
import { DraftReminderLoader } from "./skeletonAppointmentCard";

export default function DraftReminder() {
  const { data: appointments, isLoading } = useGetAppointments({
    filter: {
      status: "draft",
    },
  });
  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle>Citas por agendar</CardTitle>
      </CardHeader>
      <CardContent>
        <DraftReminderLoader isLoading={Boolean(isLoading || !appointments)}>
          {appointments?.length === 0 ? (
            <NoDraftAppointments />
          ) : (
            <div className="space-y-4">
              {appointments?.map((appointment) => (
                <div
                  key={appointment.id}
                  className="flex items-center justify-between"
                >
                  <div>
                    <p className="font-medium">{appointment.doctorName}</p>
                    <p className="text-sm text-muted-foreground">
                      {appointment.specialty}
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button size="icon">
                      <CalendarPlus />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </DraftReminderLoader>
      </CardContent>
    </Card>
  );
}
