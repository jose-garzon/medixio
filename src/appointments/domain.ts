import { z } from "zod";

export type AppointmentStatus = "draft" | "active" | "lost" | "done";

export interface Appointment {
  id: string;
  doctorName: string;
  specialty: string;
  date: string;
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

export type CreateAppointmentVariables = Omit<Appointment, "id" | "time">;
export type UpdateAppointmentVariables = Partial<Appointment>;

export const createAppointmentSchema = z
  .object({
    doctorName: z.string().nonempty("Campo requerido"),
    specialty: z.string().nonempty("Campo requerido"),
    phoneNumber: z
      .string()
      .nonempty("Campo requerido")
      .regex(
        /^\+\d{1,3}\d{7,}$/i,
        "Número de teléfono inválido. Usa el formato internacional (+573002346892)"
      ),
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

export type QuickScheduleVariables = Pick<
  CreateAppointmentFormSchema,
  "date" | "time"
>;

export const scheduleSchema = z.object({
  date: z.date({ required_error: "Campo requerido" }),
  time: z.string().nonempty("Campo requerido"),
});

// SERVICE
export interface AppointmentsAPI {
  getAppointments: (filter?: GetAppointmentVariables) => Promise<Appointment[]>;
  getAppointment: (id: string) => Promise<Appointment>;
  createAppointment: (
    appointment: CreateAppointmentVariables
  ) => Promise<Appointment>;
  updateAppointment: (params: {
    id: string;
    appointment: UpdateAppointmentVariables;
  }) => Promise<Appointment>;
  deleteAppointment: (id: string) => Promise<string>;
}
