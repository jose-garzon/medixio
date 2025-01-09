import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PhoneIcon as WhatsappIcon } from "lucide-react";

type AppointmentStatus = "Draft" | "Active" | "Outdated" | "Done";

interface Appointment {
  id: string;
  doctorName: string;
  specialty: string;
  date: string;
  time: string;
  status: AppointmentStatus;
}

interface AppointmentListProps {
  type: "active" | "past";
}

const mockAppointments: Appointment[] = [
  {
    id: "1",
    doctorName: "Dr. John Doe",
    specialty: "Cardiologist",
    date: "2023-06-15",
    time: "10:00 AM",
    status: "Active",
  },
  {
    id: "2",
    doctorName: "Dr. Jane Smith",
    specialty: "Neurologist",
    date: "2023-06-20",
    time: "2:00 PM",
    status: "Draft",
  },
  {
    id: "3",
    doctorName: "Dr. Mike Johnson",
    specialty: "Oncologist",
    date: "2023-05-10",
    time: "11:30 AM",
    status: "Done",
  },
];

export default function AppointmentList({ type }: AppointmentListProps) {
  const appointments = mockAppointments.filter((appointment) =>
    type === "active"
      ? ["Active", "Draft"].includes(appointment.status)
      : ["Done", "Outdated"].includes(appointment.status)
  );

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {appointments.map((appointment) => (
        <Card key={appointment.id}>
          <CardHeader>
            <CardTitle>{appointment.doctorName}</CardTitle>
            <CardDescription>{appointment.specialty}</CardDescription>
          </CardHeader>
          <CardContent>
            <p>Date: {appointment.date}</p>
            <p>Time: {appointment.time}</p>
            <Badge
              className="mt-2"
              variant={
                appointment.status === "Active" ? "default" : "secondary"
              }
            >
              {appointment.status}
            </Badge>
          </CardContent>
          <CardFooter className="flex justify-between">
            <Button variant="outline">View Details</Button>
            <Button>
              <WhatsappIcon className="mr-2 h-4 w-4" /> WhatsApp
            </Button>
          </CardFooter>
        </Card>
      ))}
    </div>
  );
}
