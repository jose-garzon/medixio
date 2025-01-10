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
import { TextAreaField } from "@/components/forms/textarea.field";

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
      addess: "",
      phoneNumber: "",
      notes: "",
    },
  });
  return (
    <div className="flex justify-center">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Crear nueva cita</CardTitle>
          <CardDescription>
            Rellena los detalles de tu nueva cita
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
              <InputField
                control={form.control}
                name="addess"
                label="Dirección"
                placeholder="Ingresa la dirección de la clínica"
              />
              <InputField
                control={form.control}
                name="phoneNumber"
                label="Número de Whatsapp"
                placeholder="Ingresa su número de Whatsapp"
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

              <TextAreaField
                control={form.control}
                name="notes"
                label="Notas"
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
