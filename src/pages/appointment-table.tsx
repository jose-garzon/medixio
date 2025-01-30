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

export function AppointmentsTable() {
  const { data: appointments } = useGetAppointments();
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
        </TableBody>
      </Table>
    </div>
  );
}
