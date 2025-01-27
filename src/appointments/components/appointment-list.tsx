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
import { Appointment } from "@/appointments/types";
import { StatusBadge } from "../../components/status-badge";
import { convertTo12HourFormat, formatDate } from "@/lib/dates";
import { DaysToDate } from "../../components/DaysToDate";
import { NoAppointments } from "./no-appointments";
import useGetAppointments from "../services/useGetAppointments";
import { AppointmentListLoader } from "./skeletonAppointmentCard";
import { openWhatsAppConversation } from "@/notifications/services/whatsappMessage";
import { QuickSchedule } from "./quick-schedule";

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

  const { data: appointments, isLoading } = useGetAppointments({
    filter: {
      status: type === "active" ? ["active", "draft"] : ["lost", "done"],
    },
  });

  return (
    <>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <AppointmentListLoader isLoading={Boolean(isLoading || !appointments)}>
          {appointments?.length === 0 ? (
            <NoAppointments className="md:col-span-2 lg:col-span-3 h-full" />
          ) : (
            appointments?.map((appointment) => (
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
                  {appointment.date && appointment.time ? (
                    <>
                      <div>
                        <p>
                          <strong>Fecha: </strong>
                          {formatDate(new Date(appointment.date))}
                        </p>
                        <p>
                          <strong>Hora:</strong>
                          {convertTo12HourFormat(appointment.time)}
                        </p>
                      </div>
                      <DaysToDate
                        appointmentDate={new Date(appointment.date)}
                      />
                    </>
                  ) : (
                    <QuickSchedule id={appointment.id} />
                  )}
                </CardContent>
                <CardFooter className="flex lg:flex-col xl:flex-row justify-end gap-4">
                  <Button
                    variant="outline"
                    className="lg:w-full"
                    onClick={() => openDrawer(appointment)}
                  >
                    Detalles
                  </Button>
                  <Button
                    className="lg:w-full"
                    onClick={() => openWhatsAppConversation(appointment)}
                  >
                    <WhatsappIcon className="mr-2 h-4 w-4" /> WhatsApp
                  </Button>
                </CardFooter>
              </Card>
            ))
          )}
        </AppointmentListLoader>
      </div>
      <AppointmentDrawer
        appointment={selectedAppointment}
        onClose={closeDrawer}
      />
    </>
  );
}
