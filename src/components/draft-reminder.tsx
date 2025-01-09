import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CalendarPlus } from "lucide-react";

interface DraftAppointment {
  id: string;
  doctorName: string;
  specialty: string;
  date: string | null;
}

interface DraftReminderProps {
  draftAppointments: DraftAppointment[];
}

export default function DraftReminder({
  draftAppointments,
}: DraftReminderProps) {
  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle>Draft Appointments</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {draftAppointments.map((appointment) => (
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
                {appointment.date ? (
                  <p className="text-sm">{appointment.date}</p>
                ) : (
                  <Badge variant="outline">No date set</Badge>
                )}
                <Button size="sm">
                  <CalendarPlus className="mr-2 h-4 w-4" />
                  Schedule
                </Button>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
