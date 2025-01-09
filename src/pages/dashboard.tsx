import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { PlusCircle } from "lucide-react";
import Stats from "@/components/stats";
import DraftReminder from "@/components/draft-reminder";
import AppointmentList from "@/components/appointment-list";

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

export const Dashboard: React.FC = () => {
  return (
    <div className="flex flex-col lg:flex-row lg:space-x-6">
      <div className="flex-grow lg:max-w-[calc(100%-320px)]">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-3xl font-bold tracking-tight">Citas medicas</h2>
          <Button>
            <PlusCircle className="mr-2 h-4 w-4" /> Nueva cita
          </Button>
        </div>
        <Tabs defaultValue="active" className="w-full">
          <TabsList>
            <TabsTrigger value="active">Activas</TabsTrigger>
            <TabsTrigger value="past">Pasadas</TabsTrigger>
          </TabsList>
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
};
