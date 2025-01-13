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
import { DaysToDate } from "./DaysToDate";
import { getAppointments } from "@/services/db/store";

interface AppointmentListProps {
  type: "active" | "past";
}

export default function AppointmentList({ type }: AppointmentListProps) {
  const [selectedAppointment, setSelectedAppointment] =
    useState<Appointment | null>(null);

  const openDrawer = (appointment: Appointment) => {
    setSelectedAppointment(appointment);
  };

  const closeDrawer = () => {
    setSelectedAppointment(null);
  };

  const appointments = getAppointments(type);

  return (
    <>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {appointments.length === 0 ? (
          <NoAppointments className="md:col-span-2 lg:col-span-3 h-full" />
        ) : (
          appointments.map((appointment) => (
            <Card key={appointment.id} className="justify-between">
              <CardHeader>
                <div className="flex flex-wrap justify-between items-start gap-2">
                  <div>
                    <CardTitle>{appointment.doctorName}</CardTitle>
                    <CardDescription>{appointment.specialty}</CardDescription>
                  </div>
                  <StatusBadge status={appointment.status} />
                </div>
              </CardHeader>
              <CardContent className="flex justify-between items-start">
                <div>
                  <p>
                    <strong>Fecha: </strong>
                    {formatDate(new Date(appointment.date))}
                  </p>
                  <p>
                    <strong>Hora:</strong> {appointment.time}
                  </p>
                </div>
                <DaysToDate appointmentDate={new Date(appointment.date)} />
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
