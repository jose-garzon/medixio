import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { PlusCircle } from "lucide-react";
import Stats from "@/appointments/components/stats";
import DraftReminder from "@/appointments/components/draft-reminder";
import AppointmentList from "@/appointments/components/appointment-list";
import { Link } from "wouter";

const dashboardData = {
  totalAppointments: 15,
  upcomingAppointments: 5,
  missedAppointments: 2,
  draftAppointments: [
    {
      id: "1",
      doctorName: "Dr. Jane Smith",
      specialty: "Neurologist",
      date: null,
    },
    {
      id: "2",
      doctorName: "Dr. Mike Johnson",
      specialty: "Oncologist",
      date: "2023-07-15",
    },
  ],
};

export function Dashboard() {
  return (
    <div className="flex flex-col lg:flex-row lg:space-x-6">
      <div className="flex-grow lg:max-w-[calc(100%-320px)]">
        <div className="flex justify-between  gap-4 items-center mb-6">
          <h2 className="text-3xl font-bold tracking-tight">Citas medicas</h2>
          <Link to="/citas/nueva">
            <Button size="sm">
              <PlusCircle className="mr-2 h-2 w-2" /> Nueva cita
            </Button>
          </Link>
        </div>
        <Tabs defaultValue="active" className="w-full">
          <div className="flex justify-between items-center mb-4">
            <TabsList>
              <TabsTrigger value="active">Activas</TabsTrigger>
              <TabsTrigger value="past">Pasadas</TabsTrigger>
            </TabsList>
            <Link to="/citas">
              <Button variant="ghost" size="sm">
                Ver todas las citas
              </Button>
            </Link>
          </div>
          <TabsContent value="active">
            <AppointmentList type="active" />
          </TabsContent>
          <TabsContent value="past">
            <AppointmentList type="past" />
          </TabsContent>
        </Tabs>
      </div>
      <div className="lg:w-80 mt-6 lg:mt-0">
        <div className="lg:sticky lg:top-4 space-y-6">
          <Stats
            totalAppointments={dashboardData.totalAppointments}
            upcomingAppointments={dashboardData.upcomingAppointments}
            missedAppointments={dashboardData.missedAppointments}
          />
          <DraftReminder draftAppointments={dashboardData.draftAppointments} />
        </div>
      </div>
    </div>
  );
}
