"use client";

import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { WhatsAppButton } from "@/notifications/components/whatsapp-button";
import useGetAppointments from "@/appointments/services/useGetAppointments";
import { AppointmentTableLoader } from "@/appointments/components/skeletonAppointmentCard";
import { CalendarXIcon, PlusCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "wouter";

export function AppointmentsTable() {
  const { data: appointments, isLoading } = useGetAppointments();
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Fecha</TableHead>
            <TableHead>Hora</TableHead>
            <TableHead>Nombre del doctor</TableHead>
            <TableHead>Especialidad</TableHead>
            <TableHead>Direccion</TableHead>
            <TableHead>Estado</TableHead>
            <TableHead>Agendar</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <AppointmentTableLoader isLoading={isLoading}>
            {appointments?.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center p-4">
                  <div className="flex flex-col justify-center items-center gap-1">
                    <CalendarXIcon className="h-8 w-8 text-muted-foreground" />
                    <p className="text-xl font-bold">
                      No hay citas disponibles
                    </p>
                    <p className=" text-muted-foreground">
                      Aún no tienes citas agendadas. Agrega una nueva desde el
                      formulario.
                    </p>
                    <Link to="/citas/nueva" className="mt-10">
                      <Button size="sm">
                        <PlusCircle className="mr-2 h-2 w-2" /> Nueva cita
                      </Button>
                    </Link>
                  </div>
                </TableCell>
              </TableRow>
            )}
            {appointments?.map((appointment) => (
              <TableRow key={appointment.id}>
                <TableCell>{appointment.date}</TableCell>
                <TableCell>{appointment.time}</TableCell>
                <TableCell>{appointment.doctorName}</TableCell>
                <TableCell>{appointment.specialty}</TableCell>
                <TableCell>{appointment.address}</TableCell>
                <TableCell>
                  <Badge
                    variant={
                      appointment.status === "active" ? "default" : "secondary"
                    }
                  >
                    {appointment.status}
                  </Badge>
                </TableCell>
                <TableCell>
                  <WhatsAppButton appointment={appointment} />
                </TableCell>
              </TableRow>
            ))}
          </AppointmentTableLoader>
        </TableBody>
      </Table>
    </div>
  );
}
