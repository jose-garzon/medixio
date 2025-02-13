import { Route, Switch, Router, Link } from "wouter";
import { Dashboard } from "./pages/dashboard";
import { CreateAppointment } from "./pages/create-appointment";
import { AppointmentsTable } from "./pages/appointment-table";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "./components/ui/toaster";
import { NotificationPermissionBanner } from "./notifications/components/notification-permissions-alert";

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="flex flex-col min-h-screen">
        <header className="px-4 md:px-12 bg-primary text-primary-foreground py-4 flex items-center">
          <img src="/logo-dark.svg" alt="Medixio" className="h-12" />
          <Link to="/" className="container px-4">
            <h1 className="text-2xl font-bold">Medixio</h1>
          </Link>
        </header>
        <NotificationPermissionBanner />
        <main className="flex-grow container mx-auto px-4 py-8">
          <Router>
            <Switch>
              <Route path="/" component={Dashboard} />
              <Route path="/citas" component={AppointmentsTable} />
              <Route path="/citas/nueva" component={CreateAppointment} />
            </Switch>
          </Router>
        </main>
      </div>
      <Toaster />
    </QueryClientProvider>
  );
}

export default App;
