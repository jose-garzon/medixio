import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PhoneIcon as WhatsappIcon } from "lucide-react";
import { AppointmentDrawer } from "./appointment-drawer";
import { useState } from "react";
import { Appointment } from "@/services/appointments/types";
import { StatusBadge } from "./status-badge";
import { formatDate } from "@/lib/dates";
import { NoAppointments } from "./no-appointments";

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
    address: "Clinica san diego",
    phoneNumber: "+57 3004486873",
    notes: "Llevar examenes",
  },
  {
    id: "2",
    doctorName: "Dr. Jane Smith",
    specialty: "Neurologist",
    date: "2023-06-20",
    time: "2:00 PM",
    status: "Draft",
    address: "Clinica san diego",
    phoneNumber: "+57 3004486873",
    notes: "Llevar examenes",
  },
  {
    id: "4",
    doctorName: "Dr. Saibi",
    specialty: "Reumatologo",
    date: "2023-06-20",
    time: "2:00 PM",
    status: "Active",
    address: "Clinica Foscal",
    phoneNumber: "+57 3004486873",
    notes: "Llevar examenes",
  },
  {
    id: "3",
    doctorName: "Dr. Mike Johnson",
    specialty: "Oncologist",
    date: "2023-05-10",
    time: "11:30 AM",
    status: "Done",
    address: "Clinica san diego",
    phoneNumber: "+57 3004486873",
    notes: "Llevar examenes",
  },
];

export default function AppointmentList({ type }: AppointmentListProps) {
  const [selectedAppointment, setSelectedAppointment] =
    useState<Appointment | null>(null);

  const openDrawer = (appointment: Appointment) => {
    setSelectedAppointment(appointment);
  };

  const closeDrawer = () => {
    setSelectedAppointment(null);
  };

  const appointments = mockAppointments.filter((appointment) =>
    type === "active"
      ? ["Active", "Draft"].includes(appointment.status)
      : ["Done", "Outdated"].includes(appointment.status)
  );

  return (
    <>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {appointments.length === 0 ? (
          <NoAppointments className="md:col-span-2 lg:col-span-3 h-full" />
        ) : (
          appointments.map((appointment) => (
            <Card key={appointment.id} className="justify-between">
              <CardHeader>
                <CardTitle>{appointment.doctorName}</CardTitle>
                <CardDescription>{appointment.specialty}</CardDescription>
              </CardHeader>
              <CardContent>
                <p>
                  <strong>Fecha:</strong>{" "}
                  {formatDate(new Date(appointment.date))}
                </p>
                <p>
                  <strong>Hora:</strong> {appointment.time}
                </p>
                <StatusBadge status={appointment.status} />
              </CardContent>
              <CardFooter className="flex lg:flex-col xl:flex-row justify-end gap-4">
                <Button
                  variant="outline"
                  className="lg:w-full"
                  onClick={() => openDrawer(appointment)}
                >
                  Detalles
                </Button>
                <Button className="lg:w-full">
                  <WhatsappIcon className="mr-2 h-4 w-4" /> WhatsApp
                </Button>
              </CardFooter>
            </Card>
          ))
        )}
      </div>
      <AppointmentDrawer
        appointment={selectedAppointment}
        onClose={closeDrawer}
      />
    </>
  );
}
