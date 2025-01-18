import {
  Appointment,
  CreateAppointmentVariables,
  GetAppointmentVariables,
} from "../../appointments/types";
import { generateId } from "./manageIds";

const appointmentsStorage: Appointment[] = [
  {
    id: "1",
    doctorName: "Dr. John Doe",
    specialty: "Cardiologist",
    date: "2025-06-15",
    time: "10:00",
    status: "active",
    address: "Clinica san diego",
    phoneNumber: "+57 3004486873",
    notes: "Llevar examenes",
  },
  {
    id: "2",
    doctorName: "Dr. Jane Smith",
    specialty: "Neurologist",
    date: "2025-02-20",
    time: "14:00",
    status: "draft",
    address: "Clinica san diego",
    phoneNumber: "+57 3004486873",
    notes: "Llevar examenes",
  },
  {
    id: "3",
    doctorName: "Dr. Saibi",
    specialty: "Reumatologo",
    date: "2025-01-20",
    time: "14:00",
    status: "active",
    address: "Clinica Foscal",
    phoneNumber: "+57 3004486873",
    notes: "Llevar examenes",
  },
  {
    id: "4",
    doctorName: "Dr. Mike Johnson",
    specialty: "Oncologist",
    date: "2025-05-10",
    time: "11:30",
    status: "done",
    address: "Clinica san diego",
    phoneNumber: "+57 3004486873",
    notes: "Llevar examenes",
  },
];

export async function getAppointments(
  filter: GetAppointmentVariables
): Promise<Appointment[]> {
  return new Promise((resolve) => {
    setTimeout(() => {
      const filteredAppointments = appointmentsStorage.filter((appointment) =>
        Array.isArray(filter.status)
          ? filter.status.includes(appointment.status)
          : appointment.status === filter.status
      );
      resolve(filteredAppointments);
    }, 1000);
  });
}

export function createAppointment(
  appointment: CreateAppointmentVariables
): Promise<Appointment> {
  const newAppointment: Appointment = { id: generateId(), ...appointment };
  return new Promise((resolve) => {
    setTimeout(() => {
      appointmentsStorage.push(newAppointment);
      resolve(newAppointment);
    }, 1000);
  });
}

export function getAppointment(id: string) {
  return appointmentsStorage.find((a) => a.id === id);
}
