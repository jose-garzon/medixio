export type AppointmentStatus = "Draft" | "Active" | "Outdated" | "Done";

export interface Appointment {
  id: string;
  doctorName: string;
  specialty: string;
  date: Date;
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
  addess: string;
  phoneNumber: string;
  notes: string;
}
