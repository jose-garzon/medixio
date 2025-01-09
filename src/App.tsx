import { Route, Switch, Router } from "wouter";
import { Dashboard } from "./pages/dashboard";
import { CreateAppointment } from "./pages/create-appointment";

function App() {
  return (
    <div className="flex flex-col min-h-screen">
      <header className="bg-primary text-primary-foreground py-4">
        <div className="container mx-auto px-4">
          <h1 className="text-2xl font-bold">Medixio</h1>
        </div>
      </header>
      <main className="flex-grow container mx-auto px-4 py-8">
        <Router>
          <Switch>
            <Route path="/" component={Dashboard} />
            <Route path="/citas/nueva" component={CreateAppointment} />
          </Switch>
        </Router>
      </main>
    </div>
  );
}

export default App;