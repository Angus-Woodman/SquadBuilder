import { Routes, Route } from "react-router-dom";
import "./App.css";

import { LandingPage } from "./components/LandingPage";
import { BuilderPage } from "./components/BuilderPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/builder" element={<BuilderPage />} />
    </Routes>
  );
}
