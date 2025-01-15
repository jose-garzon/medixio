import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface AppointmentListLoaderProps {
  count?: number;
  isLoading: boolean;
  children: React.ReactNode;
}
export function AppointmentListLoader({
  count = 3,
  isLoading,
  children,
}: AppointmentListLoaderProps) {
  if (isLoading)
    return (
      <>
        {Array.from({ length: count }).map((_, index) => (
          <Card key={index} className="animate-pulse">
            <CardHeader>
              <Skeleton className="h-6 w-1/2 mb-2" />
              <Skeleton className="h-4 w-1/3" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-5 w-full mb-2" />
              <Skeleton className="h-5 w-2/3" />
            </CardContent>
            <CardFooter className="flex gap-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </CardFooter>
          </Card>
        ))}
      </>
    );
  return children;
}
