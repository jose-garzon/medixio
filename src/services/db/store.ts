import {
  Appointment,
  CreateAppointmentVariables,
  GetAppointmentVariables,
} from "../../appointments/types";
import { indexedDB } from "./indexedDB";

const storage = indexedDB("appointments");

export async function getAppointments(
  filter: GetAppointmentVariables
): Promise<Appointment[]> {
  return await storage.get<Appointment>(filter);
}

export async function createAppointment(
  appointment: CreateAppointmentVariables
): Promise<Appointment> {
  const newApointment = await storage.create(appointment);
  return newApointment;
}

export async function getAppointment(id: string) {
  return storage.get({ id });
}
