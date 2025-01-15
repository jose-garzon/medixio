import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerDescription,
  DrawerFooter,
} from "@/components/ui/drawer";
import { Button } from "@/components/ui/button";
import { CalendarIcon, ClockIcon, FileTextIcon, MapPin } from "lucide-react";
import { Appointment } from "@/appointments/types";
import { StatusBadge } from "../../components/status-badge";
import { formatDate } from "@/lib/dates";
import { DaysToDate } from "../../components/DaysToDate";

interface AppointmentDrawerProps {
  appointment: Appointment | null;
  onClose: () => void;
}

export function AppointmentDrawer({
  appointment,
  onClose,
}: AppointmentDrawerProps) {
  if (!appointment) return null;

  const appointmentDate = new Date(appointment.date);
  return (
    <Drawer open={Boolean(appointment)} onClose={onClose}>
      <DrawerContent>
        <div className="mx-auto w-full max-w-sm">
          <DrawerHeader className="flex justify-between items-center">
            <div>
              <DrawerTitle className="text-2xl font-bold">
                {appointment.doctorName}
              </DrawerTitle>
              <DrawerDescription>{appointment.specialty}</DrawerDescription>
            </div>
            <StatusBadge status={appointment.status} />
          </DrawerHeader>
          <div className="p-4 pb-0 space-y-4">
            <div className="flex  justify-between">
              <div>
                <div className="flex items-center space-x-2 text-lg">
                  <CalendarIcon className="text-primary" />
                  <span className="font-medium">
                    {formatDate(appointmentDate)}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <ClockIcon className="text-primary" />
                  <span>{appointment.time}</span>
                </div>
              </div>
              <DaysToDate appointmentDate={appointmentDate} />
            </div>
            <div className="flex items-center space-x-2">
              <MapPin className="text-primary" />
              <span>{appointment.address}</span>
            </div>
            {appointment.notes && (
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <FileTextIcon className="text-primary" />
                  <span className="font-medium">Notas</span>
                </div>
                <p className="text-sm text-muted-foreground">
                  {appointment.notes}
                </p>
              </div>
            )}
          </div>
          <DrawerFooter>
            <Button onClick={onClose}>Cerrar</Button>
          </DrawerFooter>
        </div>
      </DrawerContent>
    </Drawer>
  );
}