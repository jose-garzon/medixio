import { Button } from "@/components/ui/button";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Form } from "@/components/ui/form";
import { InputField } from "@/components/forms/input-field";
import { DatePickerField } from "@/components/forms/datepicker-field";
import { SwitchField } from "@/components/forms/switch-field";
import { useForm } from "react-hook-form";
import { TimeField } from "@/components/forms/time-field";

const onSubmit = (data: unknown) => {
  console.log(data);
};

export const CreateAppointment: React.FC = () => {
  const form = useForm({
    defaultValues: {
      doctorName: "",
      specialty: "",
      date: new Date(),
      time: "",
      isActive: false,
    },
  });
  return (
    <div className="flex justify-center">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Create New Appointment</CardTitle>
          <CardDescription>
            Fill in the details for your new appointment
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <InputField
                control={form.control}
                name="doctorName"
                label="Nombre del doctor"
                placeholder="Ingresa el nombre de tu doctor"
              />
              <InputField
                control={form.control}
                name="specialty"
                label="Especialidad"
                placeholder="Ingresa su especialidad"
              />

              <DatePickerField
                control={form.control}
                name="date"
                label="Fecha"
              />

              <TimeField control={form.control} label="Hora" name="time" />

              <SwitchField
                control={form.control}
                name="isActive"
                label="Cita agendada"
                description="Selecciona si ya agendaste la cita."
              />

              <Button type="submit" className="w-full">
                Crear cita
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
};
