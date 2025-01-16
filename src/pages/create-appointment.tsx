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
import { CreateAppointmentFormSchema } from "@/appointments/types";
import { useCreateNewAppointment } from "@/appointments/services/useCreateAppointment";
import { useLocation } from "wouter";
import { ButtonLoader } from "@/components/ButtonLoader";

export function CreateAppointment() {
  const [, navigate] = useLocation();
  const form = useForm<CreateAppointmentFormSchema>({
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
  const createNewAppointment = useCreateNewAppointment();

  const onSubmit = (data: CreateAppointmentFormSchema) => {
    createNewAppointment.mutate(
      {
        address: data.addess,
        doctorName: data.doctorName,
        notes: data.notes,
        phoneNumber: data.phoneNumber,
        specialty: data.specialty,
        time: data.time,
        date: data.date.toString(),
        status: data.isActive ? "Active" : "Draft",
      },
      {
        onSuccess: () => {
          navigate("/");
        },
      }
    );
  };

  return (
    <div className="flex justify-center">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>Crear nueva cita</CardTitle>
          <CardDescription>
            Rellena los detalles de tu nueva cita
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(onSubmit)}
              className="grid space-6 gap-6 grid-cols-1 md:grid-cols-2"
            >
              <InputField
                className="md:col-span-2"
                control={form.control}
                name="doctorName"
                label="Nombre del doctor"
                placeholder="Nombre de tu doctor"
              />
              <InputField
                control={form.control}
                name="specialty"
                label="Especialidad"
                placeholder="Especialidad del doctor"
              />
              <InputField
                control={form.control}
                name="addess"
                label="Dirección"
                placeholder="Dirección de la clínica"
              />

              <DatePickerField
                control={form.control}
                name="date"
                label="Fecha"
              />
              <TimeField control={form.control} label="Hora" name="time" />
              <InputField
                control={form.control}
                name="phoneNumber"
                label="Número de Whatsapp"
                placeholder="Número para agendar citas"
                description="Agrega el codigo de pais +57"
              />
              <SwitchField
                control={form.control}
                name="isActive"
                label="Cita agendada"
                description="Selecciona si ya agendaste la cita."
              />

              <TextAreaField
                className="md:col-span-2"
                control={form.control}
                name="notes"
                label="Notas"
              />

              <ButtonLoader
                isLoading={createNewAppointment.isPending}
                type="submit"
                className="w-full md:col-span-2"
              >
                Crear cita
              </ButtonLoader>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
