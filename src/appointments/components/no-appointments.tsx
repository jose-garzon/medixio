import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { CalendarHeart, CalendarOff } from "lucide-react";
import { Link } from "wouter";

interface NoAppointmentsProps {
  className?: string;
}

export function NoAppointments({ className }: NoAppointmentsProps) {
  return (
    <Card className={cn(className, "text-center")}>
      <CardHeader>
        <CardTitle className="text-lg text-muted-foreground">
          No hay citas medicas
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 flex flex-col items-center">
        <div className="flex justify-center">
          <CalendarOff className="w-12 h-12 text-muted-foreground" />
        </div>
        <p className="text-sm text-muted-foreground">
          Comienza creando tu primera cita médica.
        </p>
        <Link to="/citas/nueva" className="block mx-auto w-autoS">
          <Button>Crear cita</Button>
        </Link>
      </CardContent>
    </Card>
  );
}

export function NoDraftAppointments() {
  return (
    <>
      <div className="flex justify-center">
        <CalendarHeart className="w-12 h-12 text-muted-foreground mb-5" />
      </div>
      <p className="text-sm text-center text-muted-foreground">No hay citas</p>
    </>
  );
}
