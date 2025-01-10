export type AppointmentStatus = "Draft" | "Active" | "Outdated" | "Done";

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
