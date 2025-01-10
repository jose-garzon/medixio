import { Clock } from "lucide-react";
import {
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "../ui/form";
import { Control, FieldValues, Path } from "react-hook-form";
import { Combobox } from "../combobox";

interface TimeFieldProps<T extends FieldValues> {
  control: Control<T>;
  name: Path<T>;
  label: string;
  description?: string;
}

export const TimeField = <T extends FieldValues>({
  control,
  name,
  label,
  description,
}: TimeFieldProps<T>) => {
  // Generate hours in 12-hour format (1-12)
  const hours = Array.from({ length: 12 }, (_, i) => ({
    value: (i + 1).toString().padStart(2, "0"),
    label: (i + 1).toString().padStart(2, "0"),
  }));

  // Generate minutes in 15-minute increments
  const minutes = Array.from({ length: 4 }, (_, i) => ({
    value: (i * 15).toString().padStart(2, "0"),
    label: (i * 15).toString().padStart(2, "0"),
  }));

  // AM/PM options
  const periods = [
    { value: "AM", label: "AM" },
    { value: "PM", label: "PM" },
  ];

  const convertTo24Hour = (hour: string, minute: string, period: string) => {
    console.log({ hour, minute, period });
    let h = parseInt(hour);
    if (period === "PM" && h !== 12) h += 12;
    if (period === "AM" && h === 12) h = 0;
    return `${h.toString().padStart(2, "0")}:${minute}`;
  };

  const convertTo12Hour = (value: string) => {
    if (!value) return { hour: "12", minute: "00", period: "AM" };

    const [h, m] = value?.split(":") || ["12", "00"];
    let hour = parseInt(h);
    let period = "AM";

    if (hour >= 12) {
      period = "PM";
      if (hour > 12) hour -= 12;
    }
    if (hour === 0) hour = 12;

    return {
      hour: hour.toString().padStart(2, "0"),
      minute: m,
      period,
    };
  };

  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => {
        const { hour, minute, period } = convertTo12Hour(field.value);

        return (
          <FormItem className="flex flex-col">
            <FormLabel>{label}</FormLabel>
            <div className="flex gap-2 items-center">
              {/* Hours Combobox */}
              <Combobox
                id="hours"
                icon={Clock}
                value={field.value}
                onChange={(value) =>
                  field.onChange(convertTo24Hour(value, minute, period))
                }
                options={hours}
                emptyMessage="No se encontró la hora."
                placeholder={hour}
                sarchPlaceholder="Buscar hora..."
              />

              <span className="text-xl">:</span>

              {/* Minutes Combobox */}
              <Combobox
                id="minutes"
                value={field.value}
                onChange={(value) =>
                  field.onChange(convertTo24Hour(hour, value, period))
                }
                options={minutes}
                emptyMessage="No se encontraron los minutos."
                placeholder={minute}
                sarchPlaceholder="Buscar minutos..."
              />

              {/* AM/PM Combobox */}
              <Combobox
                id="periods"
                value={field.value}
                onChange={(value) =>
                  field.onChange(convertTo24Hour(hour, minute, value))
                }
                options={periods}
                placeholder={period}
                searchable={false}
              />
            </div>
            {description && <FormDescription>{description}</FormDescription>}
            <FormMessage />
          </FormItem>
        );
      }}
    />
  );
};
