import {
  Appointment,
  CreateAppointmentVariables,
  GetAppointmentVariables,
  UpdateAppointmentVariables,
} from "../../appointments/types";
import { indexedDB } from "./indexedDB";

const storage = indexedDB("appointments");

export async function getAppointments(
  filter?: GetAppointmentVariables
): Promise<Appointment[]> {
  return await storage.get<Appointment>(filter);
}

export async function createAppointment(
  appointment: CreateAppointmentVariables
): Promise<Appointment> {
  const newApointment = await storage.create(appointment);
  return newApointment;
}

export async function updateAppointment({
  id,
  appointment,
}: {
  id: string;
  appointment: UpdateAppointmentVariables;
}): Promise<Partial<Appointment>> {
  const updatedApointment = await storage.update(id, appointment);
  return updatedApointment;
}

export async function getAppointment(id: string) {
  return storage.get({ id });
}
