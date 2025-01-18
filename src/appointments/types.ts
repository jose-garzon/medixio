import { z } from "zod";

export type AppointmentStatus = "draft" | "active" | "lost" | "done";

export interface Appointment {
  id: string;
  doctorName: string;
  specialty: string;
  date: string;
  time: string;
  status: AppointmentStatus;
  address: string;
  phoneNumber: string;
  notes?: string;
}

export interface CreateAppointmentFormSchema {
  doctorName: string;
  specialty: string;
  date: Date;
  time: string;
  isActive: boolean;
  address: string;
  phoneNumber: string;
  notes: string;
}

export type GetAppointmentVariables = {
  status: AppointmentStatus | AppointmentStatus[];
};

export type CreateAppointmentVariables = Omit<Appointment, "id">;

export const createAppointmentSchema = z
  .object({
    doctorName: z.string().nonempty("Campo requerido"),
    specialty: z.string().nonempty("Campo requerido"),
    phoneNumber: z.string().nonempty("Campo requerido"),
    address: z.string().nonempty("Campo requerido"),
    isActive: z.boolean(),
    date: z.date().optional(),
    time: z.string().optional(),
    notes: z.string().optional(),
  })
  .superRefine((data, ctx) => {
    if (data.isActive) {
      if (!data.date) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["date"],
          message: "Fecha es requerida cuando la cita está agendada",
        });
      }
      if (!data.time) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["time"],
          message: "Hora es requerida cuando la cita está agendada",
        });
      }
    }
  });
