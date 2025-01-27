import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { QuickScheduleVariables, scheduleSchema } from "../types";
import { useForm } from "react-hook-form";
import { Form } from "@/components/ui/form";
import { DatePickerField } from "@/components/forms/datepicker-field";
import { TimeField } from "@/components/forms/time-field";
import { CalendarPlus } from "lucide-react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { useUpdateAppointment } from "../services/useUpdateAppointment";
import { ButtonLoader } from "@/components/ButtonLoader";

interface QuickScheduleProps {
  id: string;
  variant?: "icon" | "text";
  onScheduleSuccess?: () => void;
}

export function QuickSchedule({
  id,
  variant = "text",
  onScheduleSuccess,
}: QuickScheduleProps) {
  const form = useForm<QuickScheduleVariables>({
    defaultValues: {
      date: undefined,
      time: "",
    },
    resolver: zodResolver(scheduleSchema),
  });

  const { mutate, isPending } = useUpdateAppointment();
  const handleConfirm = (data: QuickScheduleVariables) => {
    mutate(
      {
        id,
        appointment: {
          time: data.time,
          date: data.date && data.date.toString(),
          status: "active",
        },
      },
      { onSuccess: onScheduleSuccess }
    );
  };

  return (
    <Popover>
      <PopoverTrigger asChild>
        {variant === "icon" ? (
          <Button size="icon">
            <CalendarPlus />
          </Button>
        ) : (
          <Button size="sm" variant="secondary">
            Agendar
          </Button>
        )}
      </PopoverTrigger>
      <PopoverContent className="w-64 space-y-4">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleConfirm)}>
            <DatePickerField
              control={form.control}
              name="date"
              label="Fecha"
              placeholder="Fecha de la cita"
            />
            <TimeField control={form.control} label="Hora" name="time" />
            <ButtonLoader className="w-full mt-4" isLoading={isPending}>
              Confirmar
            </ButtonLoader>
          </form>
        </Form>
      </PopoverContent>
    </Popover>
  );
}
