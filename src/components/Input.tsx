import { Input } from "./ui/input";
import { Label } from "./ui/label";

interface InputFieldProps {
  id: string;
  label: string;
  placeholder: string;
  onChange: React.ChangeEventHandler<HTMLInputElement>;
  value: string | number | readonly string[] | undefined;
}

export const InputField = ({
  id,
  label,
  placeholder,
  onChange,
  value,
}: InputFieldProps) => {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        placeholder={placeholder}
        onChange={onChange}
        value={value}
      />
    </div>
  );
};
