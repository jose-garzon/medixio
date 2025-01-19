export async function requestNotificationPermission() {
  if ("permissions" in navigator) {
    await Notification.requestPermission();
  }
}

export async function checkNotificationPermissions({
  subscribe,
}: {
  subscribe: (
    status: "granted" | "denied" | "prompt" | "notSupported" | null
  ) => void;
}) {
  if ("permissions" in navigator) {
    const status = await navigator.permissions.query({ name: "notifications" });
    subscribe(status.state);
    status.onchange = () => {
      subscribe(status.state);
    };
  } else {
    subscribe("notSupported");
  }
}
