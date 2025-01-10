import { format, differenceInDays } from "date-fns";
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerDescription,
  DrawerFooter,
} from "@/components/ui/drawer";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CalendarIcon, ClockIcon, FileTextIcon, MapPin } from "lucide-react";
import { Appointment } from "@/services/appointments/types";

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
  const daysLeft = differenceInDays(appointmentDate, new Date());

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
            <Badge
              variant={
                appointment.status === "Active" ? "default" : "secondary"
              }
              className="px-3 py-1"
            >
              {appointment.status}
            </Badge>
          </DrawerHeader>
          <div className="p-4 pb-0 space-y-4">
            <div className="flex  justify-between">
              <div>
                <div className="flex items-center space-x-2 text-lg">
                  <CalendarIcon className="text-primary" />
                  <span className="font-medium">
                    {format(appointmentDate, "MMMM d, yyyy")}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <ClockIcon className="text-primary" />
                  <span>{appointment.time}</span>
                </div>
              </div>
              <span className="text-lg font-semibold">
                {daysLeft > 0 ? `En ${daysLeft} days` : "Hoy"}
              </span>
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
