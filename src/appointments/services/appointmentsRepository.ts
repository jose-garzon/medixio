import { indexedDB } from "@/services/db/indexedDB";
import {
  Appointment,
  AppointmentsAPI,
  CreateAppointmentVariables,
  GetAppointmentVariables,
  UpdateAppointmentVariables,
} from "../domain";

const storage = indexedDB("appointments");

export async function getAppointments(
  filter?: GetAppointmentVariables
): Promise<Appointment[]> {
  return await storage.get<Appointment>(filter);
}

export async function getAppointment(id: string): Promise<Appointment> {
  const results = await storage.get<Appointment>({ id });
  return results[0];
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
}): Promise<Appointment> {
  const updatedApointment = await storage.update(id, appointment);
  return updatedApointment as Appointment;
}

export async function deleteAppointment(id: string): Promise<string> {
  return storage.destroy(id);
}

export const appointmentRepository: AppointmentsAPI = {
  getAppointments,
  getAppointment,
  createAppointment,
  updateAppointment,
  deleteAppointment,
};
