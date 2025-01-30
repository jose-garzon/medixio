import { AlertCircle, BellIcon } from "lucide-react";
import { useEffect, useState } from "react";
import {
  checkNotificationPermissions,
  requestNotificationPermission,
} from "../services/pushNotifications";

export function NotificationPermissionBanner() {
  const [status, setStatus] = useState<
    "denied" | "granted" | "prompt" | "notSupported" | null
  >(null);
  async function validatePermission() {
    await checkNotificationPermissions({
      subscribe: setStatus,
    });
  }
  async function requestPermission() {
    if (status !== "granted" && status !== "notSupported") {
      requestNotificationPermission();
    }
  }
  useEffect(() => {
    validatePermission();
  }, [status]);

  if (status === "granted" || status === null) return;
  if (status === "notSupported")
    return (
      <div
        role="alert"
        className="bg-destructive flex items-center gap-4 px-4 py-4"
      >
        <AlertCircle className="w-4 h-4 text-white shrink-0" />
        <div>
          <p className="text-white text-sm font-bold">
            Tu navegador no soporta las notificaciones.
          </p>
        </div>
      </div>
    );

  return (
    <div
      role="alert"
      className="bg-muted flex cursor-pointer gap-4 px-4 py-2"
      onClick={requestPermission}
    >
      <BellIcon className="w-5 h-5  shrink-0 mt-1" />
      <div>
        <p className=" text-sm">
          <strong>Activa las notificaciones:</strong> haz click y recibe
          recordatorios de tus citas médicas a tiempo
        </p>
      </div>
    </div>
  );
}
