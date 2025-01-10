"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { PhoneIcon } from "lucide-react";
import { Appointment } from "@/services/appointments/types";

const appointments: Pick<
  Appointment,
  "id" | "date" | "time" | "doctorName" | "specialty" | "address" | "status"
>[] = [
  {
    id: "1",
    date: "2023-06-15",
    time: "10:00 AM",
    doctorName: "Dr. John Doe",
    specialty: "Cardiologist",
    address: "123 Heart St, Cardio City, CC 12345",
    status: "Active",
  },
  {
    id: "2",
    date: "2023-06-20",
    time: "2:00 PM",
    doctorName: "Dr. Jane Smith",
    specialty: "Neurologist",
    address: "456 Brain Ave, Neuro Town, NT 67890",
    status: "Draft",
  },
  {
    id: "3",
    date: "2023-05-10",
    time: "11:30 AM",
    doctorName: "Dr. Mike Johnson",
    specialty: "Oncologist",
    address: "789 Cell Rd, Onco Village, OV 13579",
    status: "Done",
  },
  {
    id: "4",
    date: "2023-07-05",
    time: "3:30 PM",
    doctorName: "Dr. Sarah Lee",
    specialty: "Pediatrician",
    address: "101 Kid Lane, Pedia City, PC 24680",
    status: "Active",
  },
  {
    id: "5",
    date: "2023-06-30",
    time: "9:00 AM",
    doctorName: "Dr. Robert Brown",
    specialty: "Dermatologist",
    address: "202 Skin Blvd, Derm Town, DT 35791",
    status: "Active",
  },
];

export function AppointmentsTable() {
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
          {appointments.map((appointment) => (
            <TableRow key={appointment.id}>
              <TableCell>{appointment.date}</TableCell>
              <TableCell>{appointment.time}</TableCell>
              <TableCell>{appointment.doctorName}</TableCell>
              <TableCell>{appointment.specialty}</TableCell>
              <TableCell>{appointment.address}</TableCell>
              <TableCell>
                <Badge
                  variant={
                    appointment.status === "Active" ? "default" : "secondary"
                  }
                >
                  {appointment.status}
                </Badge>
              </TableCell>
              <TableCell>
                <Button size="sm" variant="default">
                  <PhoneIcon className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
