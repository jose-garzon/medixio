import { Appointment } from "../appointments/types";
import { generateId } from "./manageIds";

const appointmentsStorage: Appointment[] = [
  {
    id: "1",
    doctorName: "Dr. John Doe",
    specialty: "Cardiologist",
    date: "2025-06-15",
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
    date: "2025-02-20",
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
    date: "2025-01-20",
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
    date: "2025-05-10",
    time: "11:30 AM",
    status: "Done",
    address: "Clinica san diego",
    phoneNumber: "+57 3004486873",
    notes: "Llevar examenes",
  },
];

export function getAppointments(filter: "active" | "past") {
  return appointmentsStorage.filter((appointment) =>
    filter === "active"
      ? ["Active", "Draft"].includes(appointment.status)
      : ["Done", "Outdated"].includes(appointment.status)
  );
}

export function createAppointment(appointment: Omit<Appointment, "id">) {
  const newAppointment: Appointment = { id: generateId(), ...appointment };
  appointmentsStorage.push(newAppointment);
}

export function getAppointment(id: string) {
  return appointmentsStorage.find((a) => a.id === id);
}
