import { Loader2 } from "lucide-react";

import { Button, ButtonProps } from "@/components/ui/button";

interface ButtonLoaderProps extends ButtonProps {
  isLoading: boolean;
  children: React.ReactNode;
}

export function ButtonLoader({
  isLoading,
  children,
  ...rest
}: ButtonLoaderProps) {
  return (
    <Button disabled={isLoading} {...rest}>
      {isLoading && <Loader2 className="animate-spin" />}
      {children}
    </Button>
  );
}
